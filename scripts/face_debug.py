"""One-off face similarity debugging script.

Runs the test plan against test_imgs/images.webp and the stored
contact_face_embeddings table. Prints results to stdout — no DB writes
except the optional pipeline-version stamp.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# import the pipeline under test
from utils.face_embeddings import (
    _preprocess,
    _normalize,
    extract_single_embedding,
    extract_embedding_for_profile,
    detect_faces,
    EMBED_DIM,
)


TEST_IMG = ROOT / "test_imgs" / "images.webp"
PIPELINE_VERSION = "mtcnn-standalone-arcface512-noalign-conf95-v5"


def cos_sim(a, b) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def best_match(db, emb: list[float]) -> tuple[int | None, float, list[tuple[int, float]]]:
    emb_str = "[" + ",".join(f"{x:.8f}" for x in emb) + "]"
    rows = db.execute(text("""
        SELECT contact_id,
               1 - (embedding <=> CAST(:emb AS vector)) AS similarity
        FROM contact_face_embeddings
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 5
    """), {"emb": emb_str}).fetchall()
    if not rows:
        return None, 0.0, []
    top = [(int(r.contact_id), float(r.similarity)) for r in rows]
    return top[0][0], top[0][1], top


def variant_embed(img_array: np.ndarray, *, clahe: bool, align: bool, normalize: bool) -> list[float]:
    """A flexible _embed used to ablate each preprocessing step."""
    from deepface import DeepFace
    img = img_array.copy()
    # mimic _preprocess upscale, then optionally CLAHE
    h, w = img.shape[:2]
    MIN_DIM = 320
    if min(h, w) < MIN_DIM:
        scale = MIN_DIM / min(h, w)
        img = np.array(Image.fromarray(img).resize(
            (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS))
    if clahe:
        try:
            import cv2
            lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
            cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            lab[:, :, 0] = cl.apply(lab[:, :, 0])
            img = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        except Exception:
            pass
    reps = DeepFace.represent(
        img,
        model_name="ArcFace",
        detector_backend="mtcnn",
        enforce_detection=False,
        align=align,
    )
    if not reps:
        raise ValueError("no face")
    best = max(reps, key=lambda r: r.get("facial_area", {}).get("w", 0)
                                 * r.get("facial_area", {}).get("h", 0))
    emb = best["embedding"]
    if normalize:
        emb = _normalize(emb)
    return emb


def main() -> None:
    print("=" * 70)
    print("FACE SIMILARITY DEBUG  —  test image:", TEST_IMG)
    print("=" * 70)

    if not TEST_IMG.exists():
        print(f"!! Test image not found: {TEST_IMG}")
        sys.exit(2)

    image_bytes = TEST_IMG.read_bytes()

    # DB
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    db = Session()

    # ── Test 4: stale index ──────────────────────────────────────────────
    print("\n[Test 4] Stale-index check")
    try:
        row = db.execute(text(
            "SELECT value FROM face_pipeline_meta WHERE key = 'pipeline_version'"
        )).first()
        stored = row[0] if row else None
        print(f"  stored pipeline_version  = {stored!r}")
        print(f"  current PIPELINE_VERSION = {PIPELINE_VERSION!r}")
        print(f"  index_stale              = {stored != PIPELINE_VERSION}")
    except Exception as e:
        print(f"  (could not read face_pipeline_meta: {e})")

    cnt = db.execute(text("SELECT COUNT(*) FROM contact_face_embeddings")).scalar()
    print(f"  contact_face_embeddings rows = {cnt}")

    # ── Test 1: determinism ──────────────────────────────────────────────
    print("\n[Test 1] Determinism — extract_single_embedding × 10")
    first5_runs = []
    full_runs = []
    for i in range(10):
        emb, n_faces = extract_single_embedding(image_bytes)
        if emb is None:
            print(f"  run {i}: NO embedding (faces detected = {n_faces})")
            continue
        first5 = [round(x, 6) for x in emb[:5]]
        first5_runs.append(first5)
        full_runs.append(np.asarray(emb))
        print(f"  run {i}: faces={n_faces}  first5={first5}")
    if len(full_runs) >= 2:
        sims = [cos_sim(full_runs[0], full_runs[i]) for i in range(1, len(full_runs))]
        print(f"  cos-sim of run 0 vs runs 1..{len(full_runs)-1}: "
              f"min={min(sims):.6f}  max={max(sims):.6f}")
        all_same = all(r == first5_runs[0] for r in first5_runs)
        if all_same and min(sims) > 0.9999:
            print("  PASS: embeddings deterministic")
        else:
            print("  WARN: embeddings NOT deterministic")

    # ── Test 5: code-path comparison (no execution needed, but verify) ──
    print("\n[Test 5] Code-path: extract_single_embedding vs extract_embedding_for_profile")
    img_array = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
    emb_search = extract_single_embedding(image_bytes)[0]
    emb_profile = extract_embedding_for_profile(image_bytes)
    if emb_search and emb_profile:
        s = cos_sim(emb_search, emb_profile)
        print(f"  cos-sim(search-path, profile-path) = {s:.6f}  (expected ~1.0)")

    # ── Test 3: ablation against DB ──────────────────────────────────────
    print("\n[Test 3] Ablation — find best stored match for each variant")
    variants = [
        ("current  (CLAHE on,  align T, norm T)", dict(clahe=True,  align=True,  normalize=True)),
        ("no_clahe (CLAHE off, align T, norm T)", dict(clahe=False, align=True,  normalize=True)),
        ("no_norm  (CLAHE on,  align T, norm F)", dict(clahe=True,  align=True,  normalize=False)),
        ("no_align (CLAHE on,  align F, norm T)", dict(clahe=True,  align=False, normalize=True)),
        ("clean    (CLAHE off, align T, norm F)", dict(clahe=False, align=True,  normalize=False)),
    ]
    results = []
    for name, kw in variants:
        try:
            emb = variant_embed(img_array, **kw)
            cid, sim, top = best_match(db, emb)
            print(f"  {name}: best_contact={cid}  sim={sim:.4f}  top5={[(c, round(s,4)) for c,s in top]}")
            results.append((name, cid, sim))
        except Exception as e:
            print(f"  {name}: ERROR {e}")
    if results:
        winner = max(results, key=lambda r: r[2])
        print(f"\n  WINNER: {winner[0]}  (sim={winner[2]:.4f})")

    db.close()


if __name__ == "__main__":
    main()

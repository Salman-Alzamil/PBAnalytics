"""Test whether CLAHE preprocessing is what causes DeepFace's internal
MTCNN to reject otherwise-valid faces.
"""
from __future__ import annotations

import os, sys
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

from utils.face_embeddings import _preprocess, _normalize  # noqa: E402

MIN_DIM = 320


def upscale_only(img):
    h, w = img.shape[:2]
    if min(h, w) < MIN_DIM:
        s = MIN_DIM / min(h, w)
        img = np.array(Image.fromarray(img).resize(
            (max(1, int(w*s)), max(1, int(h*s))), Image.LANCZOS))
    return img


def cos(a, b) -> float:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def represent(img, *, enforce: bool):
    from deepface import DeepFace
    return DeepFace.represent(
        img, model_name="ArcFace", detector_backend="mtcnn",
        enforce_detection=enforce, align=True,
    )


def main():
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    db = Session()

    rows = db.execute(text("""
        SELECT c.id, c.first_name, ui.image_bytes
        FROM contacts c JOIN uploaded_images ui ON ui.id = c.profile_picture_id
        WHERE c.profile_picture_id IS NOT NULL
        ORDER BY c.id
    """)).fetchall()
    test_files = sorted((ROOT / "test_imgs").iterdir())

    samples: list[tuple[str, bytes]] = (
        [(f"contact_{r.id}_{r.first_name}", bytes(r.image_bytes)) for r in rows]
        + [(f"test_{f.name}", f.read_bytes()) for f in test_files]
    )

    print(f"{'sample':<46} | upscale+CLAHE | upscale only")
    print("-" * 80)
    for label, ib in samples:
        arr = np.array(Image.open(BytesIO(ib)).convert("RGB"))
        with_clahe = _preprocess(arr.copy())
        without_clahe = upscale_only(arr.copy())
        try:
            n_with = len(represent(with_clahe, enforce=True))
        except Exception:
            n_with = 0
        try:
            n_no = len(represent(without_clahe, enforce=True))
        except Exception:
            n_no = 0
        print(f"{label[:46]:<46} | {n_with:>13} | {n_no:>11}")

    print("\nNow re-test cross-sim with NO-CLAHE pipeline:")
    fresh = {}
    for r in rows:
        arr = np.array(Image.open(BytesIO(bytes(r.image_bytes))).convert("RGB"))
        try:
            reps = represent(upscale_only(arr), enforce=True)
            if reps:
                best = max(reps, key=lambda x: x["facial_area"]["w"]*x["facial_area"]["h"])
                fresh[(r.id, r.first_name)] = np.asarray(_normalize(best["embedding"]))
        except Exception as e:
            print(f"  contact {r.id}: rejected ({e.__class__.__name__})")

    print(f"  contacts with valid embeddings (no-CLAHE): {len(fresh)}")
    if not fresh:
        return

    header = " | ".join(f"c{cid}({fn[:6]})" for (cid, fn) in fresh)
    print(f"\n{'TEST IMG':<55} | {header}")
    print("-" * 100)
    for f in test_files:
        arr = np.array(Image.open(BytesIO(f.read_bytes())).convert("RGB"))
        try:
            reps = represent(upscale_only(arr), enforce=True)
            if not reps:
                print(f"{f.name[:55]:<55} | (no face)")
                continue
            best = max(reps, key=lambda x: x["facial_area"]["w"]*x["facial_area"]["h"])
            e = np.asarray(_normalize(best["embedding"]))
            sims = " | ".join(f"{cos(e, v):>10.4f}" for v in fresh.values())
            print(f"{f.name[:55]:<55} | {sims}")
        except Exception as ex:
            print(f"{f.name[:55]:<55} | ERROR {ex.__class__.__name__}")

    db.close()


if __name__ == "__main__":
    main()

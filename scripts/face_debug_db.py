"""Inspect what is actually stored in contact_face_embeddings."""
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

from utils.face_embeddings import extract_embedding_for_profile, _normalize


def parse_pgvector(s) -> np.ndarray:
    if isinstance(s, (list, tuple)):
        return np.asarray(s, dtype=np.float64)
    s = str(s).strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return np.asarray([float(x) for x in s.split(",") if x.strip()], dtype=np.float64)


def cos(a, b) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    db = Session()

    print("=" * 70)
    print("DB INSPECTION  —  contact_face_embeddings")
    print("=" * 70)

    rows = db.execute(text("""
        SELECT cfe.contact_id,
               c.first_name, c.last_name, c.profile_picture_id,
               cfe.embedding::text   AS emb_text,
               cfe.created_at
        FROM contact_face_embeddings cfe
        JOIN contacts c ON c.id = cfe.contact_id
        ORDER BY cfe.contact_id
    """)).fetchall()

    print(f"\nrows: {len(rows)}\n")
    stored = {}
    for r in rows:
        emb = parse_pgvector(r.emb_text)
        norm = float(np.linalg.norm(emb))
        nz = int(np.count_nonzero(emb))
        nan = int(np.isnan(emb).sum())
        first5 = [round(float(x), 6) for x in emb[:5]]
        print(f"  contact {r.contact_id} ({r.first_name} {r.last_name})")
        print(f"    pfp_id={r.profile_picture_id}  created_at={r.created_at}")
        print(f"    dim={emb.shape[0]}  ||v||={norm:.6f}  nonzero={nz}  nan={nan}")
        print(f"    first5={first5}")
        stored[int(r.contact_id)] = emb

    # Pairwise cos-sim of stored embeddings
    print("\n  Pairwise cos-sim of STORED embeddings:")
    ids = sorted(stored)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            print(f"    {a} <-> {b}: {cos(stored[a], stored[b]):.4f}")

    # Re-extract from each contact's stored profile picture and compare.
    print("\n  Re-extracting from each contact's stored UploadedImage and comparing:")
    img_rows = db.execute(text("""
        SELECT c.id AS contact_id, c.first_name, c.last_name,
               ui.id AS image_id, ui.image_bytes,
               octet_length(ui.image_bytes) AS image_size
        FROM contacts c
        JOIN uploaded_images ui ON ui.id = c.profile_picture_id
        WHERE c.profile_picture_id IS NOT NULL
        ORDER BY c.id
    """)).fetchall()
    print(f"  contacts with profile pictures: {len(img_rows)}")
    for r in img_rows:
        try:
            fresh = extract_embedding_for_profile(bytes(r.image_bytes))
        except Exception as e:
            print(f"    contact {r.contact_id}: re-extract ERROR {e}")
            continue
        if fresh is None:
            print(f"    contact {r.contact_id}: re-extract returned None (no face found)")
            continue
        fresh_arr = np.asarray(fresh, dtype=np.float64)
        if r.contact_id in stored:
            sim = cos(fresh_arr, stored[r.contact_id])
            tag = "MATCH" if sim > 0.99 else ("DIFF" if sim < 0.5 else "PARTIAL")
            print(f"    contact {r.contact_id} ({r.first_name}): "
                  f"fresh-vs-stored cos-sim = {sim:.4f}  [{tag}]  "
                  f"(image bytes={r.image_size})")
        else:
            print(f"    contact {r.contact_id}: no stored embedding to compare against")

    # And finally, compare the test image to the *fresh* re-extractions
    print("\n  Test image (test_imgs/images.webp) vs each contact's FRESH embedding:")
    img_path = ROOT / "test_imgs" / "images.webp"
    test_emb = extract_embedding_for_profile(img_path.read_bytes())
    if test_emb is None:
        print("    test image: no face found")
    else:
        test_arr = np.asarray(test_emb, dtype=np.float64)
        for r in img_rows:
            try:
                fresh = extract_embedding_for_profile(bytes(r.image_bytes))
            except Exception:
                continue
            if fresh is None:
                continue
            sim = cos(test_arr, np.asarray(fresh))
            print(f"    test vs contact {r.contact_id} ({r.first_name} {r.last_name}): {sim:.4f}")

    db.close()


if __name__ == "__main__":
    main()

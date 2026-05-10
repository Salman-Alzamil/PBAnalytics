"""Cross-compare every file in test_imgs/ against every stored contact, and
save the detected face crops as PNGs under scripts/_face_debug_out/ so they
can be eyeballed.
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

from utils.face_embeddings import (
    extract_embedding_for_profile,
    detect_faces,
)


OUT = ROOT / "scripts" / "_face_debug_out"
OUT.mkdir(exist_ok=True)


def cos(a, b) -> float:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def save_crops(label: str, image_bytes: bytes) -> None:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img.save(OUT / f"{label}__full.png")
    faces = detect_faces(image_bytes)
    arr = np.array(img)
    for i, f in enumerate(faces):
        b = f["box"]
        x, y, w, h = b["x"], b["y"], b["width"], b["height"]
        crop = arr[max(0, y):y + h, max(0, x):x + w]
        if crop.size:
            Image.fromarray(crop).save(OUT / f"{label}__face{i}_conf{f['confidence']:.2f}.png")
    print(f"  {label}: faces detected = {len(faces)}")


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    db = Session()

    test_files = sorted((ROOT / "test_imgs").iterdir())
    print(f"Test images: {[f.name for f in test_files]}\n")

    # Re-extract DB contacts (fresh embeddings + crops)
    contacts = db.execute(text("""
        SELECT c.id, c.first_name, c.last_name,
               ui.image_bytes, octet_length(ui.image_bytes) AS sz
        FROM contacts c JOIN uploaded_images ui ON ui.id = c.profile_picture_id
        WHERE c.profile_picture_id IS NOT NULL
        ORDER BY c.id
    """)).fetchall()
    contact_emb = {}
    print("Saving contact face crops:")
    for r in contacts:
        label = f"contact{r.id}_{r.first_name}_{r.sz}b"
        save_crops(label, bytes(r.image_bytes))
        emb = extract_embedding_for_profile(bytes(r.image_bytes))
        if emb is not None:
            contact_emb[r.id] = (np.asarray(emb), r.first_name, r.last_name, r.sz)

    print("\nSaving test_imgs face crops:")
    test_emb = {}
    for f in test_files:
        label = f"test_{f.stem}_{f.stat().st_size}b".replace(" ", "_")
        save_crops(label, f.read_bytes())
        emb = extract_embedding_for_profile(f.read_bytes())
        if emb is not None:
            test_emb[f.name] = (np.asarray(emb), f.stat().st_size)

    print("\nCross-similarity matrix (test image -> contact):")
    print(f"{'TEST':<55} | " + " | ".join(
        f"c{cid}({n[:6]})" for cid, (_, n, _, _) in contact_emb.items()))
    print("-" * 100)
    for fname, (e, sz) in test_emb.items():
        sims = []
        for cid, (ce, fn, ln, _) in contact_emb.items():
            sims.append(f"{cos(e, ce):>10.4f}")
        print(f"{fname[:55]:<55} | " + " | ".join(sims))

    print("\nByte-size cross-check (does any test file match a stored profile bytes?):")
    test_sizes = {f.stat().st_size: f.name for f in test_files}
    for cid, (_, fn, _, sz) in contact_emb.items():
        match = test_sizes.get(sz, "<no test file with this size>")
        print(f"  contact {cid} ({fn}, stored size={sz}) -> matching test file by size: {match}")

    print(f"\nFace crops saved to: {OUT}")
    db.close()


if __name__ == "__main__":
    main()

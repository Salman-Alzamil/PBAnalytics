"""Re-precompute embeddings with the new pipeline, then re-verify
cross-similarity. Replicates the precompute logic from
backend/routes/face_search.py without going through the API.
"""
from __future__ import annotations

import os, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ensure caches are clear (in case modules were imported with old code)
for mod in [m for m in list(sys.modules) if m.startswith("utils.")]:
    sys.modules.pop(mod, None)

from utils.face_embeddings import extract_embedding_for_profile  # noqa: E402

PIPELINE_VERSION = "mtcnn-standalone-facenet512-pad25-noalign-v7"


def emb_str(e: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in e) + "]"


def cos(a, b) -> float:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    db = Session()

    print("=" * 70)
    print("RE-PRECOMPUTE WITH PIPELINE", PIPELINE_VERSION)
    print("=" * 70)

    contacts = db.execute(text("""
        SELECT c.id, c.first_name, c.last_name, ui.image_bytes
        FROM contacts c JOIN uploaded_images ui ON ui.id = c.profile_picture_id
        WHERE c.profile_picture_id IS NOT NULL
        ORDER BY c.id
    """)).fetchall()

    success, skipped, errors = 0, 0, []
    for c in contacts:
        try:
            emb = extract_embedding_for_profile(bytes(c.image_bytes))
            if emb is None:
                print(f"  contact {c.id} ({c.first_name}): no face detected -> SKIP")
                skipped += 1
                # Drop any stale embedding for this contact
                db.execute(text(
                    "DELETE FROM contact_face_embeddings WHERE contact_id = :cid"
                ), {"cid": c.id})
                db.commit()
                continue
            db.execute(text(
                "DELETE FROM contact_face_embeddings WHERE contact_id = :cid"
            ), {"cid": c.id})
            db.execute(text("""
                INSERT INTO contact_face_embeddings (contact_id, embedding, created_at)
                VALUES (:cid, CAST(:emb AS vector), NOW())
            """), {"cid": c.id, "emb": emb_str(emb)})
            db.commit()
            print(f"  contact {c.id} ({c.first_name}): OK")
            success += 1
        except Exception as e:
            db.rollback()
            errors.append((c.id, str(e)))
            print(f"  contact {c.id} ({c.first_name}): ERROR {e}")

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS face_pipeline_meta (
            key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    db.execute(text("""
        INSERT INTO face_pipeline_meta (key, value, updated_at)
        VALUES ('pipeline_version', :v, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """), {"v": PIPELINE_VERSION})
    db.commit()

    print(f"\n  success={success}  skipped={skipped}  errors={len(errors)}")

    # ── Verify ──
    print("\nCross-similarity (test_imgs vs each contact's NEW stored embedding):")
    new_rows = db.execute(text("""
        SELECT cfe.contact_id, c.first_name, cfe.embedding::text AS emb
        FROM contact_face_embeddings cfe JOIN contacts c ON c.id = cfe.contact_id
        ORDER BY cfe.contact_id
    """)).fetchall()

    def parse(s: str) -> np.ndarray:
        s = s.strip().strip("[]")
        return np.asarray([float(x) for x in s.split(",")], dtype=np.float64)

    stored = {(r.contact_id, r.first_name): parse(r.emb) for r in new_rows}
    print(f"  contacts in index after fix: {len(stored)}")

    test_dir = ROOT / "test_imgs"
    print("\n" + " " * 55 + " | " + " | ".join(
        f"c{cid}({fn[:6]})" for (cid, fn) in stored))
    print("-" * 110)
    for f in sorted(test_dir.iterdir()):
        try:
            e = extract_embedding_for_profile(f.read_bytes())
        except Exception as ex:
            print(f"{f.name[:55]:<55} | ERROR {ex}")
            continue
        if e is None:
            print(f"{f.name[:55]:<55} | (no face detected in test image)")
            continue
        sims = " | ".join(f"{cos(e, v):>10.4f}" for v in stored.values())
        print(f"{f.name[:55]:<55} | {sims}")

    db.close()


if __name__ == "__main__":
    main()

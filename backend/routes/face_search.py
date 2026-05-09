from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from models import Contact
from utils.face_embeddings import EMBED_DIM

router = APIRouter(tags=["Face Search"])

# InsightFace buffalo_l (ArcFace, 5-pt aligned). Starting threshold; tune
# from a labelled verification set after re-indexing.
SIMILARITY_THRESHOLD = 0.40
MAX_IMAGE_BYTES = 10 * 1024 * 1024

# Bump this string whenever the embedding pipeline changes (model, backend, alignment, etc.).
# The stored version in the DB is written by /face-embeddings/precompute.
# A mismatch means the index is stale and needs re-indexing.
PIPELINE_VERSION = "insightface-buffalo_l-v8"


def _ensure_meta_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS face_pipeline_meta (
            key   TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    db.commit()


def _stored_pipeline_version(db: Session) -> str | None:
    try:
        _ensure_meta_table(db)
        row = db.execute(
            text("SELECT value FROM face_pipeline_meta WHERE key = 'pipeline_version'")
        ).first()
        return row[0] if row else None
    except Exception:
        return None


def _is_index_stale(db: Session) -> bool:
    stored = _stored_pipeline_version(db)
    return stored != PIPELINE_VERSION


def _emb_str(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


def _find_best_match(db: Session, embedding: list[float]) -> tuple[int | None, float]:
    row = db.execute(
        text("""
            SELECT contact_id,
                   1 - (embedding <=> CAST(:emb AS vector)) AS similarity
            FROM contact_face_embeddings
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT 1
        """),
        {"emb": _emb_str(embedding)},
    ).first()
    if row is None:
        return None, 0.0
    return int(row.contact_id), float(row.similarity)


def _contact_payload(c: Contact) -> dict:
    return {
        "id": c.id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "phone": c.phone,
        "email": c.email,
        "city": c.city,
        "notes": c.notes,
        "possible_duplicates": c.possible_duplicates,
        "profile_picture_id": c.profile_picture_id,
    }


def _validate_image(file: UploadFile, image_bytes: bytes) -> None:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")


# ── Feature 1: single face search ────────────────────────────────────────────

@router.post("/search/by-face")
async def search_by_face(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()
    _validate_image(file, image_bytes)

    try:
        from utils.face_embeddings import extract_single_embedding
        embedding, face_count = extract_single_embedding(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face detection failed: {str(e)}")

    if face_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No face detected. Please upload a clear photo with exactly one face.",
        )
    if face_count > 1:
        raise HTTPException(
            status_code=400,
            detail=f"{face_count} faces detected. Please upload a photo with exactly one face.",
        )
    if embedding is None:
        raise HTTPException(status_code=400, detail="Could not extract face features.")

    stale = _is_index_stale(db)

    contact_id, similarity = _find_best_match(db, embedding)
    if contact_id is None or similarity < SIMILARITY_THRESHOLD:
        return {
            "matched": False,
            "message": "No matching contact found.",
            "similarity": round(similarity, 4),
            "index_stale": stale,
        }

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return {"matched": False, "message": "No matching contact found.", "similarity": 0.0, "index_stale": stale}

    return {"matched": True, "similarity": round(similarity, 4), "contact": _contact_payload(contact), "index_stale": stale}


# ── Feature 2a: group photo analysis ─────────────────────────────────────────

@router.post("/analyze/group-image")
async def analyze_group_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    _validate_image(file, image_bytes)

    try:
        from utils.face_embeddings import extract_group_embeddings
        faces = extract_group_embeddings(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face analysis failed: {str(e)}")

    return {"face_count": len(faces), "faces": faces}


# ── Feature 2b: identify one face from its embedding ─────────────────────────

class IdentifyRequest(BaseModel):
    embedding: list[float]


@router.post("/identify/face")
def identify_face(req: IdentifyRequest, db: Session = Depends(get_db)):
    if len(req.embedding) != EMBED_DIM:
        raise HTTPException(
            status_code=400,
            detail=f"Embedding must be {EMBED_DIM}-dimensional.",
        )

    contact_id, similarity = _find_best_match(db, req.embedding)
    if contact_id is None or similarity < SIMILARITY_THRESHOLD:
        return {"matched": False, "message": "No matching contact found.", "similarity": round(similarity, 4)}

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return {"matched": False, "message": "No matching contact found.", "similarity": 0.0}

    return {"matched": True, "similarity": round(similarity, 4), "contact": _contact_payload(contact)}


# ── Utility: pre-compute embeddings for all contact profile pictures ──────────

@router.post("/face-embeddings/precompute")
def precompute_embeddings(db: Session = Depends(get_db)):
    from models import UploadedImage
    from utils.face_embeddings import extract_embedding_for_profile

    contacts = db.query(Contact).filter(Contact.profile_picture_id.isnot(None)).all()
    success, skipped, errors = 0, 0, []

    for contact in contacts:
        try:
            image = db.query(UploadedImage).filter(UploadedImage.id == contact.profile_picture_id).first()
            if not image:
                skipped += 1
                continue

            embedding = extract_embedding_for_profile(image.image_bytes)
            if embedding is None:
                skipped += 1
                continue

            db.execute(
                text("DELETE FROM contact_face_embeddings WHERE contact_id = :cid"),
                {"cid": contact.id},
            )
            db.execute(
                text("""
                    INSERT INTO contact_face_embeddings (contact_id, embedding, created_at)
                    VALUES (:cid, CAST(:emb AS vector), NOW())
                """),
                {"cid": contact.id, "emb": _emb_str(embedding)},
            )
            db.commit()
            success += 1
        except Exception as e:
            db.rollback()
            errors.append({"contact_id": contact.id, "error": str(e)})

    # Stamp the pipeline version so search can detect stale indexes in future
    try:
        _ensure_meta_table(db)
        db.execute(text("""
            INSERT INTO face_pipeline_meta (key, value, updated_at)
            VALUES ('pipeline_version', :ver, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """), {"ver": PIPELINE_VERSION})
        db.commit()
    except Exception:
        pass

    return {
        "processed": len(contacts),
        "success": success,
        "skipped": skipped,
        "errors": errors,
        "pipeline_version": PIPELINE_VERSION,
    }


# ── Status: is the index fresh? ───────────────────────────────────────────────

@router.get("/face-embeddings/status")
def face_index_status(db: Session = Depends(get_db)):
    stored = _stored_pipeline_version(db)
    stale = stored != PIPELINE_VERSION
    return {
        "pipeline_version": PIPELINE_VERSION,
        "stored_version": stored,
        "index_stale": stale,
        "message": "Re-index required — click 'Index Faces'." if stale else "Index is up to date.",
    }

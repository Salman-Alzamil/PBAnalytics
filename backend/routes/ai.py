<<<<<<< HEAD
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database import get_db
from models import UploadedImage
from utils.ai_classifier import classify_image_bytes
from utils.image_store import compress_image
router = APIRouter(prefix="/ai", tags=["AI"])

=======
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import UploadedImage
from utils.ai_classifier import classify_image_bytes, get_model_info, reload_model

router = APIRouter(prefix="/ai", tags=["AI"])

_CONFIG_PATH = "model/active_model.json"
_MODEL_DIR   = "model"


# ── Image endpoints ───────────────────────────────────────────────────────────

>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0
@router.get("/images/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db)):
    record = db.query(UploadedImage).filter(UploadedImage.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=record.image_bytes, media_type=record.content_type)


@router.get("/images")
def list_saved_images(db: Session = Depends(get_db)):
<<<<<<< HEAD
   records = db.query(UploadedImage).order_by(UploadedImage.created_at.desc()).all()
   return [
       {
           "id": r.id,
           "filename": r.filename,
           "prediction": r.prediction,
           "confidence": r.confidence,
           "original_size": r.original_size,
           "compressed_size": r.compressed_size,
           "created_at": r.created_at,
       }
       for r in records
   ]


@router.post("/classify")
async def classify_image(
   file: UploadFile = File(...),
   db: Session = Depends(get_db)
):
   """
   Accept an image upload, classify it, compress it,
   and store both the image and prediction in Postgres.
   """
   if not file.content_type or not file.content_type.startswith("image/"):
       raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
   original_bytes = await file.read()
   if len(original_bytes) == 0:
       raise HTTPException(status_code=400, detail="Empty file. Please upload a valid image.")
   MAX_SIZE = 10 * 1024 * 1024  # 10 MB
   if len(original_bytes) > MAX_SIZE:
       raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
   try:
       compressed_bytes, stored_content_type = compress_image(original_bytes)
       
       # In case the original is already highly compressed and "compressing" makes it larger
       if len(compressed_bytes) >= len(original_bytes):
           compressed_bytes = original_bytes
           stored_content_type = file.content_type
           
       results = classify_image_bytes(original_bytes)
       record = UploadedImage(
           filename=file.filename or "uploaded_image",
           content_type=stored_content_type,
           image_bytes=compressed_bytes,
           original_size=len(original_bytes),
           compressed_size=len(compressed_bytes),
           prediction=results.get("prediction"),
           confidence=results.get("confidence"),
           model_version="best.pt"
       )
       db.add(record)
       db.commit()
       db.refresh(record)
       return {
           "image_id": record.id,
           "prediction": results.get("prediction"),
           "confidence": results.get("confidence"),
           "all_classes": results.get("all_classes"),
           "original_size": len(original_bytes),
           "compressed_size": len(compressed_bytes),
           "compression_ratio": round(len(compressed_bytes) / len(original_bytes), 3),
           "message": "Image classified and stored successfully."
       }
   except Exception as e:
       db.rollback()
       raise HTTPException(status_code=500, detail=f"Failed to classify and store image: {str(e)}")
=======
    records = db.query(UploadedImage).order_by(UploadedImage.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "prediction": r.prediction,
            "confidence": r.confidence,
            "original_size": r.original_size,
            "compressed_size": r.compressed_size,
            "created_at": r.created_at,
        }
        for r in records
    ]


@router.post("/classify")
async def classify_image(file: UploadFile = File(...)):
    """Classify an image using the active model. Does not save to the database."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
    original_bytes = await file.read()
    if len(original_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file. Please upload a valid image.")
    if len(original_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    try:
        results = classify_image_bytes(original_bytes)
        return {
            "prediction": results["prediction"],
            "confidence": results["confidence"],
            "all_classes": results["all_classes"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to classify image: {str(e)}")


# ── Model management endpoints ────────────────────────────────────────────────

@router.get("/model/info")
def model_info():
    """Return metadata about the currently loaded model checkpoint."""
    try:
        return get_model_info()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
def list_models():
    """
    List every .pt checkpoint file available under backend/model/.
    Returns file paths relative to the backend working directory.
    """
    model_dir = Path(_MODEL_DIR)
    if not model_dir.exists():
        return {"available": []}

    checkpoints = []
    for pt_file in sorted(model_dir.rglob("*.pt")):
        rel_path = str(pt_file).replace("\\", "/")
        checkpoints.append({
            "path": rel_path,
            "size_mb": round(pt_file.stat().st_size / 1_048_576, 2),
        })
    return {"available": checkpoints}


class SelectModelRequest(BaseModel):
    path: str
    version: str = "v2.0"
    checkpoint: str = "best"
    description: str = ""


@router.post("/model/select")
def select_model(body: SelectModelRequest):
    """
    Switch the active model checkpoint.

    - path: path to the .pt file relative to the backend working directory
             e.g. "model/v2.0/epoch15.pt"
    - version: label for the run (e.g. "v2.0")
    - checkpoint: which checkpoint within that run (e.g. "epoch15" or "best")
    - description: optional note about why you chose this checkpoint
    """
    if not os.path.exists(body.path):
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint not found: {body.path}",
        )

    config = {
        "version": body.version,
        "checkpoint": body.checkpoint,
        "path": body.path,
        "description": body.description,
    }
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    try:
        loaded = reload_model()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Model switched successfully.", "active": loaded}
>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0

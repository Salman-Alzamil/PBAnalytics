from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database import get_db
from models import UploadedImage
from utils.ai_classifier import classify_image_bytes
from utils.image_store import compress_image
router = APIRouter(prefix="/ai", tags=["AI"])

@router.get("/images/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db)):
    record = db.query(UploadedImage).filter(UploadedImage.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=record.image_bytes, media_type=record.content_type)


@router.get("/images")
def list_saved_images(db: Session = Depends(get_db)):
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
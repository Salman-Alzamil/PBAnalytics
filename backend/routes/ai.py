from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database import get_db
from models import UploadedImage
from utils.ai_classifier import classify_image_bytes

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
):
   """Classify an image using the YOLO model. Only for testing the model, no saving to database."""
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
           "prediction": results.get("prediction"),
           "confidence": results.get("confidence"),
           "all_classes": results.get("all_classes"),
       }
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Failed to classify image: {str(e)}")
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import Contact, UploadedImage
from schemas import ContactCreate, ContactResponse
from utils.ai_classifier import classify_image_bytes
from utils.image_store import compress_image

router = APIRouter(prefix="/contacts", tags=["Contacts"])

@router.get("/", response_model=list[ContactResponse])
def get_contacts( # Returns a paginated, filtered, and sorted list of contacts
    search: str | None =None,
    city: str | None = None,
    sort_by: str | None = Query(None, description="Sort by 'name' or 'city'"),
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
 ):
    query = db.query(Contact)

    if search:
        query = query.filter(
            (Contact.first_name.ilike(f"%{search}%")) |
            (Contact.last_name.ilike(f"%{search}%")) |
            (Contact.phone.ilike(f"%{search}%"))
        )
    if city:
        query = query.filter(Contact.city.ilike(f"%{city}%"))

    if sort_by == "name" or sort_by == "name_asc":
        query = query.order_by(Contact.first_name, Contact.last_name)
    elif sort_by == "name_desc":
        query = query.order_by(Contact.first_name.desc(), Contact.last_name.desc())
    elif sort_by == "city" or sort_by == "city_asc":
        query = query.order_by(Contact.city)

    return query.offset((page - 1) * limit).limit(limit).all()
    

@router.get("/duplicates", response_model=list[ContactResponse])
def get_duplicate(db: Session = Depends(get_db)):  # Returns all contacts flagged as possible duplicates during import
    return db.query(Contact).filter(Contact.possible_duplicates == True).all()

@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)): # Returns a single contact by ID, raises 404 if not found
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.post("/", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)): # Validates and inserts a new contact, returns the created record with its assigned ID
    new_contact = Contact(**contact.model_dump())
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return new_contact

@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)): # Deletes a contact by ID and returns 204 No Content; raises 404 if not found
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return Response()

from pydantic import BaseModel

class ProfilePictureUpdate(BaseModel):
    profile_picture_id: int | None

@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact_update: ContactCreate, db: Session = Depends(get_db)): # Updates all fields of an existing contact; raises 404 if not found
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Exclude profile_picture_id from regular updates if needed, or include it if it's part of the dump
    update_data = contact_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contact, key, value)

    db.commit()
    db.refresh(contact)
    return contact

@router.patch("/{contact_id}/picture", response_model=ContactResponse)
def update_contact_picture(contact_id: int, update_data: ProfilePictureUpdate, db: Session = Depends(get_db)):
    from models import UploadedImage
    from sqlalchemy import text
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.profile_picture_id = update_data.profile_picture_id
    db.commit()
    db.refresh(contact)

    # Best-effort: index the new face so it's immediately searchable
    if update_data.profile_picture_id:
        try:
            from utils.face_embeddings import extract_embedding_for_profile
            from routes.face_search import _emb_str
            image = db.query(UploadedImage).filter(UploadedImage.id == update_data.profile_picture_id).first()
            if image:
                embedding = extract_embedding_for_profile(image.image_bytes)
                if embedding:
                    db.execute(text("DELETE FROM contact_face_embeddings WHERE contact_id = :cid"), {"cid": contact.id})
                    db.execute(
                        text("INSERT INTO contact_face_embeddings (contact_id, embedding, created_at) VALUES (:cid, CAST(:emb AS vector), NOW())"),
                        {"cid": contact.id, "emb": _emb_str(embedding)},
                    )
                    db.commit()
        except Exception:
            pass  # never block the picture save if face indexing fails

    return contact

@router.post("/{contact_id}/picture")
async def upload_contact_picture(
    contact_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    from models import UploadedImage
    
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    original_bytes = await file.read()
    if len(original_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(original_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    try:
        results = classify_image_bytes(original_bytes)
        prediction = results.get("prediction")
        confidence = results.get("confidence")
        accepted = confidence >= 90

        image_id = None
        if accepted:
            compressed_bytes, stored_content_type = compress_image(original_bytes)
            if len(compressed_bytes) >= len(original_bytes):
                compressed_bytes = original_bytes
                stored_content_type = file.content_type

            old_image_id = contact.profile_picture_id

            record = UploadedImage(
                filename=file.filename or "uploaded_image",
                content_type=stored_content_type,
                image_bytes=compressed_bytes,
                original_size=len(original_bytes),
                compressed_size=len(compressed_bytes),
                prediction=prediction,
                confidence=confidence,
                model_version="best.pt"
            )
            db.add(record)
            db.flush()
            contact.profile_picture_id = record.id
            db.commit()
            image_id = record.id

            if old_image_id:
                old_image = db.query(UploadedImage).filter(UploadedImage.id == old_image_id).first()
                if old_image:
                    db.delete(old_image)
                    db.commit()

        return {
            "accepted": accepted,
            "prediction": prediction,
            "confidence": confidence,
            "all_classes": results.get("all_classes"),
            "image_id": image_id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@router.delete("/{contact_id}/picture", status_code=204)
def delete_contact_picture(contact_id: int, db: Session = Depends(get_db)):
    from models import UploadedImage
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    image_id = contact.profile_picture_id
    contact.profile_picture_id = None
    db.commit()

    if image_id:
        image = db.query(UploadedImage).filter(UploadedImage.id == image_id).first()
        if image:
            db.delete(image)
            db.commit()

    # Remove stale face embedding
    try:
        db.execute(text("DELETE FROM contact_face_embeddings WHERE contact_id = :cid"), {"cid": contact_id})
        db.commit()
    except Exception:
        pass

    return Response()
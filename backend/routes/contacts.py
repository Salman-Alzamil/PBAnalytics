from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Contact
from schemas import ContactCreate, ContactResponse

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
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.profile_picture_id = update_data.profile_picture_id
    db.commit()
    db.refresh(contact)
    return contact

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

    return Response()
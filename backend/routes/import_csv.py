from io import BytesIO
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import Contact, CallHistory
from utils.cleaner import clean_contacts, clean_calls


router = APIRouter(prefix="/import", tags=["Import CSV"])

@router.post("/contacts")
async def import_contacts(file: UploadFile = File(...), db: Session = Depends(get_db)): # Reads an uploaded CSV, cleans it, skips existing phone+email combos, inserts new contacts
    contents = await file.read()
    df = pd.read_csv(BytesIO(contents))
    df = clean_contacts(df)
    
    # removes id column if exists 
    # postgresql auto increments id
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # Fetch existing contacts to skip duplicates
    existing_contacts = {(c.phone, c.email) for c in db.query(Contact.phone, Contact.email).all()}

    def _none_if_nan(v):
        try:
            return None if pd.isna(v) else v
        except (TypeError, ValueError):
            return v

    imported_count = 0
    skipped_count = 0
    new_contacts = []
    for row in df.to_dict(orient="records"):
        clean_row = {k: _none_if_nan(v) for k, v in row.items()}

        # Skip if already in database
        if (clean_row.get("phone"), clean_row.get("email")) not in existing_contacts:
            new_contacts.append(Contact(**clean_row))
            existing_contacts.add((clean_row.get("phone"), clean_row.get("email")))
            imported_count += 1
        else:
            skipped_count += 1

    db.add_all(new_contacts)
    db.commit()
    return {
        "message": f"{imported_count} contacts imported, {skipped_count} skipped.",
        "contacts_imported": imported_count,
        "contacts_skipped": skipped_count,
        "duplicates_flagged": int(df["possible_duplicates"].sum()),
    }

@router.post("/calls")
async def import_calls(file: UploadFile = File(...), db: Session = Depends(get_db)): # Reads an uploaded CSV, skips calls with existing call_id, inserts new call records
    contents = await file.read()
    df = pd.read_csv(BytesIO(contents))
    df = clean_calls(df)

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # Fetch existing call IDs to skip duplicates
    existing_call_ids = {c.call_id for c in db.query(CallHistory.call_id).all()}

    # Replace nan values specifically for string fields so psycopg doesn't fail on inserts
    df = df.replace({pd.NA: None, float('nan'): None})

    def _none_if_nan(v):
        try:
            return None if pd.isna(v) else v
        except (TypeError, ValueError):
            return v

    imported_count = 0
    skipped_count = 0
    new_calls = []
    for row in df.to_dict(orient="records"):
        clean_row = {k: _none_if_nan(v) for k, v in row.items()}

        # Skip if already in database
        if clean_row.get("call_id") not in existing_call_ids:
            new_calls.append(CallHistory(**clean_row))
            existing_call_ids.add(clean_row.get("call_id"))
            imported_count += 1
        else:
            skipped_count += 1

    db.add_all(new_calls)
    db.commit()
    return {
        "message": f"{imported_count} calls imported, {skipped_count} skipped.",
        "calls_imported": imported_count,
        "calls_skipped": skipped_count
    }
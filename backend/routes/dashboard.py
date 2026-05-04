from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Contact, CallHistory
from utils.favourites import compute_favourites

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)): # Returns all summary stats in one call: contact count, call stats, top favourites, and duplicates
    total_contacts = db.query(Contact).count()
    total_calls = db.query(CallHistory).count()
    missed_calls = db.query(CallHistory).filter(CallHistory.status == "missed").count()
    avg_duration_seconds = db.query(func.avg(CallHistory.duration_seconds)).scalar()
    avg_duration_minutes = round(avg_duration_seconds / 60, 2) if avg_duration_seconds else 0
    duplicates = db.query(Contact).filter(Contact.possible_duplicates == True).count()
    top_favourites = compute_favourites(db, mode="most_called", limit=5)
    possible_duplicates = db.query(Contact).filter(Contact.possible_duplicates == True).all()

    return {
        "total_contacts": total_contacts,
        "total_calls": total_calls,
        "missed_calls": missed_calls,
        "avg_duration_seconds": avg_duration_seconds,
        "avg_duration_minutes": avg_duration_minutes,
        "duplicates": duplicates,
        "top_favourites": top_favourites,
        "possible_duplicates": possible_duplicates
    }
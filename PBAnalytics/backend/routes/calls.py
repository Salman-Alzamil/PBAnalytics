from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import CallHistory
from schemas import CallHistoryResponse

router = APIRouter(prefix="/calls", tags=["Calls"])

@router.get("/", response_model=list[CallHistoryResponse])
def get_calls(  # Returns paginated call history with optional filters for phone, status, and date range
    phone: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(CallHistory)

    if phone:
        query = query.filter(CallHistory.phone_number == phone)
    if status:
        query = query.filter(CallHistory.status == status)
    if date_from:
        query = query.filter(CallHistory.date >= date_from)
    if date_to:
        query = query.filter(CallHistory.date <= date_to)

    query = query.order_by(CallHistory.date.desc(), CallHistory.time.desc())

    return query.offset((page - 1) * limit).limit(limit).all()

@router.get("/stats")
def get_call_stats(db: Session = Depends(get_db)): # Returns aggregate stats: total calls, missed count, average duration, and breakdown by type
    total_calls = db.query((CallHistory)).count()
    missed_calls = db.query(CallHistory).filter(CallHistory.status == "missed").count()
    avg_duration = db.query(func.avg(CallHistory.duration_seconds)).scalar()

    missed_percentage_val = round((missed_calls / total_calls) * 100, 2) if total_calls > 0 else 0.0
    missed_percentage = f"{missed_percentage_val}%"
    avg_duration_minutes = round(avg_duration / 60, 2) if avg_duration else 0.0

    calls_by_type_query = db.query(CallHistory.call_type, func.count(CallHistory.id)).group_by(CallHistory.call_type).all()
    calls_by_type = {t: c for t, c in calls_by_type_query if t is not None}

    return {
        "total_calls": total_calls,
        "missed_calls": missed_calls,
        "missed_percentage": missed_percentage,
        "avg_duration": avg_duration or 0.0,
        "avg_duration_minutes": avg_duration_minutes,
        "calls_by_type": calls_by_type
    }
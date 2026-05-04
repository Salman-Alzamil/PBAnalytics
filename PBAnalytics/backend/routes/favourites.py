from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from utils.favourites import compute_favourites

router = APIRouter(prefix="/favourites", tags=["Favourites"])

@router.get("/")
def get_favourites(  # Returns top N contacts ranked by the requested mode (most_called, longest_calls, recent)
    mode: str = Query("most_called", pattern="^(most_called|longest_calls|recent)$"),
    limit: int = 10,
    db: Session = Depends(get_db)
):
    return compute_favourites(db, mode=mode, limit=limit)


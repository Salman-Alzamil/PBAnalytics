from datetime import date as Date
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Contact, CallHistory


def get_contact(db: Session, contact_id: int):
    """Return a single Contact by primary key, or None if not found."""
    return db.query(Contact).filter(Contact.id == contact_id).first()


def get_contacts(
    db: Session,
    search: str | None = None,
    city: str | None = None,
    sort_by: str | None = None,
    page: int = 1,
    limit: int = 10,
):
    """Return a paginated, optionally filtered and sorted list of contacts."""
    query = db.query(Contact)
    if search:
        query = query.filter(
            (Contact.first_name.ilike(f"%{search}%")) |
            (Contact.last_name.ilike(f"%{search}%")) |
            (Contact.phone.ilike(f"%{search}%"))
        )
    if city:
        query = query.filter(Contact.city.ilike(f"%{city}%"))
    if sort_by == "name":
        query = query.order_by(Contact.first_name, Contact.last_name)
    elif sort_by == "city":
        query = query.order_by(Contact.city)
    return query.offset((page - 1) * limit).limit(limit).all()


def get_duplicate_contacts(db: Session):
    """Return all contacts flagged as possible duplicates."""
    return db.query(Contact).filter(Contact.possible_duplicates == True).all()


def create_contact(db: Session, contact_data: dict):
    """Insert a new contact row and return the created Contact instance."""
    contact = Contact(**contact_data)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(db: Session, contact_id: int, contact_data: dict):
    """Update an existing contact's fields; return the updated instance or None."""
    contact = get_contact(db, contact_id)
    if not contact:
        return None
    for key, value in contact_data.items():
        setattr(contact, key, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: int) -> bool:
    """Delete a contact by id; return True on success, False if not found."""
    contact = get_contact(db, contact_id)
    if not contact:
        return False
    db.delete(contact)
    db.commit()
    return True


def get_calls(
    db: Session,
    phone: str | None = None,
    status: str | None = None,
    date_from: Date | None = None,
    date_to: Date | None = None,
    page: int = 1,
    limit: int = 10,
):
    """Return a paginated list of call history records with optional filters."""
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


def get_call_stats(db: Session) -> dict:
    """Return aggregate call statistics: totals, missed count, avg duration, by-type breakdown."""
    total = db.query(CallHistory).count()
    missed = db.query(CallHistory).filter(CallHistory.status == "missed").count()
    avg_dur = db.query(func.avg(CallHistory.duration_seconds)).scalar()
    by_type_rows = (
        db.query(CallHistory.call_type, func.count(CallHistory.id))
        .group_by(CallHistory.call_type)
        .all()
    )
    return {
        "total_calls": total,
        "missed_calls": missed,
        "missed_percentage": f"{round((missed / total) * 100, 2)}%" if total else "0.0%",
        "avg_duration": avg_dur or 0.0,
        "avg_duration_minutes": round(avg_dur / 60, 2) if avg_dur else 0.0,
        "calls_by_type": {t: c for t, c in by_type_rows if t is not None},
    }

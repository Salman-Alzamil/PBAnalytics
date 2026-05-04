from sqlalchemy.orm import Session 
from models import Contact, CallHistory

def compute_favourites(db: Session, mode="most_called", limit=10): # Scores contacts by call count and duration, normalises to 0-100, sorts by the requested mode
    completed_calls = db.query(CallHistory).filter(CallHistory.status == "completed").all()
    
    grouped = {}

    for call in completed_calls:
        phone = call.phone_number

        if phone not in grouped:
            grouped[phone] = {
                "phone": phone,
                "call_count": 0,
                "total_duration_seconds": 0,
                "last_call_date": call.date,
            }

        grouped[phone]["call_count"] += 1
        grouped[phone]["total_duration_seconds"] += call.duration_seconds

        if call.date > grouped[phone]["last_call_date"]:
            grouped[phone]["last_call_date"] = call.date

    results = []

    max_score  = 1

    for item in grouped.values():
        total_minutes = item["total_duration_seconds"] / 60
        raw_score = (item["call_count"] * 2) + total_minutes
        item["raw_score"] = raw_score
        max_score = max(max_score, raw_score)

    phones = list(grouped.keys())
    contacts_map = {
        c.phone: c
        for c in db.query(Contact).filter(Contact.phone.in_(phones)).all()
    }

    for item in grouped.values():
        contacts = contacts_map.get(item["phone"])

        item["score"] = round((item["raw_score"] / max_score) * 100, 2)
        item["name"] = f"{contacts.first_name} {contacts.last_name}" if contacts else "Unknown"
        item["city"] = contacts.city if contacts else None
        item["profile_picture_id"] = contacts.profile_picture_id if contacts else None

        results.append(item)

    if mode == "most_called":
            results.sort(key=lambda x: x["call_count"], reverse=True)    
    elif mode == "longest_calls":
            results.sort(key=lambda x: x["total_duration_seconds"], reverse=True)
    elif mode == "recent":
            results.sort(key=lambda x: x["last_call_date"], reverse=True)    

    return results[:limit]

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, Time, LargeBinary, DateTime
from datetime import datetime
from database import Base

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    phone = Column(String, index=True)
    email = Column(String)
    city = Column(String)
    notes = Column(String)
    possible_duplicates = Column(Boolean, default=False)
    profile_picture_id = Column(Integer, nullable=True)


class CallHistory(Base):
    __tablename__ = "call_history"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True)
    phone_number = Column(String, index=True)
    contact_name = Column(String)
    date = Column(Date)
    time = Column(Time)
    duration_seconds = Column(Integer)
    call_type = Column(String)
    status = Column(String)

class UploadedImage(Base):
    __tablename__ = "uploaded_images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    image_bytes = Column(LargeBinary, nullable=False)
    original_size = Column(Integer, nullable=False)
    compressed_size = Column(Integer, nullable=False)
    prediction = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
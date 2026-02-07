from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import random
import string
import qrcode
import io
import base64

from database.connection import get_db
from models.event import Event
from models.room import Room
from models.table import Table

router = APIRouter()

# Hardcoded admin credentials (MVP)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "bilhetinho2024"


class AdminLogin(BaseModel):
    username: str
    password: str


def generate_event_code(db: Session) -> str:
    """Generate unique 6-character event code (A-Z, 0-9)"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing = db.query(Event).filter(Event.code == code).first()
        if not existing:
            return code


@router.post("/admin/login")
def admin_login(credentials: AdminLogin):
    """
    Admin login endpoint (hardcoded for MVP)

    Default credentials:
    - username: admin
    - password: bilhetinho2024
    """
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        return {
            "success": True,
            "token": "admin-session-token",
            "message": "Login successful"
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/admin/events")
def create_event(
    start_date: str,
    end_date: str,
    number_of_tables: int,
    db: Session = Depends(get_db)
):
    """
    Create a new event with QR code

    Only one event can be active at a time.
    Automatically creates a room and tables for the event.
    """
    # Parse dates
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use ISO 8601 format.")

    # Validate dates
    if start >= end:
        raise HTTPException(400, "Start date must be before end date")

    # Validate table count
    if number_of_tables < 1 or number_of_tables > 50:
        raise HTTPException(400, "Number of tables must be between 1 and 50")

    # Deactivate existing active events
    db.query(Event).filter(Event.is_active == True).update({"is_active": False})

    # Generate unique code
    code = generate_event_code(db)

    # Generate QR code as base64
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    # QR code contains URL with event code
    qr.add_data(f"https://bilhetinho.vercel.app/?code={code}")
    qr.make(fit=True)

    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    qr_data_uri = f"data:image/png;base64,{qr_base64}"

    # Create event
    event = Event(
        code=code,
        start_date=start,
        end_date=end,
        number_of_tables=number_of_tables,
        is_active=True,
        qr_code_data=qr_data_uri
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    # Create room for this event
    room = Room(
        name=f"Evento {code}",
        is_active=True,
        event_code=code
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    # Create tables
    for i in range(1, number_of_tables + 1):
        table = Table(room_id=room.id, number=i)
        db.add(table)

    db.commit()

    return {
        "success": True,
        "event": {
            "id": event.id,
            "code": event.code,
            "start_date": event.start_date.isoformat(),
            "end_date": event.end_date.isoformat(),
            "number_of_tables": event.number_of_tables,
            "qr_code": event.qr_code_data
        }
    }


@router.get("/admin/events")
def list_events(db: Session = Depends(get_db)):
    """
    List all events ordered by creation date (newest first)
    """
    events = db.query(Event).order_by(Event.created_at.desc()).all()

    now = datetime.utcnow()

    return {
        "events": [
            {
                "id": e.id,
                "code": e.code,
                "start_date": e.start_date.isoformat(),
                "end_date": e.end_date.isoformat(),
                "status": "active" if (e.is_active and e.start_date <= now <= e.end_date) else "expired",
                "number_of_tables": e.number_of_tables
            }
            for e in events
        ]
    }


@router.get("/events/validate/{code}")
def validate_event_code(code: str, db: Session = Depends(get_db)):
    """
    Validate event code and return associated room

    Checks if:
    - Event exists
    - Event is within date range
    - Room is available
    """
    # Find event
    event = db.query(Event).filter(Event.code == code.upper()).first()
    if not event:
        raise HTTPException(404, detail="Invalid event code")

    # Check if event is within date range
    now = datetime.utcnow()
    if not (event.start_date <= now <= event.end_date):
        if now < event.start_date:
            raise HTTPException(400, detail="Event has not started yet")
        else:
            raise HTTPException(400, detail="Event has expired")

    # Get associated room
    room = db.query(Room).filter(Room.event_code == code.upper()).first()
    if not room:
        raise HTTPException(404, detail="Event room not found")

    return {
        "valid": True,
        "event": {
            "code": event.code,
            "room_id": room.id,
            "room_name": room.name
        }
    }

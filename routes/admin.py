from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import random
import string
import qrcode
import io
import base64
import jwt

from database.connection import get_db
from models.event import Event
from models.room import Room
from models.table import Table
from models.admin_user import AdminUser
from models.establishment import Establishment
from utils.auth import create_admin_token, verify_admin_token

router = APIRouter()


class AdminLogin(BaseModel):
    username: str
    password: str


def get_current_admin(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> AdminUser:
    """
    Dependency to verify JWT admin token and return authenticated admin user
    Validates token signature, expiration, and user existence
    Ensures only authenticated admins with valid tokens can access protected routes
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Remove "Bearer " prefix if present
    token = authorization.replace("Bearer ", "").strip()

    try:
        # Verify JWT token and extract payload
        payload = verify_admin_token(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token type")

        admin_id = payload.get("admin_id")
        establishment_id = payload.get("establishment_id")

        # Verify admin exists in database
        admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()

        if not admin:
            raise HTTPException(status_code=401, detail="Admin user not found")

        # Double-check establishment matches (security)
        if admin.establishment_id != establishment_id:
            raise HTTPException(status_code=401, detail="Token establishment mismatch")

        return admin

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired - Please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def generate_event_code(db: Session) -> str:
    """Generate unique 6-character event code (A-Z, 0-9)"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing = db.query(Event).filter(Event.code == code).first()
        if not existing:
            return code


@router.post("/admin/login")
def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)):
    """
    Admin login endpoint with JWT token generation
    Validates credentials and returns a signed JWT token that expires in 8 hours
    Token includes admin_id and establishment_id for security validation
    """
    admin_user = db.query(AdminUser).filter(AdminUser.username == credentials.username).first()

    if not admin_user or not admin_user.verify_password(credentials.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get establishment info
    establishment = db.query(Establishment).filter(Establishment.id == admin_user.establishment_id).first()

    # Generate JWT token with expiration
    token = create_admin_token(admin_user.id, admin_user.establishment_id)

    return {
        "success": True,
        "token": token,  # JWT token with 8-hour expiration
        "role": "admin",
        "admin_id": admin_user.id,
        "establishment_id": admin_user.establishment_id,
        "establishment_name": establishment.name if establishment else "Unknown",
        "message": "Login successful"
    }


@router.post("/admin/events")
def create_event(
    start_date: str,
    end_date: str,
    number_of_tables: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Create a new event with QR code
    Only authenticated admins can create events
    Events are automatically linked to the admin's establishment
    Only one event per establishment can be active at a time
    Automatically creates a room and tables for the event
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
    if number_of_tables < 1 or number_of_tables > 100:
        raise HTTPException(400, "Number of tables must be between 1 and 100")

    # Deactivate existing active events FOR THIS ESTABLISHMENT ONLY
    db.query(Event).filter(
        Event.is_active == True,
        Event.establishment_id == admin.establishment_id
    ).update({"is_active": False})

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

    # Create event LINKED TO ESTABLISHMENT
    event = Event(
        code=code,
        establishment_id=admin.establishment_id,  # ✅ LINK TO ESTABLISHMENT
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
def list_events(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    List events for authenticated admin's establishment only
    Ordered by creation date (newest first)
    Prevents cross-establishment data access
    """
    # Filter by establishment - CRITICAL SECURITY CHECK
    events = db.query(Event).filter(
        Event.establishment_id == admin.establishment_id
    ).order_by(Event.created_at.desc()).all()

    now = datetime.utcnow()

    return {
        "events": [
            {
                "id": e.id,
                "code": e.code,
                "start_date": e.start_date.isoformat(),
                "end_date": e.end_date.isoformat(),
                "status": "active" if (e.is_active and e.start_date <= now <= e.end_date) else "expired",
                "number_of_tables": e.number_of_tables,
                "qr_code_data": e.qr_code_data
            }
            for e in events
        ]
    }


@router.post("/admin/events/{event_id}/deactivate")
def deactivate_event(
    event_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Deactivate an event and its associated room
    Only the admin from the event's establishment can deactivate it
    This will immediately kick out all users
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")

    # CRITICAL SECURITY CHECK: Verify event belongs to admin's establishment
    if event.establishment_id != admin.establishment_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied - You can only deactivate events from your establishment"
        )

    # Deactivate event
    event.is_active = False

    # Deactivate associated room
    room = db.query(Room).filter(Room.event_code == event.code).first()
    if room:
        room.is_active = False

    db.commit()

    return {
        "success": True,
        "message": f"Event {event.code} deactivated successfully",
        "event": {
            "id": event.id,
            "code": event.code,
            "is_active": False
        }
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

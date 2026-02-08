from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import jwt

from database.connection import get_db
from models.establishment import Establishment
from models.admin_user import AdminUser
from models.event import Event
from utils.auth import create_master_token, verify_master_token

router = APIRouter()

# Master credentials from environment variables for security
MASTER_USERNAME = os.getenv("MASTER_USERNAME", "master")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD", "123456")


def verify_master_token_dependency(authorization: Optional[str] = Header(None)):
    """
    Dependency to verify JWT master token in requests
    Validates token signature and expiration
    Ensures only authenticated master can access protected routes
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Remove "Bearer " prefix if present
    token = authorization.replace("Bearer ", "").strip()

    try:
        # Verify JWT token
        if not verify_master_token(token):
            raise HTTPException(status_code=403, detail="Invalid master token - Access denied")

        return token

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired - Please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid master token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


class MasterLogin(BaseModel):
    username: str
    password: str


class EstablishmentCreate(BaseModel):
    name: str


class EstablishmentUpdate(BaseModel):
    name: str


class AdminUserCreate(BaseModel):
    username: str
    password: str
    establishment_id: str


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    establishment_id: Optional[str] = None


class AdminPasswordUpdate(BaseModel):
    password: str


@router.post("/master/login")
def master_login(credentials: MasterLogin):
    """
    Master login endpoint with JWT token generation
    Validates credentials from environment variables
    Returns a signed JWT token that expires in 8 hours
    """
    if credentials.username != MASTER_USERNAME or credentials.password != MASTER_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token with expiration
    token = create_master_token()

    return {
        "success": True,
        "token": token,  # JWT token with 8-hour expiration
        "role": "master",
        "message": "Master login successful"
    }


@router.post("/master/establishments")
def create_establishment(
    establishment: EstablishmentCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Create a new establishment
    Only accessible by master account
    """
    db_establishment = Establishment(name=establishment.name)
    db.add(db_establishment)
    db.commit()
    db.refresh(db_establishment)

    return {
        "success": True,
        "establishment": {
            "id": db_establishment.id,
            "name": db_establishment.name,
            "created_at": db_establishment.created_at.isoformat()
        }
    }


@router.get("/master/establishments")
def list_establishments(
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    List all establishments with admin and event counts
    Only accessible by master account
    """
    establishments = db.query(Establishment).order_by(Establishment.created_at.desc()).all()

    return {
        "establishments": [
            {
                "id": e.id,
                "name": e.name,
                "created_at": e.created_at.isoformat(),
                "admin_count": db.query(AdminUser).filter(AdminUser.establishment_id == e.id).count(),
                "event_count": db.query(Event).filter(Event.establishment_id == e.id).count()
            }
            for e in establishments
        ]
    }


@router.get("/master/establishments/{establishment_id}")
def get_establishment(
    establishment_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Get a single establishment with detailed stats
    Only accessible by master account
    """
    establishment = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not establishment:
        raise HTTPException(404, "Establishment not found")

    admins = db.query(AdminUser).filter(AdminUser.establishment_id == establishment_id).all()
    events = db.query(Event).filter(Event.establishment_id == establishment_id).all()

    return {
        "establishment": {
            "id": establishment.id,
            "name": establishment.name,
            "created_at": establishment.created_at.isoformat(),
            "admin_count": len(admins),
            "event_count": len(events),
            "admins": [{"id": a.id, "username": a.username} for a in admins],
            "events": [{"id": e.id, "code": e.code, "status": "active" if e.is_active else "inactive"} for e in events]
        }
    }


@router.put("/master/establishments/{establishment_id}")
def update_establishment(
    establishment_id: str,
    data: EstablishmentUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Update establishment name
    Only accessible by master account
    """
    establishment = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not establishment:
        raise HTTPException(404, "Establishment not found")

    establishment.name = data.name
    db.commit()
    db.refresh(establishment)

    return {
        "success": True,
        "establishment": {
            "id": establishment.id,
            "name": establishment.name,
            "created_at": establishment.created_at.isoformat()
        }
    }


@router.delete("/master/establishments/{establishment_id}")
def delete_establishment(
    establishment_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Delete establishment and all associated data (admin users, events, rooms, tables, users, notes)
    Only accessible by master account
    """
    from models.room import Room
    from models.table import Table
    from models.user import User
    from models.note import Note

    establishment = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not establishment:
        raise HTTPException(404, "Establishment not found")

    # Get all events for this establishment
    events = db.query(Event).filter(Event.establishment_id == establishment_id).all()
    event_codes = [e.code for e in events]

    # Delete notes -> users -> tables -> rooms for each event
    for code in event_codes:
        rooms = db.query(Room).filter(Room.event_code == code).all()
        for room in rooms:
            # Delete notes
            db.query(Note).filter(Note.room_id == room.id).delete()
            # Delete users
            db.query(User).filter(User.room_id == room.id).delete()
            # Delete tables
            db.query(Table).filter(Table.room_id == room.id).delete()
        # Delete rooms
        db.query(Room).filter(Room.event_code == code).delete()

    # Delete events
    db.query(Event).filter(Event.establishment_id == establishment_id).delete()

    # Delete admin users
    db.query(AdminUser).filter(AdminUser.establishment_id == establishment_id).delete()

    # Delete establishment
    db.delete(establishment)
    db.commit()

    return {
        "success": True,
        "message": f"Establishment '{establishment.name}' and all associated data deleted successfully"
    }


@router.post("/master/admin-users")
def create_admin_user(
    admin: AdminUserCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Create a new admin user for an establishment
    Only accessible by master account
    """
    # Check if establishment exists
    establishment = db.query(Establishment).filter(Establishment.id == admin.establishment_id).first()
    if not establishment:
        raise HTTPException(404, "Establishment not found")

    # Check if username already exists
    existing_user = db.query(AdminUser).filter(AdminUser.username == admin.username).first()
    if existing_user:
        raise HTTPException(400, "Username already exists")

    # Create admin user
    db_admin = AdminUser(
        username=admin.username,
        password_hash=AdminUser.hash_password(admin.password),
        establishment_id=admin.establishment_id
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    return {
        "success": True,
        "admin_user": {
            "id": db_admin.id,
            "username": db_admin.username,
            "establishment_id": db_admin.establishment_id,
            "establishment_name": establishment.name,
            "created_at": db_admin.created_at.isoformat()
        }
    }


@router.get("/master/admin-users")
def list_admin_users(
    establishment_id: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    List all admin users with event counts, optionally filtered by establishment
    Only accessible by master account
    """
    query = db.query(AdminUser, Establishment).join(
        Establishment, AdminUser.establishment_id == Establishment.id
    )

    if establishment_id:
        query = query.filter(AdminUser.establishment_id == establishment_id)

    results = query.order_by(AdminUser.created_at.desc()).all()

    return {
        "admin_users": [
            {
                "id": admin.id,
                "username": admin.username,
                "establishment_id": admin.establishment_id,
                "establishment_name": est.name,
                "created_at": admin.created_at.isoformat(),
                "event_count": db.query(Event).filter(Event.establishment_id == admin.establishment_id).count()
            }
            for admin, est in results
        ]
    }


@router.get("/master/admin-users/{admin_id}")
def get_admin_user(
    admin_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Get a single admin user with detailed info
    Only accessible by master account
    """
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(404, "Admin user not found")

    establishment = db.query(Establishment).filter(Establishment.id == admin.establishment_id).first()
    events = db.query(Event).filter(Event.establishment_id == admin.establishment_id).all()

    return {
        "admin_user": {
            "id": admin.id,
            "username": admin.username,
            "establishment_id": admin.establishment_id,
            "establishment_name": establishment.name if establishment else "N/A",
            "created_at": admin.created_at.isoformat(),
            "event_count": len(events),
            "events": [{"id": e.id, "code": e.code, "status": "active" if e.is_active else "inactive"} for e in events]
        }
    }


@router.put("/master/admin-users/{admin_id}")
def update_admin_user(
    admin_id: str,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Update admin user (username and/or establishment)
    Only accessible by master account
    """
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(404, "Admin user not found")

    # Check if new username already exists (if changing username)
    if data.username and data.username != admin.username:
        existing = db.query(AdminUser).filter(AdminUser.username == data.username).first()
        if existing:
            raise HTTPException(400, "Username already exists")
        admin.username = data.username

    # Check if new establishment exists (if changing establishment)
    if data.establishment_id and data.establishment_id != admin.establishment_id:
        establishment = db.query(Establishment).filter(Establishment.id == data.establishment_id).first()
        if not establishment:
            raise HTTPException(404, "Establishment not found")

        # Move all events to new establishment
        db.query(Event).filter(Event.establishment_id == admin.establishment_id).update(
            {"establishment_id": data.establishment_id}
        )
        admin.establishment_id = data.establishment_id

    db.commit()
    db.refresh(admin)

    establishment = db.query(Establishment).filter(Establishment.id == admin.establishment_id).first()

    return {
        "success": True,
        "admin_user": {
            "id": admin.id,
            "username": admin.username,
            "establishment_id": admin.establishment_id,
            "establishment_name": establishment.name if establishment else "N/A",
            "created_at": admin.created_at.isoformat()
        }
    }


@router.put("/master/admin-users/{admin_id}/password")
def update_admin_password(
    admin_id: str,
    data: AdminPasswordUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Update admin user password
    Only accessible by master account
    """
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(404, "Admin user not found")

    admin.password_hash = AdminUser.hash_password(data.password)
    db.commit()

    return {
        "success": True,
        "message": "Password updated successfully"
    }


@router.delete("/master/admin-users/{admin_id}")
def delete_admin_user(
    admin_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    Delete admin user
    Note: Associated events remain but without an admin owner
    Only accessible by master account
    """
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(404, "Admin user not found")

    username = admin.username
    db.delete(admin)
    db.commit()

    return {
        "success": True,
        "message": f"Admin user '{username}' deleted successfully"
    }


@router.get("/master/events")
def list_all_events(
    establishment_id: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_master_token_dependency)
):
    """
    List all events across all establishments
    Optionally filter by establishment
    Only accessible by master account
    """
    from datetime import datetime

    query = db.query(Event, Establishment).outerjoin(
        Establishment, Event.establishment_id == Establishment.id
    )

    if establishment_id:
        query = query.filter(Event.establishment_id == establishment_id)

    results = query.order_by(Event.created_at.desc()).all()
    now = datetime.utcnow()

    return {
        "events": [
            {
                "id": event.id,
                "code": event.code,
                "establishment_id": event.establishment_id,
                "establishment_name": est.name if est else "N/A",
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat(),
                "status": "active" if (event.is_active and event.start_date <= now <= event.end_date) else "expired",
                "number_of_tables": event.number_of_tables
            }
            for event, est in results
        ]
    }

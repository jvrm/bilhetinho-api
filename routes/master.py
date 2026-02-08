from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.connection import get_db
from models.establishment import Establishment
from models.admin_user import AdminUser
from models.event import Event

router = APIRouter()

# Hardcoded master credentials (MVP)
MASTER_USERNAME = "master"
MASTER_PASSWORD = "123456"  # Change this in production!


class MasterLogin(BaseModel):
    username: str
    password: str


class EstablishmentCreate(BaseModel):
    name: str


class AdminUserCreate(BaseModel):
    username: str
    password: str
    establishment_id: str


@router.post("/master/login")
def master_login(credentials: MasterLogin):
    """
    Master login endpoint (hardcoded for MVP)
    Returns a token and role for authentication
    """
    if credentials.username != MASTER_USERNAME or credentials.password != MASTER_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "success": True,
        "token": "master-session-token",
        "role": "master",
        "message": "Master login successful"
    }


@router.post("/master/establishments")
def create_establishment(establishment: EstablishmentCreate, db: Session = Depends(get_db)):
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
def list_establishments(db: Session = Depends(get_db)):
    """
    List all establishments
    Only accessible by master account
    """
    establishments = db.query(Establishment).order_by(Establishment.created_at.desc()).all()

    return {
        "establishments": [
            {
                "id": e.id,
                "name": e.name,
                "created_at": e.created_at.isoformat()
            }
            for e in establishments
        ]
    }


@router.post("/master/admin-users")
def create_admin_user(admin: AdminUserCreate, db: Session = Depends(get_db)):
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
def list_admin_users(establishment_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    List all admin users, optionally filtered by establishment
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
                "created_at": admin.created_at.isoformat()
            }
            for admin, est in results
        ]
    }


@router.get("/master/events")
def list_all_events(establishment_id: Optional[str] = None, db: Session = Depends(get_db)):
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

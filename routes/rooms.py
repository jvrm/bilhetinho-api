from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models.room import Room
from models.table import Table
from schemas.room import RoomResponse, RoomCreate
from schemas.table import TableResponse

router = APIRouter()

@router.get("/room/active", response_model=RoomResponse)
def get_active_room(db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.is_active == True).first()
    if not room:
        raise HTTPException(status_code=404, detail="Nenhuma sala ativa no momento")
    return room

@router.get("/room/{room_id}/tables", response_model=list[TableResponse])
def get_room_tables(room_id: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")

    if not room.is_active:
        raise HTTPException(status_code=403, detail="Evento foi encerrado pelo administrador")

    tables = db.query(Table).filter(Table.room_id == room_id).order_by(Table.number).all()
    return tables

@router.post("/room", response_model=RoomResponse)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    db_room = Room(name=room.name, event_code=room.event_code)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.patch("/room/{room_id}/activate", response_model=RoomResponse)
def activate_room(room_id: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")

    # Deactivate all rooms first
    db.query(Room).update({Room.is_active: False})

    # Activate this room
    room.is_active = True
    db.commit()
    db.refresh(room)
    return room

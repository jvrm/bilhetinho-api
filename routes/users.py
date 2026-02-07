from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models.user import User
from models.table import Table
from models.room import Room
from schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == user.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    room = db.query(Room).filter(Room.id == table.room_id).first()
    if not room or not room.is_active:
        raise HTTPException(status_code=400, detail="Sala não está ativa")

    db_user = User(
        nickname=user.nickname,
        table_id=user.table_id,
        room_id=room.id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.get("/tables/{table_id}/users", response_model=list[UserResponse])
def get_table_users(table_id: str, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    users = db.query(User).filter(User.table_id == table_id).all()
    return users

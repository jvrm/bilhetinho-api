from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models.room import Room
from models.table import Table

router = APIRouter()

@router.post("/seed")
def seed_database(db: Session = Depends(get_db)):
    """
    Endpoint para popular o banco de dados com dados iniciais.
    ATENÇÃO: Limpa todos os dados existentes!
    """
    try:
        # Limpar dados existentes
        db.query(Table).delete()
        db.query(Room).delete()
        db.commit()

        # Criar sala ativa
        room = Room(
            name="Noite do Bilhetinho - Bar Central",
            is_active=True
        )
        db.add(room)
        db.commit()
        db.refresh(room)

        # Criar 10 mesas
        tables_created = []
        for i in range(1, 11):
            table = Table(room_id=room.id, number=i)
            db.add(table)
            tables_created.append(f"Mesa {i}")

        db.commit()

        return {
            "success": True,
            "message": "Banco de dados populado com sucesso!",
            "room": {
                "id": room.id,
                "name": room.name,
                "is_active": room.is_active
            },
            "tables_created": len(tables_created),
            "tables": tables_created
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao popular banco: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string

from database.connection import get_db
from models.room import Room
from models.table import Table
from models.event import Event

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
        db.query(Event).delete()
        db.commit()

        # Generate event code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Create event
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        event = Event(
            code=code,
            start_date=start,
            end_date=end,
            number_of_tables=10,
            is_active=True
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        # Criar sala ativa
        room = Room(
            name="Noite do Bilhetinho - Bar Central",
            is_active=True,
            event_code=code
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
            "event": {
                "code": event.code,
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat()
            },
            "room": {
                "id": room.id,
                "name": room.name,
                "is_active": room.is_active,
                "event_code": room.event_code
            },
            "tables_created": len(tables_created),
            "tables": tables_created,
            "access_url": f"http://localhost:3000?code={code}"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao popular banco: {str(e)}")

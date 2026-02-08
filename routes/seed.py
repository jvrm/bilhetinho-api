from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
import qrcode
import io
import base64

from database.connection import get_db
from models.room import Room
from models.table import Table
from models.event import Event
from models.establishment import Establishment
from models.admin_user import AdminUser
from models.user import User
from models.note import Note

router = APIRouter()


def generate_event_code(db: Session) -> str:
    """Generate unique 6-character event code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing = db.query(Event).filter(Event.code == code).first()
        if not existing:
            return code


@router.post("/seed")
def seed_database(db: Session = Depends(get_db)):
    """
    Endpoint para popular o banco de dados com dados completos de teste.
    ATENÇÃO: Limpa todos os dados existentes!

    Cria:
    - 3 Estabelecimentos
    - 1 Admin user para cada estabelecimento
    - 1 Evento ativo para cada estabelecimento
    """
    try:
        # Limpar dados existentes
        db.query(Note).delete()
        db.query(User).delete()
        db.query(Table).delete()
        db.query(Room).delete()
        db.query(Event).delete()
        db.query(AdminUser).delete()
        db.query(Establishment).delete()
        db.commit()

        establishments_data = []

        # Criar 3 estabelecimentos
        establishments_info = [
            {"name": "Bar Central", "username": "bar_central", "password": "senha123", "tables": 15},
            {"name": "Noite do Bilhetinho", "username": "noite_bilhetinho", "password": "senha123", "tables": 20},
            {"name": "Casa Show Tropical", "username": "casa_tropical", "password": "senha123", "tables": 10}
        ]

        for est_info in establishments_info:
            # Criar estabelecimento
            establishment = Establishment(name=est_info["name"])
            db.add(establishment)
            db.commit()
            db.refresh(establishment)

            # Criar admin user
            admin_user = AdminUser(
                username=est_info["username"],
                password_hash=AdminUser.hash_password(est_info["password"]),
                establishment_id=establishment.id
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            # Gerar código do evento
            code = generate_event_code(db)

            # Criar evento
            start = datetime.utcnow()
            end = start + timedelta(hours=6)

            # Gerar QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(f"https://bilhetinho.vercel.app/?code={code}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            qr_data_uri = f"data:image/png;base64,{qr_base64}"

            event = Event(
                code=code,
                establishment_id=establishment.id,
                start_date=start,
                end_date=end,
                number_of_tables=est_info["tables"],
                is_active=True,
                qr_code_data=qr_data_uri
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            # Criar sala
            room = Room(
                name=f"Evento {code}",
                is_active=True,
                event_code=code
            )
            db.add(room)
            db.commit()
            db.refresh(room)

            # Criar mesas
            for i in range(1, est_info["tables"] + 1):
                table = Table(room_id=room.id, number=i)
                db.add(table)

            db.commit()

            establishments_data.append({
                "establishment": {
                    "id": establishment.id,
                    "name": establishment.name
                },
                "admin": {
                    "username": admin_user.username,
                    "password": est_info["password"]
                },
                "event": {
                    "code": event.code,
                    "tables": est_info["tables"],
                    "access_url": f"http://localhost:3001?code={code}"
                }
            })

        return {
            "success": True,
            "message": "✅ Banco de dados populado com sucesso!",
            "master_credentials": {
                "username": "master",
                "password": "123456",
                "login_url": "http://localhost:3001/master"
            },
            "establishments": establishments_data,
            "summary": {
                "total_establishments": len(establishments_data),
                "total_events": len(establishments_data),
                "total_admin_users": len(establishments_data)
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao popular banco: {str(e)}")

from database.connection import SessionLocal, engine, Base
from models.room import Room
from models.table import Table

def seed_database():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        existing_room = db.query(Room).first()
        if existing_room:
            print("Banco de dados já possui dados. Limpando...")
            db.query(Table).delete()
            db.query(Room).delete()
            db.commit()

        room = Room(
            name="Noite do Bilhetinho - Bar Central",
            is_active=True
        )
        db.add(room)
        db.commit()
        db.refresh(room)

        print(f"Sala criada: {room.name} (ID: {room.id})")

        for i in range(1, 11):
            table = Table(room_id=room.id, number=i)
            db.add(table)

        db.commit()
        print("10 mesas criadas (Mesa 1 a Mesa 10)")

        print("\n✓ Seed concluído com sucesso!")
        print(f"✓ Sala ativa: {room.name}")
        print(f"✓ Total de mesas: 10")

    except Exception as e:
        print(f"Erro ao popular banco: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

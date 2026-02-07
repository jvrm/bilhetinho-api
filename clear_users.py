from database.connection import SessionLocal
from models.user import User
from models.note import Note

def clear_users_and_notes():
    db = SessionLocal()

    try:
        users_deleted = db.query(User).delete()
        notes_deleted = db.query(Note).delete()
        db.commit()

        print(f"✓ {users_deleted} usuários removidos")
        print(f"✓ {notes_deleted} bilhetes removidos")
        print("\nBanco limpo! Pronto para nova sessão.")

    except Exception as e:
        print(f"Erro ao limpar banco: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_users_and_notes()

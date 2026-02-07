from sqlalchemy import Column, Boolean, text
from database.connection import engine

def add_anonymous_column():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE notes ADD COLUMN is_anonymous BOOLEAN DEFAULT 1"))
            conn.commit()
            print("✓ Coluna is_anonymous adicionada com sucesso!")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✓ Coluna is_anonymous já existe")
            else:
                print(f"Erro: {e}")

if __name__ == "__main__":
    add_anonymous_column()

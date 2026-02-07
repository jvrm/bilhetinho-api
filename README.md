# Bilhetinho Backend

API FastAPI para o sistema Bilhetinho.

## Setup

### 1. Criar ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env conforme necessário
```

### 4. Popular banco de dados inicial

```bash
python seed.py
```

### 5. Rodar servidor

```bash
# Modo desenvolvimento
uvicorn main:app --reload

# Ou usando Python diretamente
python main.py
```

A API estará disponível em `http://localhost:8000`

## Documentação Automática

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Estrutura

```
backend/
├── main.py              # Entry point da aplicação
├── models/              # Modelos SQLAlchemy
│   ├── room.py
│   ├── table.py
│   ├── user.py
│   └── note.py
├── schemas/             # Schemas Pydantic
│   ├── room.py
│   ├── table.py
│   ├── user.py
│   └── note.py
├── routes/              # Rotas da API
│   ├── rooms.py
│   ├── users.py
│   └── notes.py
├── database/            # Configuração do banco
│   └── connection.py
├── requirements.txt     # Dependências Python
└── seed.py             # Script para popular BD inicial
```

## Endpoints Principais

### Salas
- `GET /api/room/active` - Buscar sala ativa
- `GET /api/room/{room_id}/tables` - Listar mesas da sala

### Usuários
- `POST /api/users` - Criar usuário temporário
- `GET /api/users/{user_id}` - Buscar usuário

### Bilhetes
- `POST /api/notes` - Enviar bilhete
- `GET /api/tables/{table_id}/notes` - Receber bilhetes da mesa
- `POST /api/notes/{note_id}/accept` - Aceitar bilhete
- `POST /api/notes/{note_id}/ignore` - Ignorar bilhete

## Banco de Dados

### Desenvolvimento
Por padrão usa SQLite (`bilhetinho.db`)

### Produção
Configure PostgreSQL no `.env`:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

## Deploy

### Railway / Render
1. Configure a variável `DATABASE_URL` com PostgreSQL
2. Configure `CORS_ORIGINS` com URL do frontend
3. Use `uvicorn main:app --host 0.0.0.0 --port $PORT`

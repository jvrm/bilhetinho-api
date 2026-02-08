from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from database.connection import engine, Base
from routes import rooms, users, notes, seed, admin, master

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Bilhetinho API",
    description="API para sistema de bilhetes anônimos temporários",
    version="1.0.0"
)

# CORS configuration - Restrict to specific origins for security
allowed_origins = [
    "https://bilhetinho.vercel.app",  # Production
    "http://localhost:3001",           # Local development frontend
    "http://localhost:3000",           # Alternative local dev port
]

# In development, allow localhost with any port
if os.getenv("ENVIRONMENT") == "development":
    allowed_origins.append("http://localhost:*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Enable credentials (cookies, auth headers)
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Specific methods only
    allow_headers=["Content-Type", "Authorization"],  # Specific headers only
)

# Include routers (no /api prefix - routes are at root level)
app.include_router(rooms.router, tags=["Rooms"])
app.include_router(users.router, tags=["Users"])
app.include_router(notes.router, tags=["Notes"])
app.include_router(seed.router, tags=["Seed"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(master.router, tags=["Master"])


@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Bilhetinho API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    # Local development uses port 8001, production uses 8000
    port = int(os.getenv("API_PORT", 8001))
    uvicorn.run("main:app", host=host, port=port, reload=True)

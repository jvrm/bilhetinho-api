from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from database.connection import engine, Base
from routes import rooms, users, notes, seed, admin

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

# CORS configuration - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (no /api prefix - routes are at root level)
app.include_router(rooms.router, tags=["Rooms"])
app.include_router(users.router, tags=["Users"])
app.include_router(notes.router, tags=["Notes"])
app.include_router(seed.router, tags=["Seed"])
app.include_router(admin.router, tags=["Admin"])


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
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database.connection import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tables = relationship("Table", back_populates="room", cascade="all, delete-orphan")
    users = relationship("User", back_populates="room", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="room", cascade="all, delete-orphan")

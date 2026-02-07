from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nickname = Column(String, nullable=False)
    table_id = Column(String, ForeignKey("tables.id"), nullable=False)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="users")
    table = relationship("Table", back_populates="users")

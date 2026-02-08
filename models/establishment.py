from sqlalchemy import Column, String, DateTime
from datetime import datetime
import uuid
from database.connection import Base


class Establishment(Base):
    """
    Establishment model - represents a bar, club, or venue
    Each establishment can have multiple admin users and events
    """
    __tablename__ = "establishments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Establishment(name={self.name})>"

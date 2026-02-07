from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from database.connection import Base

class NoteStatus(str, enum.Enum):
    SENT = "sent"
    ACCEPTED = "accepted"
    IGNORED = "ignored"

class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    from_table_id = Column(String, ForeignKey("tables.id"), nullable=False)
    to_table_id = Column(String, ForeignKey("tables.id"), nullable=False)
    message = Column(String(140), nullable=False)
    status = Column(Enum(NoteStatus), default=NoteStatus.SENT)
    is_anonymous = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="notes")
    from_table = relationship("Table", foreign_keys=[from_table_id], back_populates="notes_sent")
    to_table = relationship("Table", foreign_keys=[to_table_id], back_populates="notes_received")

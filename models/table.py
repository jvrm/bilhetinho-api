from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from database.connection import Base

class Table(Base):
    __tablename__ = "tables"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    number = Column(Integer, nullable=False)

    room = relationship("Room", back_populates="tables")
    users = relationship("User", back_populates="table")
    notes_sent = relationship("Note", foreign_keys="Note.from_table_id", back_populates="from_table")
    notes_received = relationship("Note", foreign_keys="Note.to_table_id", back_populates="to_table")

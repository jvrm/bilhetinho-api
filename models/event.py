from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from datetime import datetime
import uuid
from database.connection import Base


class Event(Base):
    """
    Event model - represents a bar event with access code

    Only one event can be active at a time.
    Each event has a unique 6-character code used for access control.
    """
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(6), unique=True, nullable=False, index=True)
    establishment_id = Column(String, ForeignKey("establishments.id"), nullable=True)  # Nullable for backward compatibility
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    number_of_tables = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=False)
    qr_code_data = Column(String, nullable=True)  # Base64 encoded QR code
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Event(code={self.code}, active={self.is_active})>"

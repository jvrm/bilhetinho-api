from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class NoteStatus(str, Enum):
    SENT = "sent"
    ACCEPTED = "accepted"
    IGNORED = "ignored"

class NoteCreate(BaseModel):
    from_table_id: str
    to_table_id: str
    message: str = Field(..., min_length=1, max_length=140)
    is_anonymous: bool = True

class NoteResponse(BaseModel):
    id: str
    room_id: str
    from_table_id: str
    to_table_id: str
    message: str
    status: NoteStatus
    is_anonymous: bool
    created_at: datetime

    class Config:
        from_attributes = True

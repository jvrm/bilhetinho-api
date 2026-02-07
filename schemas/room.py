from pydantic import BaseModel
from datetime import datetime

class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    event_code: str

class RoomResponse(RoomBase):
    id: str
    is_active: bool
    event_code: str
    created_at: datetime

    class Config:
        from_attributes = True

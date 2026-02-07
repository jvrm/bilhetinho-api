from pydantic import BaseModel
from datetime import datetime

class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

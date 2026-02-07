from pydantic import BaseModel, Field
from datetime import datetime

class UserCreate(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    table_id: str

class UserResponse(BaseModel):
    id: str
    nickname: str
    table_id: str
    room_id: str
    created_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel

class TableBase(BaseModel):
    number: int

class TableCreate(TableBase):
    room_id: str

class TableResponse(TableBase):
    id: str
    room_id: str

    class Config:
        from_attributes = True

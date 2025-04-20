from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FarmBase(BaseModel):
    name: str
    location: str
    size: float

class FarmCreate(FarmBase):
    pass

class FarmUpdate(FarmBase):
    name: Optional[str] = None
    location: Optional[str] = None
    size: Optional[float] = None

class Farm(FarmBase):
    id: int
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True 
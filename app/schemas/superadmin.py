from pydantic import BaseModel, Field
from datetime import date
from models import ZoneEnum
from typing import Literal, Optional


class CreateCalender(BaseModel):
    date: date
    holiday: str
    
class CalenderResponse(BaseModel):
    date: date
    holiday: str

class AnnouncementBase(BaseModel):
    title: str
    description: str
    # campus: Optional[List[str]] = Field(default=[])
    # zone: Optional[ZoneEnum] = None
    # link: Optional[str] = None

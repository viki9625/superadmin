from models import LeaveTypeEnum, StatusEnum
from beanie import PydanticObjectId
from datetime import date
from pydantic import BaseModel
from typing import Optional

class LeaveBase(BaseModel):
    start_date: date
    end_date: date
    out_of_station: Optional[bool] = False
    address_out_of_station: Optional[str] = None
    mobile_no_of_contact: Optional[str] = None
    child_age: Optional[int] = None
    reason: str
    

    
class LeaveResponse(BaseModel):
    leave_type: LeaveTypeEnum
    start_date: str
    end_date: str
    status: StatusEnum
    
class LeaveUpdate(BaseModel):
    reason: str 
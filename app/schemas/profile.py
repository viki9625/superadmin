from typing import Optional, List
from pydantic import BaseModel
from models import BankDetail, RoleEnum
from datetime import date, datetime, time
from schemas.auth import CampusCreate


# Pydantic model for bank details
class BankDetailRequest(BaseModel):
    bank_name: Optional[str] = None
    account_number: str
    ifsc_code: str
    branch_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    pan_number: str

class BankDetailResponse(BaseModel):
    bank_name: Optional[str]
    account_number: str
    ifsc_code: str
    branch_name: Optional[str]
    account_holder_name: str
    pan_number: str
    
class CampusResponse(BaseModel):
    name: str
    
class GetProfile(BaseModel):
    user_id: Optional[int] = None # Make optional if not always present
    name: str
    email: str
    role: RoleEnum # Consider using RoleEnum here for consistency if desired
    campus: CampusResponse = None
    departmenrt: Optional[List[str]] = None # Make optional if not always present
    designation: Optional[List[str]] = None # Make optional if not always present
    date_of_joining: Optional[date] = None # Make optional if not always present
    bank_detail: Optional[BankDetailRequest] = None # <-- Changed 'Bank_detail' to 'bank_detail'
    picture: Optional[str] = None # <-- Add field for profile picture URL

    # class Config:
    #     orm_attributes = True
    
class UserAttendanceReport(BaseModel):
    user_id: int
    name: str
    Date: date
    punch_in_time: datetime
    punch_out_time: Optional[datetime]
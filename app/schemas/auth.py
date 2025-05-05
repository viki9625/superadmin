from pydantic import BaseModel, EmailStr, Field
from models import RoleEnum, ZoneEnum, GenderEnum
from datetime import date
from typing import Optional, List, Tuple

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
class AdminUserCreate(BaseModel):
    user_id: int = Field(unique=True)
    name: Optional[str] = None
    email: EmailStr = Field(
        # pattern=r"^[a-zA-Z0-9._%+-]+@dseu\.ac\.in$",
        unique=True,
        description="Email must belong to the @dseu.ac.in domain."
    )
    gender: GenderEnum
    dob: Optional[date] = None
    date_of_joining: Optional[date] = Field(default_factory=date.today)
    designation: Optional[List[str]]
    role: RoleEnum = Field(default=RoleEnum.Employee)
    campus: str = Field(default="BPIBS")
    department: List[str] = Field(default=[])
    password: str = Field(
    pattern=r'[A-Za-z\d@$!%*?&_-]{8,}',
    description="Password must be at least 8 characters long and contain letters, numbers, and special characters."
)

    

class BankDetailCreate(BaseModel):
    account_number: str
    account_holder_name: str
    ifsc_code: str
    pan_number: str

class UserResponse(BaseModel):
    email: EmailStr
    role: RoleEnum
    Date_of_joining: date
    # Daily_working_hours: float
    # Monthly_working_hours: int
    # Designation: str
    # Bank_detail: BankDetail
    

class Token(BaseModel):
    access_token: str
    token_type: str
    # refresh_token: str # Client will receive this
    # email: EmailStr
    # role: RoleEnum

    
class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
    password: str 
    
class University(BaseModel):
    name: str
    description: str

class CampusCreate(BaseModel):
    campus_id: int = Field(unique = True)
    name: str = Field(unique = True)
    address: Optional[str] = None
    geo_boundary: List[Tuple[float, float]]
    description: Optional[str] = None

class CampusResponse(BaseModel):
    campus_id: int
    name: str
    zone: ZoneEnum
    address: Optional[str] = None
    description: Optional[str] = None
    geo_boundary: List[Tuple[float, float]]

class UpdateCampus(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    # geo_boundary: Optional[List[Tuple[float, float]]] = Field(default=None)


    
    
from pydantic import BaseModel, Field
from beanie import Document, Indexed
from beanie.odm.fields import Link
from beanie import Insert, before_event
from pydantic import Field, model_validator, EmailStr # Added EmailStr
from datetime import datetime, date, time
from enum import Enum
from typing import Optional, List, Tuple, Literal
from uuid import uuid4
import os
import dotenv
dotenv.load_dotenv()


class DesignationEnum(str, Enum):
    PROFESSOR = "Professor"
    ASSISTANT_PROFESSOR = "Assistant Professor"
    ASSOCIATE_PROFESSOR = "Associate Professor"
    LECTURER = "Lecturer"
    CLERK = "Clerk"
    LAB_ASSISTANT = "Lab Assistant"
    ADMINISTRATIVE_OFFICER = "Administrative Officer"
    REGISTRAR = "Registrar"
    DEAN = "Dean"
    # Add more as needed


class StaffTypeEnum(str, Enum):
    TEACHING = "Teaching"
    NON_TEACHING = "Non-Teaching"
    ADMINISTRATIVE = "Administrative"
    TECHNICAL = "Technical"
    SUPPORT = "Support"

# --- Enums ---
class RoleEnum(str, Enum):
    Admin = "admin"
    SuperAdmin = "super_admin"
    Employee = "employee"

class GenderEnum(str, Enum):
    Male = "Male"
    Female = "Female"

class LeaveTypeEnum(str, Enum):
    CasualLeave = "Casual Leave"
    RestrictedLeave = "Restricted Leave"
    CommutedLeave = "Commuted Leave"
    ChildCareLeave = "Child Care Leave"
    SpecialCasualLeave = "Special Casual Leave"
    MaternityLeave = "Maternity Leave"
    PaternityLeave = "Paternity Leave"
    EarnedLeave = "Earned Leave"
    HalfPayLeave = "Half Pay Leave"
    JoiningReportAfterAvailingLeave = "Joining Report After Availing Leave"
    Other = "Other"

class StatusEnum(str, Enum):
    Approved = "Approved"
    Pending = "Pending"
    Rejected = "Rejected"
    
class AttendanceStatusEnum(str, Enum):
    Present = "Present"
    Absent = "Absent"
    OnLeave = "On Leave"
    OnDuty = "On Duty"

# --- Documents ---

class BankDetail(Document):
    bank_name: Optional[str] = None
    account_number: Indexed(bytes, unique=True)
    ifsc_code: bytes
    branch_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    pan_number: bytes
    
class ZoneEnum(str, Enum):
    East = "East"
    West = "West"
    North = "North"
    South = "South"
    Central = "Central"

class Calender(Document):
    date: date
    holiday: str

    
class Campus(Document):
    campus_id: Indexed(int, unique=True)
    name: Indexed(str, unique=True)
    zone: Optional[ZoneEnum] = None
    description: Optional[str] = None
    address: Optional[str] = None
    geo_boundary: Optional[List[Tuple[float, float]]] = None

    # current_location: Optional[Tuple[float, float]] = None
    
    # @model_validator(mode="after")
    # def validate_end_date(cls, values):
    #     if values["start_date"] > values["end_date"]:
    #         raise ValueError("End date must be after start date.")
    #     return values

class User(Document):
    user_id: Indexed(int, unique=True)
    email: Indexed(EmailStr, unique=True)
    name: Optional[str] = "User"
    campus: Optional[Link[Campus]] = None
    gender: Optional[GenderEnum] = None
    dob: Optional[date] = None
    date_of_joining: Optional[date] = Field(default=date.today())
    role: RoleEnum = Field(default=RoleEnum.Employee)
    designation: Optional[List[str]] = []
    staff_type: Optional[str] = None
    department: Optional[List[str]] = Field(default=[])
    is_active: bool = Field(default=True)
    bank_detail: Optional[Link[BankDetail]] = None
    picture: Optional[str] = None
    totp_secret: Optional[str] = None
    hashed_password: Optional[str] = Field(default=None)

    
class Attendance(Document):
    link_id: Link[User]
    user_id: int  # If you're using ObjectId, change this accordingly
    name: str
    Date: date = Field(default = date.today())
    punch_in_time: datetime = Field(default= datetime.now())
    punch_out_time: Optional[datetime] = None
    last_check: Optional[datetime] = None
    location_status: Optional[bool] = True
    total_out_of_bound_time_in_minutes: Optional[float] = Field(default=0.0)
    time_duration_in_hours: Optional[float] = Field(default=0.0)
    status: AttendanceStatusEnum
    @before_event(Insert)
    async def calculate_time_duration(self):
        if self.punch_in_time and self.punch_out_time:
            self.time_duration_in_hours = (self.punch_out_time - self.punch_in_time).total_seconds() / 3600
        else:
            self.time_duration_in_hours = (datetime.now() - self.punch_in_time).total_seconds() / 3600
    

class Leave(Document):
    user_id: Link[User]
    request_date: date = Field(default = date.today())
    leave_type: LeaveTypeEnum
    start_date: date
    end_date: date
    out_of_station: Optional[bool] = False
    address_out_of_station: Optional[str] = None
    mobile_no_of_contact: Optional[str] = None
    child_age: Optional[int] = None
    reason: Optional[str] = None
    status: StatusEnum = Field(default=StatusEnum.Pending)
    remarks: Optional[str] = None


class Announcement(Document):
    title: str
    description: str
    current_date: date = Field(default = date.today())
    campus: Optional[List[str]] = Field(default=[])
    zone: Optional[ZoneEnum] = None  # <--- Potential issue here
    send_to: Optional[str] = None
    link: Optional[str] = None
    image: Optional[str] = None
    

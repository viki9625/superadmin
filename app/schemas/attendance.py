from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime, time, date

class Location(BaseModel):
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)

    
class PunchInResponse(BaseModel):
    message: str

class PunchOutResponse(BaseModel):
    message: str
    punch_out_time: time
    
class TotalDurationResponse(BaseModel):
    punch_in_time: time
    punch_out_time: Optional[time]
    total_duration_seconds: int
    formatted_duration: str
    
class LocationStatusResponse(BaseModel):
    user_email: str
    date: date
    is_within_boundary: bool
    last_updated: time
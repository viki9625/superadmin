from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse, Response
from utils.auth import get_current_user, role_dependency
from schemas.attendance import Location, PunchInResponse, PunchOutResponse, TotalDurationResponse, LocationStatusResponse
from datetime import date, datetime, time, timezone
from models import User, RoleEnum, Campus, Attendance, AttendanceStatusEnum
from utils.attendance import is_point_within_polygon, fetch_attendance_records, generate_csv_report, generate_pdf_report
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from decimal import Decimal
from datetime import date
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["Attendance"])

class CheckLocationResponse(BaseModel):
    message: str
    is_inside: bool
    out_of_bound_duration_added_minutes: Optional[float] = None # Time added *in this specific call*
    total_out_of_bound_minutes: float # The running total

@router.post("/punch", response_model=dict, dependencies=[Depends(role_dependency([RoleEnum.Employee]))])
async def punch(current_user: User = Depends(get_current_user)):
    try:
        # Check if the user has already punched in for today
        existing_attendance = await Attendance.find_one(
            Attendance.user_id == current_user.user_id,
            Attendance.Date == date.today()
        )

        if existing_attendance:
            # If attendance exists, handle punch-out
            if existing_attendance.punch_out_time:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already punched out for today.")

            existing_attendance.punch_out_time = datetime.now()
            await existing_attendance.save()
            return {"message": "Punched out successfully."}
        else:
            # If no attendance exists, handle punch-in
            new_attendance = Attendance(
                link_id=current_user,
                user_id=current_user.user_id,
                name=current_user.name,
                last_check=datetime.now(),
                Location_status=True,
                status=AttendanceStatusEnum.Present
            )
            await new_attendance.insert()
            return {"message": "Punched in successfully."}

    except Exception as e:
        logger.error(f"Error in punch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.post("/check-location", response_model=CheckLocationResponse, dependencies=[Depends(role_dependency([RoleEnum.Employee]))])
async def check_location(coordinates: Location, current_user: User = Depends(get_current_user)):
    try:
        # Fetch the attendance record for today
        attendance_record = await Attendance.find_one(
            Attendance.user_id == current_user.user_id,
            Attendance.Date == date.today()
        )
        if not attendance_record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not punched in for today.")

        # Check if already punched out
        if attendance_record.punch_out_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already punched out for today. Cannot check location.")

        # Handle specific statuses where location check might be irrelevant or different
        if attendance_record.status == AttendanceStatusEnum.OnDuty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is marked as 'On Duty'. Location check policy may differ.")
        if attendance_record.status != AttendanceStatusEnum.Present:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot check location, current status is '{attendance_record.status.value}'. Must be 'Present'."
            )

        # Ensure campus boundary is defined
        if not current_user.campus or not current_user.campus.geo_boundary:
            logger.warning(f"User {current_user.email} has no campus or boundary despite being punched in.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campus boundary not defined for user.")

        # Check if the user is inside the campus boundary
        is_inside = is_point_within_polygon(
            coordinates.longitude, coordinates.latitude,
            current_user.campus.geo_boundary
        )

        now = datetime.now()
        current_location_status = attendance_record.location_status  # Status before this check
        out_of_bound_duration_added = 0.0  # Duration added in this call

        # --- State Transition Logic ---
        message = ""
        if is_inside and not current_location_status:
            # Transition: Outside -> Inside
            message = "User is now inside the campus."
            if attendance_record.last_check:
                time_diff_seconds = (now - attendance_record.last_check).total_seconds()
                if time_diff_seconds > 0:  # Ensure time difference is positive
                    out_of_bound_duration_added = time_diff_seconds / 60  # Convert seconds to minutes
                    attendance_record.total_out_of_bound_time_in_minutes += out_of_bound_duration_added
                    logger.info(f"User {current_user.email} returned inside. Spent {out_of_bound_duration_added:.2f} minutes out of bounds.")

            attendance_record.location_status = True  # Update status to inside

        elif not is_inside and current_location_status:
            # Transition: Inside -> Outside
            message = "User is now outside the campus."
            attendance_record.location_status = False  # Update status to outside
            attendance_record.last_check = now  # Save the time when the user went outside
            logger.info(f"User {current_user.email} is now outside the campus.")

        elif is_inside and current_location_status:
            # State: Inside -> Inside
            message = "User is still inside the campus."
            # No change in location_status needed

        elif not is_inside and not current_location_status:
            # State: Outside -> Outside
            message = "User is still outside the campus."
            # No change in location_status needed

        # --- Update last_check consistently and save ---
        # attendance_record.last_check = now
        await attendance_record.save()

        # Return structured response
        return CheckLocationResponse(
            message=message,
            is_inside=is_inside,
            out_of_bound_duration_added_minutes=round(out_of_bound_duration_added, 2) if out_of_bound_duration_added > 0 else None,
            total_out_of_bound_minutes=round(attendance_record.total_out_of_bound_time_in_minutes, 2)
        )

    except HTTPException as e:
        logger.error(f"HTTPException in check_location for user {current_user.email}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in check_location for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error during location check.")
    

@router.put("/on_duty", dependencies=[Depends(role_dependency([RoleEnum.Employee]))])
async def mark_on_duty(remarks: str, current_user: User = Depends(get_current_user)):
    try:
        # Fetch the attendance record for today
        attendance_record = await Attendance.find_one(
            Attendance.user_id == current_user.user_id,
            Attendance.Date == date.today()
        )
        
        if not attendance_record:
            raise HTTPException(
                status_code=404,
                detail="Attendance record not found for today."
            )

        # Check if already punched out
        if attendance_record.punch_out_time:
            raise HTTPException(
                status_code=400,
                detail="Already punched out for today. Cannot mark as 'On Duty'."
            )

        # Ensure the current status is 'Present'
        if attendance_record.status != AttendanceStatusEnum.Present:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark as 'On Duty' because the current status is '{attendance_record.status}'."
            )

        # Transition from 'Present' to 'On Duty'
        attendance_record.status = AttendanceStatusEnum.OnDuty
        attendance_record.remarks = remarks
        await attendance_record.save()

        return JSONResponse(content={"message": "Marked as 'On Duty' successfully."}, status_code=200)

    except HTTPException as e:
        # Log HTTP exceptions
        logger.error(f"HTTPException in mark_on_duty: {e.detail}")
        raise e
    except Exception as e:
        # Log unexpected exceptions with traceback
        logger.error(f"Unexpected error in mark_on_duty: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error while marking as 'On Duty'."
        )

@router.put("/off_on_duty", dependencies=[Depends(role_dependency([RoleEnum.Employee]))])
async def mark_off_on_duty(current_user: User = Depends(get_current_user)):
    try:
        # Fetch the attendance record for today
        attendance_record = await Attendance.find_one(
            Attendance.user_id == current_user.user_id,
            Attendance.Date == date.today()
        )
        
        if not attendance_record:
            raise HTTPException(
                status_code=404,
                detail="Attendance record not found for today."
            )

        # Check if already punched out
        if attendance_record.punch_out_time:
            raise HTTPException(
                status_code=400,
                detail="Already punched out for today. Cannot mark as 'Off On Duty'."
            )

        # Handle status transitions
        if attendance_record.status == AttendanceStatusEnum.OnDuty:
            # Transition from 'On Duty' to 'Present' and set remarks to None
            attendance_record.status = AttendanceStatusEnum.Present
            attendance_record.remarks = None
            await attendance_record.save()
            return JSONResponse(content={"message": "Marked as 'Present' successfully."}, status_code=200)
        else:
            # Invalid status for this operation
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{attendance_record.status}'. Cannot mark as 'Off On Duty'."
            )

    except HTTPException as e:
        # Log HTTP exceptions
        logger.error(f"HTTPException in mark_off_on_duty: {e.detail}")
        raise e
    except Exception as e:
        # Log unexpected exceptions with traceback
        logger.error(f"Unexpected error in mark_off_on_duty: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error while marking as 'Off On Duty'."
        )
        


@router.get(
    "/total_duration",
    dependencies=[Depends(role_dependency([RoleEnum.Employee]))]
)
async def get_total_duration(
    current_user: User = Depends(get_current_user)
):
    try:
        # Fetch the attendance record for today
        attendance_record = await Attendance.find_one(
            Attendance.user_id == current_user.user_id,
            Attendance.Date == date.today()
        )

        if not attendance_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance record not found for today."
            )

        # Determine punch-out time (use current time if not punched out yet)
        punch_out_time = attendance_record.punch_out_time or datetime.now()

        # Calculate total seconds worked
        total_duration = punch_out_time - attendance_record.punch_in_time

        # Convert total duration to hours, minutes, and seconds
        total_seconds = total_duration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        # Return the formatted duration
        return {
            "total_duration_in_hours": round(total_seconds / 3600, 2),
            "formatted_duration": f"{hours}h {minutes}m {seconds}s"
        }

    except HTTPException:
        # Propagate our own HTTPExceptions
        raise
    except Exception as e:
        # Log and return 500 on any other error
        logger.error(f"Error in get_total_duration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error."
        )

@router.get("/report"
            # dependencies=[Depends(role_dependency([RoleEnum.Admin, RoleEnum.SuperAdmin]))]
            )
async def download_attendance_report(
    campus_name: str,
    department: Optional[str]= None,
    user_id: Optional[int] = None,
    file_format: str = "csv"
    # current_user: User = Depends(get_current_user)
):
    """Download attendance report in CSV or PDF format for a specific campus and department."""

    # Fetch attendance records
    attendance_records = await fetch_attendance_records(campus_name, department, user_id)

    if not attendance_records:
        raise HTTPException(status_code=404, detail="No attendance records found for the specified criteria.")

    # Generate CSV or PDF report
    if file_format.lower() == "csv":
        filename = f"attendance_report_{campus_name}_{department}_{date.today()}.csv"
        return generate_csv_report(attendance_records, filename)

    elif file_format.lower() == "pdf":
        filename = f"attendance_report_{campus_name}_{department}_{date.today()}.pdf"
        return generate_pdf_report(attendance_records, filename)

    else:
        raise HTTPException(status_code=400, detail="Invalid file format. Use 'csv' or 'pdf'.")
from fastapi import HTTPException, status, APIRouter, Depends, File, UploadFile, Form
from models import User, RoleEnum, Attendance, Calender, StatusEnum, Leave, Announcement, ZoneEnum, Campus
from pydantic import Field
from utils.auth import get_current_user, role_dependency
from schemas.superadmin import CreateCalender, CalenderResponse, AnnouncementBase
from fastapi import APIRouter, Depends, HTTPException, status
from utils.image import upload_to_imgbb
from datetime import date
from typing import List, Optional
from bson import ObjectId
import os
import logging
import tempfile


router = APIRouter(
    prefix="/superadmin",
    tags=["SuperAdmin"],
    responses={404: {"description": "Not found"}},
)

ALLOWED_IMAGE_CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif"]
ALLOWED_PDF_CONTENT_TYPE = "application/pdf"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

logger = logging.getLogger(__name__)


@router.get("/get-all-attendance", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_all_attendance(current_user: User = Depends(get_current_user)):
    try:
        # Fetch all attendance records
        attendance_records = await Attendance.find().to_list()
        
        return attendance_records
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/todays-attendance", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_todays_attendance(current_user: User = Depends(get_current_user)):
    try:
        # Fetch all attendance records for today
        attendance_records = await Attendance.find(Attendance.Date == date.today()).to_list()
        
        return attendance_records
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/add-calender", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def add_calender(
    calender: List[CreateCalender],
    current_user: User = Depends(get_current_user)
):
    """
    Adds multiple calendar entries to the database.
    """
    try:
        # Iterate over the list of calendar entries and insert them into the database
        for entry in calender:
            new_calender = Calender(date=entry.date, holiday=entry.holiday)
            await new_calender.insert()

        return {"message": "Calendar entries added successfully."}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while adding calendar entries: {str(e)}"
        )
        


@router.get("/get-leave-requests", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_leave_requests(current_user: User = Depends(get_current_user)):
    try:
        leave_requests = await Leave.find(
            {
                "$and": [
                    {"status": StatusEnum.Pending},  # Filter for pending leave requests
                    {
                        "$or": [
                            {"user_id.role": RoleEnum.Admin},
                            {"user_id.designation": {"$in": ["Professor", "OSD"]}}
                        ]
                    }
                ]
            },
            fetch_links=True
        ).to_list()

        return {"message": "Leave requests fetched successfully.", "data": leave_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )

@router.get("/get-leave-requests-history", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_leave_requests_history(current_user: User = Depends(get_current_user)):
    try:
        leave_requests = await Leave.find(
            {
                "$and": [
                    {"status": {"$ne": StatusEnum.Pending}},  # Exclude pending leave requests
                    {
                        "$or": [
                            {"user_id.role": RoleEnum.Admin},
                            {"user_id.designation": {"$in": ["Professor", "OSD"]}}
                        ]
                    }
                ]
            },
            fetch_links=True
        ).to_list()

        return {"message": "Leave requests fetched successfully.", "data": leave_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )

@router.patch(
    "/approve-leave-request/{leave_request_id}",
    dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin]))],
    tags=["Admin"]
)
async def approve_leave_request(leave_request_id: str, current_user: User = Depends(get_current_user)):
    """
    Approve a leave request.
    """
    try:
        # Validate leave_request_id as a valid ObjectId
        if not ObjectId.is_valid(leave_request_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid leave request ID."
            )
        
        # Convert leave_request_id to ObjectId
        leave_request_id = ObjectId(leave_request_id)

        # Find the leave request with status "PENDING"
        leave_request = await Leave.find_one(
            {"_id": leave_request_id, "status": StatusEnum.Pending},
        )
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found or already processed."
            )

        # Update the status to "APPROVED"
        leave_request.status = StatusEnum.Approved
        await leave_request.save()

        return {"message": "Leave request approved successfully."}
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while approving the leave request: {str(e)}"
        )


@router.patch(
    "/reject-leave-request/{leave_request_id}",
    dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin]))],
    tags=["Admin"]
)
async def reject_leave_request(leave_request_id: str,remarks: str, current_user: User = Depends(get_current_user)):
    """
    Reject a leave request.
    """
    try:
        # Validate leave_request_id as a valid ObjectId
        if not ObjectId.is_valid(leave_request_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid leave request ID."
            )
        
        # Convert leave_request_id to ObjectId
        leave_request_id = ObjectId(leave_request_id)

        # Find the leave request with status "PENDING"
        leave_request = await Leave.find_one(
            {"_id": leave_request_id, "status": StatusEnum.Pending}
        )
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found or already processed."
            )

        # Update the status to "REJECTED"
        leave_request.status = StatusEnum.Rejected
        leave_request.remarks = remarks
        await leave_request.save()

        return {"message": "Leave request rejected successfully."}
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while rejecting the leave request: {str(e)}"
        )
        
@router.get("/all-users",dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_all_users(current_user: User = Depends(get_current_user)):
    try:
        users = await User.find(
            User.role != RoleEnum.SuperAdmin,
            fetch_links=True
            ).to_list()
        return {"message": "Users fetched successfully.", "data": users}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users: {str(e)}"
        )
        

@router.get("/get-all-campuses", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_all_campuses(current_user: User = Depends(get_current_user)):
    try:
        campuses = await Campus.find().to_list()
        return {"message": "Campuses fetched successfully.", "data": campuses}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching campuses: {str(e)}"
        )
        
@router.get("/get-approved-leaves", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_approved_leaves(current_user: User = Depends(get_current_user)):
    try:
        leaves = await Leave.find(Leave.status == StatusEnum.Approved).to_list()
        return {"message": "Leaves fetched successfully.", "data": leaves}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leaves: {str(e)}"
        )
        
@router.get("/get-rejected-leaves", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))])
async def get_rejected_leaves(current_user: User = Depends(get_current_user)):
    try:
        leaves = await Leave.find(Leave.status == StatusEnum.Rejected).to_list()
        return {"message": "Leaves fetched successfully.", "data": leaves}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leaves: {str(e)}"
        )


@router.post(
    "/create-announcement",
    response_model=AnnouncementBase,
    # dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin]))]  # Security dependency
)
async def create_announcement(
    announcement_data: AnnouncementBase,  # All fields in the body
    image: Optional[UploadFile] = File(None)  # Handle file upload separately
    # current_user: User = Depends(get_current_user)  # Security dependency
):
    try:
        image_url = None
        if image:
            # Create a temporary file to store the uploaded image
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(await image.read())  # Write the file content to the temp file
                temp_file_path = temp_file.name  # Get the temporary file path

            # Pass the temporary file path to the upload function
            image_url = await upload_to_imgbb(temp_file_path, image.filename)

            # Remove the temporary file after uploading
            os.remove(temp_file_path)

        # Prepare data for the new announcement
        announcement_dict = announcement_data.dict()
        if image_url:
            announcement_dict["image"] = image_url  # Add the image URL if uploaded

        # Create and save the new announcement
        new_announcement = Announcement(**announcement_dict)
        await new_announcement.save()

        # Return the created announcement
        return new_announcement
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the announcement: {str(e)}"
        )
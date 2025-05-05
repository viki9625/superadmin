from fastapi import APIRouter, Depends, HTTPException, status
from models import Leave, LeaveTypeEnum, User, RoleEnum, StaffTypeEnum, StatusEnum, Attendance, Calender
from schemas.leave import LeaveBase, LeaveResponse
from utils.auth import get_current_user, role_dependency
from typing import List
from bson import ObjectId
import logging

from datetime import date

router = APIRouter()


@router.get("/get-campus-attendance", dependencies=[Depends(role_dependency([RoleEnum.Admin]))], tags=["Admin"])
async def get_all_attendance(current_user: User = Depends(get_current_user)):
    try:
        # Fetch all attendance records
        attendance_records = await Attendance.find(
            Attendance.link_id.campus.name == current_user.campus.name,
            fetch_links=True
            ).to_list()
        
        return attendance_records
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/request-for-leave", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_dependency([RoleEnum.Admin, RoleEnum.Employee]))], tags=["User","Admin"])
async def create_leave(leave_type:LeaveTypeEnum,leave: LeaveBase, current_user: User = Depends(get_current_user)):
    """
    Create a new leave request.
    """
    try:
        object_id = await User.find_one(User.user_id == current_user.user_id)
        await Leave(**leave.dict(), leave_type=leave_type, user_id=object_id).insert()
        return {"message": "Leave request submitted successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while submitting the leave request: {str(e)}"
        )
        
@router.get("/get-current-user")
async def get_current_user(current_user: User = Depends(get_current_user)):
    return current_user
        

# from beanie import Q

@router.get("/admin/get-leave-requests", dependencies=[Depends(role_dependency([RoleEnum.Admin, RoleEnum.Employee]))], tags=["Admin"])
async def get_leave_requests(current_user: User = Depends(get_current_user)):
    try:
        # MongoDB query using $nor to exclude specific designations and filter by pending status
        query = {
            "$and": [
                {"user_id.staff_type": StaffTypeEnum.TEACHING},
                {"user_id.campus.name": current_user.campus.name},  # Ensure campus matches
                {"user_id.role": RoleEnum.Employee},
                {"status": StatusEnum.Pending},  # Filter only pending requests
                {"$nor": [{"user_id.designation": {"$in": ["Professor", "OSD", "Dean"]}}]}  # Exclude these designations
            ]
        }

        # Fetch filtered leave requests
        filtered_requests = await Leave.find(query, fetch_links=True).to_list()

        return {"message": "Leave requests fetched successfully.", "data": filtered_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )

@router.get("/admin/get-leave-requests-history", dependencies=[Depends(role_dependency([RoleEnum.Admin, RoleEnum.Employee]))], tags=["Admin"])
async def get_leave_requests_history(current_user: User = Depends(get_current_user)):
    try:
        # MongoDB query to exclude pending status and specific designations
        query = {
            "$and": [
                {"user_id.staff_type": StaffTypeEnum.TEACHING},
                {"user_id.campus.name": current_user.campus.name},  # Ensure campus matches
                {"user_id.role": RoleEnum.Employee},
                {"status": {"$ne": StatusEnum.Pending}},  # Exclude pending requests
                {"$nor": [{"user_id.designation": {"$in": ["Professor", "OSD", "Dean"]}}]}  # Exclude these designations
            ]
        }

        # Fetch filtered leave requests
        filtered_requests = await Leave.find(query, fetch_links=True).to_list()

        return {"message": "Leave requests fetched successfully.", "data": filtered_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )


@router.get("/user/get-leave-history", dependencies=[Depends(role_dependency([RoleEnum.Employee, RoleEnum.Admin]))], tags=["User","Admin"])
async def get_leave_requests(current_user: User = Depends(get_current_user)):
    try:
        # Fetch all leave requests and resolve the user_id reference
        leave_requests = await Leave.find(
            Leave.user_id.user_id == current_user.user_id,  # Filter by the current user's ID
            fetch_links=True  # Resolve the user_id reference
        ).to_list()
        return leave_requests
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )
        
@router.get("/user/get-leave-status", dependencies=[Depends(role_dependency([RoleEnum.Employee, RoleEnum.Admin]))], tags=["User"])
async def get_leave_status(Leave_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Validate Leave_id as a valid ObjectId
        if not ObjectId.is_valid(Leave_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid leave request ID."
            )
        
        # Fetch the leave request and resolve the user_id reference
        leave_request = await Leave.find_one(
            {"_id": ObjectId(Leave_id)},  # Filter by the leave request ID
            fetch_links=True  # Resolve the user_id reference
        )
        
        # Check if the leave request exists
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found."
            )
        
        # # Check if the current user has permission to view the leave request
        # if leave_request.user_id != current_user.id and current_user.role != RoleEnum.Admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="You do not have permission to view this leave request."
        #     )
        
        return leave_request
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )
        
@router.get("/user/attendance-record", dependencies=[Depends(role_dependency([RoleEnum.Employee]))], tags=["User"])
async def get_attendance_record(current_user: User = Depends(get_current_user)):
    try:
        # Fetch the attendance record
        attendance_record = await Attendance.find_one(
            {"user_id": current_user.user_id}
        )
        return attendance_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching attendance record: {str(e)}"
        )
        
@router.get("/get-my-calender", dependencies=[Depends(role_dependency([RoleEnum.Employee, RoleEnum.Admin]))], tags=["User"])
async def get_my_calender_with_leaves(current_user: User = Depends(get_current_user)):
    try:
        # Fetch all calendar entries
        calender_entries = await Calender.find().to_list()
        
        # Fetch leave requests for the current user
        leave_requests = await Leave.find(
            Leave.user_id.user_id == current_user.user_id,  # Filter by the current user's ID
            fetch_links=True  # Resolve the user_id reference
        ).to_list()
        
        # Add leave requests to the calendar entries
        for leave_request in leave_requests:
            calender_entries.append(leave_request)
        
        return calender_entries
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching calendar entries: {str(e)}"
        )
        
@router.get("/all-campus-users", dependencies=[Depends(role_dependency([RoleEnum.Admin]))], tags=["Admin"])
async def get_all_users(current_user: User = Depends(get_current_user)):
    try:
        users = await User.find(
            User.campus.name == current_user.campus.name,
            fetch_links=True
            ).to_list()
        return {"message": "Users fetched successfully.", "data": users}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users: {str(e)}"
        )
        
@router.get("/get-approved-requests", dependencies=[Depends(role_dependency([RoleEnum.Admin]))], tags=["Admin"])
async def get_approved_requests(current_user: User = Depends(get_current_user)):
    try:
        leave_requests = await Leave.find(
            Leave.user_id.campus.name == current_user.campus.name,
            Leave.status == StatusEnum.Approved,
            fetch_links=True
        ).to_list()
        return {"message": "Leave requests fetched successfully.", "data": leave_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )

@router.get("/get-rejected-requests", dependencies=[Depends(role_dependency([RoleEnum.Admin]))], tags=["Admin"])
async def get_rejected_requests(current_user: User = Depends(get_current_user)):
    try:
        leave_requests = await Leave.find(
            Leave.user_id.campus.name == current_user.campus.name,
            Leave.status == StatusEnum.Rejected,
            fetch_links=True
        ).to_list()
        return {"message": "Leave requests fetched successfully.", "data": leave_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )
        
@router.get("/get-pending-requests", dependencies=[Depends(role_dependency([RoleEnum.Employee]))], tags=["User"])
async def get_pending_requests(current_user: User = Depends(get_current_user)):
    try:
        leave_requests = await Leave.find(
            Leave.user_id.user_id == current_user.user_id,
            Leave.status == StatusEnum.Pending,
            fetch_links=True
        ).to_list()
        return {"message": "Leave requests fetched successfully.", "data": leave_requests}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching leave requests: {str(e)}"
        )

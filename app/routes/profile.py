from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from typing import Annotated, List
import os # Added for file operations if needed later
import shutil # Added for file operations if needed later
from uuid import uuid4 # Added for unique filenames if needed later
import logging # <-- Import logging (Added based on previous suggestions)

# --- Model and Schema Imports ---
from models import User, RoleEnum, BankDetail, Attendance, Calender, Leave
from schemas.auth import BankDetailCreate # Might not be needed if using BankDetailRequest
from schemas.profile import GetProfile, BankDetailResponse, BankDetailRequest, UserAttendanceReport
from schemas.leave import LeaveBase

# --- Utility Imports ---

from utils.auth import role_dependency, get_current_user
from utils.encryption import encrypt_data, decrypt_data # Import encryption functions
from utils.image import upload_to_imgbb


import tempfile
# --- Logging Configuration (Added based on previous suggestions) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PROFILE_PICS_DIR = os.path.join("static", "profile_pics")
# Create the directory if it doesn't exist
# os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

router = APIRouter(
    prefix="/profile", # Add a prefix for profile-related routes
    tags=["Profile Management"] # Add a tag for API documentation
)

# --- Modified /profile GET endpoint (Based on previous suggestions) ---
@router.get("/", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin, RoleEnum.Employee]))])
async def get_profile(current_user: User = Depends(get_current_user)):
    # Explicitly fetch the user again, this time with linked documents (like bank_detail)
    user = await User.find_one({"_id": current_user.id}, fetch_links=True) # <-- Added fetch_links=True

    # Although unlikely after authentication, add a check just in case
    if not user:
        logger.warning(f"Authenticated user not found in DB: {current_user.email}") # Log warning
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user profile not found."
        )

    # Ensure the field name in GetProfile matches the User model field name (e.g., 'bank_detail')
    # Ensure the User model has 'profile_picture_url' field
    return user # Return the newly fetched user object


# --- Add Bank Details POST endpoint ---
@router.post(
    "/bank_details",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin, RoleEnum.Employee]))]
)
async def add_bank_details(
    bank_detail_request: BankDetailRequest,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Adds encrypted bank details for the currently authenticated user.
    Ensures that bank details are only added once.
    """
    # Fetch the user again to check the current bank_detail link status
    user = await User.find_one({"_id": current_user.id}, fetch_links=True)
    if not user:
        # Should not happen if get_current_user worked
        logger.error(f"Authenticated user {current_user.email} not found during bank detail add.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.bank_detail:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank details already added for this user.",
        )

    # Encrypt the data before saving
    # Ensure encrypt_data returns bytes and BankDetail model fields are bytes
    try:
        encrypted_account = encrypt_data(bank_detail_request.account_number)
        encrypted_ifsc = encrypt_data(bank_detail_request.ifsc_code)
        encrypted_pan = encrypt_data(bank_detail_request.pan_number) if bank_detail_request.pan_number else None

        if encrypted_account is None or encrypted_ifsc is None or encrypted_pan is None:
            logger.error(f"Encryption failed for user {user.email}. encrypt_data returned None.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not encrypt bank details.",
            )

        # Ensure BankDetail model expects bytes for these fields
        bank_detail = BankDetail(
            account_holder_name=bank_detail_request.account_holder_name,
            pan_number=encrypted_pan,
            bank_name=bank_detail_request.bank_name,
            account_number=encrypted_account, # Should be bytes
            ifsc_code=encrypted_ifsc         # Should be bytes
        )
        await bank_detail.insert()

        # Link the newly created bank detail document to the user
        user.bank_detail = bank_detail
        await user.save()

        logger.info(f"Bank details added successfully for user {user.email}")
        return {"message": "Bank details added successfully."}

    except Exception as e:
        logger.error(f"Error adding bank details for user {user.email}: {e}", exc_info=True) # Log full traceback
        # Attempt to clean up orphaned bank detail if insert succeeded but linking failed? (Complex)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while adding bank details."
        )


@router.get("/bank_details",response_model=BankDetailResponse, dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin, RoleEnum.Employee]))])
async def get_bank_detail(
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves and decrypts the bank details for the currently authenticated user.
    """
    # Fetch the user with the linked bank details
    user = await User.find_one({"_id": current_user.id}, fetch_links=True)

    if not user:
        # Should not happen if get_current_user worked
        logger.error(f"Authenticated user {current_user.email} not found during bank detail get.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.bank_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank details not found for this user.",
        )

    # Decrypt the data before returning
    try:
        # Ensure user.bank_detail.account_number/ifsc_code are bytes
        account_number_bytes = user.bank_detail.account_number
        ifsc_code_bytes = user.bank_detail.ifsc_code
        pan_number_bytes = user.bank_detail.pan_number

        # Add type check for debugging the bytes issue
        if not isinstance(account_number_bytes, bytes) or not isinstance(ifsc_code_bytes, bytes):
            logger.error(f"Data type error for user {user.email}. Account number type: {type(account_number_bytes)}, IFSC code type: {type(ifsc_code_bytes)}. Expected bytes.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal data format error retrieving bank details."
            )

        decrypted_account = decrypt_data(account_number_bytes)
        decrypted_ifsc = decrypt_data(ifsc_code_bytes)
        decrypted_pan = decrypt_data(pan_number_bytes)

        # Check if decryption failed (e.g., wrong key, corrupted data)
        if decrypted_account is None or decrypted_ifsc is None or decrypted_pan is None:
            logger.error(f"Failed to decrypt bank details for user {user.email}. decrypt_data returned None.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve bank details due to a decryption error."
            )

        # Return the decrypted data using the response model
        return BankDetailResponse(
            account_number=decrypted_account,
            ifsc_code=decrypted_ifsc,
            pan_number=decrypted_pan,
            bank_name=user.bank_detail.bank_name,
            account_holder_name=user.bank_detail.account_holder_name,
            branch_name=user.bank_detail.branch_name
        )
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions directly
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error retrieving/decrypting bank details for user {user.email}: {e}", exc_info=True) # Log full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving bank details."
        )


# --- Upload Profile Picture POST endpoint ---
@router.post("/upload-image", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin, RoleEnum.Employee]))])
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Uploads an image to ImgBB and returns the image URL.
    """
    allowed_content_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPG, PNG, and GIF are allowed."
        )

    try:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Upload the file to ImgBB
        image_url = await upload_to_imgbb(temp_file_path)

        # Delete the temporary file
        os.remove(temp_file_path)
        
        current_user.picture = image_url
        await current_user.save()

        return {"message": "Image uploaded successfully.", "image_url": image_url}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while uploading the image: {str(e)}"
        )

        
@router.get("/attendance_report", response_model=List[UserAttendanceReport] ,dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin, RoleEnum.Employee]))])
async def get_attendance_report(current_user: User = Depends(get_current_user)):
    try:
        return await Attendance.find(
            Attendance.user_id == current_user.user_id
        ).to_list()

    except Exception as e:
        logger.error(f"Error in get_attendance_report: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.get("/get-calender", dependencies=[Depends(role_dependency([RoleEnum.SuperAdmin, RoleEnum.Admin, RoleEnum.Employee]))])
async def get_calender(current_user: User = Depends(get_current_user)):
    try:
        # Fetch all calendar entries
        calender_entries = await Calender.find().to_list()
        return calender_entries
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching calendar entries: {str(e)}"
        )

# @router.post("/request-leave", dependencies=[Depends(role_dependency([RoleEnum.Admin, RoleEnum.Employee]))])
# async def request_leave(leave_request: LeaveBase, current_user: User = Depends(get_current_user)):    
#     try:
#         new_leave_request = Leave(**leave_request.dict(), user_id=current_user.user_id)
#         await new_leave_request.insert()
#         return {"message": "Leave request submitted successfully."}
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred while submitting the leave request: {str(e)}"
#         )
        

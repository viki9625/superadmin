from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from models import User, RoleEnum, Campus, User, DesignationEnum, StaffTypeEnum, ZoneEnum
from schemas.auth import (UserResponse, 
                        Token, OTPRequest, OTPVerify, 
                        AdminUserCreate, University,
                        CampusCreate, CampusResponse
                        , UpdateCampus)
from utils.auth import (
    create_access_token,
    hash_password,
    hash_otp,
    verify_password,
    get_current_user,
    role_dependency
)
from utils.email import send_otp_email
from utils.otp import generate_totp_secret, generate_totp, verify_totp
from datetime import timedelta
from core.config import settings
from typing import Annotated, List
import pyotp
from passlib.context import CryptContext

router = APIRouter()

@router.post("/send-otp", response_model=dict)
async def send_otp(data: OTPRequest):
    """
    Sends an OTP to the user's email for password reset.
    """
    user = await User.find_one(User.email == data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Ensure the user has a valid TOTP secret
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a valid TOTP secret."
        )

    # Generate the OTP using the TOTP secret
    otp = generate_totp(user.totp_secret)

    # Send the OTP via email
    try:
        await send_otp_email(email=user.email, otp=otp)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP email: {str(e)}"
        )

    return {"message": "OTP sent successfully to your email"}


@router.post("/reset-password", response_model=dict)
async def reset_password_with_otp(data: OTPVerify):
    """
    Resets the user's password after verifying the OTP.
    """
    user = await User.find_one(User.email == data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Ensure the user has a valid TOTP secret
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a valid TOTP secret."
        )

    # Verify the OTP using the TOTP secret
    if not verify_totp(user.totp_secret, data.otp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    # Update the password
    user.hashed_password = hash_password(data.password)
    await user.save()

    return {"message": "Password changed successfully"}

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    db_user = await User.find_one(User.email == form_data.username)
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please verify the OTP or contact the admin",
        )

    expires_delta = timedelta(seconds=settings.jwt_expiration)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=expires_delta
    )
    return {"access_token": access_token, "token_type": "bearer",  "role": db_user.role}

@router.post(
    "/admin/add_user",
    status_code=status.HTTP_201_CREATED,
    # dependencies=[Depends(role_dependency([RoleEnum.VC]))]
)
async def add_user(
    staff_type: StaffTypeEnum,
    user_data: AdminUserCreate
):
    """
    Adds a new user to the system. Designation and staff_type are passed as Enums.
    """

    # Check if a user with the same user_id already exists (if provided)
    if user_data.user_id:
        existing_user_id = await User.find_one(User.user_id == user_data.user_id)
        if existing_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User already exists with Employee ID: {user_data.user_id}"
            )
            
    # Check if a user with the same email already exists
    existing_user_email = await User.find_one(User.email == user_data.email)
    if existing_user_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already exists with email: {user_data.email}"
        )

    # Hash the password
    hashed_pwd = hash_password(user_data.password)
    totp_secret = generate_totp_secret()

    # Find the campus by name
    campus = await Campus.find_one(Campus.name == user_data.campus)
    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus '{user_data.campus}' not found."
        )

    # Create a new user instance
    new_user = User(
        **user_data.dict(exclude={"password", "campus"}),
        hashed_password=hashed_pwd,
        staff_type=staff_type.value,
        totp_secret=totp_secret,
        campus=campus
    )

    # Insert the new user into the database
    try:
        await new_user.insert()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while adding the user: {str(e)}"
        )

    # Return the created user's details (excluding sensitive fields)
    return {
        "message": f"User {new_user.email} added successfully.",
        "user": {
            "user_id": new_user.user_id,
            "email": new_user.email,
            "staff_type": new_user.staff_type,
            "campus": new_user.campus.name,
            "role": new_user.role
        }
    }

@router.post("/admin/add_campus", description="add geocoordinate as long lat manner")
async def add_campus(zone: ZoneEnum,campus: CampusCreate):
    # Check if the campus already exists
    existing_campus = await Campus.find_one(Campus.name == campus.name)
    if existing_campus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campus already exists with name: {campus}"
        )

    # Create a new campus
    new_campus = Campus(
        **campus.dict(),
        zone=zone.value
    )
    await new_campus.insert()

    # Return the response
    return ("campus added")

@router.post("/admin/add_campuses", description="Add multiple campuses with geocoordinates in long-lat format")
async def add_campuses(zone: ZoneEnum, campuses: List[CampusCreate]):
    """
    Add multiple campuses to the database.
    """
    added_campuses = []
    existing_campuses = []

    try:
        for campus in campuses:
            # Check if the campus already exists
            existing_campus = await Campus.find_one(Campus.name == campus.name)
            if existing_campus:
                existing_campuses.append(campus.name)
                continue

            # Create a new campus
            new_campus = Campus(
                **campus.dict(),
                zone=zone.value
            )
            await new_campus.insert()
            added_campuses.append(campus.name)

        # Return the response
        return {
            "message": "Campuses processed successfully.",
            "added_campuses": added_campuses,
            "existing_campuses": existing_campuses
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while adding campuses: {str(e)}"
        )

# @router.post("/add_university")
# async def add_university(university: University):
#     # Check if the university already exists
#     existing_university = await DSEU.find_one(DSEU.name == university.name)
#     if existing_university:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail=f"University already exists with name: {university}"
#         )

#     # Create a new university
#     new_university = DSEU(
#         name=university.name,
#         description=university.description
        
#         )
#     await new_university.insert()

#     # Return the response
#     return ("university added")

@router.delete("/admin/remove_campus/{campus_id}")
async def remove_campus(campus_id: int):
    # Check if the campus exists
    existing_campus = await Campus.find_one(Campus.campus_id == campus_id)
    if not existing_campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus with ID {campus_id} not found"
        )

    # Delete the campus
    await existing_campus.delete()

    # Return the response
    return ("campus removed")

@router.get("/all-campuses", response_model=List[CampusResponse])
async def get_all_campuses():
    campuses = await Campus.find_all().to_list()

    # Ensure all campuses have a campus_id
    for campus in campuses:
        if not hasattr(campus, "campus_id"):
            campus.campus_id = None  # Provide a default value

    return campuses

@router.patch("/admin/update_campus/{campus_id}", response_model=CampusResponse)
async def update_campus(campus_id: int, campus: UpdateCampus):
    """
    Updates an existing campus by its campus_id.
    """
    # Check if the campus exists
    existing_campus = await Campus.find_one(Campus.campus_id == campus_id)
    if not existing_campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus with ID {campus_id} not found"
        )

    # Prepare the update data
    update_data = campus.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update"
        )

    # Perform the update using $set
    try:
        await existing_campus.update({"$set": update_data})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the campus: {str(e)}"
        )

    # Fetch the updated campus
    updated_campus = await Campus.find_one(Campus.campus_id == campus_id)

    # Return the updated campus
    return updated_campus
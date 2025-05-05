from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException, status
from utils.otp import generate_totp
import logging
from typing import List

# Connection configuration for FastAPI-Mail
conf = ConnectionConfig(
    MAIL_USERNAME="pankajku.8700@gmail.com",
    MAIL_PASSWORD="asmxjbitlkjtscth",
    MAIL_FROM="pankajku.8700@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_FROM_NAME="Delhi Skill And Entrepreneurship University",
    USE_CREDENTIALS=True
)


async def send_otp_email(email: str, otp: str):
    """
    Sends an OTP to the user's email.
    """
    message = MessageSchema(
        subject="Your OTP Code",
        recipients=[email],
        body=f"Your OTP code is: {otp}, your otp valid only for 2 minutes. Please do not share with anyone. - DSEU Admin",
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
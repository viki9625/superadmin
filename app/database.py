from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models import Attendance, BankDetail, User, Campus,Announcement, Leave, Calender
from core.config import settings

async def init_db():
    client = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(database=client.get_default_database(), document_models=[Announcement, Campus, User, BankDetail, Attendance, Leave, Calender])
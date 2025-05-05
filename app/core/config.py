from pydantic_settings import BaseSettings
import os # Import os
# import redis.asyncio as redis # Import redis
# from redis.asyncio.connection import ConnectionPool # Import ConnectionPool

class Settings(BaseSettings):
    mongodb_url: str = os.getenv("MONGODB_URL")
    jwt_secret: str = os.getenv("JWT_SECRET")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM")
    jwt_expiration: int = int(os.getenv("JWT_EXPIRATION"))
    # refresh_token_expire_minutes: int = os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 10080) # e.g., 7 days (7 * 24 * 60)


    # Redis configuration
    # redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0") # Corrected default

settings = Settings()

# --- Define the Redis pool here ---
# redis_pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True)

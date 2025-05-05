# c:\biometric\app\main.py
from fastapi import FastAPI
from database import init_db
from routes import auth, profile, attendance, superadmin, admin
# import redis.asyncio as redis # Keep this for the client type hint if needed
# --- Import redis_pool from core.config ---
from core.config import settings # Import redis_pool here


app = FastAPI(title="Biometric API")

@app.on_event("startup")
async def startup_event():
    await init_db()
    # try:
    #     # Get a temporary client from the pool to test connection
    #     client = redis.Redis(connection_pool=redis_pool) # Use imported pool
    #     await client.ping()
    #     print("Successfully connected to Redis.")
    #     # No need to explicitly close client obtained like this with pool
    # except Exception as e:
    #     print(f"ERROR: Could not connect to Redis during startup: {e}")
    #     # Consider if your app should fail to start if Redis is essential

# --- Make sure shutdown_event is registered ---
@app.on_event("shutdown")
async def shutdown_event():
    # Gracefully close the Redis connection pool when the app stops
    # print("Disconnecting Redis pool...")
    # await redis_pool.disconnect() # Use imported pool
    # print("Redis connection pool disconnected.")
    print("app closing.....")

# Include routes
app.include_router(auth.router, tags=["Authentication"])
app.include_router(profile.router)
app.include_router(attendance.router)
app.include_router(superadmin.router)
app.include_router(admin.router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Biometric API"}

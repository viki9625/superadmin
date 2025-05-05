from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated, List
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from core.config import settings
from models import User, RoleEnum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") 

SECRET_KEY = settings.jwt_secret
# REFRESH_SECRET_KEY = settings.jwt_secret + "_refresh" # Use a different secret or append something for refresh tokens
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_SECONDS = settings.jwt_expiration
# REFRESH_TOKEN_EXPIRE_MINUTES = settings.refresh_token_expire_minutes

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def hash_otp(otp: str) -> str:
    return pwd_context.hash(otp)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.jwt_expiration)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Dependency for Getting Current User ---

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e # Chain the original exception
    user = await User.find_one(User.email == username , fetch_links=True)
    if user is None:
        raise credentials_exception
    return user

def role_dependency(required_roles: List[RoleEnum]):
    async def check_user_role(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions to access this resource.",
            )
        return current_user
    return check_user_role

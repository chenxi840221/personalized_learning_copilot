from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from config.settings import Settings
# Initialize settings
settings = Settings()
# Configure password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
def verify_password(plain_password, hashed_password):
    """Verify password against hashed version."""
    return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password):
    """Hash password."""
    return pwd_context.hash(password)
async def get_user(username: str):
    """Get user from database."""
    db = 
    user_dict = await db.users.find_one({"username": username})
    return user_dict
async def get_user_by_email(email: str):
    """Get user by email from database."""
    db = 
    user_dict = await db.users.find_one({"email": email})
    return user_dict
async def authenticate_user(username: str, password: str):
    """Authenticate user."""
    user = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.get("hashed_password", "")):
        return False
    return user
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user(username=username)
    if user is None:
        raise credentials_exception
    return user

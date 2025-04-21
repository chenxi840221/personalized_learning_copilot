from fastapi import FastAPI, Depends, HTTPException, status, Body, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Import simplified settings
import sys
import os
sys.path.append(os.path.abspath("."))
from config.settings_simple import settings

# Initialize FastAPI app
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot POC",
    version="0.1.0",
)

# Add CORS middleware with hardcoded values to avoid env var issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock databases for testing
mock_users = {}
mock_contents = {}
mock_learning_plans = {}

# Utility functions
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    from jose import jwt
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = mock_users.get(username)
    if user is None:
        raise credentials_exception
    
    return user

# Authentication routes
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = mock_users.get(form_data.username)
    if not user or not verify_password(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User routes
@app.post("/users/")
async def create_user(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    full_name: Optional[str] = Body(None),
    grade_level: Optional[int] = Body(None),
    subjects_of_interest: List[str] = Body([]),
    learning_style: Optional[str] = Body(None)
):
    """Create a new user."""
    # Check if username exists
    if username in mock_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create user document
    now = datetime.utcnow().isoformat()
    user_id = str(uuid.uuid4())
    
    user_dict = {
        "id": user_id,
        "username": username,
        "email": email,
        "full_name": full_name,
        "grade_level": grade_level,
        "subjects_of_interest": subjects_of_interest,
        "learning_style": learning_style,
        "is_active": True,
        "hashed_password": get_password_hash(password),
        "created_at": now,
        "updated_at": now
    }
    
    # Insert user
    mock_users[username] = user_dict
    
    # Return user data (exclude password)
    return {k: v for k, v in user_dict.items() if k != "hashed_password"}

@app.get("/users/me/")
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    """Get current user profile."""
    return {k: v for k, v in current_user.items() if k != "hashed_password"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

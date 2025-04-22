from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict
from auth.simple_auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot POC",
    version="0.1.0",
)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    await db_manager.init_db()
    await db_manager.ensure_indexes_exist()
    print("Database initialized")
@app.get("/")
async def root():
    return {"message": "Hello from Learning Co-pilot API"}
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
@app.get("/users/me/")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user
@app.post("/users/")
async def create_user(username: str, email: str, password: str, full_name: str = None):
    # Check if username exists
    if username in authenticate_user.fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    # Create user
    hashed_password = authenticate_user.get_password_hash(password)
    authenticate_user.fake_users_db[username] = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "hashed_password": hashed_password,
        "is_active": True
    }
    return {
        "username": username,
        "email": email,
        "full_name": full_name,
        "is_active": True
    }

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
import logging
import uvicorn

from auth.authentication import (
    create_access_token, 
    get_current_user, 
    authenticate_user,
    get_password_hash
)
from models.user import User, UserCreate, UserInDB, TokenData, Token
from models.content import Content, ContentType
from models.learning_plan import LearningPlan, LearningActivity
from rag.retriever import retrieve_relevant_content
from rag.generator import generate_learning_plan
from utils.db_manager import get_db, init_db
from utils.logger import setup_logger
from config.settings import Settings

# Initialize configuration
settings = Settings()

# Setup logger
logger = setup_logger()

# Initialize FastAPI app
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot POC",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize database
@app.on_event("startup")
async def startup_db_client():
    await init_db()
    logger.info("Database initialized")

# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    db = await get_db()
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict.pop("password")
    user_in_db = UserInDB(**user_dict, hashed_password=hashed_password)
    
    new_user = await db.users.insert_one(user_in_db.dict())
    created_user = await db.users.find_one({"_id": new_user.inserted_id})
    
    return User(**created_user)

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Content routes
@app.get("/content/", response_model=List[Content])
async def get_content(
    subject: Optional[str] = None, 
    content_type: Optional[ContentType] = None,
    current_user: User = Depends(get_current_user)
):
    db = await get_db()
    query = {}
    
    if subject:
        query["subject"] = subject
    if content_type:
        query["content_type"] = content_type
    
    contents = await db.contents.find(query).to_list(length=100)
    return contents

@app.get("/content/recommendations/", response_model=List[Content])
async def get_recommendations(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Here we use RAG to get personalized recommendations
    relevant_content = await retrieve_relevant_content(
        student_profile=current_user,
        subject=subject
    )
    return relevant_content

# Learning plan routes
@app.post("/learning-plans/", response_model=LearningPlan)
async def create_learning_plan(
    subject: str,
    current_user: User = Depends(get_current_user)
):
    # Use RAG to generate a personalized learning plan
    learning_plan = await generate_learning_plan(
        student=current_user,
        subject=subject
    )
    
    # Save the learning plan to the database
    db = await get_db()
    result = await db.learning_plans.insert_one(learning_plan.dict())
    created_plan = await db.learning_plans.find_one({"_id": result.inserted_id})
    
    return LearningPlan(**created_plan)

@app.get("/learning-plans/", response_model=List[LearningPlan])
async def get_learning_plans(
    current_user: User = Depends(get_current_user)
):
    db = await get_db()
    learning_plans = await db.learning_plans.find(
        {"student_id": current_user.id}
    ).to_list(length=100)
    
    return learning_plans

# Main entry point
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
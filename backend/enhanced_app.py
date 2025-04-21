from fastapi import FastAPI, Depends, HTTPException, status, Body, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

from models.user import User, UserCreate, Token, TokenData
from models.content import Content, ContentType, DifficultyLevel
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus, LearningActivityUpdate
from auth.authentication import authenticate_user, create_access_token, get_current_user, get_password_hash
from utils.db_manager import get_db, init_db, ensure_indexes_exist
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize FastAPI app
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
    await init_db()
    await ensure_indexes_exist()
    print("Database initialized")

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
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User routes
@app.post("/users/", response_model=User)
async def create_user(user_data: UserCreate):
    """Create a new user."""
    db = await get_db()
    
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await db.users.find_one({"email": user_data.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate passwords match if confirm_password is provided
    if user_data.confirm_password and user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Create user document
    now = datetime.utcnow()
    user_id = str(uuid.uuid4())
    
    user_dict = {
        "id": user_id,
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "grade_level": user_data.grade_level,
        "subjects_of_interest": user_data.subjects_of_interest,
        "learning_style": user_data.learning_style.value if user_data.learning_style else None,
        "is_active": True,
        "hashed_password": get_password_hash(user_data.password),
        "created_at": now,
        "updated_at": now
    }
    
    # Insert user
    await db.users.insert_one(user_dict)
    
    # Return user data (exclude password)
    return {**user_dict, "hashed_password": None}

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    """Get current user profile."""
    return current_user

# Content routes
@app.get("/content/", response_model=List[Content])
async def get_content(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    current_user: Dict = Depends(get_current_user)
):
    """Get content with optional filters."""
    db = await get_db()
    
    # Build query
    query = {}
    if subject:
        query["subject"] = subject
    if content_type:
        query["content_type"] = content_type
    
    # Get content
    contents = await db.contents.find(query).to_list(length=100)
    return contents

# Learning plan routes
@app.get("/learning-plans/", response_model=List[LearningPlan])
async def get_learning_plans(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    current_user: Dict = Depends(get_current_user)
):
    """Get learning plans for the current user."""
    db = await get_db()
    
    # Build query
    query = {"student_id": current_user["id"]}
    if subject:
        query["subject"] = subject
    
    # Get learning plans
    plans = await db.learning_plans.find(query).to_list(length=100)
    return plans

@app.post("/learning-plans/", response_model=LearningPlan)
async def create_learning_plan(
    plan_data: LearningPlanCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new learning plan."""
    db = await get_db()
    
    # Generate a sample learning plan (normally would use AI here)
    now = datetime.utcnow()
    plan_id = str(uuid.uuid4())
    
    # Create plan document
    plan_dict = {
        "id": plan_id,
        "_id": plan_id,
        "student_id": current_user["id"],
        "title": plan_data.title or f"Learning Plan for {plan_data.subject}",
        "description": plan_data.description or f"A personalized learning plan for {plan_data.subject}",
        "subject": plan_data.subject,
        "topics": plan_data.topics or [plan_data.subject],
        "activities": [activity.dict() for activity in plan_data.activities],
        "created_at": now,
        "updated_at": now,
        "start_date": plan_data.start_date or now,
        "end_date": plan_data.end_date or (now + timedelta(days=14)),
        "status": ActivityStatus.NOT_STARTED,
        "progress_percentage": 0.0,
        "metadata": plan_data.metadata or {}
    }
    
    # If no activities provided, create some sample ones
    if not plan_dict["activities"]:
        for i in range(1, 4):
            activity_id = str(uuid.uuid4())
            activity = {
                "id": activity_id,
                "title": f"Activity {i}",
                "description": f"Sample activity {i} for {plan_data.subject}",
                "content_id": None,
                "duration_minutes": 30,
                "order": i,
                "status": ActivityStatus.NOT_STARTED,
                "completed_at": None
            }
            plan_dict["activities"].append(activity)
    
    # Insert plan
    await db.learning_plans.insert_one(plan_dict)
    
    return plan_dict

@app.put("/learning-plans/{plan_id}/activities/{activity_id}")
async def update_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    update_data: LearningActivityUpdate = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Update activity status in a learning plan."""
    db = await get_db()
    
    # Get the plan and verify ownership
    plan = await db.learning_plans.find_one({
        "_id": plan_id,
        "student_id": current_user["id"]
    })
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan not found"
        )
    
    # Find and update the activity
    activity_found = False
    activities = plan["activities"]
    
    for i, activity in enumerate(activities):
        if activity["id"] == activity_id:
            activities[i]["status"] = update_data.status
            if update_data.status == ActivityStatus.COMPLETED:
                activities[i]["completed_at"] = datetime.utcnow().isoformat()
            activity_found = True
            break
    
    if not activity_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found in learning plan"
        )
    
    # Calculate progress percentage
    total_activities = len(activities)
    completed_activities = sum(1 for a in activities if a["status"] == ActivityStatus.COMPLETED)
    progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
    
    # Determine plan status
    plan_status = ActivityStatus.NOT_STARTED
    if completed_activities == total_activities:
        plan_status = ActivityStatus.COMPLETED
    elif completed_activities > 0:
        plan_status = ActivityStatus.IN_PROGRESS
    
    # Update plan in database
    await db.learning_plans.update_one(
        {"_id": plan_id},
        {
            "$set": {
                "activities": activities,
                "progress_percentage": progress_percentage,
                "status": plan_status,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Activity status updated",
        "progress_percentage": progress_percentage,
        "plan_status": plan_status
    }

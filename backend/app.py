from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
import logging
import uvicorn

from auth.authentication import (
    create_access_token,
    get_current_user,
    authenticate_user_password,
    get_microsoft_token,
    get_microsoft_user_info,
    create_user_from_microsoft
)
from models.user import User, UserCreate, Token
from models.content import Content, ContentType
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from rag.retriever import retrieve_relevant_content
from rag.document_processor import ensure_indexes_exist
from rag.generator import generate_learning_plan
from rag.learning_planner import get_learning_planner
from rag.content_analyzer import get_content_analyzer
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

# Initialize database and search indexes
@app.on_event("startup")
async def startup_db_client():
    await init_db()
    await ensure_indexes_exist()
    logger.info("Database and search indexes initialized")

# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user_password(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/microsoft/token")
async def microsoft_auth(code: str, redirect_uri: str):
    """Exchange Microsoft authorization code for access token."""
    token_data = await get_microsoft_token(code, redirect_uri)
    
    # Get user info from Microsoft Graph
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token response"
        )
    
    user_info = await get_microsoft_user_info(access_token)
    
    # Create or update user
    user = await create_user_from_microsoft(user_info)
    
    # Create JWT token for our API
    access_token = create_access_token(data={"sub": user.username})
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

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
    
    # Create user document
    user_dict = user_data.dict(exclude={"password"})
    user_dict["hashed_password"] = get_password_hash(user_data.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    # Insert user
    result = await db.users.insert_one(user_dict)
    
    # Get the created user
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    return User(**created_user)

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user

# Content routes
@app.get("/content/", response_model=List[Content])
async def get_content(
    subject: Optional[str] = None, 
    content_type: Optional[ContentType] = None,
    current_user: User = Depends(get_current_user)
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

@app.get("/content/recommendations/", response_model=List[Content])
async def get_recommendations(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get personalized content recommendations."""
    try:
        # Get relevant content using RAG
        relevant_content = await retrieve_relevant_content(
            student_profile=current_user,
            subject=subject,
            k=10
        )
        return relevant_content
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendations"
        )

@app.get("/content/analyze/{content_id}")
async def analyze_content(
    content_id: str,
    current_user: User = Depends(get_current_user)
):
    """Analyze content using Azure Cognitive Services."""
    try:
        # Get content
        db = await get_db()
        content_doc = await db.contents.find_one({"id": content_id})
        
        if not content_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        
        content = Content(**content_doc)
        
        # Get content analyzer
        analyzer = await get_content_analyzer()
        
        # Analyze content
        analysis_results = await analyzer.analyze_content(content)
        
        return {
            "content_id": content_id,
            "title": content.title,
            "analysis": analysis_results
        }
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze content"
        )

# Learning plan routes
@app.post("/learning-plans/", response_model=LearningPlan)
async def create_learning_plan(
    subject: str,
    duration_days: Optional[int] = 14,
    current_user: User = Depends(get_current_user)
):
    """Create a personalized learning plan."""
    try:
        # Get relevant content for the subject
        relevant_content = await retrieve_relevant_content(
            student_profile=current_user,
            subject=subject,
            k=15
        )
        
        # Get learning planner
        planner = await get_learning_planner()
        
        # Create learning plan
        learning_plan = await planner.create_learning_plan(
            student=current_user,
            subject=subject,
            relevant_content=relevant_content,
            duration_days=duration_days
        )
        
        # Save learning plan to database
        db = await get_db()
        result = await db.learning_plans.insert_one(learning_plan.dict())
        
        # Get created plan
        created_plan = await db.learning_plans.find_one({"_id": result.inserted_id})
        
        return LearningPlan(**created_plan)
    except Exception as e:
        logger.error(f"Error creating learning plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create learning plan"
        )

@app.get("/learning-plans/", response_model=List[LearningPlan])
async def get_learning_plans(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get learning plans for the current user."""
    try:
        db = await get_db()
        
        # Build query
        query = {"student_id": current_user.id}
        if subject:
            query["subject"] = subject
        
        # Get learning plans
        plans = await db.learning_plans.find(query).to_list(length=100)
        
        return plans
    except Exception as e:
        logger.error(f"Error getting learning plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning plans"
        )

@app.put("/learning-plans/{plan_id}/activities/{activity_id}")
async def update_activity_status(
    plan_id: str,
    activity_id: str,
    status: ActivityStatus,
    current_user: User = Depends(get_current_user)
):
    """Update activity status in a learning plan."""
    try:
        db = await get_db()
        
        # Get the learning plan
        plan = await db.learning_plans.find_one({
            "id": plan_id,
            "student_id": current_user.id
        })
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
            )
        
        # Parse as LearningPlan model
        learning_plan = LearningPlan(**plan)
        
        # Find and update the activity
        activity_found = False
        for i, activity in enumerate(learning_plan.activities):
            if activity.id == activity_id:
                learning_plan.activities[i].status = status
                if status == ActivityStatus.COMPLETED:
                    learning_plan.activities[i].completed_at = datetime.utcnow()
                activity_found = True
                break
        
        if not activity_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found in learning plan"
            )
        
        # Calculate progress percentage
        total_activities = len(learning_plan.activities)
        completed_activities = sum(1 for a in learning_plan.activities if a.status == ActivityStatus.COMPLETED)
        learning_plan.progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
        
        # Update plan status
        if completed_activities == total_activities:
            learning_plan.status = ActivityStatus.COMPLETED
        elif completed_activities > 0:
            learning_plan.status = ActivityStatus.IN_PROGRESS
        else:
            learning_plan.status = ActivityStatus.NOT_STARTED
        
        # Update learning plan in database
        await db.learning_plans.update_one(
            {"id": plan_id},
            {"$set": {
                "activities": [a.dict() for a in learning_plan.activities],
                "progress_percentage": learning_plan.progress_percentage,
                "status": learning_plan.status,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {
            "success": True,
            "message": "Activity status updated",
            "progress_percentage": learning_plan.progress_percentage,
            "status": learning_plan.status
        }
    except Exception as e:
        logger.error(f"Error updating activity status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update activity status"
        )

@app.post("/learning-paths/")
async def create_advanced_learning_path(
    subject: str,
    duration_weeks: Optional[int] = 4,
    current_user: User = Depends(get_current_user)
):
    """Create an advanced learning path with weekly structure."""
    try:
        # Get relevant content for the subject
        relevant_content = await retrieve_relevant_content(
            student_profile=current_user,
            subject=subject,
            k=20
        )
        
        # Get learning planner
        planner = await get_learning_planner()
        
        # Create advanced learning path
        learning_path = await planner.create_advanced_learning_path(
            student=current_user,
            subject=subject,
            relevant_content=relevant_content,
            duration_weeks=duration_weeks
        )
        
        # Save learning path to database
        db = await get_db()
        await db.learning_paths.insert_one(learning_path)
        
        return learning_path
    except Exception as e:
        logger.error(f"Error creating advanced learning path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create advanced learning path"
        )

@app.get("/learning-paths/")
async def get_learning_paths(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get advanced learning paths for the current user."""
    try:
        db = await get_db()
        
        # Build query
        query = {"student_id": str(current_user.id)}
        if subject:
            query["subject"] = subject
        
        # Get learning paths
        paths = await db.learning_paths.find(query).to_list(length=100)
        
        return paths
    except Exception as e:
        logger.error(f"Error getting learning paths: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning paths"
        )

@app.get("/student/progress/")
async def get_student_progress(
    current_user: User = Depends(get_current_user)
):
    """Get student progress analytics."""
    try:
        db = await get_db()
        
        # Get completed activities
        completed_plans = await db.learning_plans.find({
            "student_id": current_user.id,
            "status": {"$in": ["in_progress", "completed"]}
        }).to_list(length=100)
        
        # Extract quiz responses and writing samples
        quiz_scores = []
        writing_samples = []
        
        for plan in completed_plans:
            plan_obj = LearningPlan(**plan)
            for activity in plan_obj.activities:
                if activity.status == ActivityStatus.COMPLETED:
                    # You would typically have actual quiz scores and writing samples
                    # stored in your database. For this example, we'll simulate them.
                    if "quiz" in activity.title.lower():
                        quiz_scores.append(0.8)  # Simulated score
                    elif "writing" in activity.title.lower():
                        writing_samples.append(activity.description)
        
        # Get content analyzer
        analyzer = await get_content_analyzer()
        
        # Analyze progress
        progress_analysis = await analyzer.analyze_student_progress(
            writing_samples=writing_samples,
            quiz_scores=quiz_scores
        )
        
        # Calculate overall completion metrics
        total_plans = len(await db.learning_plans.find({"student_id": current_user.id}).to_list(length=100))
        completed_count = len([p for p in completed_plans if p["status"] == "completed"])
        in_progress_count = len([p for p in completed_plans if p["status"] == "in_progress"])
        
        # Get subject-specific progress
        subjects = {}
        for plan in completed_plans:
            subject = plan["subject"]
            if subject not in subjects:
                subjects[subject] = {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "percentage": 0
                }
            
            subjects[subject]["total"] += 1
            if plan["status"] == "completed":
                subjects[subject]["completed"] += 1
            elif plan["status"] == "in_progress":
                subjects[subject]["in_progress"] += 1
            
            # Calculate completion percentage
            subjects[subject]["percentage"] = (subjects[subject]["completed"] / subjects[subject]["total"]) * 100
        
        return {
            "total_plans": total_plans,
            "completed_plans": completed_count,
            "in_progress_plans": in_progress_count,
            "overall_completion": (completed_count / total_plans) * 100 if total_plans > 0 else 0,
            "subjects": subjects,
            "performance_analysis": progress_analysis
        }
    except Exception as e:
        logger.error(f"Error getting student progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve student progress"
        )

# Main entry point
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
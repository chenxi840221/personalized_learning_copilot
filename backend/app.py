<<<<<<< HEAD
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
from utils.logger import setup_logger
from config.settings import Settings
# Add these imports and route to your existing app.py
from fastapi import APIRouter, BackgroundTasks
from scheduler.scheduler import run_scraper
# Create scheduler router
scheduler_router = APIRouter(prefix="/admin/scheduler", tags=["admin"])
@scheduler_router.post("/run-scraper")
async def trigger_scraper(background_tasks: BackgroundTasks):
    """Manually trigger the ABC Education scraper."""
    background_tasks.add_task(run_scraper)
    return {"message": "ABC Education scraper started in background"}
# Include the router in your app
app.include_router(scheduler_router)
# Add startup event to initialize scheduler
@app.on_event("startup")
async def startup_scheduler():
    """Start scheduler in background."""
    # Uncomment the following line if you want to start the scheduler directly with the app
    # background_tasks.add_task(run_scheduler)
    pass
# Initialize configuration
settings = Settings()
# Setup logger
logger = setup_logger()
=======
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import uuid
import os

# Initialize OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Import simplified settings
from config.settings_simple import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

>>>>>>> dc2c151 (b)
# Initialize FastAPI app
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot POC",
    version="0.1.0",
)
<<<<<<< HEAD
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend URL
=======

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
>>>>>>> dc2c151 (b)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
<<<<<<< HEAD
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
=======

# Mock databases for development/testing
mock_users = {}
mock_contents = {}
mock_learning_plans = {}

# Create test user at startup
@app.on_event("startup")
async def startup_event():
    """Setup test data and initialize services"""
    
    # Create test user if not exists
    if "testuser" not in mock_users:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        mock_users["testuser"] = {
            "id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "grade_level": 8,
            "subjects_of_interest": ["Mathematics", "Science"],
            "learning_style": "visual",
            "is_active": True,
            "hashed_password": pwd_context.hash("password"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    # Create sample content
    if not mock_contents:
        # Math content
        math_id = str(uuid.uuid4())
        mock_contents[math_id] = {
            "id": math_id,
            "title": "Introduction to Algebra",
            "description": "Learn the basics of algebraic expressions and equations",
            "content_type": "video",
            "subject": "Mathematics",
            "topics": ["Algebra", "Equations"],
            "url": "https://example.com/algebra-intro",
            "difficulty_level": "beginner",
            "grade_level": [7, 8, 9],
            "duration_minutes": 15,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Science content
        science_id = str(uuid.uuid4())
        mock_contents[science_id] = {
            "id": science_id,
            "title": "The Solar System",
            "description": "Explore our solar system and learn about planets",
            "content_type": "interactive",
            "subject": "Science",
            "topics": ["Astronomy", "Solar System"],
            "url": "https://example.com/solar-system",
            "difficulty_level": "intermediate",
            "grade_level": [6, 7, 8],
            "duration_minutes": 25,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    logger.info("Server started with test user: testuser (password: password)")
    logger.info(f"Added {len(mock_contents)} sample content items")

# Auth utils
from passlib.context import CryptContext
from jose import jwt, JWTError

# Password utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verify password against hashed version."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password."""
    return pwd_context.hash(password)

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
    user = mock_users.get(username)
    if user is None:
        raise credentials_exception
    return user

# Authentication routes
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login to get access token."""
    user = mock_users.get(form_data.username)
    if not user or not verify_password(form_data.password, user.get("hashed_password", "")):
>>>>>>> dc2c151 (b)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
<<<<<<< HEAD
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
    db = 
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
=======
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User routes
@app.post("/users/")
async def create_user(
    user_data: Dict[str, Any] = Body(...)
):
    """Create a new user."""
    # Extract required fields
    username = user_data.get("username")
    email = user_data.get("email")
    password = user_data.get("password")
    
    # Validate required fields
    if not username or not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username, email, and password are required"
        )
    
    # Extract optional fields
    full_name = user_data.get("full_name")
    grade_level = user_data.get("grade_level")
    subjects_of_interest = user_data.get("subjects_of_interest", [])
    learning_style = user_data.get("learning_style")
    
    # Check if username exists
    if username in mock_users:
>>>>>>> dc2c151 (b)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
<<<<<<< HEAD
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
    db = 
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
        db = 
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
        db = 
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
        db = 
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
=======
        
    # Create user
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
    
    # Store in mock database
    mock_users[username] = user_dict
    
    # Return user data (exclude password)
    return {k: v for k, v in user_dict.items() if k != "hashed_password"}

@app.get("/users/me/")
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    """Get current user profile."""
    return {k: v for k, v in current_user.items() if k != "hashed_password"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}

# Content routes
@app.get("/content/")
async def get_content(
    subject: Optional[str] = None,
    content_type: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get content with optional filters."""
    # Filter content
    results = []
    for content in mock_contents.values():
        if subject and content["subject"] != subject:
            continue
        if content_type and content["content_type"] != content_type:
            continue
        results.append(content)
    return results

@app.get("/content/recommendations/")
async def get_recommendations(
    subject: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get personalized content recommendations."""
    # In a real app, this would use AI to generate personalized recommendations
    # For now, just return all content for the subject
    results = []
    for content in mock_contents.values():
        if subject and content["subject"] != subject:
            continue
        results.append(content)
    return results[:10]  # Return up to 10 items

# Learning plans routes
@app.get("/learning-plans/")
async def get_learning_plans(
    subject: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get learning plans for current user."""
    # Filter plans
    results = []
    for plan in mock_learning_plans.values():
        if plan["student_id"] != current_user["id"]:
            continue
        if subject and plan["subject"] != subject:
            continue
        results.append(plan)
    return results

@app.post("/learning-plans/")
async def create_learning_plan(
    plan_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Create a new learning plan."""
    # Extract required fields
    subject = plan_data.get("subject")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subject is required"
        )
    
    # Extract optional fields
    title = plan_data.get("title")
    description = plan_data.get("description")
    topics = plan_data.get("topics", [])
    activities = plan_data.get("activities", [])
    
    # Default title and description if not provided
    if not title:
        title = f"Learning Plan for {subject}"
    if not description:
        description = f"A personalized learning plan for {subject}"
    
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Process activities
    processed_activities = []
    
    # Use provided activities if available
    if activities:
        for i, activity in enumerate(activities):
            activity_id = str(uuid.uuid4())
            processed_activity = {
                "id": activity_id,
                "title": activity.get("title", f"Activity {i+1}"),
                "description": activity.get("description", f"Activity for {subject}"),
                "content_id": activity.get("content_id"),
                "duration_minutes": activity.get("duration_minutes", 30),
                "order": i + 1,
                "status": "not_started",
                "completed_at": None
            }
            processed_activities.append(processed_activity)
    else:
        # Use available content as activities
        for i, content_id in enumerate(list(mock_contents.keys())[:3]):  # Get up to 3 content items
            content = mock_contents[content_id]
            if content["subject"] == subject:
                activity_id = str(uuid.uuid4())
                activity = {
                    "id": activity_id,
                    "title": f"Study: {content['title']}",
                    "description": content['description'],
                    "content_id": content_id,
                    "duration_minutes": content.get("duration_minutes", 30),
                    "order": i + 1,
                    "status": "not_started",
                    "completed_at": None
                }
                processed_activities.append(activity)
    
    # If no activities created yet, add generic ones
    if not processed_activities:
        for i in range(3):
            activity_id = str(uuid.uuid4())
            activity = {
                "id": activity_id,
                "title": f"Activity {i+1}",
                "description": f"Learn about an important topic in {subject}",
                "content_id": None,
                "duration_minutes": 30,
                "order": i + 1,
                "status": "not_started",
                "completed_at": None
            }
            processed_activities.append(activity)
    
    # Create the plan
    plan = {
        "id": plan_id,
        "student_id": current_user["id"],
        "title": title,
        "description": description,
        "subject": subject,
        "topics": topics or [subject],
        "activities": processed_activities,
        "created_at": now,
        "updated_at": now,
        "start_date": now,
        "end_date": now,  # Would calculate based on activities in production
        "status": "not_started",
        "progress_percentage": 0.0
    }
    
    # Save to mock database
    mock_learning_plans[plan_id] = plan
    return plan

>>>>>>> dc2c151 (b)
@app.put("/learning-plans/{plan_id}/activities/{activity_id}")
async def update_activity_status(
    plan_id: str,
    activity_id: str,
<<<<<<< HEAD
    status: ActivityStatus,
    current_user: User = Depends(get_current_user)
):
    """Update activity status in a learning plan."""
    try:
        db = 
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
        db = 
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
        db = 
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
        db = 
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
=======
    status: str,
    current_user: Dict = Depends(get_current_user)
):
    """Update activity status in a learning plan."""
    # Find the plan
    plan = mock_learning_plans.get(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan not found"
        )
    
    # Check ownership
    if plan["student_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this plan"
        )
    
    # Find the activity
    activity_found = False
    activities = plan["activities"]
    for i, activity in enumerate(activities):
        if activity["id"] == activity_id:
            activities[i]["status"] = status
            if status == "completed":
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
    completed_activities = sum(1 for a in activities if a["status"] == "completed")
    progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
    
    # Determine plan status
    plan_status = "not_started"
    if completed_activities == total_activities:
        plan_status = "completed"
    elif completed_activities > 0:
        plan_status = "in_progress"
    
    # Update plan
    plan["activities"] = activities
    plan["progress_percentage"] = progress_percentage
    plan["status"] = plan_status
    plan["updated_at"] = datetime.utcnow().isoformat()
    
    return {
        "success": True,
        "message": "Activity status updated",
        "progress_percentage": progress_percentage,
        "plan_status": plan_status
    }

# Main entrypoint
if __name__ == "__main__":
    import uvicorn
>>>>>>> dc2c151 (b)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
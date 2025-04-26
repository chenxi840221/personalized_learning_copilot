# backend/app.py
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
    
    # Initialize Azure LangChain integration
    try:
        from rag.azure_langchain_integration import get_azure_langchain
        azure_langchain = await get_azure_langchain()
        logger.info("Azure LangChain integration initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Azure LangChain integration: {e}")
    
    # Initialize LangChain service
    try:
        from services.azure_langchain_service import get_azure_langchain_service
        langchain_service = await get_azure_langchain_service()
        logger.info("Azure LangChain service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Azure LangChain service: {e}")
    
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
    # Enhanced logging for debugging authentication
    logger.info(f"Login attempt for user: {form_data.username}")
    
    user = mock_users.get(form_data.username)
    if not user or not verify_password(form_data.password, user.get("hashed_password", "")):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token with extended expiry for testing
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    logger.info(f"Successful login for user: {form_data.username}")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
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

@app.put("/learning-plans/{plan_id}/activities/{activity_id}")
async def update_activity_status(
    plan_id: str,
    activity_id: str,
    status: str = Body(...),
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

# Include LangChain endpoints
try:
    from api.langchain_endpoints import langchain_router
    app.include_router(langchain_router)
    logger.info("LangChain router included")
except ImportError as e:
    logger.warning(f"LangChain endpoints not available: {e}")

# Include Azure LangChain endpoints
try:
    from api.azure_langchain_routes import azure_langchain_router
    app.include_router(azure_langchain_router)
    logger.info("Azure LangChain router included")
except ImportError as e:
    logger.warning(f"Azure LangChain endpoints not available: {e}")

# Main entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
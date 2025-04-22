from fastapi import FastAPI, Depends, HTTPException, status, Body, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from passlib.context import CryptContext
from jose import jwt, JWTError
# Constants
SECRET_KEY = "yoursecretkey"  # In production, use a proper secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Password security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# Mock databases
mock_users = {}
mock_contents = {}
mock_learning_plans = {}
# Initialize FastAPI app
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot POC",
    version="0.1.0",
)
# Add CORS middleware with hardcoded values
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password):
    return pwd_context.hash(password)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
# Add a demo user for testing
@app.on_event("startup")
async def startup_event():
    # Create a test user
    if "testuser" not in mock_users:
        mock_users["testuser"] = {
            "id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "grade_level": 5,
            "subjects_of_interest": ["Math", "Science"],
            "learning_style": "visual",
            "is_active": True,
            "hashed_password": get_password_hash("password"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    print("Server started with test user: testuser (password: password)")
# Content Type and Difficulty Enums
class ContentType:
    ARTICLE = "article"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    LESSON = "lesson"
    ACTIVITY = "activity"
class DifficultyLevel:
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
# Content endpoints
@app.get("/content/")
async def get_content(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
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
@app.post("/content/")
async def create_content(
    title: str = Body(...),
    description: str = Body(...),
    content_type: str = Body(...),
    subject: str = Body(...),
    url: str = Body(...),
    difficulty_level: str = Body(...),
    topics: List[str] = Body([]),
    grade_level: List[int] = Body([]),
    duration_minutes: Optional[int] = Body(None),
    current_user: Dict = Depends(get_current_user)
):
    """Create new content."""
    content_id = str(uuid.uuid4())
    content = {
        "id": content_id,
        "title": title,
        "description": description,
        "content_type": content_type,
        "subject": subject,
        "topics": topics,
        "url": url,
        "difficulty_level": difficulty_level,
        "grade_level": grade_level,
        "duration_minutes": duration_minutes,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    mock_contents[content_id] = content
    return content
# Add some sample content at startup
@app.on_event("startup")
async def add_sample_content():
    if not mock_contents:
        # Math content
        mock_contents["math1"] = {
            "id": "math1",
            "title": "Introduction to Algebra",
            "description": "Learn the basics of algebraic expressions and equations",
            "content_type": ContentType.VIDEO,
            "subject": "Mathematics",
            "topics": ["Algebra", "Equations"],
            "url": "https://example.com/algebra-intro",
            "difficulty_level": DifficultyLevel.BEGINNER,
            "grade_level": [5, 6, 7],
            "duration_minutes": 15,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        # Science content
        mock_contents["science1"] = {
            "id": "science1",
            "title": "The Solar System",
            "description": "Explore our solar system and learn about planets",
            "content_type": ContentType.INTERACTIVE,
            "subject": "Science",
            "topics": ["Astronomy", "Solar System"],
            "url": "https://example.com/solar-system",
            "difficulty_level": DifficultyLevel.INTERMEDIATE,
            "grade_level": [4, 5, 6],
            "duration_minutes": 25,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        # English content
        mock_contents["english1"] = {
            "id": "english1",
            "title": "Basic Grammar Rules",
            "description": "Learn essential grammar rules for better writing",
            "content_type": ContentType.ARTICLE,
            "subject": "English",
            "topics": ["Grammar", "Writing"],
            "url": "https://example.com/grammar-basics",
            "difficulty_level": DifficultyLevel.BEGINNER,
            "grade_level": [3, 4, 5, 6],
            "duration_minutes": 10,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    print(f"Added {len(mock_contents)} sample content items")
# Activity Status Enum
class ActivityStatus:
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
# Learning Plan endpoints
@app.get("/learning-plans/")
async def get_learning_plans(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    current_user: Dict = Depends(get_current_user)
):
    """Get learning plans for the current user."""
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
    subject: str = Body(...),
    title: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    topics: List[str] = Body([]),
    activities: List[Dict] = Body([]),
    current_user: Dict = Depends(get_current_user)
):
    """Create a new learning plan."""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    # Default title and description if not provided
    if not title:
        title = f"Learning Plan for {subject}"
    if not description:
        description = f"A personalized learning plan for {subject}"
    # Process activities
    processed_activities = []
    for i, activity in enumerate(activities):
        activity_id = str(uuid.uuid4())
        processed_activity = {
            "id": activity_id,
            "title": activity.get("title", f"Activity {i+1}"),
            "description": activity.get("description", f"Learn about {subject}"),
            "content_id": activity.get("content_id"),
            "duration_minutes": activity.get("duration_minutes", 30),
            "order": i + 1,
            "status": ActivityStatus.NOT_STARTED,
            "completed_at": None
        }
        processed_activities.append(processed_activity)
    # If no activities provided, create some sample ones
    if not processed_activities:
        # Use the sample content as activities
        for i, content_id in enumerate(mock_contents.keys()):
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
                    "status": ActivityStatus.NOT_STARTED,
                    "completed_at": None
                }
                processed_activities.append(activity)
    # Default to some generic activities if no content matched
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
                "status": ActivityStatus.NOT_STARTED,
                "completed_at": None
            }
            processed_activities.append(activity)
    # Create the learning plan
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
        "end_date": now,  # In a real app, would be calculated based on activities
        "status": ActivityStatus.NOT_STARTED,
        "progress_percentage": 0.0
    }
    mock_learning_plans[plan_id] = plan
    return plan
@app.put("/learning-plans/{plan_id}/activities/{activity_id}")
async def update_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    status: str = Body(..., description="New status"),
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
            if status == ActivityStatus.COMPLETED:
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
@app.get("/learning-plans/{plan_id}")
async def get_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific learning plan."""
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
            detail="You don't have permission to view this plan"
        )
    return plan

import logging
import motor.motor_asyncio
from typing import Optional
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Database client
client = None
db = None

async def init_db():
    """Initialize database connection."""
    global client, db
    try:
        # Create MongoDB client
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]
        
        # Create indexes for faster queries
        await db.users.create_index("username", unique=True)
        await db.users.create_index("email", unique=True)
        await db.contents.create_index("subject")
        await db.contents.create_index("content_type")
        await db.contents.create_index([("title", "text"), ("description", "text")])
        await db.learning_plans.create_index("student_id")
        await db.learning_plans.create_index("subject")
        
        logger.info("Database connection established")
        return db
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def get_db():
    """Get database connection."""
    global db
    if db is None:
        await init_db()
    return db

async def close_db():
    """Close database connection."""
    global client
    if client:
        client.close()
        logger.info("Database connection closed")

async def seed_sample_data():
    """Seed the database with sample data for testing."""
    from models.user import UserCreate, User
    from models.content import ContentCreate, Content
    from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
    from auth.authentication import get_password_hash
    
    # Get database connection
    db = await get_db()
    
    # Check if we already have data
    user_count = await db.users.count_documents({})
    if user_count > 0:
        logger.info("Database already seeded")
        return
    
    try:
        # Create sample users
        sample_users = [
            {
                "username": "student1",
                "email": "student1@example.com",
                "full_name": "Student One",
                "password": "password123",
                "grade_level": 5,
                "subjects_of_interest": ["Mathematics", "Science"],
                "learning_style": "visual"
            },
            {
                "username": "student2",
                "email": "student2@example.com",
                "full_name": "Student Two",
                "password": "password123",
                "grade_level": 8,
                "subjects_of_interest": ["English", "History"],
                "learning_style": "reading_writing"
            }
        ]
        
        for user_data in sample_users:
            password = user_data.pop("password")
            hashed_password = get_password_hash(password)
            user_data["hashed_password"] = hashed_password
            await db.users.insert_one(user_data)
        
        # Create sample content
        sample_contents = [
            {
                "title": "Introduction to Fractions",
                "description": "Learn about fractions and how they represent parts of a whole.",
                "content_type": "lesson",
                "subject": "Mathematics",
                "topics": ["Fractions", "Numbers"],
                "url": "https://www.abc.net.au/education/subjects-and-topics/mathematics/fractions",
                "difficulty_level": "beginner",
                "grade_level": [4, 5, 6],
                "duration_minutes": 30
            },
            {
                "title": "The Water Cycle",
                "description": "Explore how water moves through the Earth's systems.",
                "content_type": "interactive",
                "subject": "Science",
                "topics": ["Water Cycle", "Earth Systems"],
                "url": "https://www.abc.net.au/education/subjects-and-topics/science/water-cycle",
                "difficulty_level": "intermediate",
                "grade_level": [5, 6, 7],
                "duration_minutes": 45
            },
            {
                "title": "Shakespeare's Romeo and Juliet",
                "description": "An introduction to Shakespeare's famous tragedy.",
                "content_type": "article",
                "subject": "English",
                "topics": ["Shakespeare", "Drama", "Literature"],
                "url": "https://www.abc.net.au/education/subjects-and-topics/english/shakespeare",
                "difficulty_level": "advanced",
                "grade_level": [8, 9, 10],
                "duration_minutes": 60
            }
        ]
        
        for content_data in sample_contents:
            await db.contents.insert_one(content_data)
        
        logger.info("Sample data seeded successfully")
    except Exception as e:
        logger.error(f"Failed to seed sample data: {e}")
        raise

async def initialize_db():
    """Initialize the database with collections and sample data."""
    await init_db()
    await seed_sample_data()
    return db
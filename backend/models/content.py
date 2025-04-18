from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from bson import ObjectId
import uuid

# Custom ObjectId for MongoDB
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Content Type Enum
class ContentType(str, Enum):
    ARTICLE = "article"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    LESSON = "lesson"
    ACTIVITY = "activity"

# Difficulty Level Enum
class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# Content models
class Content(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str
    description: str
    content_type: ContentType
    subject: str
    topics: List[str] = []
    url: HttpUrl
    source: str = "ABC Education"
    difficulty_level: DifficultyLevel
    grade_level: List[int] = []  # List of grade levels this content is suitable for
    duration_minutes: Optional[int] = None
    keywords: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

# Content Creation model
class ContentCreate(BaseModel):
    title: str
    description: str
    content_type: ContentType
    subject: str
    topics: List[str] = []
    url: HttpUrl
    source: str = "ABC Education"
    difficulty_level: DifficultyLevel
    grade_level: List[int] = []
    duration_minutes: Optional[int] = None
    keywords: List[str] = []
    metadata: Dict[str, Any] = {}

# Content with embedding
class ContentWithEmbedding(Content):
    embedding: List[float] = []
    embedding_model: str = "text-embedding-ada-002"
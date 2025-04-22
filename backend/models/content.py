from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    class Config:
        orm_mode = True
# Content with embedding model
class ContentWithEmbedding(Content):
    embedding: List[float]
    embedding_model: str = "text-embedding-ada-002"
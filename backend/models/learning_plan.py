from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from bson import ObjectId

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

# Activity Status Enum
class ActivityStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Learning Activity model
class LearningActivity(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    title: str
    description: str
    content_id: Optional[PyObjectId] = None
    duration_minutes: int
    order: int
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    completed_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

# Learning Plan model
class LearningPlan(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    student_id: PyObjectId
    title: str
    description: str
    subject: str
    topics: List[str] = []
    activities: List[LearningActivity] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    progress_percentage: float = 0.0
    metadata: Dict[str, Any] = {}
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

# Learning Plan Creation model
class LearningPlanCreate(BaseModel):
    student_id: PyObjectId
    title: str
    description: str
    subject: str
    topics: List[str] = []
    activities: List[LearningActivity] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

# Learning Plan Progress Update
class LearningActivityUpdate(BaseModel):
    activity_id: str
    status: ActivityStatus
    completed_at: Optional[datetime] = None
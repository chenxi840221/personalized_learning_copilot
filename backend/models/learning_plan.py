from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

# Activity Status Enum
class ActivityStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Learning Activity model
class LearningActivity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    content_id: Optional[str] = None
    duration_minutes: int
    order: int
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    completed_at: Optional[datetime] = None

# Learning Plan model
class LearningPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
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
        orm_mode = True

# Learning Plan Creation model
class LearningPlanCreate(BaseModel):
    subject: str
    title: Optional[str] = None
    description: Optional[str] = None
    topics: List[str] = []
    activities: List[LearningActivity] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

# Learning Activity Update
class LearningActivityUpdate(BaseModel):
    activity_id: str
    status: ActivityStatus
    completed_at: Optional[datetime] = None

# API Endpoints (endpoints.py)
# ./personalized_learning_copilot/backend/api/endpoints.py

from fastapi import Depends, HTTPException, Query, Path, Body, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from models.user import User
from models.content import Content, ContentType
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.authentication import get_current_user
from rag.retriever import retrieve_relevant_content
from rag.generator import generate_learning_plan
from utils.db_manager import get_db

# User endpoints
async def get_user_endpoint(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user's profile."""
    return current_user

# Content endpoints
async def get_content_endpoint(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    current_user: User = Depends(get_current_user)
) -> List[Content]:
    """Get content with optional filters."""
    db = await get_db()
    query = {}
    
    if subject:
        query["subject"] = subject
    if content_type:
        query["content_type"] = content_type
    
    contents = await db.contents.find(query).to_list(length=100)
    return [Content(**content) for content in contents]

async def get_recommendations_endpoint(
    subject: Optional[str] = Query(None, description="Optional subject focus"),
    current_user: User = Depends(get_current_user)
) -> List[Content]:
    """Get personalized content recommendations."""
    relevant_content = await retrieve_relevant_content(
        student_profile=current_user,
        subject=subject
    )
    return relevant_content

# Learning plan endpoints
async def get_learning_plans_endpoint(
    current_user: User = Depends(get_current_user)
) -> List[LearningPlan]:
    """Get all learning plans for the current user."""
    db = await get_db()
    plans = await db.learning_plans.find({"student_id": current_user.id}).to_list(length=100)
    return [LearningPlan(**plan) for plan in plans]

async def create_learning_plan_endpoint(
    subject: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user)
) -> LearningPlan:
    """Create a new personalized learning plan."""
    learning_plan = await generate_learning_plan(
        student=current_user,
        subject=subject
    )
    
    # Save to database
    db = await get_db()
    result = await db.learning_plans.insert_one(learning_plan.dict())
    created_plan = await db.learning_plans.find_one({"_id": result.inserted_id})
    
    return LearningPlan(**created_plan)

async def update_activity_status_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    status: ActivityStatus = Body(..., embed=True),
    completed_at: Optional[datetime] = Body(None, embed=True),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update the status of a learning activity."""
    db = await get_db()
    
    # Get the plan and verify ownership
    plan = await db.learning_plans.find_one({
        "_id": ObjectId(plan_id),
        "student_id": current_user.id
    })
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan not found or access denied"
        )
    
    # Convert to model for easier handling
    plan_model = LearningPlan(**plan)
    
    # Find and update the activity
    activity_found = False
    updated_activities = []
    
    for activity in plan_model.activities:
        if activity.id == activity_id:
            activity.status = status
            activity.completed_at = completed_at if status == ActivityStatus.COMPLETED else None
            activity_found = True
        updated_activities.append(activity.dict())
    
    if not activity_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    # Calculate new progress percentage
    total_activities = len(updated_activities)
    completed_activities = sum(1 for a in updated_activities if a["status"] == ActivityStatus.COMPLETED)
    progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
    
    # Determine plan status
    if completed_activities == total_activities:
        plan_status = ActivityStatus.COMPLETED
    elif completed_activities > 0:
        plan_status = ActivityStatus.IN_PROGRESS
    else:
        plan_status = ActivityStatus.NOT_STARTED
    
    # Update the plan in the database
    await db.learning_plans.update_one(
        {"_id": ObjectId(plan_id)},
        {
            "$set": {
                "activities": updated_activities,
                "progress_percentage": progress_percentage,
                "status": plan_status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Activity status updated",
        "progress_percentage": progress_percentage,
        "plan_status": plan_status
    }
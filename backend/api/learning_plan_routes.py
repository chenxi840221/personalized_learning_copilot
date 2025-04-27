# backend/api/learning_plan_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.entra_auth import get_current_user
from services.azure_learning_plan_service import get_learning_plan_service
from rag.generator import get_plan_generator
from rag.retriever import retrieve_relevant_content

# Create router
router = APIRouter(prefix="/learning-plans", tags=["learning-plans"])

@router.get("/")
async def get_learning_plans(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    limit: int = Query(50, description="Maximum number of plans to return"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all learning plans for the current user.
    
    Args:
        subject: Optional subject filter
        limit: Maximum number of plans to return
        current_user: Current authenticated user
        
    Returns:
        List of learning plans
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Get learning plans
        plans = await learning_plan_service.get_learning_plans(
            user_id=current_user["id"],
            subject=subject,
            limit=limit
        )
        
        # Convert to JSON-serializable format
        return [plan.dict() for plan in plans]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning plans: {str(e)}"
        )

@router.post("/")
async def create_learning_plan(
    subject: str = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new personalized learning plan.
    
    Args:
        subject: Subject for the learning plan
        current_user: Current authenticated user
        
    Returns:
        Created learning plan
    """
    try:
        # Create a user model from current user
        from models.user import User, LearningStyle
        
        user = User(
            id=current_user["id"],
            username=current_user["username"],
            email=current_user["email"],
            full_name=current_user.get("full_name", ""),
            grade_level=current_user.get("grade_level"),
            subjects_of_interest=current_user.get("subjects_of_interest", []),
            learning_style=LearningStyle(current_user.get("learning_style")) if current_user.get("learning_style") else None,
            is_active=True
        )
        
        # Get relevant content for the learning plan
        relevant_content = await retrieve_relevant_content(
            student_profile=user,
            subject=subject,
            k=15
        )
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Generate learning plan
        learning_plan = await plan_generator.create_learning_plan(
            student=user,
            subject=subject,
            relevant_content=relevant_content
        )
        
        # Get learning plan service and save the plan
        learning_plan_service = await get_learning_plan_service()
        success = await learning_plan_service.create_learning_plan(learning_plan)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save learning plan"
            )
        
        # Return the created plan
        return learning_plan.dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating learning plan: {str(e)}"
        )

@router.get("/{plan_id}")
async def get_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific learning plan.
    
    Args:
        plan_id: Learning plan ID
        current_user: Current authenticated user
        
    Returns:
        Learning plan
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Get learning plan
        plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
            )
        
        # Return the plan
        return plan.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning plan: {str(e)}"
        )

@router.put("/{plan_id}/activities/{activity_id}")
async def update_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    status: str = Body(..., embed=True),
    completed_at: Optional[str] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the status of a learning activity.
    
    Args:
        plan_id: Learning plan ID
        activity_id: Activity ID
        status: New status (not_started, in_progress, completed)
        completed_at: Optional completion date (ISO format)
        current_user: Current authenticated user
        
    Returns:
        Status update information
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Parse status
        try:
            activity_status = ActivityStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Must be one of: not_started, in_progress, completed"
            )
        
        # Parse completed_at date if provided
        completion_date = None
        if completed_at:
            try:
                completion_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid completed_at date format: {completed_at}. Must be ISO format"
                )
        
        # Update activity status
        result = await learning_plan_service.update_activity_status(
            plan_id=plan_id,
            activity_id=activity_id,
            status=activity_status,
            completed_at=completion_date,
            user_id=current_user["id"]
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan or activity not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating activity status: {str(e)}"
        )
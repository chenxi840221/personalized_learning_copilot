# backend/api/endpoints.py
from fastapi import Depends, HTTPException, Query, Path, Body, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.user import User
from models.content import Content, ContentType
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.authentication import get_current_user
from services.recommendation_service import get_recommendation_service
from services.learning_plan_service import get_learning_plan_service
from scrapers.abc_edu_scraper import run_scraper
# User endpoints
async def get_user_endpoint(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user's profile."""
    return current_user
# Content endpoints
async def get_content_endpoint(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    current_user: User = Depends(get_current_user)
) -> List[Content]:
    """Get content with optional filters."""
    recommendation_service = await get_recommendation_service()
    # Generate filter expression based on parameters
    filter_parts = []
    if subject:
        filter_parts.append(f"subject eq '{subject}'")
    if content_type:
        filter_parts.append(f"content_type eq '{content_type.value}'")
    if difficulty:
        filter_parts.append(f"difficulty_level eq '{difficulty}'")
    if grade_level:
        filter_parts.append(f"grade_level/any(g: g eq {grade_level})")
    # Combine filter parts
    filter_expression = " and ".join(filter_parts) if filter_parts else None
    # Get content matching filters
    try:
        content_results = await recommendation_service.search_client.search(
            search_text="*",
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords"],
            top=50
        )
        # Convert to Content objects
        contents = []
        async for result in content_results:
            content_dict = dict(result)
            # Convert to proper enum types for model
            content_dict["content_type"] = ContentType(content_dict["content_type"])
            contents.append(Content(**content_dict))
        return contents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving content: {str(e)}"
        )
async def get_content_by_id_endpoint(
    content_id: str = Path(..., description="Content ID"),
    current_user: User = Depends(get_current_user)
) -> Content:
    """Get content by ID."""
    recommendation_service = await get_recommendation_service()
    # Get content
    content = await recommendation_service.get_content_by_id(content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    return content
async def get_recommendations_endpoint(
    subject: Optional[str] = Query(None, description="Optional subject focus"),
    current_user: User = Depends(get_current_user)
) -> List[Content]:
    """Get personalized content recommendations."""
    recommendation_service = await get_recommendation_service()
    # Get personalized recommendations
    recommendations = await recommendation_service.get_personalized_recommendations(
        user=current_user,
        subject=subject,
        limit=10
    )
    return recommendations
async def search_content_endpoint(
    query: str = Query(..., description="Search query"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    current_user: User = Depends(get_current_user)
) -> List[Content]:
    """Search for content."""
    recommendation_service = await get_recommendation_service()
    # Build filter expression
    filter_parts = []
    if subject:
        filter_parts.append(f"subject eq '{subject}'")
    if content_type:
        filter_parts.append(f"content_type eq '{content_type.value}'")
    # Add grade-appropriate filtering
    if current_user.grade_level:
        grade_filters = [
            f"grade_level/any(g: g eq {current_user.grade_level})",
            f"grade_level/any(g: g eq {current_user.grade_level - 1})",
            f"grade_level/any(g: g eq {current_user.grade_level + 1})"
        ]
        filter_parts.append(f"({' or '.join(grade_filters)})")
    # Combine filter parts
    filter_expression = " and ".join(filter_parts) if filter_parts else None
    try:
        # Generate embedding for query
        query_embedding = await recommendation_service._generate_embedding(query)
        # Perform hybrid search (keyword + semantic)
        search_results = await recommendation_service.search_client.search(
            search_text=query,
            vector={"value": query_embedding, "fields": "embedding", "k": 50},
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords"],
            top=20
        )
        # Convert to Content objects
        contents = []
        async for result in search_results:
            content_dict = dict(result)
            # Convert to proper enum types for model
            content_dict["content_type"] = ContentType(content_dict["content_type"])
            contents.append(Content(**content_dict))
        return contents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching content: {str(e)}"
        )
# Learning plan endpoints
async def get_learning_plans_endpoint(
    current_user: User = Depends(get_current_user)
) -> List[LearningPlan]:
    """Get all learning plans for the current user."""
    learning_plan_service = await get_learning_plan_service()
    plans = await learning_plan_service.get_user_learning_plans(current_user.id)
    return plans
async def create_learning_plan_endpoint(
    subject: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user)
) -> LearningPlan:
    """Create a new personalized learning plan."""
    learning_plan_service = await get_learning_plan_service()
    recommendation_service = await get_recommendation_service()
    # Get recommended content for this subject
    recommended_content = await recommendation_service.get_personalized_recommendations(
        user=current_user,
        subject=subject,
        limit=15
    )
    # Generate learning plan
    learning_plan = await learning_plan_service.generate_learning_plan(
        user=current_user,
        subject=subject,
        content_items=recommended_content
    )
    return learning_plan
async def get_learning_plan_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: User = Depends(get_current_user)
) -> LearningPlan:
    """Get a specific learning plan."""
    learning_plan_service = await get_learning_plan_service()
    plan = await learning_plan_service.get_learning_plan(plan_id, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan not found"
        )
    return plan
async def update_activity_status_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    status: ActivityStatus = Body(..., embed=True),
    completed_at: Optional[datetime] = Body(None, embed=True),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update the status of a learning activity."""
    learning_plan_service = await get_learning_plan_service()
    # Update activity status
    result = await learning_plan_service.update_activity_status(
        plan_id=plan_id,
        activity_id=activity_id,
        status=status,
        completed_at=completed_at,
        user_id=current_user.id
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan or activity not found"
        )
    return result
# Admin endpoints
async def trigger_scraper_endpoint(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Manually trigger the ABC Education scraper.
    Available only to admin users.
    """
    # Check if user is admin (would need role-based authentication)
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can trigger the scraper"
        )
    # Run scraper in background
    background_tasks.add_task(run_scraper)
    return {"message": "ABC Education scraper started in background"}
async def get_content_stats_endpoint(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get statistics about the content database.
    Available only to admin users.
    """
    # Check if user is admin
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access content statistics"
        )
    recommendation_service = await get_recommendation_service()
    try:
        # Get subject counts
        subject_counts = {}
        for subject in ["Mathematics", "Science", "English", "History", "Geography", "Arts"]:
            result = await recommendation_service.search_client.search(
                search_text="*",
                filter=f"subject eq '{subject}'",
                include_total_count=True,
                top=0
            )
            subject_counts[subject] = result.get_count()
        # Get content type counts
        content_type_counts = {}
        for content_type in ["article", "video", "interactive", "quiz", "worksheet", "lesson", "activity"]:
            result = await recommendation_service.search_client.search(
                search_text="*",
                filter=f"content_type eq '{content_type}'",
                include_total_count=True,
                top=0
            )
            content_type_counts[content_type] = result.get_count()
        # Get total count
        total_result = await recommendation_service.search_client.search(
            search_text="*",
            include_total_count=True,
            top=0
        )
        total_count = total_result.get_count()
        # Get last updated date
        latest_result = await recommendation_service.search_client.search(
            search_text="*",
            order_by=["updated_at desc"],
            select=["updated_at"],
            top=1
        )
        latest_date = None
        async for item in latest_result:
            latest_date = item.get("updated_at")
            break
        return {
            "total_count": total_count,
            "subject_counts": subject_counts,
            "content_type_counts": content_type_counts,
            "last_updated": latest_date
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving content statistics: {str(e)}"
        )
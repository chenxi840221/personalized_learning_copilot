# api/endpoints.py
from fastapi import Depends, HTTPException, Query, Path, Body, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import httpx
import json

from models.user import User
from models.content import Content, ContentType
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.authentication import get_current_user
from services.search_service import get_search_service
from rag.openai_adapter import get_openai_adapter
from rag.generator import get_plan_generator
from config.settings import Settings

# Initialize settings
settings = Settings()

# User endpoints
async def get_user_endpoint(current_user: Dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    search_service = await get_search_service()
    
    # Get user from search index
    user = await search_service.get_user(current_user["id"])
    
    if not user:
        # Create user if it doesn't exist in our system
        user_data = {
            "id": current_user["id"],
            "ms_object_id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "full_name": current_user.get("full_name", ""),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        user = await search_service.create_user(user_data)
        
    return user

async def update_user_profile_endpoint(
    profile_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Update the user profile in Azure AI Search."""
    search_service = await get_search_service()
    
    # Get existing user
    user = await search_service.get_user(current_user["id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Update fields
    user.update({
        "full_name": profile_data.get("full_name", user.get("full_name")),
        "grade_level": profile_data.get("grade_level", user.get("grade_level")),
        "subjects_of_interest": profile_data.get("subjects_of_interest", user.get("subjects_of_interest", [])),
        "learning_style": profile_data.get("learning_style", user.get("learning_style")),
        "updated_at": datetime.utcnow().isoformat()
    })
    
    # Generate embedding for user profile
    profile_text = f"User {user['username']} is in grade {user.get('grade_level')} with interests in {', '.join(user.get('subjects_of_interest', []))}. Learning style: {user.get('learning_style')}"
    embedding = await search_service.openai_adapter.create_embedding(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        text=profile_text
    )
    
    # Add embedding to user data
    user["embedding"] = embedding
    
    # Save updated user
    result = await search_service.users_index_client.upload_documents(documents=[user])
    
    if not result[0].succeeded:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )
    
    return user

# Content endpoints
async def get_content_endpoint(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    current_user: Dict = Depends(get_current_user)
):
    """Get content with optional filters."""
    search_service = await get_search_service()
    
    # Build filter expression
    filter_parts = []
    if subject:
        filter_parts.append(f"subject eq '{subject}'")
    if content_type:
        filter_parts.append(f"content_type eq '{content_type}'")
    if difficulty:
        filter_parts.append(f"difficulty_level eq '{difficulty}'")
    if grade_level:
        filter_parts.append(f"grade_level/any(g: g eq {grade_level})")
    
    filter_expression = " and ".join(filter_parts) if filter_parts else None
    
    # Execute search
    try:
        results = await search_service.content_index_client.search(
            search_text="*",
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords"],
            top=50
        )
        
        # Convert results to list
        contents = []
        async for result in results:
            contents.append(dict(result))
        
        return contents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving content: {str(e)}"
        )

async def get_content_by_id_endpoint(
    content_id: str = Path(..., description="Content ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get content by ID."""
    search_service = await get_search_service()
    
    try:
        # Get content from index
        content = await search_service.content_index_client.get_document(key=content_id)
        return dict(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

async def get_recommendations_endpoint(
    subject: Optional[str] = Query(None, description="Optional subject filter"),
    current_user: Dict = Depends(get_current_user)
):
    """Get personalized content recommendations."""
    search_service = await get_search_service()
    
    try:
        # Get user profile
        user = await search_service.get_user(current_user["id"])
        
        # Generate query for recommendations
        query_text = f"Educational content for a student in grade {user.get('grade_level', 'any')} "
        
        if user.get("learning_style"):
            query_text += f"with a {user.get('learning_style')} learning style. "
        
        if user.get("subjects_of_interest"):
            interests = ", ".join(user.get("subjects_of_interest"))
            query_text += f"Interested in {interests}. "
        
        if subject:
            query_text += f"Looking specifically for {subject} content."
        
        # Generate embedding for query
        embedding = await search_service.openai_adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=query_text
        )
        
        # Build filter expression
        filter_parts = []
        
        if subject:
            filter_parts.append(f"subject eq '{subject}'")
        
        # Add grade-level filtering if available
        if user.get("grade_level"):
            grade = user.get("grade_level")
            grade_filters = [
                f"grade_level/any(g: g eq {grade})",
                f"grade_level/any(g: g eq {grade - 1})",
                f"grade_level/any(g: g eq {grade + 1})"
            ]
            filter_parts.append(f"({' or '.join(grade_filters)})")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Execute vector search
        results = await search_service.content_index_client.search(
            search_text=None,
            vectors=[{"value": embedding, "fields": "embedding", "k": 10}],
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords"],
            top=10
        )
        
        # Convert results to list
        recommendations = []
        async for result in results:
            recommendations.append(dict(result))
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations: {str(e)}"
        )

async def search_content_endpoint(
    query: str = Query(..., description="Search query"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    current_user: Dict = Depends(get_current_user)
):
    """Search for content using both text and vector search."""
    search_service = await get_search_service()
    
    try:
        # Generate embedding for query
        embedding = await search_service.openai_adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=query
        )
        
        # Build filter expression
        filter_parts = []
        if subject:
            filter_parts.append(f"subject eq '{subject}'")
        if content_type:
            filter_parts.append(f"content_type eq '{content_type}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Execute hybrid search (text + vector)
        results = await search_service.content_index_client.search(
            search_text=query,
            vectors=[{"value": embedding, "fields": "embedding", "k": 50}],
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords"],
            top=20
        )
        
        # Convert results to list
        contents = []
        async for result in results:
            contents.append(dict(result))
        
        return contents
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching content: {str(e)}"
        )

# Learning plan endpoints
async def get_learning_plans_endpoint(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    current_user: Dict = Depends(get_current_user)
):
    """Get all learning plans for the current user."""
    search_service = await get_search_service()
    
    try:
        # Build filter expression
        filter_expression = f"student_id eq '{current_user['id']}'"
        if subject:
            filter_expression += f" and subject eq '{subject}'"
        
        # Execute search
        results = await search_service.plans_index_client.search(
            search_text="*",
            filter=filter_expression,
            order_by=["created_at desc"],
            include_total_count=True
        )
        
        # Convert results to list
        plans = []
        async for result in results:
            plans.append(dict(result))
        
        return plans
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning plans: {str(e)}"
        )

async def create_learning_plan_endpoint(
    subject: str = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """Create a new personalized learning plan."""
    search_service = await get_search_service()
    openai_adapter = await get_openai_adapter()
    
    try:
        # Get user profile
        user = await search_service.get_user(current_user["id"])
        
        # Generate query for content
        query_text = f"Educational content for {subject} appropriate for a student in grade {user.get('grade_level', 'any')} "
        
        if user.get("learning_style"):
            query_text += f"with {user.get('learning_style')} learning style. "
        
        if user.get("subjects_of_interest"):
            interests = ", ".join(user.get("subjects_of_interest"))
            query_text += f"Interested in {interests}."
        
        # Generate embedding for query
        embedding = await openai_adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=query_text
        )
        
        # Get relevant content using vector search
        filter_expression = f"subject eq '{subject}'"
        if user.get("grade_level"):
            grade = user.get("grade_level")
            grade_filters = [
                f"grade_level/any(g: g eq {grade})",
                f"grade_level/any(g: g eq {grade - 1})",
                f"grade_level/any(g: g eq {grade + 1})"
            ]
            filter_expression += f" and ({' or '.join(grade_filters)})"
        
        results = await search_service.content_index_client.search(
            search_text=None,
            vectors=[{"value": embedding, "fields": "embedding", "k": 15}],
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "url", "duration_minutes"],
            top=15
        )
        
        # Extract content items
        content_items = []
        async for result in results:
            content_items.append(dict(result))
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Generate learning plan
        plan_dict = await plan_generator.generate_plan(
            student=user,
            subject=subject,
            relevant_content=content_items
        )
        
        # Add metadata
        plan_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        plan_dict["id"] = plan_id
        plan_dict["student_id"] = current_user["id"]
        plan_dict["created_at"] = now
        plan_dict["updated_at"] = now
        plan_dict["start_date"] = now
        plan_dict["end_date"] = now  # Would be calculated based on activities
        plan_dict["status"] = "not_started"
        plan_dict["progress_percentage"] = 0.0
        
        # Generate embedding for plan
        plan_text = f"{plan_dict['title']} {plan_dict['description']} for {plan_dict['subject']}"
        plan_embedding = await openai_adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=plan_text
        )
        plan_dict["embedding"] = plan_embedding
        
        # Save to Azure AI Search
        result = await search_service.plans_index_client.upload_documents(documents=[plan_dict])
        
        if not result[0].succeeded:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save learning plan"
            )
        
        return plan_dict
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating learning plan: {str(e)}"
        )

async def get_learning_plan_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific learning plan."""
    search_service = await get_search_service()
    
    try:
        # Get plan from index
        plan = await search_service.plans_index_client.get_document(key=plan_id)
        
        # Check ownership
        if plan.get("student_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this plan"
            )
        
        return dict(plan)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan not found"
        )

async def update_activity_status_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    status: str = Body(..., embed=True),
    completed_at: Optional[str] = Body(None, embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """Update the status of a learning activity."""
    search_service = await get_search_service()
    
    try:
        # Get plan from index
        plan = await search_service.plans_index_client.get_document(key=plan_id)
        
        # Check ownership
        if plan.get("student_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this plan"
            )
        
        # Find and update activity
        activities = plan.get("activities", [])
        activity_found = False
        
        for i, activity in enumerate(activities):
            if activity.get("id") == activity_id:
                activities[i]["status"] = status
                if status == "completed":
                    activities[i]["completed_at"] = completed_at or datetime.utcnow().isoformat()
                activity_found = True
                break
        
        if not activity_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found in learning plan"
            )
        
        # Calculate progress percentage
        total_activities = len(activities)
        completed_activities = sum(1 for a in activities if a.get("status") == "completed")
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
        
        # Save updated plan
        result = await search_service.plans_index_client.upload_documents(documents=[plan])
        
        if not result[0].succeeded:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update activity status"
            )
        
        return {
            "success": True,
            "message": "Activity status updated",
            "progress_percentage": progress_percentage,
            "plan_status": plan_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating activity status: {str(e)}"
        )

# Admin endpoints
async def trigger_scraper_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Manually trigger the content scraper.
    Available only to admin users.
    """
    # Check if user is admin (would be in roles from Entra ID token)
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can trigger the scraper"
        )
    
    # Run scraper in background
    from scrapers.abc_edu_scraper import run_scraper
    background_tasks.add_task(run_scraper)
    
    return {"message": "Content scraper started in background"}

async def get_content_stats_endpoint(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get statistics about the content database.
    Available only to admin users.
    """
    # Check if user is admin
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access content statistics"
        )
    
    search_service = await get_search_service()
    
    try:
        # Get subject counts
        subject_counts = {}
        for subject in ["Mathematics", "Science", "English", "History", "Geography", "Arts"]:
            result = await search_service.content_index_client.search(
                search_text="*",
                filter=f"subject eq '{subject}'",
                include_total_count=True,
                top=0
            )
            subject_counts[subject] = result.get_count()
        
        # Get content type counts
        content_type_counts = {}
        for content_type in ["article", "video", "interactive", "quiz", "worksheet", "lesson", "activity"]:
            result = await search_service.content_index_client.search(
                search_text="*",
                filter=f"content_type eq '{content_type}'",
                include_total_count=True,
                top=0
            )
            content_type_counts[content_type] = result.get_count()
        
        # Get total count
        total_result = await search_service.content_index_client.search(
            search_text="*",
            include_total_count=True,
            top=0
        )
        total_count = total_result.get_count()
        
        # Get last updated date
        latest_result = await search_service.content_index_client.search(
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

async def get_student_progress_endpoint(
    current_user: Dict = Depends(get_current_user)
):
    """Get student progress analytics."""
    search_service = await get_search_service()
    
    try:
        # Get all user's learning plans
        results = await search_service.plans_index_client.search(
            search_text="*",
            filter=f"student_id eq '{current_user['id']}'",
            include_total_count=True
        )
        
        # Extract plans
        plans = []
        async for result in results:
            plans.append(dict(result))
        
        # Calculate overall stats
        total_plans = len(plans)
        completed_plans = sum(1 for p in plans if p.get("status") == "completed")
        in_progress_plans = sum(1 for p in plans if p.get("status") == "in_progress")
        overall_completion = (completed_plans / total_plans) * 100 if total_plans > 0 else 0
        
        # Get subject-specific progress
        subjects = {}
        for plan in plans:
            subject = plan.get("subject")
            if subject not in subjects:
                subjects[subject] = {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "percentage": 0
                }
            
            subjects[subject]["total"] += 1
            
            if plan.get("status") == "completed":
                subjects[subject]["completed"] += 1
            elif plan.get("status") == "in_progress":
                subjects[subject]["in_progress"] += 1
        
        # Calculate percentages for each subject
        for subject, stats in subjects.items():
            if stats["total"] > 0:
                stats["percentage"] = (stats["completed"] / stats["total"]) * 100
        
        return {
            "total_plans": total_plans,
            "completed_plans": completed_plans,
            "in_progress_plans": in_progress_plans,
            "overall_completion": overall_completion,
            "subjects": subjects
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving progress: {str(e)}"
        )
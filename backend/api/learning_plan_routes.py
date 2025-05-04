# backend/api/learning_plan_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging
import json

from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.entra_auth import get_current_user
from services.azure_learning_plan_service import get_learning_plan_service
from rag.generator import get_plan_generator
from rag.retriever import retrieve_relevant_content
from services.search_service import get_search_service

# Setup logger
logger = logging.getLogger(__name__)

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
        
        # Generate learning plan using the generate_plan method
        plan_dict = await plan_generator.generate_plan(
            student=user,
            subject=subject,
            relevant_content=relevant_content
        )
        
        # Create learning plan object from the returned dictionary
        now = datetime.utcnow()
        learning_plan = LearningPlan(
            id=str(uuid.uuid4()),
            student_id=user.id,
            title=plan_dict.get("title", f"{subject} Learning Plan"),
            description=plan_dict.get("description", f"A learning plan for {subject}"),
            subject=plan_dict.get("subject", subject),
            topics=plan_dict.get("topics", [subject]),
            activities=[LearningActivity(**activity) for activity in plan_dict.get("activities", [])],
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            owner_id=current_user["id"]  # Set the owner_id to the current user
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

@router.post("/profile-based")
async def create_profile_based_learning_plan(
    plan_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new personalized learning plan based on a student profile.
    
    Args:
        plan_data: Learning plan data with student_profile_id
        current_user: Current authenticated user
        
    Returns:
        Created learning plan
    """
    try:
        logger.info(f"Creating profile-based learning plan with data: {plan_data}")
        
        # Validate required fields
        student_profile_id = plan_data.get("student_profile_id")
        if not student_profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="student_profile_id is required"
            )
            
        # Get the student profile
        search_service = await get_search_service()
        if not search_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service not available"
            )
            
        # Find the student profile
        filter_expression = f"id eq '{student_profile_id}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student profile with ID {student_profile_id} not found"
            )
            
        student_profile = profiles[0]
        logger.info(f"Found student profile: {student_profile.get('full_name')}")
        
        # Create a user model from the student profile
        from models.user import User, LearningStyle
        
        # Extract subjects of interest from profile strengths if available
        subjects_of_interest = []
        if "strengths" in student_profile and student_profile["strengths"]:
            # Keep only subject names from strengths (Math, Science, etc.)
            # This is a simplistic approach - in a real system, you'd want
            # to map strengths to actual subjects more intelligently
            known_subjects = ["Mathematics", "Math", "Science", "English", "History", "Geography", "Art", "Music", "Physical Education", "PE"]
            subjects_of_interest = [strength for strength in student_profile["strengths"] 
                                  if any(subject.lower() in strength.lower() for subject in known_subjects)]
            
        # Handle learning style conversion safely
        learning_style_value = None
        if student_profile.get("learning_style"):
            try:
                # Convert to lowercase and try to match with enum
                ls_value = student_profile.get("learning_style", "").lower()
                
                # Map common learning style names to our enum values
                learning_style_mapping = {
                    "visual": LearningStyle.VISUAL,
                    "auditory": LearningStyle.AUDITORY,
                    "reading": LearningStyle.READING_WRITING,
                    "reading_writing": LearningStyle.READING_WRITING,
                    "read/write": LearningStyle.READING_WRITING,
                    "kinesthetic": LearningStyle.KINESTHETIC,
                    "tactile": LearningStyle.KINESTHETIC,
                    "mixed": LearningStyle.MIXED,
                    "multimodal": LearningStyle.MIXED
                }
                
                # Try to find a match
                if ls_value in learning_style_mapping:
                    learning_style_value = learning_style_mapping[ls_value]
                else:
                    # Fall back to mixed if no match
                    logger.warning(f"Unknown learning style: {student_profile.get('learning_style')}. Using 'mixed' instead.")
                    learning_style_value = LearningStyle.MIXED
            except Exception as e:
                logger.warning(f"Error processing learning style: {e}")
                learning_style_value = LearningStyle.MIXED
        
        user = User(
            id=student_profile_id,  # Use profile ID as user ID
            username=student_profile.get("full_name", "").replace(" ", "_").lower(),
            email=f"{student_profile_id}@example.com",  # Use placeholder email
            full_name=student_profile.get("full_name", ""),
            grade_level=student_profile.get("grade_level"),
            subjects_of_interest=subjects_of_interest,
            learning_style=learning_style_value,
            is_active=True
        )
        
        # Get plan parameters
        plan_type = plan_data.get("type", "balanced")
        daily_minutes = plan_data.get("daily_minutes", 60)
        
        # For balanced plans, we need to determine subjects and time allocation
        if plan_type == "balanced":
            # Analyze the student profile to create a balanced plan across subjects
            # For example, allocate more time to subjects in areas_for_improvement
            # and less time to subjects in strengths
            
            # Get improvement areas and strengths
            areas_for_improvement = student_profile.get("areas_for_improvement", [])
            strengths = student_profile.get("strengths", [])
            
            # Map to main subject categories
            subject_categories = {
                "Mathematics": ["math", "mathematics", "algebra", "geometry", "calculus", "arithmetic"],
                "Science": ["science", "biology", "physics", "chemistry", "laboratory"],
                "English": ["english", "writing", "reading", "literature", "grammar", "vocabulary"],
                "History": ["history", "social studies", "geography", "civics"],
                "Art": ["art", "creative", "drawing", "painting"]
            }
            
            # Determine which subjects need more attention
            focus_subjects = []
            for area in areas_for_improvement:
                area_lower = area.lower()
                for subject, keywords in subject_categories.items():
                    if any(keyword in area_lower for keyword in keywords):
                        if subject not in focus_subjects:
                            focus_subjects.append(subject)
            
            # Determine which subjects are strengths
            strong_subjects = []
            for strength in strengths:
                strength_lower = strength.lower()
                for subject, keywords in subject_categories.items():
                    if any(keyword in strength_lower for keyword in keywords):
                        if subject not in strong_subjects:
                            strong_subjects.append(subject)
            
            # If no focus subjects identified, use a balanced approach across main subjects
            if not focus_subjects:
                focus_subjects = list(subject_categories.keys())
                
            # Generate plans for each focus subject
            all_plans = []
            time_per_subject = daily_minutes // len(focus_subjects)
            
            # Calculate time allocation - more time for areas of improvement
            subject_times = {}
            for subject in focus_subjects:
                # Allocate more time to subjects needing improvement
                if subject in strong_subjects:
                    # Less time for strengths
                    subject_times[subject] = max(10, int(time_per_subject * 0.7))
                else:
                    # More time for areas needing improvement
                    subject_times[subject] = max(15, int(time_per_subject * 1.3))
            
            # Adjust total to match daily_minutes
            total_allocated = sum(subject_times.values())
            scaling_factor = daily_minutes / total_allocated if total_allocated > 0 else 1
            for subject in subject_times:
                subject_times[subject] = max(10, int(subject_times[subject] * scaling_factor))
                
            logger.info(f"Time allocation for subjects: {subject_times}")
            
            # Create separate plans for each subject
            combined_activities = []
            
            for subject, minutes in subject_times.items():
                # Get relevant content for the subject
                relevant_content = await retrieve_relevant_content(
                    student_profile=user,
                    subject=subject,
                    grade_level=student_profile.get("grade_level"),
                    k=5
                )
                
                # Get plan generator
                plan_generator = await get_plan_generator()
                
                # Create mini-plan for the subject
                # Note: Using generate_plan (the method that exists in LearningPlanGenerator)
                # instead of create_learning_plan which doesn't exist
                plan_dict = await plan_generator.generate_plan(
                    student=user,
                    subject=subject,
                    relevant_content=relevant_content
                )
                
                # Create a mini plan manually from the plan dictionary
                # The generator doesn't have parameters for max_activities,
                # so we'll limit the activities after generation
                mini_plan = LearningPlan(
                    id=str(uuid.uuid4()),
                    student_id=user.id,
                    title=plan_dict.get("title", f"{subject} Learning Plan"),
                    description=plan_dict.get("description", f"Plan for {subject}"),
                    subject=subject,
                    topics=plan_dict.get("topics", [subject]),
                    activities=[],  # Will add only the needed activities
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status=ActivityStatus.NOT_STARTED,
                    progress_percentage=0.0,
                    owner_id=current_user["id"]  # Set the owner_id to the current user
                )
                
                # Add only up to 2 activities (for balancing across subjects)
                activities_to_add = []
                for i, activity_dict in enumerate(plan_dict.get("activities", [])[:2]):  # Limit to first 2
                    # Get content URL from either the activity or the matched content
                    content_url = activity_dict.get("content_url")
                    if not content_url and activity_dict.get("content_id"):
                        # Try to find matching content to get URL
                        matching_content = next(
                            (content for content in relevant_content if str(content.id) == activity_dict.get("content_id")),
                            None
                        )
                        if matching_content:
                            content_url = matching_content.url
                    
                    # Create enhanced activity with appropriate duration
                    activity = LearningActivity(
                        id=str(uuid.uuid4()),
                        title=activity_dict.get("title", f"Activity {i+1}"),
                        description=activity_dict.get("description", "Complete this activity"),
                        content_id=activity_dict.get("content_id"),
                        content_url=content_url,
                        # Scale duration to fit within allocated minutes
                        duration_minutes=min(activity_dict.get("duration_minutes", 15), 
                                            int(minutes / 2)),  # Cap at half the allocated time
                        order=i + 1,
                        status=ActivityStatus.NOT_STARTED,
                        learning_benefit=activity_dict.get("learning_benefit", f"This activity helps develop {subject} skills"),
                        metadata=activity_dict.get("metadata", {"subject": subject})
                    )
                    activities_to_add.append(activity)
                
                # Set the activities on the mini plan
                mini_plan.activities = activities_to_add
                
                # Add activities to the combined list
                for i, activity in enumerate(mini_plan.activities):
                    activity.id = str(uuid.uuid4())  # Ensure unique IDs
                    activity.title = f"{subject}: {activity.title}"  # Prefix with subject
                    activity.order = len(combined_activities) + i + 1  # Update order
                    combined_activities.append(activity)
                
            # Create the combined plan
            learning_plan = LearningPlan(
                id=str(uuid.uuid4()),
                student_id=user.id,
                title=f"Balanced Learning Plan for {user.full_name}",
                description=f"A personalized daily learning plan with {daily_minutes} minutes of balanced study across multiple subjects.",
                subject="Multiple Subjects",
                topics=focus_subjects,
                activities=combined_activities,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                metadata={
                    "plan_type": "balanced",
                    "daily_minutes": daily_minutes,
                    "focus_areas": focus_subjects,
                    "student_profile_id": student_profile_id
                },
                owner_id=current_user["id"]  # Set the owner_id to the current user
            )
            
        else:
            # For single subject plans, use the specified subject
            subject = plan_data.get("subject")
            if not subject:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="subject is required for focused plans"
                )
                
            # Extract areas for improvement from student profile, if available
            areas_for_improvement = student_profile.get("areas_for_improvement", [])
            if isinstance(areas_for_improvement, str):
                # If it's a string, try to parse as JSON or split by commas
                try:
                    areas_for_improvement = json.loads(areas_for_improvement)
                except:
                    areas_for_improvement = [area.strip() for area in areas_for_improvement.split(",") if area.strip()]
            
            # Add areas_for_improvement to the user model
            user.areas_for_improvement = areas_for_improvement
            
            logger.info(f"Retrieving content for student profile: grade_level={student_profile.get('grade_level')}, subject={subject}")
            logger.info(f"Areas for improvement: {areas_for_improvement}")
            
            # Get relevant content for the subject with enhanced filtering based on student profile
            relevant_content = await retrieve_relevant_content(
                student_profile=user,
                subject=subject,
                grade_level=student_profile.get("grade_level"),
                k=15  # Get more content for better selection
            )
            
            logger.info(f"Retrieved {len(relevant_content)} relevant content items for learning plan")
            
            # Get plan generator
            plan_generator = await get_plan_generator()
            
            # Generate enhanced plan using improved generate_plan method
            plan_dict = await plan_generator.generate_plan(
                student=user,
                subject=subject,
                relevant_content=relevant_content
            )
            
            # Convert to LearningPlan object with enhanced activity details
            activities = []
            for i, activity_dict in enumerate(plan_dict.get("activities", [])):
                # Get any existing content URL from the activity or from matching content
                content_url = activity_dict.get("content_url")
                if not content_url and activity_dict.get("content_id"):
                    # Try to find matching content to get URL
                    matching_content = next(
                        (content for content in relevant_content if str(content.id) == activity_dict.get("content_id")),
                        None
                    )
                    if matching_content:
                        content_url = matching_content.url
                
                # Create enhanced activity with new fields
                activity = LearningActivity(
                    id=str(uuid.uuid4()),
                    title=activity_dict.get("title", f"Activity {i+1}"),
                    description=activity_dict.get("description", "Complete this activity"),
                    content_id=activity_dict.get("content_id"),
                    content_url=content_url,
                    duration_minutes=activity_dict.get("duration_minutes", 15),
                    order=i + 1,
                    status=ActivityStatus.NOT_STARTED,
                    learning_benefit=activity_dict.get("learning_benefit", f"This activity helps develop skills in {subject}"),
                    metadata=activity_dict.get("metadata", {})
                )
                activities.append(activity)
                
            # Create learning plan with the correct data
            learning_plan = LearningPlan(
                id=str(uuid.uuid4()),
                student_id=user.id,
                title=plan_dict.get("title", f"{subject} Learning Plan"),
                description=plan_dict.get("description", f"A learning plan for {subject}"),
                subject=subject,
                topics=plan_dict.get("topics", [subject]),
                activities=activities,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                owner_id=current_user["id"]  # Set the owner_id to the current user
            )
            
            # Update metadata
            learning_plan.metadata = {
                "plan_type": "focused",
                "daily_minutes": daily_minutes,
                "student_profile_id": student_profile_id
            }
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating profile-based learning plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating profile-based learning plan: {str(e)}"
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

@router.delete("/{plan_id}")
async def delete_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a learning plan.
    
    Args:
        plan_id: Learning plan ID
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Check if plan exists and belongs to user
        plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
            )
        
        # Delete the learning plan
        success = await learning_plan_service.delete_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete learning plan"
            )
        
        # Return success
        return {"message": "Learning plan deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting learning plan: {str(e)}"
        )

@router.put("/{plan_id}")
async def update_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    plan_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a learning plan.
    
    Args:
        plan_id: Learning plan ID
        plan_data: Updated plan data
        current_user: Current authenticated user
        
    Returns:
        Updated learning plan
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Check if plan exists and belongs to user
        existing_plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not existing_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
            )
        
        # Update fields from plan_data
        for field, value in plan_data.items():
            # Skip id, student_id, and owner_id fields for security
            if field not in ["id", "student_id", "owner_id"]:
                setattr(existing_plan, field, value)
        
        # Always update the updated_at timestamp
        existing_plan.updated_at = datetime.utcnow()
        
        # Update the learning plan
        updated_plan = await learning_plan_service.update_learning_plan(
            plan=existing_plan,
            user_id=current_user["id"]
        )
        
        if not updated_plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update learning plan"
            )
        
        # Return the updated plan
        return updated_plan.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating learning plan: {str(e)}"
        )

@router.get("/{plan_id}/export")
async def export_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    format: str = Query("json", description="Export format (json, pdf, html)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Export a learning plan in the specified format.
    
    Args:
        plan_id: Learning plan ID
        format: Export format (json, pdf, html)
        current_user: Current authenticated user
        
    Returns:
        Learning plan in the specified format
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
        
        # Format as requested
        if format.lower() == "json":
            # Return the plan as JSON
            return plan.dict()
        elif format.lower() == "html":
            # Generate HTML representation
            html_content = await learning_plan_service.generate_html_export(plan)
            return {"content": html_content, "format": "html"}
        elif format.lower() == "pdf":
            # PDF not directly supported yet, fall back to HTML
            html_content = await learning_plan_service.generate_html_export(plan)
            return {
                "content": html_content, 
                "format": "html",
                "message": "PDF format is not currently supported. HTML content provided instead."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting learning plan: {str(e)}"
        )

@router.options("/{plan_id}/activities/{activity_id}")
async def options_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID")
):
    """Handle OPTIONS preflight request for activity status updates."""
    return {"detail": "OK"}

@router.put("/{plan_id}/activities/{activity_id}", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def update_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    activity_status: str = Body(..., embed=True, alias="status"),  # Renamed to avoid conflict
    completed_at: Optional[str] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
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
        
        # Log request details for debugging
        logger.info(f"Updating activity status for plan {plan_id}, activity {activity_id} to {activity_status}")
        
        # Parse status
        try:
            parsed_status = ActivityStatus(activity_status)
        except ValueError:
            logger.warning(f"Invalid status provided: {activity_status}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {activity_status}. Must be one of: not_started, in_progress, completed"
            )
        
        # Parse completed_at date if provided
        completion_date = None
        if completed_at:
            try:
                completion_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid date format: {completed_at}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid completed_at date format: {completed_at}. Must be ISO format"
                )
        
        # Update activity status
        try:
            result = await learning_plan_service.update_activity_status(
                plan_id=plan_id,
                activity_id=activity_id,
                status=parsed_status,  # Using the parsed status
                completed_at=completion_date,
                user_id=current_user["id"]
            )
            
            if not result:
                logger.warning(f"Learning plan {plan_id} or activity {activity_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Learning plan or activity not found"
                )
            
            # Ensure we return a valid JSON response
            return {
                "success": True,
                "message": "Activity status updated successfully",
                "plan_id": plan_id,
                "activity_id": activity_id,
                "status": activity_status,
                "progress_percentage": result.get("progress_percentage", 0.0),
                "plan_status": result.get("plan_status", "unknown")
            }
        except Exception as service_error:
            logger.error(f"Service error updating activity: {service_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error in learning plan service: {str(service_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unhandled error updating activity status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating activity status: {str(e)}"
        )
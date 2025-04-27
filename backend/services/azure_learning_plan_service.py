# backend/services/azure_learning_plan_service.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import aiohttp

from models.user import User
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class AzureLearningPlanService:
    """
    Service for managing learning plans using Azure AI Search.
    """
    
    def __init__(self):
        """Initialize learning plan service."""
        self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.search_key = settings.AZURE_SEARCH_KEY
        self.index_name = settings.PLANS_INDEX_NAME
    
    async def get_learning_plans(
        self, 
        user_id: str,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> List[LearningPlan]:
        """
        Get learning plans for a user.
        
        Args:
            user_id: User ID
            subject: Optional subject filter
            limit: Maximum number of results
            
        Returns:
            List of learning plans
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return []
        
        try:
            # Build search URL
            search_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search"
            search_url += f"?api-version=2023-07-01-Preview"
            
            # Build filter
            filter_expr = f"student_id eq '{user_id}'"
            if subject:
                filter_expr += f" and subject eq '{subject}'"
            
            # Build search body
            search_body = {
                "filter": filter_expr,
                "orderby": "created_at desc",
                "top": limit
            }
            
            # Execute search
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    search_url,
                    json=search_body,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                        return []
                    
                    # Parse response
                    result = await response.json()
                    
                    # Convert to LearningPlan objects
                    plans = []
                    for item in result.get("value", []):
                        try:
                            # Convert activities JSON if it's stored as a string
                            if isinstance(item.get("activities"), str):
                                try:
                                    item["activities"] = json.loads(item["activities"])
                                except json.JSONDecodeError:
                                    item["activities"] = []
                            
                            # Convert each activity to LearningActivity
                            activities = []
                            for activity_dict in item.get("activities", []):
                                activity = LearningActivity(
                                    id=activity_dict.get("id", str(uuid.uuid4())),
                                    title=activity_dict.get("title", "Activity"),
                                    description=activity_dict.get("description", ""),
                                    content_id=activity_dict.get("content_id"),
                                    duration_minutes=activity_dict.get("duration_minutes", 30),
                                    order=activity_dict.get("order", 1),
                                    status=ActivityStatus(activity_dict.get("status", "not_started")),
                                    completed_at=activity_dict.get("completed_at")
                                )
                                activities.append(activity)
                            
                            # Create LearningPlan
                            plan = LearningPlan(
                                id=item.get("id", str(uuid.uuid4())),
                                student_id=item.get("student_id", user_id),
                                title=item.get("title", "Learning Plan"),
                                description=item.get("description", ""),
                                subject=item.get("subject", "General"),
                                topics=item.get("topics", []),
                                activities=activities,
                                status=ActivityStatus(item.get("status", "not_started")),
                                progress_percentage=item.get("progress_percentage", 0.0),
                                created_at=datetime.fromisoformat(item.get("created_at").replace('Z', '+00:00')) if item.get("created_at") else datetime.utcnow(),
                                updated_at=datetime.fromisoformat(item.get("updated_at").replace('Z', '+00:00')) if item.get("updated_at") else datetime.utcnow(),
                                start_date=datetime.fromisoformat(item.get("start_date").replace('Z', '+00:00')) if item.get("start_date") else None,
                                end_date=datetime.fromisoformat(item.get("end_date").replace('Z', '+00:00')) if item.get("end_date") else None
                            )
                            plans.append(plan)
                        except Exception as e:
                            logger.error(f"Error converting plan: {e}")
                    
                    return plans
                    
        except Exception as e:
            logger.error(f"Error getting learning plans: {e}")
            return []
    
    async def create_learning_plan(self, plan: LearningPlan) -> bool:
        """
        Create a new learning plan.
        
        Args:
            plan: Learning plan to create
            
        Returns:
            Success status
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return False
        
        try:
            # Build request URL
            index_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index"
            index_url += f"?api-version=2023-07-01-Preview"
            
            # Convert plan to dict
            plan_dict = plan.dict()
            
            # Format dates properly for Azure Search
            for date_field in ["created_at", "updated_at", "start_date", "end_date"]:
                if date_field in plan_dict and plan_dict[date_field]:
                    if isinstance(plan_dict[date_field], datetime):
                        plan_dict[date_field] = plan_dict[date_field].isoformat() + "Z"
            
            # Convert activities to JSON-compatible format
            activities = []
            for activity in plan.activities:
                activity_dict = activity.dict()
                # Format completed_at date if present
                if activity_dict.get("completed_at"):
                    if isinstance(activity_dict["completed_at"], datetime):
                        activity_dict["completed_at"] = activity_dict["completed_at"].isoformat() + "Z"
                activities.append(activity_dict)
            
            plan_dict["activities"] = activities
            
            # Build request body
            request_body = {
                "value": [plan_dict]
            }
            
            # Execute request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    index_url,
                    json=request_body,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200 and response.status != 201:
                        logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                        return False
                    
                    # Parse response
                    result = await response.json()
                    
                    # Check for errors
                    if "value" in result:
                        for item in result["value"]:
                            if not item.get("status", False):
                                logger.error(f"Error creating learning plan: {item.get('errorMessage')}")
                                return False
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}")
            return False
    
    async def update_learning_plan(self, plan: LearningPlan) -> bool:
        """
        Update an existing learning plan.
        
        Args:
            plan: Learning plan to update
            
        Returns:
            Success status
        """
        # For Azure Search, create and update are the same operation
        return await self.create_learning_plan(plan)
    
    async def get_learning_plan(self, plan_id: str, user_id: str) -> Optional[LearningPlan]:
        """
        Get a specific learning plan.
        
        Args:
            plan_id: Learning plan ID
            user_id: User ID for authorization
            
        Returns:
            Learning plan or None if not found
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return None
        
        try:
            # Build search URL
            search_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search"
            search_url += f"?api-version=2023-07-01-Preview"
            
            # Build filter
            filter_expr = f"id eq '{plan_id}' and student_id eq '{user_id}'"
            
            # Build search body
            search_body = {
                "filter": filter_expr,
                "top": 1
            }
            
            # Execute search
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    search_url,
                    json=search_body,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                        return None
                    
                    # Parse response
                    result = await response.json()
                    
                    # Check if plan was found
                    if not result.get("value") or len(result["value"]) == 0:
                        return None
                    
                    # Get plan data
                    item = result["value"][0]
                    
                    # Convert activities JSON if it's stored as a string
                    if isinstance(item.get("activities"), str):
                        try:
                            item["activities"] = json.loads(item["activities"])
                        except json.JSONDecodeError:
                            item["activities"] = []
                    
                    # Convert each activity to LearningActivity
                    activities = []
                    for activity_dict in item.get("activities", []):
                        activity = LearningActivity(
                            id=activity_dict.get("id", str(uuid.uuid4())),
                            title=activity_dict.get("title", "Activity"),
                            description=activity_dict.get("description", ""),
                            content_id=activity_dict.get("content_id"),
                            duration_minutes=activity_dict.get("duration_minutes", 30),
                            order=activity_dict.get("order", 1),
                            status=ActivityStatus(activity_dict.get("status", "not_started")),
                            completed_at=activity_dict.get("completed_at")
                        )
                        activities.append(activity)
                    
                    # Create LearningPlan
                    plan = LearningPlan(
                        id=item.get("id", str(uuid.uuid4())),
                        student_id=item.get("student_id", user_id),
                        title=item.get("title", "Learning Plan"),
                        description=item.get("description", ""),
                        subject=item.get("subject", "General"),
                        topics=item.get("topics", []),
                        activities=activities,
                        status=ActivityStatus(item.get("status", "not_started")),
                        progress_percentage=item.get("progress_percentage", 0.0),
                        created_at=datetime.fromisoformat(item.get("created_at").replace('Z', '+00:00')) if item.get("created_at") else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(item.get("updated_at").replace('Z', '+00:00')) if item.get("updated_at") else datetime.utcnow(),
                        start_date=datetime.fromisoformat(item.get("start_date").replace('Z', '+00:00')) if item.get("start_date") else None,
                        end_date=datetime.fromisoformat(item.get("end_date").replace('Z', '+00:00')) if item.get("end_date") else None
                    )
                    
                    return plan
                    
        except Exception as e:
            logger.error(f"Error getting learning plan: {e}")
            return None
    
    async def update_activity_status(
        self,
        plan_id: str,
        activity_id: str,
        status: ActivityStatus,
        completed_at: Optional[datetime] = None,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update activity status in a learning plan.
        
        Args:
            plan_id: Learning plan ID
            activity_id: Activity ID
            status: New status
            completed_at: Optional completion date
            user_id: User ID for authorization
            
        Returns:
            Dictionary with status information
        """
        # Get the plan
        plan = await self.get_learning_plan(plan_id, user_id)
        if not plan:
            return None
        
        # Find and update the activity
        activity_found = False
        for i, activity in enumerate(plan.activities):
            if activity.id == activity_id:
                plan.activities[i].status = status
                if status == ActivityStatus.COMPLETED:
                    plan.activities[i].completed_at = completed_at or datetime.utcnow()
                activity_found = True
                break
        
        if not activity_found:
            return None
        
        # Update plan status and progress
        self._update_plan_progress(plan)
        
        # Update timestamp
        plan.updated_at = datetime.utcnow()
        
        # Save updated plan
        success = await self.update_learning_plan(plan)
        
        if not success:
            return None
        
        return {
            "success": True,
            "message": "Activity status updated",
            "progress_percentage": plan.progress_percentage,
            "plan_status": plan.status
        }
    
    def _update_plan_progress(self, plan: LearningPlan):
        """
        Update plan progress percentage and status.
        
        Args:
            plan: Learning plan to update
        """
        if not plan.activities:
            plan.progress_percentage = 0
            plan.status = ActivityStatus.NOT_STARTED
            return
        
        # Count completed activities
        total_activities = len(plan.activities)
        completed_activities = sum(1 for a in plan.activities if a.status == ActivityStatus.COMPLETED)
        
        # Calculate progress percentage
        plan.progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
        
        # Update plan status
        if completed_activities == total_activities:
            plan.status = ActivityStatus.COMPLETED
        elif completed_activities > 0:
            plan.status = ActivityStatus.IN_PROGRESS
        else:
            plan.status = ActivityStatus.NOT_STARTED

# Singleton instance
learning_plan_service = None

async def get_learning_plan_service():
    """Get or create learning plan service singleton."""
    global learning_plan_service
    if learning_plan_service is None:
        learning_plan_service = AzureLearningPlanService()
    return learning_plan_service
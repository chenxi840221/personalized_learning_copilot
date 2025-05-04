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
            
            # Build filter - filter by owner_id to ensure users only see plans they created
            filter_expr = f"owner_id eq '{user_id}'"
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
                            # Get activities from activities_json field if present
                            activities = []
                            if "activities_json" in item and item["activities_json"]:
                                try:
                                    activities_data = json.loads(item["activities_json"])
                                    for activity_dict in activities_data:
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
                                except json.JSONDecodeError:
                                    logger.error(f"Error parsing activities_json: {item.get('activities_json')}")
                            # Fallback to activities field for backward compatibility
                            elif "activities" in item:
                                # Convert activities JSON if it's stored as a string
                                if isinstance(item.get("activities"), str):
                                    try:
                                        item["activities"] = json.loads(item["activities"])
                                    except json.JSONDecodeError:
                                        item["activities"] = []
                                
                                # Convert each activity to LearningActivity
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
                            
                            # Parse metadata if it exists
                            metadata = {}
                            if "metadata" in item and item["metadata"]:
                                try:
                                    if isinstance(item["metadata"], str):
                                        metadata = json.loads(item["metadata"])
                                    elif isinstance(item["metadata"], dict):
                                        metadata = item["metadata"]
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse metadata JSON: {item.get('metadata')}")
                            
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
                                end_date=datetime.fromisoformat(item.get("end_date").replace('Z', '+00:00')) if item.get("end_date") else None,
                                metadata=metadata
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
            
            # Convert activities to JSON string for storage in Azure Search
            # Azure Search doesn't handle nested objects in the same way as other fields
            activities_json = []
            for activity in plan.activities:
                activity_dict = activity.dict()
                # Format completed_at date if present
                if activity_dict.get("completed_at"):
                    if isinstance(activity_dict["completed_at"], datetime):
                        activity_dict["completed_at"] = activity_dict["completed_at"].isoformat() + "Z"
                activities_json.append(activity_dict)
            
            try:
                # Store activities as a JSON string instead of a nested object
                plan_dict["activities_json"] = json.dumps(activities_json)
                
                # Remove the original activities field to avoid the Azure Search error
                if "activities" in plan_dict:
                    logger.info("Removing activities field from plan_dict")
                    del plan_dict["activities"]
                
                # Convert metadata to string if it's a dict
                if "metadata" in plan_dict and isinstance(plan_dict["metadata"], dict):
                    plan_dict["metadata"] = json.dumps(plan_dict["metadata"])
                
                logger.info(f"Plan dict ready for Azure Search with keys: {', '.join(plan_dict.keys())}")
            except Exception as e:
                logger.exception(f"Error preparing plan data for Azure Search: {e}")
                return False
            
            # Build request body
            request_body = {
                "value": [plan_dict]
            }
            
            # Execute request
            try:
                logger.info(f"Sending update request to Azure Search index: {self.index_name}")
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        index_url,
                        json=request_body,
                        headers={
                            "Content-Type": "application/json",
                            "api-key": self.search_key
                        }
                    ) as response:
                        response_text = await response.text()
                        if response.status != 200 and response.status != 201:
                            logger.error(f"Azure Search error: {response.status} - {response_text}")
                            return False
                        
                        # Parse response
                        logger.info(f"Got successful response from Azure Search: {response.status}")
                        try:
                            result = json.loads(response_text)
                        except json.JSONDecodeError as je:
                            logger.error(f"Failed to parse Azure Search response: {je} - Response: {response_text}")
                            return False
            except Exception as e:
                logger.exception(f"Network error when updating Azure Search index: {e}")
                return False
                    
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
            
            # Build filter - ensure the user only accesses plans they created
            filter_expr = f"id eq '{plan_id}' and owner_id eq '{user_id}'"
            
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
                    
                    # Get activities from activities_json field if present
                    activities = []
                    if "activities_json" in item and item["activities_json"]:
                        try:
                            activities_data = json.loads(item["activities_json"])
                            for activity_dict in activities_data:
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
                        except json.JSONDecodeError:
                            logger.error(f"Error parsing activities_json: {item.get('activities_json')}")
                    # Fallback to activities field for backward compatibility
                    elif "activities" in item:
                        # Convert activities JSON if it's stored as a string
                        if isinstance(item.get("activities"), str):
                            try:
                                item["activities"] = json.loads(item["activities"])
                            except json.JSONDecodeError:
                                item["activities"] = []
                        
                        # Convert each activity to LearningActivity
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
                    
                    # Parse metadata if it exists
                    metadata = {}
                    if "metadata" in item and item["metadata"]:
                        try:
                            if isinstance(item["metadata"], str):
                                metadata = json.loads(item["metadata"])
                            elif isinstance(item["metadata"], dict):
                                metadata = item["metadata"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse metadata JSON: {item.get('metadata')}")
                    
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
                        end_date=datetime.fromisoformat(item.get("end_date").replace('Z', '+00:00')) if item.get("end_date") else None,
                        metadata=metadata
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
        logger.info(f"Updating activity status in service: plan_id={plan_id}, activity_id={activity_id}, status={status}, user_id={user_id}")
        
        try:
            # Get the plan
            plan = await self.get_learning_plan(plan_id, user_id)
            if not plan:
                logger.warning(f"Plan not found: {plan_id} for user {user_id}")
                return None
                
            logger.info(f"Plan found with {len(plan.activities)} activities")
        except Exception as e:
            logger.exception(f"Error getting learning plan: {e}")
            return None
        
        # Find and update the activity
        activity_found = False
        try:
            for i, activity in enumerate(plan.activities):
                logger.info(f"Checking activity {activity.id} against {activity_id}")
                if activity.id == activity_id:
                    logger.info(f"Found matching activity, updating status to {status}")
                    plan.activities[i].status = status
                    if status == ActivityStatus.COMPLETED:
                        plan.activities[i].completed_at = completed_at or datetime.utcnow()
                    activity_found = True
                    break
            
            if not activity_found:
                logger.warning(f"Activity not found: {activity_id} in plan {plan_id}")
                return None
            
            # Update plan status and progress
            self._update_plan_progress(plan)
            
            # Update timestamp
            plan.updated_at = datetime.utcnow()
            
            # Save updated plan
            try:
                logger.info(f"Saving updated plan with {len(plan.activities)} activities")
                logger.info(f"Plan details before save: id={plan.id}, status={plan.status}, activities={len(plan.activities)}")
                
                try:
                    # Convert to dict first to catch any serialization issues
                    plan_dict = plan.dict()
                    logger.info(f"Plan converted to dict successfully with {len(plan_dict['activities'])} activities")
                except Exception as dict_err:
                    logger.exception(f"Error converting plan to dict: {dict_err}")
                    return None
                
                success = await self.update_learning_plan(plan)
                
                if not success:
                    logger.error("Failed to save updated plan")
                    return None
                
                logger.info(f"Plan updated successfully, new progress: {plan.progress_percentage}%")
                return {
                    "success": True,
                    "message": "Activity status updated",
                    "progress_percentage": plan.progress_percentage,
                    "plan_status": plan.status  # ActivityStatus inherits from str, so this works
                }
            except Exception as e:
                logger.exception(f"Error updating plan: {e}")
                return None
        except Exception as e:
            logger.exception(f"Error updating activity: {e}")
            return None
    
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
            
    async def delete_learning_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Delete a learning plan.
        
        Args:
            plan_id: Learning plan ID
            user_id: User ID for authorization
            
        Returns:
            Success status
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return False
        
        try:
            # First verify the plan exists and belongs to the user
            plan = await self.get_learning_plan(plan_id, user_id)
            if not plan:
                logger.warning(f"Plan not found or access denied: {plan_id} for user {user_id}")
                return False
            
            # Delete URL for Azure Search
            delete_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index"
            delete_url += f"?api-version=2023-07-01-Preview"
            
            # Build request body for delete operation
            request_body = {
                "value": [
                    {
                        "@search.action": "delete",
                        "id": plan_id
                    }
                ]
            }
            
            # Execute delete request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    delete_url,
                    json=request_body,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200 and response.status != 201:
                        response_text = await response.text()
                        logger.error(f"Azure Search error deleting plan: {response.status} - {response_text}")
                        return False
                    
                    # Parse response to check for errors
                    try:
                        result = await response.json()
                        if "value" in result:
                            for item in result["value"]:
                                if not item.get("status", False):
                                    logger.error(f"Error deleting learning plan: {item.get('errorMessage')}")
                                    return False
                    except json.JSONDecodeError:
                        # Some successful responses might not have a JSON body
                        pass
                    
                    logger.info(f"Successfully deleted learning plan {plan_id}")
                    return True
                
        except Exception as e:
            logger.error(f"Error deleting learning plan: {e}")
            return False
    
    async def generate_html_export(self, plan: LearningPlan) -> str:
        """
        Generate HTML representation of a learning plan for export.
        
        Args:
            plan: Learning plan to export
            
        Returns:
            HTML string representation of the learning plan
        """
        # Create HTML content with modern styling
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{plan.title} - Learning Plan</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #2563eb;
                }}
                .plan-header {{
                    border-bottom: 2px solid #e5e7eb;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }}
                .plan-meta {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-bottom: 15px;
                    font-size: 0.9rem;
                    color: #6b7280;
                }}
                .plan-meta div {{
                    padding: 5px 10px;
                    background-color: #f3f4f6;
                    border-radius: 4px;
                }}
                .progress-container {{
                    margin: 20px 0;
                }}
                .progress-bar {{
                    height: 8px;
                    background-color: #e5e7eb;
                    border-radius: 4px;
                    overflow: hidden;
                }}
                .progress-fill {{
                    height: 100%;
                    background-color: #2563eb;
                    width: {plan.progress_percentage}%;
                }}
                .activity {{
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                .activity-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .activity-title {{
                    font-weight: 600;
                    font-size: 1.1rem;
                    margin: 0;
                }}
                .activity-meta {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-top: 10px;
                    font-size: 0.8rem;
                }}
                .badge {{
                    padding: 3px 8px;
                    border-radius: 9999px;
                    font-weight: 500;
                }}
                .badge-blue {{
                    background-color: #dbeafe;
                    color: #1e40af;
                }}
                .badge-green {{
                    background-color: #dcfce7;
                    color: #166534;
                }}
                .badge-yellow {{
                    background-color: #fef3c7;
                    color: #92400e;
                }}
                .badge-gray {{
                    background-color: #f3f4f6;
                    color: #4b5563;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 0.8rem;
                    color: #6b7280;
                }}
                .learning-benefit {{
                    background-color: #dbeafe;
                    border-radius: 6px;
                    padding: 10px;
                    margin-top: 10px;
                }}
                .learning-benefit-title {{
                    font-weight: 600;
                    color: #1e40af;
                    margin-bottom: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="plan-header">
                <h1>{plan.title}</h1>
                <p>{plan.description}</p>
                <div class="plan-meta">
                    <div>Subject: {plan.subject}</div>
                    <div>Topics: {', '.join(plan.topics)}</div>
                    <div>Created: {plan.created_at.strftime("%Y-%m-%d")}</div>
                    <div>Status: {plan.status.value.replace('_', ' ').title()}</div>
                </div>
            </div>

            <div class="progress-container">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>Progress</span>
                    <span>{plan.progress_percentage:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
            </div>

            <h2>Activities</h2>
        """
        
        # Add activities
        for activity in plan.activities:
            # Determine status badge color
            status_badge = "badge-gray"
            if activity.status == ActivityStatus.COMPLETED:
                status_badge = "badge-green"
            elif activity.status == ActivityStatus.IN_PROGRESS:
                status_badge = "badge-yellow"
                
            # Format activity
            activity_html = f"""
            <div class="activity">
                <div class="activity-header">
                    <h3 class="activity-title">{activity.title}</h3>
                    <span class="badge {status_badge}">{activity.status.value.replace('_', ' ').title()}</span>
                </div>
                <p>{activity.description}</p>
                <div class="activity-meta">
                    <span class="badge badge-blue">{activity.duration_minutes} minutes</span>
                    {f'<span>Completed on: {activity.completed_at.strftime("%Y-%m-%d")}</span>' if activity.completed_at else ''}
                </div>
            """
            
            # Add learning benefit if present
            if hasattr(activity, 'learning_benefit') and activity.learning_benefit:
                activity_html += f"""
                <div class="learning-benefit">
                    <div class="learning-benefit-title">How This Helps Learning:</div>
                    <p>{activity.learning_benefit}</p>
                </div>
                """
                
            # Add content link if present
            if hasattr(activity, 'content_url') and activity.content_url:
                activity_html += f"""
                <div style="margin-top: 15px;">
                    <a href="{activity.content_url}" target="_blank" style="color: #2563eb; text-decoration: none;">
                        Open Learning Resource →
                    </a>
                </div>
                """
            elif activity.content_id:
                activity_html += f"""
                <div style="margin-top: 15px;">
                    <span style="color: #6b7280;">Content ID: {activity.content_id}</span>
                </div>
                """
                
            # Close activity div
            activity_html += "</div>"
            html_content += activity_html
        
        # Add footer and close HTML
        html_content += f"""
            <div class="footer">
                <p>Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
                <p>Personalized Learning Co-pilot</p>
            </div>
        </body>
        </html>
        """
        
        return html_content

# Singleton instance
learning_plan_service = None

async def get_learning_plan_service():
    """Get or create learning plan service singleton."""
    global learning_plan_service
    if learning_plan_service is None:
        learning_plan_service = AzureLearningPlanService()
    return learning_plan_service
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import uuid
from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from rag.retriever import retrieve_relevant_content
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter
# Initialize settings
settings = Settings()
# Initialize logger
logger = logging.getLogger(__name__)
class LearningPlanner:
    """
    Generate personalized learning plans and paths for students.
    """
    def __init__(self):
        # Initialize when needed
        self.openai_client = None
    async def create_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content],
        duration_days: int = 14
    ) -> LearningPlan:
        """
        Create a standard learning plan based on relevant content.
        Args:
            student: The student user
            subject: Subject to focus on
            relevant_content: List of relevant content
            duration_days: Duration of the plan in days
        Returns:
            A LearningPlan object
        """
        # Format content for prompt
        content_descriptions = ""
        for i, content in enumerate(relevant_content):
            content_descriptions += f"""
            Content {i+1}:
            - ID: {content.id}
            - Title: {content.title}
            - Type: {content.content_type}
            - Difficulty: {content.difficulty_level}
            - Description: {content.description}
            - URL: {content.url}
            """
        # Create prompt for learning plan generation
        prompt = f"""
        You are an expert educational AI assistant tasked with creating personalized learning plans.
        STUDENT PROFILE:
        - Name: {student.full_name or student.username}
        - Grade Level: {student.grade_level if student.grade_level else "Unknown"}
        - Learning Style: {student.learning_style.value if student.learning_style else "Mixed"}
        - Subjects of Interest: {', '.join(student.subjects_of_interest) if student.subjects_of_interest else "General learning"}
        SUBJECT TO FOCUS ON: {subject}
        AVAILABLE LEARNING RESOURCES:
        {content_descriptions}
        Create a {duration_days}-day learning plan with 4-6 activities that help the student master {subject}.
        Each activity should be appropriate for the student's grade level and learning style.
        Include a mix of content types (videos, articles, interactive exercises, etc.).
        Order the activities in a logical sequence from basic to more advanced concepts.
        Return the learning plan in the following JSON format:
        ```json
        {{
            "title": "Learning Plan Title",
            "description": "Brief description of overall plan",
            "subject": "{subject}",
            "topics": ["topic1", "topic2"],
            "activities": [
                {{
                    "title": "Activity Title",
                    "description": "Activity description",
                    "content_id": "<ID of content resource>",
                    "duration_minutes": <minutes>,
                    "order": <order number>
                }},
                ...
            ]
        }}
        ```
        Return ONLY the JSON response without any additional text.
        """
        try:
            # Initialize client if needed
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
            # Generate learning plan using Azure OpenAI
            response = await self.openai_client.create_chat_completion(
                model=settings.OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an educational AI that creates personalized learning plans."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            # Parse response
            plan_dict = json.loads(response["choices"][0]["message"]["content"])
            # Format activities with proper IDs and status
            for activity in plan_dict.get("activities", []):
                if "content_id" in activity and activity["content_id"]:
                    # Ensure content_id is valid
                    try:
                        # Check if the content ID exists in our resources
                        content_exists = any(str(content.id) == activity["content_id"] for content in relevant_content)
                        if not content_exists:
                            activity["content_id"] = None
                    except:
                        activity["content_id"] = None
                # Set default status
                activity["status"] = ActivityStatus.NOT_STARTED
            # Create learning plan object
            now = datetime.utcnow()
            learning_plan = LearningPlan(
                student_id=student.id,
                title=plan_dict["title"],
                description=plan_dict["description"],
                subject=plan_dict["subject"],
                topics=plan_dict["topics"],
                activities=[LearningActivity(**activity) for activity in plan_dict["activities"]],
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                created_at=now,
                updated_at=now,
                start_date=now,
                end_date=now + timedelta(days=duration_days)
            )
            return learning_plan
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}")
            # Create a fallback learning plan
            now = datetime.utcnow()
            return LearningPlan(
                student_id=student.id,
                title=f"{subject} Learning Plan",
                description=f"A basic learning plan for {subject}",
                subject=subject,
                topics=[subject],
                activities=[],
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                created_at=now,
                updated_at=now,
                start_date=now,
                end_date=now + timedelta(days=duration_days)
            )
    async def create_advanced_learning_path(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content],
        duration_weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Create an advanced learning path with weekly structure.
        Args:
            student: The student user
            subject: Subject to focus on
            relevant_content: List of relevant content
            duration_weeks: Duration of the path in weeks
        Returns:
            A structured learning path
        """
        # Format content for prompt
        content_descriptions = ""
        for i, content in enumerate(relevant_content[:15]):  # Limit to 15 items to keep prompt size reasonable
            content_descriptions += f"""
            Content {i+1}:
            - ID: {content.id}
            - Title: {content.title}
            - Type: {content.content_type}
            - Difficulty: {content.difficulty_level}
            - Description: {content.description}
            """
        # Create prompt for learning path generation
        prompt = f"""
        Create a comprehensive {duration_weeks}-week learning path for a grade {student.grade_level} student 
        with {student.learning_style.value if student.learning_style else "mixed"} learning style who wants to master {subject}.
        The student's other interests include: {', '.join(student.subjects_of_interest) if student.subjects_of_interest else 'general learning'}
        Available content:
        {content_descriptions}
        Create a structured learning path with:
        1. An overall goal for the entire path
        2. Weekly goals and themes 
        3. Daily activities for each week (5 days per week)
        4. Specific skills the student will develop
        5. Assessment points to check understanding
        For each activity, select appropriate content from the available resources when possible.
        Include a mix of content types to accommodate the student's learning style.
        Format the response as a JSON object with weeks, days, activities, and skills properties.
        For example:
        {{
            "title": "Master Algebra Fundamentals",
            "description": "A comprehensive learning path to develop strong algebra skills",
            "overall_goal": "Gain confidence in solving algebraic equations and applying algebraic concepts",
            "weeks": [
                {{
                    "week_number": 1,
                    "theme": "Introduction to Variables and Expressions",
                    "goal": "Understand what variables are and how to work with algebraic expressions",
                    "days": [
                        {{
                            "day_number": 1,
                            "activities": [
                                {{
                                    "title": "What are Variables?",
                                    "description": "Learn about variables and their role in algebra",
                                    "content_id": "123",
                                    "type": "video",
                                    "duration_minutes": 20
                                }},
                                ...
                            ]
                        }},
                        ...
                    ],
                    "skills": ["Understanding variables", "Simplifying expressions"],
                    "assessment": "Quiz on basic algebraic expressions"
                }},
                ...
            ]
        }}
        """
        try:
            # Initialize client if needed
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
            # Generate learning path using Azure OpenAI
            response = await self.openai_client.create_chat_completion(
                model=settings.OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an educational AI that creates comprehensive learning paths."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            # Parse response
            learning_path = json.loads(response["choices"][0]["message"]["content"])
            # Add path ID
            learning_path["id"] = str(uuid.uuid4())
            learning_path["student_id"] = str(student.id)
            learning_path["subject"] = subject
            learning_path["created_at"] = datetime.utcnow().isoformat()
            return learning_path
        except Exception as e:
            logger.error(f"Error creating advanced learning path: {e}")
            # Create a fallback learning path
            return {
                "id": str(uuid.uuid4()),
                "title": f"{subject} Learning Path",
                "description": f"A learning path for {subject}",
                "overall_goal": f"Learn the fundamentals of {subject}",
                "student_id": str(student.id),
                "subject": subject,
                "created_at": datetime.utcnow().isoformat(),
                "weeks": []
            }
    async def adapt_plan_for_performance(
        self,
        learning_plan: LearningPlan,
        performance_metrics: Dict[str, Any]
    ) -> LearningPlan:
        """
        Adapt a learning plan based on student performance.
        Args:
            learning_plan: Current learning plan
            performance_metrics: Student performance metrics
        Returns:
            Updated learning plan
        """
        # Get completed activities
        completed_activities = [a for a in learning_plan.activities if a.status == ActivityStatus.COMPLETED]
        # If no completed activities or no performance metrics, return original plan
        if not completed_activities or not performance_metrics:
            return learning_plan
        # Extract performance data
        avg_quiz_score = performance_metrics.get("avg_quiz_score", 0.7)
        writing_quality = performance_metrics.get("writing_quality", 70)
        areas_for_improvement = performance_metrics.get("areas_for_improvement", [])
        # Determine if plan needs adaptation
        needs_easier_content = avg_quiz_score < 0.6 or writing_quality < 60
        needs_harder_content = avg_quiz_score > 0.85 and writing_quality > 80
        if not needs_easier_content and not needs_harder_content:
            # No adaptation needed
            return learning_plan
        # Fetch relevant content to provide alternatives
        db = 
        student = await db.users.find_one({"_id": learning_plan.student_id})
        if not student:
            return learning_plan
        student_obj = User(**student)
        # Get relevant content with appropriate difficulty
        relevant_content = await retrieve_relevant_content(
            student_profile=student_obj,
            subject=learning_plan.subject,
            k=10
        )
        if needs_easier_content:
            # Filter for easier content
            easier_content = [c for c in relevant_content if c.difficulty_level == "beginner"]
            if easier_content:
                # Replace uncompleted activities with easier ones
                for i, activity in enumerate(learning_plan.activities):
                    if activity.status == ActivityStatus.NOT_STARTED and i < len(easier_content):
                        # Replace with easier content
                        learning_plan.activities[i] = LearningActivity(
                            id=str(uuid.uuid4()),
                            title=f"[EASIER] {easier_content[i].title}",
                            description=f"This activity has been adjusted to help you build foundational skills: {easier_content[i].description}",
                            content_id=easier_content[i].id,
                            duration_minutes=activity.duration_minutes,
                            order=activity.order,
                            status=ActivityStatus.NOT_STARTED
                        )
        elif needs_harder_content:
            # Filter for harder content
            harder_content = [c for c in relevant_content if c.difficulty_level == "advanced"]
            if harder_content:
                # Add challenging activities to the plan
                max_order = max([a.order for a in learning_plan.activities]) if learning_plan.activities else 0
                for i, content in enumerate(harder_content[:2]):  # Add up to 2 challenging activities
                    new_activity = LearningActivity(
                        id=str(uuid.uuid4()),
                        title=f"[CHALLENGE] {content.title}",
                        description=f"This advanced activity will challenge your skills: {content.description}",
                        content_id=content.id,
                        duration_minutes=30,
                        order=max_order + i + 1,
                        status=ActivityStatus.NOT_STARTED
                    )
                    learning_plan.activities.append(new_activity)
        # Update the learning plan
        learning_plan.updated_at = datetime.utcnow()
        return learning_plan
# Singleton instance
learning_planner = None
async def get_learning_planner():
    """Get or create the learning planner singleton."""
    global learning_planner
    if learning_planner is None:
        learning_planner = LearningPlanner()
    return learning_planner
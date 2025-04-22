from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import json
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
class LearningPlanGenerator:
    def __init__(self):
        # Will be initialized when needed
        self.openai_client = None
    async def generate_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> Dict[str, Any]:
        """Generate a learning plan for a student based on relevant content."""
        # Format content resources for the prompt
        resources_text = ""
        for i, content in enumerate(relevant_content):
            resources_text += f"""
            Content {i+1}:
            - ID: {content.id}
            - Title: {content.title}
            - Type: {content.content_type}
            - Difficulty: {content.difficulty_level}
            - Description: {content.description}
            - URL: {content.url}
            """
        # Prepare input for the prompt
        student_name = student.full_name or student.username
        grade_level = str(student.grade_level) if student.grade_level else "Unknown"
        learning_style = student.learning_style.value if student.learning_style else "Mixed"
        interests = ", ".join(student.subjects_of_interest) if student.subjects_of_interest else "General learning"
        # Construct the prompt
        prompt = f"""
        You are an expert educational AI assistant tasked with creating personalized learning plans.
        STUDENT PROFILE:
        - Name: {student_name}
        - Grade Level: {grade_level}
        - Learning Style: {learning_style}
        - Subjects of Interest: {interests}
        SUBJECT TO FOCUS ON: {subject}
        AVAILABLE LEARNING RESOURCES:
        {resources_text}
        Based on the student profile and available resources, create a personalized learning plan for the student.
        Include a title, description, and a sequence of 3-5 learning activities.
        For each activity:
        1. Choose appropriate content from the available resources
        2. Set an estimated duration in minutes
        3. Provide a brief description of what the student should do
        4. Set the activities in a logical order
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
                    "content_id": "<ID of content resource or null>",
                    "duration_minutes": <minutes>,
                    "order": <order number>
                }},
                ...
            ]
        }}
        ```
        Return ONLY the JSON response without any additional text.
        """
        # Generate learning plan using Azure OpenAI
        try:
            # Initialize client if needed
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
            response = await self.openai_client.create_chat_completion(
                model=settings.OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an AI educational assistant that creates personalized learning plans."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            response_content = response["choices"][0]["message"]["content"]
            # Parse the JSON response
            plan_dict = json.loads(response_content)
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
            return plan_dict
        except Exception as e:
            logger.error(f"Failed to generate learning plan: {e}")
            # Return a simple default plan
            return {
                "title": f"Learning Plan for {subject}",
                "description": f"A basic learning plan for {subject}",
                "subject": subject,
                "topics": [subject],
                "activities": []
            }
    async def generate_personalized_learning_path(
        self,
        user_profile: User,
        subject: str,
        recommended_content: List[Content]
    ) -> Dict[str, Any]:
        """Generate a comprehensive learning path with weekly structure."""
        # Format content for prompt
        content_descriptions = "\n".join([
            f"- {item.title}: {item.description} (Difficulty: {item.difficulty_level}, Type: {item.content_type})"
            for item in recommended_content[:10]
        ])
        # Generate learning path using Azure OpenAI
        prompt = f"""
        Create a personalized learning path for a grade {user_profile.grade_level} student 
        with {user_profile.learning_style} learning style who is interested in {subject}.
        The student's other interests include: {', '.join(user_profile.subjects_of_interest) if user_profile.subjects_of_interest else 'general learning'}
        Available content:
        {content_descriptions}
        Create a structured 4-week learning plan with:
        1. Weekly goals
        2. Daily activities using the available content
        3. Specific skills the student will develop
        4. Assessment points to check understanding
        Format the response as a JSON object with weeks, days, activities, and skills properties.
        """
        try:
            # Initialize client if needed
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
            response = await self.openai_client.create_chat_completion(
                model=settings.OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an educational AI that creates personalized learning plans."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            learning_path = json.loads(response["choices"][0]["message"]["content"])
            return learning_path
        except Exception as e:
            logger.error(f"Failed to generate learning path: {e}")
            return {
                "title": f"Learning Path for {subject}",
                "description": f"An error occurred while generating the learning path.",
                "weeks": []
            }
# Singleton instance
plan_generator = None
async def get_plan_generator():
    """Get or create the plan generator singleton."""
    global plan_generator
    if plan_generator is None:
        plan_generator = LearningPlanGenerator()
    return plan_generator
async def generate_learning_plan(
    student: User,
    subject: str
) -> LearningPlan:
    """Generate a learning plan for a student."""
    # Retrieve relevant content
    relevant_content = await retrieve_relevant_content(
        student_profile=student,
        subject=subject,
        k=10  # Get more content to have a variety of options
    )
    # Get plan generator
    generator = await get_plan_generator()
    # Generate plan
    plan_dict = await generator.generate_plan(
        student=student,
        subject=subject,
        relevant_content=relevant_content
    )
    # Create learning plan object
    learning_plan = LearningPlan(
        student_id=student.id,
        title=plan_dict["title"],
        description=plan_dict["description"],
        subject=plan_dict["subject"],
        topics=plan_dict["topics"],
        activities=[LearningActivity(**activity) for activity in plan_dict["activities"]],
        status=ActivityStatus.NOT_STARTED,
        progress_percentage=0.0
    )
    return learning_plan
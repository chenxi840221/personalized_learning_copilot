from typing import List, Optional, Dict, Any
import logging
from langchain.chat_models import AzureChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document
import asyncio
import json

from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from rag.retriever import retrieve_relevant_content
from utils.db_manager import get_db
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LearningPlanGenerator:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            openai_api_type="azure",
            openai_api_version=settings.OPENAI_API_VERSION,
            openai_api_base=settings.OPENAI_API_BASE,
            openai_api_key=settings.OPENAI_API_KEY,
            deployment_name=settings.OPENAI_DEPLOYMENT_NAME,
            temperature=0.7
        )
        
        # Prompt for generating learning plans
        self.plan_template = """
        You are an expert educational AI assistant tasked with creating personalized learning plans.
        
        STUDENT PROFILE:
        - Name: {student_name}
        - Grade Level: {grade_level}
        - Learning Style: {learning_style}
        - Subjects of Interest: {interests}
        
        SUBJECT TO FOCUS ON: {subject}
        
        AVAILABLE LEARNING RESOURCES:
        {resources}
        
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
        
        self.plan_prompt = PromptTemplate(
            input_variables=["student_name", "grade_level", "learning_style", "interests", "subject", "resources"],
            template=self.plan_template
        )
        
        self.plan_chain = LLMChain(
            llm=self.llm,
            prompt=self.plan_prompt
        )
    
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
        prompt_input = {
            "student_name": student.full_name or student.username,
            "grade_level": str(student.grade_level) if student.grade_level else "Unknown",
            "learning_style": student.learning_style.value if student.learning_style else "Mixed",
            "interests": ", ".join(student.subjects_of_interest) if student.subjects_of_interest else "General learning",
            "subject": subject,
            "resources": resources_text
        }
        
        # Generate learning plan
        response = await self.plan_chain.arun(**prompt_input)
        
        try:
            # Parse the JSON response
            plan_dict = json.loads(response)
            
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
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response}")
            # Return a simple default plan
            return {
                "title": f"Learning Plan for {subject}",
                "description": f"A basic learning plan for {subject}",
                "subject": subject,
                "topics": [subject],
                "activities": []
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
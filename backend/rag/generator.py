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
        relevant_content: List[Content],
        days: int = 1  # Default to 1 day, can be expanded based on learning period
    ) -> Dict[str, Any]:
        """Generate a learning plan for a student based on relevant content."""
        # Format content resources for the prompt with enhanced details
        resources_text = ""
        for i, content in enumerate(relevant_content):
            # Extract important content details for matching
            keywords = ", ".join(content.keywords) if hasattr(content, "keywords") and content.keywords else "Not specified"
            grade_levels = ", ".join([str(g) for g in content.grade_level]) if hasattr(content, "grade_level") and content.grade_level else "Not specified"
            duration = content.duration_minutes if hasattr(content, "duration_minutes") and content.duration_minutes else "Not specified"
            
            # Format each content resource with detailed information
            resources_text += f"""
            Content {i+1}:
            - ID: {content.id}
            - Title: {content.title}
            - Type: {content.content_type}
            - Difficulty: {content.difficulty_level}
            - Subject: {content.subject}
            - Grade Level(s): {grade_levels}
            - Keywords: {keywords}
            - Duration: {duration} minutes
            - Description: {content.description}
            - URL: {content.url}
            """
            
        # Prepare input for the prompt
        student_name = student.full_name or student.username
        grade_level = str(student.grade_level) if student.grade_level else "Unknown"
        
        # Handle learning style with fallback to Mixed
        try:
            learning_style = student.learning_style.value if student.learning_style else "mixed"
        except Exception as e:
            logger.warning(f"Error processing learning style for plan generation: {e}")
            learning_style = "mixed"
            
        interests = ", ".join(student.subjects_of_interest) if student.subjects_of_interest else "General learning"
        
        # Get areas for improvement if available in the student profile
        areas_for_improvement = []
        if hasattr(student, "areas_for_improvement") and student.areas_for_improvement:
            areas_for_improvement = student.areas_for_improvement
        
        improvement_text = ", ".join(areas_for_improvement) if areas_for_improvement else "Not specified"
        
        # Construct the enhanced prompt for multi-day learning plan
        prompt = f"""
        You are an expert educational AI assistant tasked with creating personalized learning plans based on content in Azure AI Search.
        
        STUDENT PROFILE:
        - Name: {student_name}
        - Grade Level: {grade_level}
        - Learning Style: {learning_style}
        - Subjects of Interest: {interests}
        - Areas for Improvement: {improvement_text}
        
        SUBJECT TO FOCUS ON: {subject}
        LEARNING PERIOD DURATION: {days} days
        
        AVAILABLE LEARNING RESOURCES FROM AZURE AI SEARCH:
        {resources_text}
        
        Based on the student profile and available resources, create a highly personalized learning plan that addresses the student's needs over a period of {days} days.
        
        INSTRUCTIONS:
        1. Create a coherent learning journey starting with foundational concepts and progressing to more advanced material
        2. Include a descriptive title and comprehensive plan description
        3. Create a sequence of learning activities distributed across {days} days
        4. Aim for 1-3 activities per day depending on their duration
        5. Total daily activities should take approximately 30-60 minutes to complete
        
        For each activity:
        1. Choose the most appropriate content from the available resources that matches:
           - The student's grade level
           - The student's learning style preference
           - The appropriate difficulty level for the student
           - Areas where the student needs improvement
        
        2. Each activity should:
           - Be assigned to a specific day number (from 1 to {days})
           - Use the actual duration_minutes from the content (if available)
           - Provide a clear description of what the student should do
           - Explain WHY this activity helps address the student's learning needs
           - Include the content URL for direct access
           - Set activities in a logical progression of learning
        
        Return the learning plan in the following JSON format:
        ```json
        {{
            "title": "Learning Plan Title",
            "description": "Comprehensive description of overall plan",
            "subject": "{subject}",
            "topics": ["topic1", "topic2"],
            "activities": [
                {{
                    "title": "Activity Title",
                    "description": "Detailed activity description explaining what to do and how it helps the student's learning goals",
                    "content_id": "<ID of content resource>",
                    "duration_minutes": <minutes from content>,
                    "day": <day number>,
                    "order": <order number>,
                    "content_url": "<URL of the content>",
                    "learning_benefit": "Explanation of how this specific activity addresses the student's learning needs"
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
                model=settings.AZURE_OPENAI_DEPLOYMENT,  # Using AZURE_OPENAI_DEPLOYMENT instead of OPENAI_DEPLOYMENT_NAME
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
            
            # Format activities with proper IDs, status, and enhanced fields
            for activity in plan_dict.get("activities", []):
                # Handle content_id validation
                if "content_id" in activity and activity["content_id"]:
                    try:
                        # Check if the content ID exists in our resources
                        matched_content = next((content for content in relevant_content if str(content.id) == activity["content_id"]), None)
                        if not matched_content:
                            activity["content_id"] = None
                            activity["content_url"] = None
                        else:
                            # Ensure content_url is set correctly
                            if "content_url" not in activity or not activity["content_url"]:
                                activity["content_url"] = matched_content.url
                            
                            # Use content duration if activity doesn't specify one
                            if ("duration_minutes" not in activity or activity["duration_minutes"] is None) and hasattr(matched_content, "duration_minutes"):
                                activity["duration_minutes"] = matched_content.duration_minutes
                    except:
                        activity["content_id"] = None
                        
                # Set default status
                activity["status"] = ActivityStatus.NOT_STARTED
                
                # Ensure duration_minutes has a reasonable default if not specified
                if "duration_minutes" not in activity or activity["duration_minutes"] is None:
                    activity["duration_minutes"] = 20  # Default to 20 minutes
                
                # Add or enhance learning_benefit if not present
                if "learning_benefit" not in activity or not activity["learning_benefit"]:
                    activity["learning_benefit"] = f"This activity helps build skills in {subject} and supports the student's learning journey."
                
                # Add metadata field to store additional information if needed
                if "metadata" not in activity:
                    content_info = None
                    if matched_content:
                        # Extract important content information to display in the UI
                        content_info = {
                            "title": matched_content.title,
                            "description": matched_content.description,
                            "subject": matched_content.subject,
                            "difficulty_level": matched_content.difficulty_level.value if hasattr(matched_content, "difficulty_level") else None,
                            "content_type": matched_content.content_type.value if hasattr(matched_content, "content_type") else None,
                            "grade_level": matched_content.grade_level if hasattr(matched_content, "grade_level") else None
                        }
                    
                    activity["metadata"] = {
                        "generated_at": datetime.utcnow().isoformat(),
                        "content_type": matched_content.content_type.value if matched_content else None,
                        "content_info": content_info
                    }
                
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
        
        # Handle learning style with fallback
        try:
            learning_style_text = user_profile.learning_style.value if user_profile.learning_style else "mixed"
        except Exception as e:
            logger.warning(f"Error processing learning style for path generation: {e}")
            learning_style_text = "mixed"
            
        # Generate learning path using Azure OpenAI
        prompt = f"""
        Create a personalized learning path for a grade {user_profile.grade_level} student 
        with {learning_style_text} learning style who is interested in {subject}.
        
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
                model=settings.AZURE_OPENAI_DEPLOYMENT,  # Using AZURE_OPENAI_DEPLOYMENT instead of OPENAI_DEPLOYMENT_NAME
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
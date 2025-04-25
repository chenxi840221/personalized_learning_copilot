# backend/services/azure_langchain_service.py
"""
Service for educational AI features using Azure LangChain integration.
Provides personalized learning plans, content recommendations, and Q&A functionality.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta

from models.user import User
from models.content import Content, ContentType, DifficultyLevel
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from rag.azure_langchain_integration import get_azure_langchain
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class AzureLangChainService:
    """
    Service for AI-powered educational features using Azure and LangChain.
    """
    
    def __init__(self):
        """Initialize the Azure LangChain service."""
        self.azure_langchain = None
        self.qa_chain = None
        self.conversation_chain = None
    
    async def initialize(self):
        """Initialize the service components."""
        # Get the Azure LangChain integration
        self.azure_langchain = await get_azure_langchain()
        
        # Initialize QA chain
        try:
            self.qa_chain = await self.azure_langchain.create_rag_chain()
            self.conversation_chain = await self.azure_langchain.create_conversational_rag_chain()
            logger.info("AI chains initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AI chains: {e}")
    
    async def generate_personalized_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> LearningPlan:
        """
        Generate a personalized learning plan for a student.
        
        Args:
            student: User object for the student
            subject: Subject for the learning plan
            relevant_content: List of relevant content
            
        Returns:
            A LearningPlan object
        """
        if not self.azure_langchain:
            await self.initialize()
        
        try:
            # Convert student to dictionary
            student_dict = student.dict() if hasattr(student, "dict") else dict(student)
            
            # Convert content to dictionaries
            content_dicts = []
            for content in relevant_content:
                content_dict = content.dict() if hasattr(content, "dict") else dict(content)
                content_dicts.append(content_dict)
            
            # Generate learning plan using RAG
            plan_dict = await self.azure_langchain.generate_learning_plan_with_rag(
                student_profile=student_dict,
                subject=subject,
                available_content=content_dicts
            )
            
            # Create a LearningPlan object
            now = datetime.utcnow()
            
            # Create activities
            activities = []
            for i, activity_dict in enumerate(plan_dict.get("activities", [])):
                # Generate ID
                activity_id = str(uuid.uuid4())
                
                # Set defaults for missing fields
                if "order" not in activity_dict:
                    activity_dict["order"] = i + 1
                
                if "duration_minutes" not in activity_dict:
                    activity_dict["duration_minutes"] = 30
                
                # Create activity
                activity = LearningActivity(
                    id=activity_id,
                    title=activity_dict.get("title", f"Activity {i+1}"),
                    description=activity_dict.get("description", ""),
                    content_id=activity_dict.get("content_id"),
                    duration_minutes=activity_dict.get("duration_minutes"),
                    order=activity_dict.get("order"),
                    status=ActivityStatus.NOT_STARTED,
                    completed_at=None
                )
                
                activities.append(activity)
            
            # Create the learning plan
            plan = LearningPlan(
                id=str(uuid.uuid4()),
                student_id=student_dict.get("id"),
                title=plan_dict.get("title", f"{subject} Learning Plan"),
                description=plan_dict.get("description", f"A personalized learning plan for {subject}"),
                subject=subject,
                topics=plan_dict.get("topics", [subject]),
                activities=activities,
                created_at=now,
                updated_at=now,
                start_date=now,
                end_date=now + timedelta(days=14),  # 2-week plan
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Error generating learning plan: {e}")
            
            # Create a fallback plan
            return self._create_fallback_learning_plan(student, subject, relevant_content)
    
    def _create_fallback_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> LearningPlan:
        """Create a fallback learning plan when AI generation fails."""
        now = datetime.utcnow()
        
        # Get student ID
        student_id = student.id if hasattr(student, "id") else student["id"]
        
        # Create activities from available content
        activities = []
        for i, content in enumerate(relevant_content[:5]):  # Use up to 5 content items
            content_id = content.id if hasattr(content, "id") else content["id"]
            title = content.title if hasattr(content, "title") else content["title"]
            description = content.description if hasattr(content, "description") else content["description"]
            duration = (
                content.duration_minutes if hasattr(content, "duration_minutes") 
                else content.get("duration_minutes", 30)
            )
            
            activity = LearningActivity(
                id=str(uuid.uuid4()),
                title=f"Study: {title}",
                description=description,
                content_id=content_id,
                duration_minutes=duration,
                order=i+1,
                status=ActivityStatus.NOT_STARTED,
                completed_at=None
            )
            
            activities.append(activity)
        
        # Create plan
        plan = LearningPlan(
            id=str(uuid.uuid4()),
            student_id=student_id,
            title=f"{subject} Learning Plan",
            description=f"A personalized learning plan for {subject}",
            subject=subject,
            topics=[subject],
            activities=activities,
            created_at=now,
            updated_at=now,
            start_date=now,
            end_date=now + timedelta(days=14),
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0
        )
        
        return plan
    
    async def answer_educational_question(
        self,
        question: str,
        student_grade: Optional[int] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer an educational question using RAG.
        
        Args:
            question: The student's question
            student_grade: Optional grade level for tailoring the response
            subject: Optional subject for context
            
        Returns:
            Dictionary with answer and sources
        """
        if not self.azure_langchain:
            await self.initialize()
            
        if not self.qa_chain:
            raise ValueError("QA chain not initialized")
            
        try:
            # Enhance question with grade and subject context if provided
            enhanced_question = question
            context_parts = []
            
            if student_grade:
                context_parts.append(f"I'm a grade {student_grade} student")
                
            if subject:
                context_parts.append(f"studying {subject}")
                
            if context_parts:
                context = " ".join(context_parts)
                enhanced_question = f"{context}. {question}"
            
            # Get answer
            answer = await self.qa_chain.ainvoke(enhanced_question)
            
            # Get sources (limited functionality in our implementation)
            # In a full implementation, we would track and return source documents
            
            return {
                "answer": answer,
                "sources": []  # Would contain source documents in a complete implementation
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "answer": "I'm sorry, I couldn't generate an answer to your question at this time.",
                "sources": []
            }
    
    async def index_educational_content(self, contents: List[Content]) -> bool:
        """
        Index educational content for search and retrieval.
        
        Args:
            contents: List of content items to index
            
        Returns:
            Success status
        """
        if not self.azure_langchain:
            await self.initialize()
            
        try:
            # Convert Content objects to documents for indexing
            documents = []
            
            for content in contents:
                # Extract text content
                content_dict = content.dict() if hasattr(content, "dict") else dict(content)
                
                # Get text from metadata if available
                text = ""
                metadata = content_dict.get("metadata", {})
                
                if isinstance(metadata, dict):
                    if "content_text" in metadata and metadata["content_text"]:
                        text = metadata["content_text"]
                    elif "transcription" in metadata and metadata["transcription"]:
                        text = metadata["transcription"]
                
                # If no text content, use description
                if not text and content_dict.get("description"):
                    text = content_dict["description"]
                
                # Prepare document
                document = {
                    "id": content_dict.get("id", str(uuid.uuid4())),
                    "title": content_dict.get("title", "Untitled"),
                    "subject": content_dict.get("subject", ""),
                    "content_type": content_dict.get("content_type", ""),
                    "difficulty_level": content_dict.get("difficulty_level", ""),
                    "grade_level": content_dict.get("grade_level", []),
                    "text": text,
                    "url": content_dict.get("url", "")
                }
                
                documents.append(document)
            
            # Index documents
            success = await self.azure_langchain.index_documents(documents)
            
            return success
            
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return False
    
    async def search_educational_content(
        self,
        query: str,
        student: User,
        subject: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for educational content tailored to a student.
        
        Args:
            query: Search query
            student: Student profile
            subject: Optional subject filter
            content_type: Optional content type filter
            limit: Maximum number of results
            
        Returns:
            List of relevant content items
        """
        if not self.azure_langchain:
            await self.initialize()
            
        try:
            # Build filter based on parameters
            filter_parts = []
            
            if subject:
                filter_parts.append(f"subject eq '{subject}'")
                
            if content_type:
                filter_parts.append(f"content_type eq '{content_type}'")
                
            # Add grade level filter if available
            if hasattr(student, "grade_level") and student.grade_level:
                grade = student.grade_level
                grade_filters = [
                    f"grade_level/any(g: g eq {grade})",
                    f"grade_level/any(g: g eq {grade - 1})",
                    f"grade_level/any(g: g eq {grade + 1})"
                ]
                grade_filter = f"({' or '.join(grade_filters)})"
                filter_parts.append(grade_filter)
            
            # Join filters
            filter_str = " and ".join(filter_parts) if filter_parts else None
            
            # Perform search
            search_results = await self.azure_langchain.search_documents(
                query=query,
                filter=filter_str,
                top_k=limit
            )
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching educational content: {e}")
            return []

# Singleton instance
azure_langchain_service = None

async def get_azure_langchain_service():
    """Get or create the Azure LangChain service singleton."""
    global azure_langchain_service
    if azure_langchain_service is None:
        azure_langchain_service = AzureLangChainService()
        await azure_langchain_service.initialize()
    return azure_langchain_service
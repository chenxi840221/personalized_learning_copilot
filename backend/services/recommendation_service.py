import logging
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import Vector

from models.user import User
from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for generating content recommendations using Azure AI Search."""
    
    def __init__(self):
        """Initialize recommendation service."""
        self.search_client = None
        self.openai_adapter = None
    
    async def initialize(self):
        """Initialize Azure AI Search client and OpenAI adapter."""
        self.search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        self.openai_adapter = await get_openai_adapter()
    
    async def close(self):
        """Close Azure AI Search client."""
        if self.search_client:
            await self.search_client.close()
    
    async def get_personalized_recommendations(
        self,
        user: User,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> List[Content]:
        """
        Get personalized content recommendations for a user using Azure AI Search.
        
        Args:
            user: User to get recommendations for
            subject: Optional subject filter
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended content items
        """
        if not self.search_client:
            await self.initialize()
        
        try:
            # Generate a query based on user profile
            query_text = self._generate_query_text(user, subject)
            
            # Generate embedding for the query
            query_embedding = await self._generate_embedding(query_text)
            
            # Build filter based on user and subject
            filter_expression = self._build_filter_expression(user, subject)
            
            # Create the vector query for semantic search
            vector_query = Vector(
                value=query_embedding,
                k=limit,
                fields="embedding",
                exhaustive=True
            )
            
            # Execute the search with vector and filtering
            results = await self.search_client.search(
                search_text=None,
                vectors=[vector_query],
                filter=filter_expression,
                select=["id", "title", "description", "subject", "content_type", "difficulty_level", 
                        "grade_level", "topics", "url", "duration_minutes", "keywords"],
                top=limit
            )
            
            # Convert results to Content objects
            content_items = []
            async for result in results:
                content_dict = dict(result)
                # Convert to proper enum types for model
                content_dict["content_type"] = ContentType(content_dict["content_type"])
                content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                content_items.append(Content(**content_dict))
            
            return content_items
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            # Return empty list on error
            return []
    
    def _generate_query_text(self, user: User, subject: Optional[str] = None) -> str:
        """Generate query text for embedding based on user profile."""
        grade_level = str(user.grade_level) if user.grade_level else "unknown"
        learning_style = user.learning_style.value if user.learning_style else "mixed"
        interests = ", ".join(user.subjects_of_interest) if user.subjects_of_interest else "general learning"
        
        query = f"Educational content for a student in grade {grade_level} "
        query += f"with a {learning_style} learning style. "
        query += f"Interested in {interests}. "
        
        if subject:
            query += f"Looking specifically for {subject} content."
        
        return query
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI adapter."""
        try:
            if not self.openai_adapter:
                self.openai_adapter = await get_openai_adapter()
                
            embedding = await self.openai_adapter.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fall back to empty vector
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    def _build_filter_expression(self, user: User, subject: Optional[str] = None) -> str:
        """Build OData filter expression for Azure AI Search."""
        filters = []
        
        # Add subject filter if specified
        if subject:
            filters.append(f"subject eq '{subject}'")
        
        # Add grade level filter based on user's grade
        if user.grade_level:
            # Include content for this grade level, one below, and one above
            grade_filters = [
                f"grade_level/any(g: g eq {user.grade_level})",
                f"grade_level/any(g: g eq {user.grade_level - 1})",
                f"grade_level/any(g: g eq {user.grade_level + 1})"
            ]
            filters.append(f"({' or '.join(grade_filters)})")
        
        # Filter for difficulty level based on user's grade
        if user.grade_level:
            if user.grade_level <= 6:
                filters.append("(difficulty_level eq 'beginner' or difficulty_level eq 'intermediate')")
            elif user.grade_level <= 9:
                filters.append("difficulty_level eq 'intermediate'")
            else:
                filters.append("(difficulty_level eq 'intermediate' or difficulty_level eq 'advanced')")
        
        # Combine all filters with AND
        if filters:
            return " and ".join(filters)
        
        return None
    
    async def get_content_by_id(self, content_id: str) -> Optional[Content]:
        """Get content by ID."""
        if not self.search_client:
            await self.initialize()
        
        try:
            result = await self.search_client.get_document(key=content_id)
            if result:
                content_dict = dict(result)
                # Convert to proper enum types for model
                content_dict["content_type"] = ContentType(content_dict["content_type"])
                content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                return Content(**content_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting content by ID: {e}")
            return None

# Singleton instance
recommendation_service = None

async def get_recommendation_service():
    """Get or create recommendation service singleton."""
    global recommendation_service
    if recommendation_service is None:
        recommendation_service = RecommendationService()
        await recommendation_service.initialize()
    return recommendation_service
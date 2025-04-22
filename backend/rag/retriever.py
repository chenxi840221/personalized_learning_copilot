from typing import List, Optional, Dict, Any
import logging
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
import asyncio
from models.user import User
from models.content import Content
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ContentRetriever:
    def __init__(self):
        # Initialize client when needed
        self.openai_client = None
        self.search_client = None
        
    async def initialize(self):
        """Initialize the search client."""
        if not self.search_client:
            self.search_client = SearchClient(
                endpoint=settings.AZURE_SEARCH_ENDPOINT,
                index_name=settings.CONTENT_INDEX_NAME,
                credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
            )
        
    async def get_embedding(self, text: str) -> List[float]:
        """Get embeddings from Azure OpenAI."""
        if not self.openai_client:
            self.openai_client = await get_openai_adapter()
        embedding = await self.openai_client.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=text
        )
        return embedding

    async def get_relevant_content(
        self, 
        query: str, 
        subject: Optional[str] = None,
        grade_level: Optional[int] = None,
        k: int = 5
    ) -> List[dict]:
        """Retrieve relevant content based on query and filters."""
        try:
            # Initialize if needed
            if not self.search_client:
                await self.initialize()
                
            # Get embedding for query
            query_embedding = await self.get_embedding(query)
            
            # Build filter based on parameters
            filter_expr = None
            if subject:
                filter_expr = f"subject eq '{subject}'"
            if grade_level:
                grade_filter = f"grade_level/any(g: g eq {grade_level})"
                filter_expr = grade_filter if not filter_expr else f"{filter_expr} and {grade_filter}"
            
            # Create vectorized query
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=k,
                fields="embedding"
            )
            
            # Perform vector search with metadata filtering
            results = await self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=k,
                select=["id", "title", "subject", "content_type", "difficulty_level", "url"]
            )
            
            # Convert to response format
            result_docs = []
            async for result in results:
                result_docs.append({
                    "id": result["id"],
                    "title": result["title"],
                    "subject": result["subject"],
                    "content_type": result["content_type"],
                    "difficulty_level": result["difficulty_level"],
                    "url": result["url"],
                    "relevance_score": result["@search.score"]
                })
            return result_docs
        except Exception as e:
            logger.error(f"Error retrieving relevant content: {e}")
            return []

    async def get_personalized_recommendations(
        self,
        user_profile: User,
        subject: Optional[str] = None,
        count: int = 10
    ) -> List[dict]:
        """Get personalized content recommendations for a user."""
        # Generate query based on user profile
        interests = ", ".join(user_profile.subjects_of_interest) if user_profile.subjects_of_interest else "general learning"
        grade = user_profile.grade_level if user_profile.grade_level else "unknown"
        learning_style = user_profile.learning_style.value if user_profile.learning_style else "mixed"
        query = f"Student in grade {grade} with {learning_style} learning style interested in {interests}"
        # Add subject if specified
        if subject:
            query += f" looking for content about {subject}"
        # Get relevant content
        return await self.get_relevant_content(
            query=query,
            subject=subject,
            grade_level=user_profile.grade_level,
            k=count
        )
        
    async def close(self):
        """Close the search client."""
        if self.search_client:
            await self.search_client.close()

# Singleton instance
content_retriever = None

async def get_content_retriever():
    """Get or create the content retriever singleton."""
    global content_retriever
    if content_retriever is None:
        content_retriever = ContentRetriever()
        await content_retriever.initialize()
    return content_retriever

async def retrieve_relevant_content(
    student_profile: User,
    subject: Optional[str] = None,
    k: int = 5
) -> List[Content]:
    """Retrieve relevant content for a student."""
    # Get retriever
    retriever = await get_content_retriever()
    # Get personalized recommendations
    content_dicts = await retriever.get_personalized_recommendations(
        user_profile=student_profile,
        subject=subject,
        count=k
    )
    
    # Convert to Content objects
    contents = []
    for dict_item in content_dicts:
        content = Content(
            id=dict_item["id"],
            title=dict_item["title"],
            description=dict_item.get("description", ""),
            content_type=dict_item["content_type"],
            subject=dict_item["subject"],
            difficulty_level=dict_item["difficulty_level"],
            url=dict_item["url"],
            grade_level=[],  # Default empty list if not available
            topics=[],
            source="Azure AI Search"
        )
        contents.append(content)
    
    # Return contents
    return contents
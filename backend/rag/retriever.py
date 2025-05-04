from typing import List, Optional, Dict, Any
import logging
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
import asyncio
from models.user import User
from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ContentRetriever:
    """Enhanced content retriever with improved filtering and ranking capabilities."""
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
        difficulty_level: Optional[str] = None,
        learning_style: Optional[str] = None,
        k: int = 5
    ) -> List[dict]:
        """
        Retrieve relevant content based on query and filters with enhanced filtering.
        
        Args:
            query: The query text to search for
            subject: Optional subject filter
            grade_level: Optional grade level filter
            difficulty_level: Optional difficulty level filter
            learning_style: Optional learning style to prioritize content types
            k: Number of results to return
            
        Returns:
            List of relevant content items
        """
        try:
            # Initialize if needed
            if not self.search_client:
                await self.initialize()
                
            # Get embedding for query
            query_embedding = await self.get_embedding(query)
            
            # Build comprehensive filter based on parameters
            filter_expr = []
            
            # Subject filter
            if subject:
                filter_expr.append(f"subject eq '{subject}'")
            
            # Grade level filter - expanded to include appropriate grade range
            if grade_level:
                grade_filters = []
                
                # Include the target grade and adjacent grades for better content coverage
                for g in range(max(1, grade_level - 1), min(12, grade_level + 2)):
                    grade_filters.append(f"grade_level/any(g: g eq {g})")
                
                if grade_filters:
                    filter_expr.append(f"({' or '.join(grade_filters)})")
            
            # Difficulty level filter with grade-appropriate default
            if difficulty_level:
                filter_expr.append(f"difficulty_level eq '{difficulty_level}'")
            elif grade_level:
                # If no specific difficulty requested, use grade-appropriate default
                if grade_level <= 5:  # Elementary
                    filter_expr.append("(difficulty_level eq 'beginner' or difficulty_level eq 'intermediate')")
                elif grade_level <= 8:  # Middle school
                    filter_expr.append("difficulty_level eq 'intermediate'")
                else:  # High school
                    filter_expr.append("(difficulty_level eq 'intermediate' or difficulty_level eq 'advanced')")
            
            # Combine all filters with AND
            filter_expression = " and ".join(filter_expr) if filter_expr else None
            
            # Create vectorized query
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=k * 2,  # Get more results than needed for post-filtering
                fields="embedding"
            )
            
            # Execute search with vector query and filters
            results = await self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expression,
                top=k * 2,  # Get more than needed for post-filtering
                select=["id", "title", "subject", "content_type", "difficulty_level", 
                        "description", "url", "grade_level", "topics", "duration_minutes", 
                        "keywords", "metadata_content_text", "page_content"]
            )
            
            # Process results with learning style preferences if specified
            result_docs = []
            type_counts = {}  # Track content type diversity
            
            async for result in results:
                result_dict = dict(result)
                
                # Track content type
                content_type = result_dict.get("content_type", "unknown")
                if content_type not in type_counts:
                    type_counts[content_type] = 0
                type_counts[content_type] += 1
                
                # Add relevance score
                result_dict["relevance_score"] = result["@search.score"]
                
                # Add to results
                result_docs.append(result_dict)
            
            # Apply learning style filtering if specified
            if learning_style and len(result_docs) > k:
                # Determine preferred content types for this learning style
                preferred_types = self._get_preferred_content_types(learning_style)
                
                # Sort results giving priority to preferred content types
                # but ensuring we maintain diversity in the results
                final_results = []
                
                # First add one of each preferred type (if available)
                for pref_type in preferred_types:
                    for doc in result_docs:
                        if doc["content_type"] == pref_type and doc not in final_results:
                            final_results.append(doc)
                            break
                            
                    # Stop if we've reached the desired count
                    if len(final_results) >= k:
                        break
                
                # Fill remaining slots with highest scoring remaining items
                if len(final_results) < k:
                    remaining = [doc for doc in result_docs if doc not in final_results]
                    remaining.sort(key=lambda x: x["relevance_score"], reverse=True)
                    final_results.extend(remaining[:k - len(final_results)])
                    
                return final_results[:k]
            else:
                # If no learning style filter, just return top k results
                return result_docs[:k]
                
        except Exception as e:
            logger.error(f"Error retrieving relevant content: {e}")
            return []
    
    def _get_preferred_content_types(self, learning_style: str) -> List[str]:
        """Get preferred content types for a given learning style."""
        preferences = {
            "visual": ["video", "interactive", "lesson", "article", "quiz"],
            "auditory": ["video", "audio", "podcast", "lesson", "interactive", "article"],
            "reading_writing": ["article", "worksheet", "lesson", "quiz", "video"],
            "kinesthetic": ["interactive", "activity", "quiz", "video", "lesson"],
            "mixed": ["video", "article", "interactive", "lesson", "quiz", "activity"]
        }
        
        # Return preferences for the specified style, or mixed if not found
        return preferences.get(learning_style.lower(), preferences["mixed"])

    async def get_personalized_recommendations(
        self,
        user_profile: User,
        subject: Optional[str] = None,
        count: int = 10
    ) -> List[dict]:
        """
        Get personalized content recommendations for a user with enhanced user profiling.
        
        Args:
            user_profile: User information
            subject: Optional subject filter
            count: Number of recommendations to return
            
        Returns:
            List of recommended content items
        """
        # Build a comprehensive query based on user profile
        interests = ", ".join(user_profile.subjects_of_interest) if user_profile.subjects_of_interest else "general learning"
        grade = user_profile.grade_level if user_profile.grade_level else "unknown"
        learning_style = user_profile.learning_style.value if user_profile.learning_style else "mixed"
        
        # Create a rich natural language query for better semantic matching
        query = f"Student in grade {grade} with {learning_style} learning style interested in {interests}"
        
        # Add subject if specified
        if subject:
            query += f", looking for engaging {subject} content"
            
            # If the subject matches one of their interests, emphasize the connection
            if user_profile.subjects_of_interest and subject in user_profile.subjects_of_interest:
                query += f" that builds on their existing interest in {subject}"
        else:
            # If no subject specified but they have interests, prioritize those
            if user_profile.subjects_of_interest:
                primary_interest = user_profile.subjects_of_interest[0]
                query += f", especially content related to {primary_interest}"
        
        # Add grade-level context for more appropriate results
        if user_profile.grade_level:
            if user_profile.grade_level <= 5:  # Elementary
                query += ", with easy-to-understand explanations and engaging activities"
            elif user_profile.grade_level <= 8:  # Middle school
                query += ", with clear explanations and some hands-on applications"
            else:  # High school
                query += ", with detailed explanations and real-world applications"
        
        # Get relevant content using the enhanced query
        return await self.get_relevant_content(
            query=query,
            subject=subject,
            grade_level=user_profile.grade_level,
            learning_style=user_profile.learning_style.value if user_profile.learning_style else "mixed",
            k=count
        )
        
    async def close(self):
        """Close the search client."""
        if self.search_client:
            await self.search_client.close()
            self.search_client = None

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
    k: int = 5,
    grade_level: Optional[int] = None
) -> List[Content]:
    """
    Retrieve relevant content for a student with enhanced personalization.
    
    Args:
        student_profile: The student user profile
        subject: Optional subject to focus on
        k: Number of content items to retrieve
        
    Returns:
        List of relevant Content objects
    """
    # Get retriever
    retriever = await get_content_retriever()
    
    # Get personalized recommendations
    # Use provided grade_level parameter if available, otherwise use the one from student_profile
    effective_grade = grade_level if grade_level is not None else student_profile.grade_level
    
    # If grade_level parameter is provided and different from profile, create a modified profile
    modified_profile = student_profile
    if grade_level is not None and grade_level != student_profile.grade_level:
        # Create a new User object with the modified grade level
        from models.user import User
        modified_profile = User(
            id=student_profile.id,
            username=student_profile.username,
            email=student_profile.email,
            full_name=student_profile.full_name,
            grade_level=grade_level,  # Use the provided grade level
            subjects_of_interest=student_profile.subjects_of_interest,
            areas_for_improvement=getattr(student_profile, 'areas_for_improvement', []),
            learning_style=student_profile.learning_style,
            is_active=student_profile.is_active
        )
    
    content_dicts = await retriever.get_personalized_recommendations(
        user_profile=modified_profile,
        subject=subject,
        count=k
    )
    
    # Convert to Content objects with proper type handling
    contents = []
    for dict_item in content_dicts:
        try:
            # Create Content object with proper enum type handling
            content = Content(
                id=dict_item["id"],
                title=dict_item["title"],
                description=dict_item.get("description", ""),
                content_type=ContentType(dict_item["content_type"]),
                subject=dict_item["subject"],
                difficulty_level=DifficultyLevel(dict_item["difficulty_level"]),
                url=dict_item["url"],
                grade_level=dict_item.get("grade_level", []),
                topics=dict_item.get("topics", []),
                duration_minutes=dict_item.get("duration_minutes"),
                keywords=dict_item.get("keywords", []),
                source=dict_item.get("source", "Azure AI Search")
            )
            contents.append(content)
        except Exception as e:
            logger.warning(f"Error converting content item: {e}")
    
    # Filter the results to ensure they're grade-appropriate
    grade_appropriate_content = []
    # Use provided grade_level parameter if available, otherwise use student_profile.grade_level
    effective_grade = grade_level if grade_level is not None else student_profile.grade_level
    
    if effective_grade:
        grade = effective_grade
        for content in contents:
            # Include content if it's targeted at the student's grade level ±1
            if not content.grade_level or grade in content.grade_level or (grade-1) in content.grade_level or (grade+1) in content.grade_level:
                grade_appropriate_content.append(content)
    else:
        # If no grade level specified, include all content
        grade_appropriate_content = contents
    
    return grade_appropriate_content
from typing import List, Optional, Dict, Any
import logging
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
import asyncio
from bson import ObjectId

from models.user import User
from models.content import Content, ContentWithEmbedding
from utils.db_manager import get_db
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ContentRetriever:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            azure_deployment="text-embedding-ada-002",
            openai_api_type="azure",
            openai_api_version=settings.OPENAI_API_VERSION,
            openai_api_base=settings.OPENAI_API_BASE,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.vector_store = None
        
    async def initialize_vector_store(self, contents: List[ContentWithEmbedding]):
        """Initialize the vector store with content embeddings."""
        documents = []
        embeddings_list = []
        
        for content in contents:
            if not content.embedding:
                logger.warning(f"Content {content.id} has no embedding, skipping")
                continue
                
            doc = Document(
                page_content=f"{content.title}\n{content.description}",
                metadata={
                    "id": str(content.id),
                    "title": content.title,
                    "subject": content.subject,
                    "content_type": content.content_type,
                    "difficulty_level": content.difficulty_level,
                    "grade_level": content.grade_level,
                    "url": str(content.url)
                }
            )
            documents.append(doc)
            embeddings_list.append(content.embedding)
        
        if documents:
            self.vector_store = FAISS.from_embeddings(
                text_embeddings=embeddings_list,
                embedding=self.embeddings,
                documents=documents,
                metadatas=[doc.metadata for doc in documents]
            )
        else:
            logger.warning("No documents with embeddings found")
            
    async def get_relevant_content(
        self, 
        query: str, 
        subject: Optional[str] = None,
        grade_level: Optional[int] = None,
        k: int = 5
    ) -> List[dict]:
        """Retrieve relevant content based on query and filters."""
        if not self.vector_store:
            db = await get_db()
            contents = await db.contents_with_embeddings.find({}).to_list(length=1000)
            contents = [ContentWithEmbedding(**content) for content in contents]
            await self.initialize_vector_store(contents)
            
        if not self.vector_store:
            logger.error("Failed to initialize vector store")
            return []
            
        # Build filter based on parameters
        filter_dict = {}
        if subject:
            filter_dict["subject"] = subject
        if grade_level:
            filter_dict["grade_level"] = grade_level
            
        # Get similar documents
        docs_with_scores = self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter_dict if filter_dict else None
        )
        
        # Convert to response format
        results = []
        for doc, score in docs_with_scores:
            results.append({
                "id": doc.metadata["id"],
                "title": doc.metadata["title"],
                "subject": doc.metadata["subject"],
                "content_type": doc.metadata["content_type"],
                "difficulty_level": doc.metadata["difficulty_level"],
                "url": doc.metadata["url"],
                "relevance_score": float(score)
            })
            
        return results

# Singleton instance
content_retriever = None

async def get_content_retriever():
    """Get or create the content retriever singleton."""
    global content_retriever
    if content_retriever is None:
        content_retriever = ContentRetriever()
    return content_retriever

async def retrieve_relevant_content(
    student_profile: User,
    subject: Optional[str] = None,
    k: int = 5
) -> List[Content]:
    """Retrieve relevant content for a student."""
    # Get retriever
    retriever = await get_content_retriever()
    
    # Generate query based on student profile
    interests = ", ".join(student_profile.subjects_of_interest)
    grade = student_profile.grade_level if student_profile.grade_level else "unknown"
    learning_style = student_profile.learning_style.value if student_profile.learning_style else "unknown"
    
    query = f"Student in grade {grade} with {learning_style} learning style interested in {interests}"
    
    # Add subject if specified
    if subject:
        query += f" looking for content about {subject}"
    
    # Retrieve content
    content_dicts = await retriever.get_relevant_content(
        query=query,
        subject=subject,
        grade_level=student_profile.grade_level,
        k=k
    )
    
    # Fetch full content items from database
    db = await get_db()
    content_ids = [dict_item["id"] for dict_item in content_dicts]
    
    # Convert string IDs to ObjectIds
    object_ids = [ObjectId(id_str) for id_str in content_ids]
    
    # Query database for full content items
    contents = await db.contents.find({"_id": {"$in": object_ids}}).to_list(length=k)
    
    # Return contents
    return [Content(**content) for content in contents]
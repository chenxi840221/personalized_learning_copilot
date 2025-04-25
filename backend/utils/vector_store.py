# backend/utils/vector_store.py
"""
This module provides a simplified API for interacting with vector stores
by delegating the actual work to LangChain.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio

from config.settings import Settings
from rag.langchain_manager import get_langchain_manager

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LangChainVectorStore:
    """
    Vector store implementation that delegates to LangChain.
    Provides methods for adding, querying, and managing content.
    """
    def __init__(self):
        """Initialize the LangChain vector store wrapper."""
        self.langchain_manager = get_langchain_manager()
    
    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific content item by ID.
        
        Args:
            content_id: ID of the content to retrieve
            
        Returns:
            Content item or None if not found
        """
        try:
            # Search for the document by ID
            filter_str = f"id eq '{content_id}'"
            documents = await self.langchain_manager.search_documents("", filter=filter_str, k=1)
            
            if documents:
                # Convert LangChain document to dictionary
                doc = documents[0]
                return {
                    "id": content_id,
                    **doc.metadata,
                    "page_content": doc.page_content  # Use page_content instead of content
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting content: {e}")
            return None
    
    async def vector_search(
        self, 
        query_text: str, 
        filter_expression: Optional[str] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for content using vector similarity.
        
        Args:
            query_text: Text to search for
            filter_expression: Optional filter expression
            limit: Maximum number of results to return
            
        Returns:
            List of matching content items
        """
        try:
            # Use LangChain for vector search
            documents = await self.langchain_manager.search_documents(query_text, filter=filter_expression, k=limit)
            
            # Convert documents to dictionaries
            return [
                {
                    **doc.metadata,
                    "page_content": doc.page_content  # Use page_content instead of content
                }
                for doc in documents
            ]
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    async def add_content(self, content_item: Dict[str, Any]) -> bool:
        """
        Add content to the vector store.
        
        Args:
            content_item: Content item to add
            
        Returns:
            Success status
        """
        try:
            # Prepare text and metadata
            text = self._prepare_text_from_content(content_item)
            
            # Remove fields that aren't in Azure Search schema
            metadata = {k: v for k, v in content_item.items() 
                      if k != "page_content" and k != "content" and k != "embedding"}
            
            # Add to vector store
            return await self.langchain_manager.add_documents([text], [metadata])
            
        except Exception as e:
            logger.error(f"Error adding content to vector store: {e}")
            return False
    
    async def update_content(self, content_id: str, updated_fields: Dict[str, Any]) -> bool:
        """
        Update content in the vector store by deleting and re-adding it.
        
        Args:
            content_id: ID of the content to update
            updated_fields: Fields to update
            
        Returns:
            Success status
        """
        try:
            # Get existing content
            existing = await self.get_content(content_id)
            if not existing:
                return False
                
            # Update fields
            updated_content = {**existing, **updated_fields}
            
            # Delete and re-add
            # Note: LangChain doesn't have direct update capability
            # We would need to delete and re-add, but this is not directly
            # supported by the LangChain API. In a real implementation,
            # you'd need to use the underlying Azure Search API directly.
            
            # For now, just add the updated content
            return await self.add_content(updated_content)
            
        except Exception as e:
            logger.error(f"Error updating content: {e}")
            return False
    
    async def delete_content(self, content_id: str) -> bool:
        """
        Delete content from the vector store.
        
        Args:
            content_id: ID of the content to delete
            
        Returns:
            Success status
        """
        # Note: LangChain doesn't provide a direct way to delete documents
        # This would require using the underlying Azure Search API directly
        logger.warning("Delete operation not supported by LangChain API")
        return False
    
    async def filter_search(
        self,
        filter_expression: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for content using filter expressions.
        
        Args:
            filter_expression: Filter expression
            limit: Maximum number of results to return
            
        Returns:
            List of matching content items
        """
        try:
            # Use empty query with filter
            documents = await self.langchain_manager.search_documents("", filter=filter_expression, k=limit)
            
            # Convert documents to dictionaries
            return [
                {
                    **doc.metadata,
                    "page_content": doc.page_content  # Use page_content instead of content
                }
                for doc in documents
            ]
            
        except Exception as e:
            logger.error(f"Error in filter search: {e}")
            return []
    
    def _prepare_text_from_content(self, content_item: Dict[str, Any]) -> str:
        """
        Extract text from content item for embedding.
        
        Args:
            content_item: Content item
            
        Returns:
            Text for embedding
        """
        # Combine relevant fields
        text_parts = []
        
        # Add title and subject
        if "title" in content_item:
            text_parts.append(f"Title: {content_item['title']}")
        if "subject" in content_item:
            text_parts.append(f"Subject: {content_item['subject']}")
            
        # Add description
        if "description" in content_item:
            text_parts.append(f"Description: {content_item['description']}")
            
        # Add content text if available
        if "content" in content_item:
            text_parts.append(f"Content: {content_item['content']}")
        elif "page_content" in content_item:
            text_parts.append(f"Content: {content_item['page_content']}")
        elif "text" in content_item:
            text_parts.append(f"Content: {content_item['text']}")
            
        # Check metadata
        if "metadata" in content_item:
            metadata = content_item["metadata"]
            # Add content text or transcription if available
            if "content_text" in metadata:
                text_parts.append(f"Content: {metadata['content_text']}")
            if "transcription" in metadata:
                text_parts.append(f"Transcription: {metadata['transcription']}")
                
        # Also check flattened metadata fields
        if "metadata_content_text" in content_item:
            text_parts.append(f"Content: {content_item['metadata_content_text']}")
        if "metadata_transcription" in content_item:
            text_parts.append(f"Transcription: {content_item['metadata_transcription']}")
            
        # Join all parts
        return "\n\n".join(text_parts)

# Singleton instance
vector_store = None

async def get_vector_store():
    """Get or create vector store singleton."""
    global vector_store
    if vector_store is None:
        vector_store = LangChainVectorStore()
    return vector_store
# backend/services/azure_langchain_service.py
"""
Azure LangChain Service for the Personalized Learning Co-pilot.
This module provides high-level Azure-specific LangChain functionality.
"""

import logging
from typing import List, Dict, Any, Optional
import os
import sys
import json
from datetime import datetime

# Add backend directory to path to resolve imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import after path resolution
from models.user import User
from models.content import Content
from rag.azure_langchain_integration import get_azure_langchain
from utils.vector_store import get_vector_store

# Initialize logger
logger = logging.getLogger(__name__)

class AzureLangChainService:
    """
    Service for Azure-specific LangChain operations in the Personalized Learning Co-pilot.
    """
    
    def __init__(self):
        """Initialize the Azure LangChain service."""
        self.azure_langchain = None
    
    async def initialize(self):
        """Initialize Azure LangChain integration."""
        if not self.azure_langchain:
            self.azure_langchain = await get_azure_langchain()
    
    async def create_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> Dict[str, Any]:
        """
        Create a personalized learning plan for a student using Azure LangChain.
        
        Args:
            student: The student
            subject: Subject for the learning plan
            relevant_content: List of relevant content
            
        Returns:
            Generated learning plan
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            # Convert content objects to dictionaries for the prompt
            content_dicts = []
            for content in relevant_content:
                content_dict = {
                    "id": content.id,
                    "title": content.title,
                    "description": content.description,
                    "content_type": str(content.content_type),
                    "difficulty_level": str(content.difficulty_level),
                    "url": str(content.url)
                }
                content_dicts.append(content_dict)
            
            # Convert student to dictionary
            student_dict = {
                "full_name": student.full_name or student.username,
                "grade_level": student.grade_level,
                "learning_style": student.learning_style.value if student.learning_style else "mixed",
                "subjects_of_interest": student.subjects_of_interest
            }
            
            # Generate learning plan
            learning_plan = await self.azure_langchain.generate_learning_plan_with_rag(
                student_profile=student_dict,
                subject=subject,
                available_content=content_dicts
            )
            
            # Add metadata
            learning_plan["student_id"] = student.id
            learning_plan["created_at"] = datetime.utcnow().isoformat()
            learning_plan["updated_at"] = datetime.utcnow().isoformat()
            
            return learning_plan
            
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}")
            # Return a simple default plan
            return {
                "title": f"{subject} Learning Plan",
                "description": f"A learning plan for {subject}",
                "subject": subject,
                "student_id": student.id,
                "activities": []
            }
    
    async def answer_educational_question(
        self,
        question: str,
        student_grade: Optional[int] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer an educational question using Azure LangChain RAG.
        
        Args:
            question: The question to answer
            student_grade: Optional grade level for context
            subject: Optional subject for context
            
        Returns:
            Answer with sources
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            # Create system prompt with context
            system_prompt = "You are an educational assistant that provides accurate, helpful information."
            
            if student_grade:
                system_prompt += f" The student is in grade {student_grade}, so tailor your response appropriately."
                
            if subject:
                system_prompt += f" The question is about {subject}."
            
            # Create RAG chain
            rag_chain = await self.azure_langchain.create_rag_chain(system_prompt)
            
            # Generate answer
            answer = await rag_chain.ainvoke(question)
            
            # Get vector store for retrieving sources
            vector_store = await get_vector_store()
            
            # Build filter expression
            filter_expression = None
            if subject:
                filter_expression = f"subject eq '{subject}'"
                
            # Get relevant sources
            sources = await vector_store.vector_search(
                query_text=question,
                filter_expression=filter_expression,
                limit=3
            )
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "answer": f"I wasn't able to answer that question. Error: {str(e)}",
                "sources": []
            }
    
    async def search_educational_content(
        self,
        query: str,
        filter: Optional[str] = None,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for educational content using Azure Search.
        
        Args:
            query: Search query
            filter: Optional filter expression
            k: Maximum number of results
            
        Returns:
            List of content items
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            # Get vector store for content retrieval
            vector_store = await get_vector_store()
            
            # Perform search
            results = await vector_store.vector_search(
                query_text=query,
                filter_expression=filter,
                limit=k
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching educational content: {e}")
            return []
    
    async def index_content(self, content: Dict[str, Any]) -> bool:
        """
        Index content in Azure Search.
        
        Args:
            content: Content to index
            
        Returns:
            Success status
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            # Get vector store
            vector_store = await get_vector_store()
            
            # Add content to vector store
            success = await vector_store.add_content(content)
            
            return success
            
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return False
    
    async def create_conversation_chain(self):
        """
        Create a conversational RAG chain with memory.
        
        Returns:
            A conversational RAG chain
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            # Create conversational chain
            chain = await self.azure_langchain.create_conversational_rag_chain()
            
            return chain
            
        except Exception as e:
            logger.error(f"Error creating conversation chain: {e}")
            return None
    
    async def search_by_vector(self, query_embedding: List[float], filter: Optional[str] = None, k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for content using a vector embedding.
        
        Args:
            query_embedding: Vector embedding
            filter: Optional filter expression
            k: Maximum number of results
            
        Returns:
            List of content items
        """
        try:
            # Get vector store for search
            vector_store = await get_vector_store()
            
            # Use FAISS for similarity search if vector store supports it
            if hasattr(vector_store, "similarity_search_with_score_by_vector"):
                results = await vector_store.similarity_search_with_score_by_vector(
                    embedding=query_embedding,
                    k=k,
                    filter=filter
                )
                
                # Format results
                formatted_results = []
                for doc, score in results:
                    # Convert document to dictionary
                    result = {
                        "id": doc.metadata.get("id", ""),
                        "title": doc.metadata.get("title", ""),
                        "description": doc.metadata.get("description", ""),
                        "content_type": doc.metadata.get("content_type", ""),
                        "subject": doc.metadata.get("subject", ""),
                        "page_content": doc.page_content,
                        "score": score
                    }
                    formatted_results.append(result)
                    
                return formatted_results
            else:
                # Fall back to vector store's vector search
                return await vector_store.vector_search(
                    query_text="",  # Empty query because we're using embedding directly
                    filter_expression=filter,
                    limit=k
                )
                
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
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
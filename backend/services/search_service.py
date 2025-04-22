# services/search_service.py
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import Vector
from typing import List, Dict, Any, Optional
import json

from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

class AzureSearchService:
    """Service for managing data storage in Azure AI Search."""
    
    def __init__(self):
        """Initialize search service."""
        self.content_index_client = None
        self.users_index_client = None
        self.plans_index_client = None
        self.openai_adapter = None
        
    async def initialize(self):
        """Initialize Azure AI Search clients."""
        # Content index
        self.content_index_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.CONTENT_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        # Users index
        self.users_index_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.USERS_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        # Learning plans index
        self.plans_index_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.PLANS_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        # Initialize OpenAI adapter for embeddings
        self.openai_adapter = await get_openai_adapter()
        
    async def close(self):
        """Close Azure AI Search clients."""
        if self.content_index_client:
            await self.content_index_client.close()
        if self.users_index_client:
            await self.users_index_client.close()
        if self.plans_index_client:
            await self.plans_index_client.close()
            
    # User data methods
    async def get_user(self, user_id: str):
        """Get user from Azure AI Search."""
        try:
            user = await self.users_index_client.get_document(key=user_id)
            return user
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
            
    async def create_user(self, user_data: Dict[str, Any]):
        """Create user in Azure AI Search."""
        try:
            # Generate embedding for user profile
            profile_text = f"User {user_data['username']} is in grade {user_data.get('grade_level')} with interests in {', '.join(user_data.get('subjects_of_interest', []))}. Learning style: {user_data.get('learning_style')}"
            embedding = await self.openai_adapter.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=profile_text
            )
            
            # Add embedding to user data
            user_data["embedding"] = embedding
            
            # Upload to search index
            result = await self.users_index_client.upload_documents(documents=[user_data])
            return user_data if result[0].succeeded else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
            
    # Learning plan methods
    async def create_learning_plan(self, plan_data: Dict[str, Any]):
        """Create learning plan in Azure AI Search."""
        try:
            # Generate embedding for plan content
            plan_text = f"{plan_data['title']} {plan_data['description']} for {plan_data['subject']}"
            embedding = await self.openai_adapter.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=plan_text
            )
            
            # Add embedding to plan data
            plan_data["embedding"] = embedding
            
            # Upload to search index
            result = await self.plans_index_client.upload_documents(documents=[plan_data])
            return plan_data if result[0].succeeded else None
        except Exception as e:
            print(f"Error creating learning plan: {e}")
            return None
            
    async def get_user_learning_plans(self, user_id: str):
        """Get learning plans for a user."""
        try:
            results = await self.plans_index_client.search(
                search_text="*",
                filter=f"student_id eq '{user_id}'",
                order_by=["created_at desc"],
                include_total_count=True
            )
            
            plans = []
            async for plan in results:
                plans.append(dict(plan))
                
            return plans
        except Exception as e:
            print(f"Error getting learning plans: {e}")
            return []
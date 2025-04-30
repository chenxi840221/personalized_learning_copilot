# services/search_service.py
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
# Vector is not available in this version of the SDK
# from azure.search.documents.models import Vector
from typing import List, Dict, Any, Optional
import json
import logging
import traceback
from datetime import datetime

from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class SearchService:
    """Service for interacting with Azure AI Search."""
    
    def __init__(self):
        self.search_clients = {}
    
    async def get_search_client(self, index_name: str) -> Optional[SearchClient]:
        """
        Get or create a search client for the specified index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            SearchClient for the index or None if not configured
        """
        if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
            logger.warning("Azure Search not configured")
            return None
            
        logger.info(f"Getting search client for index: {index_name}")
        
        if index_name not in self.search_clients:
            try:
                self.search_clients[index_name] = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=index_name,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                )
                logger.info(f"Created new search client for index: {index_name}")
            except Exception as e:
                logger.error(f"Error creating search client for index {index_name}: {e}")
                return None
        
        return self.search_clients[index_name]
        
    async def check_index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists in Azure Search.
        
        Args:
            index_name: Name of the index to check
            
        Returns:
            True if the index exists, False otherwise
        """
        if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
            logger.warning("Azure Search not configured")
            return False
            
        import aiohttp
        import json
        
        try:
            # Use the REST API to check if the index exists
            headers = {
                "api-key": settings.AZURE_SEARCH_KEY,
                "Content-Type": "application/json"
            }
            
            # Use aiohttp for the HTTP request
            async with aiohttp.ClientSession() as session:
                url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version=2023-07-01-Preview"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"Index {index_name} exists")
                        return True
                    elif response.status == 404:
                        logger.warning(f"Index {index_name} does not exist")
                        return False
                    else:
                        logger.error(f"Error checking if index {index_name} exists: {response.status}")
                        text = await response.text()
                        logger.error(f"Response: {text}")
                        return False
        except Exception as e:
            logger.error(f"Error checking if index {index_name} exists: {e}")
            return False
    
    async def search_documents(
        self,
        index_name: str,
        query: str,
        filter: Optional[str] = None,
        top: int = 10,
        skip: int = 0,
        select: Optional[str] = None,
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for documents in an index.
        
        Args:
            index_name: Name of the index
            query: Search query
            filter: Filter expression
            top: Maximum number of results
            skip: Number of results to skip
            select: Fields to include in results
            order_by: Order by expression
            
        Returns:
            List of matching documents
        """
        try:
            client = await self.get_search_client(index_name)
            if not client:
                logger.warning(f"No search client available for index {index_name}")
                return []
            
            # Build search options
            search_options = {
                "filter": filter,
                "top": top,
                "skip": skip,
                "include_total_count": True
            }
            
            if select:
                search_options["select"] = select.split(",")
            
            if order_by:
                search_options["order_by"] = order_by.split(",")
                
            logger.info(f"Searching index {index_name} with query: {query}")
            logger.info(f"Search options: {search_options}")
            
            # Execute search
            try:
                results = await client.search(query, **search_options)
                
                # Convert results to list of dictionaries
                documents = []
                total_count = 0
                
                async for result in results:
                    documents.append(dict(result))
                    
                # Try to get total count if available
                if hasattr(results, 'get_count'):
                    try:
                        total_count = await results.get_count()
                        logger.info(f"Total count from search: {total_count}")
                    except Exception as count_error:
                        logger.warning(f"Could not get total count: {count_error}")
                
                logger.info(f"Search returned {len(documents)} documents")
                return documents
                
            except Exception as search_error:
                logger.error(f"Error during search operation: {search_error}")
                
                # Check if the index exists
                exists = await self.check_index_exists(index_name)
                if not exists:
                    logger.warning(f"Index {index_name} does not exist. This might be why the search failed.")
                
                return []
            
        except Exception as e:
            logger.error(f"Error in search_documents: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def _prepare_document_for_indexing(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a document for indexing in Azure AI Search.
        
        Args:
            document: The document to prepare
            
        Returns:
            Prepared document
        """
        # Create a copy of the document
        cleaned_doc = document.copy()
        
        # List of fields that are not defined in the search index schema
        invalid_fields = ['_debug_info', 'metadata']
        
        # Remove fields that are not in the schema
        for field in invalid_fields:
            if field in cleaned_doc:
                del cleaned_doc[field]
        
        # Convert datetime objects to strings in format expected by Azure Search
        for key, value in list(document.items()):
            if isinstance(value, datetime):
                # Format as ISO 8601 with Z for UTC timezone
                cleaned_doc[key] = value.strftime("%Y-%m-%dT%H:%M:%SZ")
                
        # Make sure embedding is a simple list with no metadata
        if 'embedding' in cleaned_doc and isinstance(cleaned_doc['embedding'], list):
            # Keep the embedding vector as is
            pass
        elif 'embedding' in cleaned_doc and hasattr(cleaned_doc['embedding'], 'metadata'):
            # Extract just the embedding vector for Azure Search
            cleaned_doc['embedding'] = cleaned_doc['embedding'].get('vector', [])
            
        # Convert subjects to a format that works with the schema
        if 'subjects' in cleaned_doc and cleaned_doc['subjects'] is not None:
            # Make sure subjects field is a list of dicts with the expected keys
            subjects = cleaned_doc['subjects']
            
            if isinstance(subjects, list):
                for i, subj in enumerate(subjects):
                    # Make sure areas_for_improvement and strengths are lists
                    for field in ['areas_for_improvement', 'strengths']:
                        if field in subj and not isinstance(subj[field], list):
                            if subj[field] is None:
                                subj[field] = []
                            elif isinstance(subj[field], str):
                                subj[field] = [subj[field]]
                            else:
                                subj[field] = []
        
        # Ensure encrypted_fields is a string
        if 'encrypted_fields' in cleaned_doc and not isinstance(cleaned_doc['encrypted_fields'], str):
            try:
                cleaned_doc['encrypted_fields'] = json.dumps(cleaned_doc['encrypted_fields'])
            except (TypeError, ValueError):
                # If it can't be serialized, set it to an empty JSON object
                cleaned_doc['encrypted_fields'] = '{}'
                
        # Log what we're about to index    
        logger.info(f"Prepared document for indexing: ID={cleaned_doc.get('id')}")
                
        return cleaned_doc
        
    async def index_document(
        self,
        index_name: str,
        document: Dict[str, Any]
    ) -> bool:
        """
        Index a document in Azure AI Search.
        
        Args:
            index_name: Name of the index
            document: Document to index
            
        Returns:
            Success status
        """
        try:
            client = await self.get_search_client(index_name)
            if not client:
                logger.warning(f"No search client available for index {index_name}")
                return False
                
            # Prepare the document for indexing
            try:
                prepared_doc = self._prepare_document_for_indexing(document)
                logger.info(f"Document prepared for indexing with ID: {prepared_doc.get('id')}")
            except Exception as prep_err:
                logger.error(f"Error preparing document for indexing: {prep_err}")
                logger.error(traceback.format_exc())
                return False
            
            # Upload the document
            try:
                result = await client.upload_documents(documents=[prepared_doc])
                
                # Check if the operation was successful
                is_success = result[0].succeeded
                if is_success:
                    logger.info(f"Successfully indexed document with ID: {prepared_doc.get('id')}")
                else:
                    logger.error(f"Failed to index document: {result[0].error_message}")
                
                return is_success
            except Exception as upload_err:
                logger.error(f"Error uploading document to search index: {upload_err}")
                logger.error(traceback.format_exc())
                
                # Check if this is a schema mismatch issue
                error_msg = str(upload_err)
                if "property" in error_msg and "does not exist" in error_msg:
                    # Try to extract the problematic field name
                    import re
                    field_match = re.search(r"property '([^']+)'", error_msg)
                    if field_match:
                        field_name = field_match.group(1)
                        logger.error(f"Schema mismatch for field: {field_name}")
                        
                return False
            
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def delete_document(
        self,
        index_name: str,
        document_id: str
    ) -> bool:
        """
        Delete a document from Azure AI Search.
        
        Args:
            index_name: Name of the index
            document_id: ID of the document to delete
            
        Returns:
            Success status
        """
        try:
            client = await self.get_search_client(index_name)
            if not client:
                return False
            
            # Delete the document
            result = await client.delete_documents(documents=[{"id": document_id}])
            
            # Check if the operation was successful
            return result[0].succeeded
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    async def close(self):
        """Close all search clients."""
        for client in self.search_clients.values():
            await client.close()

# Singleton instance
search_service = None

async def get_search_service():
    """Get or create search service singleton."""
    global search_service
    if search_service is None:
        search_service = SearchService()
    return search_service

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
        try:
            # Validate Azure Search configurations
            if not (settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY):
                logger.warning("Azure Search not configured. Search functionality will be disabled.")
                return False
            
            # Content index
            if settings.CONTENT_INDEX_NAME:
                self.content_index_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.CONTENT_INDEX_NAME,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                )
                logger.info(f"Initialized content index client for {settings.CONTENT_INDEX_NAME}")
            
            # Users index
            if settings.USERS_INDEX_NAME:
                self.users_index_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.USERS_INDEX_NAME,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                )
                logger.info(f"Initialized users index client for {settings.USERS_INDEX_NAME}")
            
            # Learning plans index
            if settings.PLANS_INDEX_NAME:
                self.plans_index_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.PLANS_INDEX_NAME,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                )
                logger.info(f"Initialized plans index client for {settings.PLANS_INDEX_NAME}")
            
            # Initialize OpenAI adapter for embeddings
            self.openai_adapter = await get_openai_adapter()
            
            return True
        except Exception as e:
            logger.error(f"Error initializing Azure Search: {e}")
            return False
        
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
        if not self.users_index_client:
            logger.warning("Users index client not initialized. Cannot get user.")
            return None
            
        try:
            user = await self.users_index_client.get_document(key=user_id)
            return user
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
            
    async def create_user(self, user_data: Dict[str, Any]):
        """Create user in Azure AI Search."""
        if not self.users_index_client:
            logger.warning("Users index client not initialized. Cannot create user.")
            return user_data  # Return the data anyway so the app can continue
            
        try:
            # Generate embedding for user profile if OpenAI is available
            if self.openai_adapter and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
                try:
                    profile_text = f"User {user_data['username']} is in grade {user_data.get('grade_level')} with interests in {', '.join(user_data.get('subjects_of_interest', []))}. Learning style: {user_data.get('learning_style')}"
                    embedding = await self.openai_adapter.create_embedding(
                        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                        text=profile_text
                    )
                    # Add embedding to user data
                    user_data["embedding"] = embedding
                except Exception as e:
                    logger.warning(f"Error generating embedding for user: {e}")
            
            # Upload to search index
            result = await self.users_index_client.upload_documents(documents=[user_data])
            return user_data if result[0].succeeded else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return user_data  # Return the data anyway so the app can continue
            
    # Learning plan methods
    async def create_learning_plan(self, plan_data: Dict[str, Any]):
        """Create learning plan in Azure AI Search."""
        if not self.plans_index_client:
            logger.warning("Plans index client not initialized. Learning plan will not be indexed.")
            return plan_data  # Return the data anyway so the app can continue
            
        try:
            # Generate embedding for plan content if OpenAI is available
            if self.openai_adapter and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
                try:
                    plan_text = f"{plan_data['title']} {plan_data['description']} for {plan_data['subject']}"
                    embedding = await self.openai_adapter.create_embedding(
                        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                        text=plan_text
                    )
                    # Add embedding to plan data
                    plan_data["embedding"] = embedding
                except Exception as e:
                    logger.warning(f"Error generating embedding for learning plan: {e}")
            
            # Upload to search index
            result = await self.plans_index_client.upload_documents(documents=[plan_data])
            return plan_data if result[0].succeeded else None
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}")
            return plan_data  # Return the data anyway so the app can continue
            
    async def get_user_learning_plans(self, user_id: str):
        """Get learning plans for a user."""
        if not self.plans_index_client:
            logger.warning("Plans index client not initialized. Cannot retrieve learning plans.")
            return []
            
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
            logger.error(f"Error getting learning plans: {e}")
            return []
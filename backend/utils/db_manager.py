import logging
import asyncio
from typing import Optional, Dict, List, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import IndexDocumentsResult
import uuid
import json
from datetime import datetime
import httpx
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Search clients for different indexes
search_clients = {}

async def init_db():
    """Initialize connection to Azure Cognitive Search."""
    global search_clients
    try:
        # Define indexes
        indexes = {
            "users": "users-index",
            "contents": "contents-index",
            "learning_plans": "learning-plans-index"
        }
        
        # Create search clients for each index
        for collection, index_name in indexes.items():
            search_clients[collection] = SearchClient(
                endpoint=settings.SEARCH_ENDPOINT,
                index_name=index_name,
                credential=AzureKeyCredential(settings.SEARCH_API_KEY)
            )
            
        logger.info("Successfully connected to Azure Cognitive Search")
        return search_clients
    except Exception as e:
        logger.error(f"Failed to initialize Azure Cognitive Search: {e}")
        raise

async def get_db():
    """Get database connection."""
    global search_clients
    if not search_clients:
        await init_db()
    return SearchDBProxy(search_clients)

async def close_db():
    """Close database connection."""
    global search_clients
    if search_clients:
        for client in search_clients.values():
            await client.close()
        search_clients = {}
        logger.info("Search connections closed")

# Async methods to ensure index existence using Azure Search REST API
async def ensure_indexes_exist():
    """Ensure all required indexes exist in Azure Cognitive Search."""
    try:
        # Define index schemas
        index_schemas = {
            "users-index": {
                "name": "users-index",
                "fields": [
                    {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
                    {"name": "username", "type": "Edm.String", "searchable": True, "filterable": True},
                    {"name": "email", "type": "Edm.String", "searchable": True, "filterable": True},
                    {"name": "full_name", "type": "Edm.String", "searchable": True},
                    {"name": "grade_level", "type": "Edm.Int32", "filterable": True},
                    {"name": "subjects_of_interest", "type": "Collection(Edm.String)", "searchable": True, "filterable": True},
                    {"name": "learning_style", "type": "Edm.String", "filterable": True},
                    {"name": "is_active", "type": "Edm.Boolean", "filterable": True},
                    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                    {"name": "hashed_password", "type": "Edm.String", "searchable": False}
                ]
            },
            "contents-index": {
                "name": "contents-index",
                "fields": [
                    {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
                    {"name": "title", "type": "Edm.String", "searchable": True},
                    {"name": "description", "type": "Edm.String", "searchable": True},
                    {"name": "content_type", "type": "Edm.String", "filterable": True},
                    {"name": "subject", "type": "Edm.String", "searchable": True, "filterable": True},
                    {"name": "topics", "type": "Collection(Edm.String)", "searchable": True, "filterable": True},
                    {"name": "url", "type": "Edm.String"},
                    {"name": "source", "type": "Edm.String", "filterable": True},
                    {"name": "difficulty_level", "type": "Edm.String", "filterable": True},
                    {"name": "grade_level", "type": "Collection(Edm.Int32)", "filterable": True},
                    {"name": "duration_minutes", "type": "Edm.Int32", "filterable": True},
                    {"name": "keywords", "type": "Collection(Edm.String)", "searchable": True},
                    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchConfiguration": "my-vector-config"}
                ]
            },
            "learning-plans-index": {
                "name": "learning-plans-index",
                "fields": [
                    {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
                    {"name": "student_id", "type": "Edm.String", "filterable": True},
                    {"name": "title", "type": "Edm.String", "searchable": True},
                    {"name": "description", "type": "Edm.String", "searchable": True},
                    {"name": "subject", "type": "Edm.String", "searchable": True, "filterable": True},
                    {"name": "topics", "type": "Collection(Edm.String)", "searchable": True, "filterable": True},
                    {"name": "activities", "type": "Edm.String", "searchable": True},  # Store as JSON string
                    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                    {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True},
                    {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True},
                    {"name": "status", "type": "Edm.String", "filterable": True},
                    {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True}
                ]
            }
        }
        
        # Define vector search configuration
        vector_search_config = {
            "name": "my-vector-config",
            "algorithms": "hnsw",
            "hnsw": {
                "m": 4,
                "efConstruction": 400,
                "efSearch": 500,
                "metric": "cosine"
            }
        }
        
        # Check if indexes exist, create them if they don't
        async with httpx.AsyncClient() as client:
            headers = {
                "Content-Type": "application/json",
                "api-key": settings.SEARCH_API_KEY
            }
            
            # Check/create each index
            for index_name, schema in index_schemas.items():
                # Check if index exists
                check_url = f"{settings.SEARCH_ENDPOINT}/indexes/{index_name}?api-version=2023-11-01"
                response = await client.get(check_url, headers=headers)
                
                if response.status_code == 404:
                    # Index doesn't exist, create it
                    create_url = f"{settings.SEARCH_ENDPOINT}/indexes?api-version=2023-11-01"
                    
                    # Add vector search config if required
                    if any("vectorSearchConfiguration" in field for field in schema["fields"]):
                        schema["vectorSearch"] = {
                            "algorithmConfigurations": [vector_search_config]
                        }
                    
                    response = await client.post(
                        create_url,
                        headers=headers,
                        json=schema
                    )
                    
                    if response.status_code not in (200, 201):
                        logger.error(f"Failed to create index {index_name}: {response.text}")
                        raise Exception(f"Failed to create index {index_name}")
                    
                    logger.info(f"Created index {index_name}")
                elif response.status_code != 200:
                    logger.error(f"Error checking index {index_name}: {response.text}")
                    raise Exception(f"Error checking index {index_name}")
                else:
                    logger.info(f"Index {index_name} already exists")
        
        logger.info("All indexes verified/created successfully")
        
    except Exception as e:
        logger.error(f"Error ensuring indexes exist: {e}")
        raise

class SearchDBProxy:
    """
    A proxy class that provides MongoDB-like interface 
    for Azure Cognitive Search.
    """
    def __init__(self, clients):
        self.clients = clients
        
    def __getattr__(self, name):
        if name in self.clients:
            return SearchCollectionProxy(self.clients[name], name)
        raise AttributeError(f"Collection {name} not found")

class SearchCollectionProxy:
    """
    A proxy class that wraps Azure Cognitive Search operations
    to match MongoDB interface.
    """
    def __init__(self, client, collection_name):
        self.client = client
        self.collection_name = collection_name
    
    async def find_one(self, query):
        """Find a single document by query."""
        filter_expr = self._build_filter(query)
        
        results = await self.client.search(
            search_text="*",
            filter=filter_expr,
            top=1,
            include_total_count=True
        )
        
        documents = []
        async for document in results:
            # Convert activities from JSON string to dict if it exists
            if "activities" in document and isinstance(document["activities"], str):
                document["activities"] = json.loads(document["activities"])
            documents.append(document)
            
        return documents[0] if documents else None
    
    async def find(self, query=None):
        """Find documents by query."""
        filter_expr = self._build_filter(query) if query else None
        
        return SearchQueryResultProxy(self.client, filter_expr)
    
    async def insert_one(self, document):
        """Insert a document."""
        # Generate ID if not present
        if "_id" not in document and "id" not in document:
            document_id = str(uuid.uuid4())
            document["id"] = document_id
            document["_id"] = document_id
        elif "_id" in document and "id" not in document:
            document["id"] = str(document["_id"])
        elif "id" in document and "_id" not in document:
            document["_id"] = document["id"]
        
        # Handle special field types
        # Convert dates to ISO format strings
        for key, value in document.items():
            if isinstance(value, datetime):
                document[key] = value.isoformat()
        
        # Special handling for learning plan activities - convert to JSON string
        if self.collection_name == "learning_plans" and "activities" in document and isinstance(document["activities"], list):
            document["activities"] = json.dumps(document["activities"])
        
        # Upload to Azure Search
        try:
            result = await self.client.upload_documents(documents=[document])
            return SearchInsertOneResult(document["id"])
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            raise
    
    async def update_one(self, query, update):
        """Update a document."""
        # Find the document first
        document = await self.find_one(query)
        
        if not document:
            return SearchUpdateResult(matched_count=0, modified_count=0)
        
        # Apply updates
        if "$set" in update:
            for key, value in update["$set"].items():
                document[key] = value
        
        if "$currentDate" in update:
            current_time = datetime.utcnow().isoformat()
            for key in update["$currentDate"]:
                document[key] = current_time
        
        # Special handling for learning plan activities - convert to JSON string
        if self.collection_name == "learning_plans" and "activities" in document and not isinstance(document["activities"], str):
            document["activities"] = json.dumps(document["activities"])
        
        # Update the document
        try:
            result = await self.client.upload_documents(documents=[document])
            return SearchUpdateResult(matched_count=1, modified_count=1)
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    async def count_documents(self, query=None):
        """Count documents matching a query."""
        filter_expr = self._build_filter(query) if query else None
        
        results = await self.client.search(
            search_text="*",
            filter=filter_expr,
            top=0,
            include_total_count=True
        )
        
        return results.get_count()
    
    async def create_index(self, keys, **kwargs):
        """Create index (not used with Azure Search as indexes are defined on service setup)."""
        logger.warning("create_index is not directly supported with Azure Search")
        return None
    
    def _build_filter(self, query):
        """Build an OData filter expression from a MongoDB-style query."""
        if not query:
            return None
        
        conditions = []
        for key, value in query.items():
            # Handle the _id field specially
            if key == "_id":
                conditions.append(f"id eq '{value}'")
            elif isinstance(value, str):
                conditions.append(f"{key} eq '{value}'")
            elif isinstance(value, bool):
                conditions.append(f"{key} eq {str(value).lower()}")
            elif isinstance(value, (int, float)):
                conditions.append(f"{key} eq {value}")
            elif isinstance(value, dict):
                # Handle operators
                for op, op_value in value.items():
                    if op == "$in":
                        if all(isinstance(v, str) for v in op_value):
                            # String values need quotes
                            values_str = ", ".join([f"'{v}'" for v in op_value])
                        else:
                            values_str = ", ".join([str(v) for v in op_value])
                        conditions.append(f"{key}/any(v: search.in(v, {values_str}))")
            else:
                conditions.append(f"{key} eq {value}")
        
        return " and ".join(conditions) if conditions else None

class SearchQueryResultProxy:
    """A proxy for Azure Search query results that mimics MongoDB cursor."""
    def __init__(self, client, filter_expr=None):
        self.client = client
        self.filter_expr = filter_expr
        
    async def to_list(self, length=None):
        """Convert search results to a list."""
        top = length if length else 1000  # Set reasonable default
        
        results = await self.client.search(
            search_text="*",
            filter=self.filter_expr,
            top=top
        )
        
        documents = []
        async for document in results:
            # Convert activities from JSON string to dict if it exists
            if "activities" in document and isinstance(document["activities"], str):
                document["activities"] = json.loads(document["activities"])
            documents.append(document)
            
        return documents

class SearchInsertOneResult:
    """A proxy for search insert result that mimics MongoDB's InsertOneResult."""
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class SearchUpdateResult:
    """A proxy for search update result that mimics MongoDB's UpdateResult."""
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count
import logging
from typing import Optional, Dict, List, Any
import uuid
import json
from datetime import datetime

# Initialize logger
logger = logging.getLogger(__name__)

# Mock database for development
mock_db = {
    "users": {},
    "contents": {},
    "learning_plans": {}
}

async def init_db():
    """Initialize connection to database."""
    logger.info("Mock database initialized")
    return mock_db

async def get_db():
    """Get database connection."""
    return MockDBProxy(mock_db)

async def close_db():
    """Close database connection."""
    logger.info("Mock database connection closed")

async def ensure_indexes_exist():
    """Ensure all required indexes exist."""
    logger.info("Mock indexes verified")

class MockDBProxy:
    """A proxy class that provides MongoDB-like interface for mock DB."""
    def __init__(self, db):
        self.db = db
        
    def __getattr__(self, name):
        if name in self.db:
            return MockCollectionProxy(self.db[name], name)
        raise AttributeError(f"Collection {name} not found")

class MockCollectionProxy:
    """A proxy class that wraps mock DB operations to match MongoDB interface."""
    def __init__(self, collection, collection_name):
        self.collection = collection
        self.collection_name = collection_name
    
    async def find_one(self, query):
        """Find a single document by query."""
        # Simple implementation for query by ID or username
        if "_id" in query:
            return self.collection.get(str(query["_id"]))
        elif "id" in query:
            return self.collection.get(str(query["id"]))
        elif "username" in query:
            # Search by username
            for doc in self.collection.values():
                if doc.get("username") == query["username"]:
                    return doc
        return None
    
    async def find(self, query=None):
        """Find documents by query."""
        return MockQueryResultProxy(self.collection, query)
    
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
        
        # Store in mock DB
        self.collection[str(document["id"])] = document
        return MockInsertOneResult(document["id"])
    
    async def update_one(self, query, update):
        """Update a document."""
        # Find the document first
        doc_id = None
        if "_id" in query:
            doc_id = str(query["_id"])
        elif "id" in query:
            doc_id = str(query["id"])
        
        if not doc_id or doc_id not in self.collection:
            return MockUpdateResult(matched_count=0, modified_count=0)
        
        # Apply updates
        document = self.collection[doc_id]
        if "$set" in update:
            for key, value in update["$set"].items():
                document[key] = value
        
        if "$currentDate" in update:
            current_time = datetime.utcnow().isoformat()
            for key in update["$currentDate"]:
                document[key] = current_time
        
        # Update in mock DB
        self.collection[doc_id] = document
        return MockUpdateResult(matched_count=1, modified_count=1)
    
    async def count_documents(self, query=None):
        """Count documents matching a query."""
        if not query:
            return len(self.collection)
        
        count = 0
        for doc in self.collection.values():
            matches = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    matches = False
                    break
            if matches:
                count += 1
        
        return count

class MockQueryResultProxy:
    """A proxy for mock query results that mimics MongoDB cursor."""
    def __init__(self, collection, query=None):
        self.collection = collection
        self.query = query
        
    async def to_list(self, length=None):
        """Convert query results to a list."""
        results = []
        
        # Apply query filters if provided
        if self.query:
            for doc in self.collection.values():
                matches = True
                for key, value in self.query.items():
                    if key not in doc or doc[key] != value:
                        matches = False
                        break
                if matches:
                    results.append(doc)
        else:
            results = list(self.collection.values())
        
        # Apply length limit if provided
        if length and len(results) > length:
            results = results[:length]
            
        return results

class MockInsertOneResult:
    """A proxy for mock insert result that mimics MongoDB's InsertOneResult."""
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class MockUpdateResult:
    """A proxy for mock update result that mimics MongoDB's UpdateResult."""
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count

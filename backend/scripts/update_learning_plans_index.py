#!/usr/bin/env python3
"""Update the learning-plans index with chunking fields.

This script updates the learning-plans index to include the 
activities_chunking field and dynamically create fields for week chunks.
"""
from __future__ import annotations

import asyncio
import logging
import os
import json
import aiohttp
import sys
from typing import List, Dict, Any, Optional

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)  # Add backend to path
sys.path.insert(0, project_root)  # Add project root to path

from dotenv import load_dotenv

###############################################################################
# Environment & logging                                                       #
###############################################################################

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Get settings from environment or settings module
from config.settings import Settings
settings = Settings()

AZURE_SEARCH_ENDPOINT = settings.AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_KEY = settings.AZURE_SEARCH_KEY
API_VERSION = "2024-03-01-Preview"  # Using latest preview API

# Index name
PLANS_INDEX_NAME = "learning-plans"

###############################################################################
# Field definitions                                                           #
###############################################################################

# Learning Plans index fields with chunk support
PLANS_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "student_id", "type": "Edm.String", "filterable": True},
    {"name": "title", "type": "Edm.String", "searchable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    # Store activities as JSON string
    {"name": "activities_json", "type": "Edm.String"},
    # Chunking metadata fields
    {"name": "activities_chunking", "type": "Edm.String", "filterable": True},
    {"name": "activities_weeks", "type": "Collection(Edm.Int32)", "filterable": True},
    # Week chunk fields for activities (one per week)
    {"name": "activities_week_1", "type": "Edm.String"},
    {"name": "activities_week_2", "type": "Edm.String"},
    {"name": "activities_week_3", "type": "Edm.String"},
    {"name": "activities_week_4", "type": "Edm.String"},
    {"name": "activities_week_5", "type": "Edm.String"},
    {"name": "activities_week_6", "type": "Edm.String"},
    {"name": "activities_week_7", "type": "Edm.String"},
    {"name": "activities_week_8", "type": "Edm.String"},
    # Base fields
    {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "metadata", "type": "Edm.String"},
    {"name": "page_content", "type": "Edm.String", "searchable": True},
    {"name": "owner_id", "type": "Edm.String", "filterable": True},
    
    # Vector field for embeddings
    {
        "name": "embedding", 
        "type": "Collection(Edm.Single)", 
        "searchable": True, 
        "dimensions": 1536, 
        "vectorSearchProfile": "default-profile"
    }
]

###############################################################################
# Helpers                                                                     #
###############################################################################

async def create_index(index_name: str, fields: List[Dict[str, Any]]) -> bool:
    """Create an index with the given name and fields."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    # Build the index definition
    index_def = {
        "name": index_name,
        "fields": fields,
        "vectorSearch": {
            "profiles": [
                {
                    "name": "default-profile",
                    "algorithm": "default-algorithm"
                }
            ],
            "algorithms": [
                {
                    "name": "default-algorithm",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500
                    }
                }
            ]
        }
    }
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Check if index exists
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if index_name in existing_indexes:
                        logger.info(f"Index '{index_name}' exists - retrieving to migrate data")
                        
                        # Get all documents from the index before deletion
                        documents = await get_all_documents(index_name)
                        
                        # Delete the existing index
                        logger.info(f"Deleting index '{index_name}'")
                        delete_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
                        async with session.delete(delete_url, headers=headers) as delete_response:
                            if delete_response.status == 204:
                                logger.info(f"Successfully deleted index '{index_name}'")
                            else:
                                error_text = await delete_response.text()
                                logger.error(f"Failed to delete index: {delete_response.status} - {error_text}")
                                return False
            
            # Create the index
            create_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.post(create_url, headers=headers, json=index_def) as response:
                if response.status == 201:
                    logger.info(f"Successfully created index '{index_name}'")
                    
                    # Restore data if we have documents
                    if 'documents' in locals() and documents:
                        logger.info(f"Migrating {len(documents)} documents back to the index")
                        await restore_documents(index_name, documents)
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create index: {response.status} - {error_text}")
                    # Log the full request for debugging
                    logger.info(f"Request payload: {json.dumps(index_def)}")
                    return False
                
    except Exception as e:
        logger.error(f"Error in REST API call: {e}")
        return False

async def get_all_documents(index_name: str) -> List[Dict[str, Any]]:
    """Get all documents from an index."""
    documents = []
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Search for all documents (in batches)
            search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
            
            # First batch
            search_body = {
                "search": "*",
                "top": 1000,
                "skip": 0
            }
            
            # Get documents in batches of 1000
            has_more = True
            skip = 0
            
            while has_more:
                search_body["skip"] = skip
                
                async with session.post(search_url, headers=headers, json=search_body) as response:
                    if response.status == 200:
                        result = await response.json()
                        batch = result.get("value", [])
                        documents.extend(batch)
                        
                        logger.info(f"Retrieved {len(batch)} documents (skip={skip})")
                        
                        # Check if there might be more
                        if len(batch) < 1000:
                            has_more = False
                        else:
                            skip += 1000
                    else:
                        error_text = await response.text()
                        logger.error(f"Error retrieving documents: {response.status} - {error_text}")
                        has_more = False
                        
            return documents
    
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return []

async def restore_documents(index_name: str, documents: List[Dict[str, Any]]) -> bool:
    """Restore documents to an index."""
    if not documents:
        logger.info("No documents to restore")
        return True
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Process in batches of 100
            batch_size = 100
            success = True
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                logger.info(f"Indexing batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
                
                # Prepare documents for indexing
                migrated_batch = []
                for doc in batch:
                    # Check if we need to migrate activity data
                    if "activities_json" in doc and doc["activities_json"]:
                        # No chunking needed - just ensure all required fields exist
                        doc["activities_chunking"] = "none"
                        # Ensure all week fields are removed
                        for week in range(1, 9):
                            field = f"activities_week_{week}"
                            if field in doc:
                                del doc[field]
                    
                    # Migrate weekly chunked data from non-standard fields
                    for key in list(doc.keys()):
                        if key.startswith("activities_week_") and key not in [f"activities_week_{i}" for i in range(1, 9)]:
                            # Extract week number
                            try:
                                week_num = int(key.replace("activities_week_", ""))
                                if 1 <= week_num <= 8:
                                    # Keep the data but move to standard field
                                    doc[f"activities_week_{week_num}"] = doc[key]
                                    # Ensure chunking is set
                                    doc["activities_chunking"] = "weekly"
                                    
                                    # Record the week in activities_weeks if it doesn't exist
                                    if "activities_weeks" not in doc:
                                        doc["activities_weeks"] = [week_num]
                                    elif week_num not in doc["activities_weeks"]:
                                        doc["activities_weeks"].append(week_num)
                                        
                                # Clean up non-standard field
                                del doc[key]
                            except ValueError:
                                # Not a numeric week - skip
                                pass
                    
                    migrated_batch.append(doc)
                
                # Index the batch
                index_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/index?api-version={API_VERSION}"
                async with session.post(index_url, headers=headers, json={"value": migrated_batch}) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error indexing batch: {response.status} - {error_text}")
                        success = False
            
            return success
    
    except Exception as e:
        logger.error(f"Error restoring documents: {e}")
        return False

###############################################################################
# Main                                                                        #
###############################################################################

async def update_learning_plans_index() -> bool:
    """Update the learning plans index to support activity chunking."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
        
    try:
        logger.info(f"Updating learning plans index: {PLANS_INDEX_NAME}")
        success = await create_index(PLANS_INDEX_NAME, PLANS_FIELDS)
        
        if success:
            logger.info("🎉 Learning plans index updated successfully with chunking support")
            return True
        else:
            logger.error("Failed to update learning plans index")
            return False
    
    except Exception as e:
        logger.error(f"Error updating learning plans index: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(update_learning_plans_index())
#!/usr/bin/env python3
"""Create Azure AI Search indexes for the Personalized Learning Co‑pilot.

This script creates the necessary search indexes for LangChain integration
with Azure AI Search. It has been updated to work with the 2024-03-01-Preview API.
"""
from __future__ import annotations

import asyncio
import logging
import os
import json
import aiohttp
from typing import List, Dict, Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from dotenv import load_dotenv

###############################################################################
# Environment & logging                                                       #
###############################################################################

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")
API_VERSION = "2024-03-01-Preview"  # Updated to latest preview API

###############################################################################
# Helpers                                                                     #
###############################################################################

async def _create_index_with_rest(index_name: str, fields: List, vector_config: bool = True):
    """Create an index using direct REST API call."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    # Build the index definition
    index_def = {
        "name": index_name,
        "fields": fields
    }
    
    # Add vector search configuration if requested - SIMPLIFIED FORMAT for 2024-03-01-Preview
    if vector_config:
        index_def["vectorSearch"] = {
            "profiles": [
                {
                    "name": "default-profile",
                    "algorithm": "default-algorithm"
                }
            ],
            "algorithms": [
                {
                    "name": "default-algorithm",
                    "kind": "hnsw"
                }
            ]
        }
    
    # Check if index exists and delete if it does
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            # Check if index exists
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if index_name in existing_indexes:
                        logger.info(f"Index '{index_name}' exists – deleting")
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
                    logger.info(f"✅ Created index: {index_name}")
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

###############################################################################
# Field definitions                                                           #
###############################################################################

CONTENT_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "title", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "content_type", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "url", "type": "Edm.String"},
    {"name": "source", "type": "Edm.String", "filterable": True},
    {"name": "difficulty_level", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "grade_level", "type": "Collection(Edm.Int32)", "filterable": True, "facetable": True},
    {"name": "duration_minutes", "type": "Edm.Int32", "filterable": True, "facetable": True},
    {"name": "keywords", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    # Flattened metadata
    {"name": "metadata_content_text", "type": "Edm.String", "searchable": True},
    {"name": "metadata_transcription", "type": "Edm.String", "searchable": True},
    {"name": "metadata_thumbnail_url", "type": "Edm.String"},
    # This is the main field that will be used for text content
    {"name": "page_content", "type": "Edm.String", "searchable": True},
    # Vector field for embeddings - UPDATED FIELD CONFIGURATION
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

USER_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "username", "type": "Edm.String", "filterable": True},
    {"name": "full_name", "type": "Edm.String", "searchable": True},
    {"name": "email", "type": "Edm.String", "filterable": True},
    {"name": "grade_level", "type": "Edm.Int32", "filterable": True, "facetable": True},
    {"name": "learning_style", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "subjects_of_interest", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    # Vector field for embeddings - UPDATED FIELD CONFIGURATION
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

PLAN_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "student_id", "type": "Edm.String", "filterable": True},
    {"name": "title", "type": "Edm.String", "searchable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    # Activities complex collection
    {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True},
    # LangChain can work with page_content field 
    {"name": "page_content", "type": "Edm.String", "searchable": True},
    # Vector field for embeddings - UPDATED FIELD CONFIGURATION
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

###############################################################################
# Main                                                                        #
###############################################################################

async def main() -> bool:
    """Create all search indexes."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False

    try:
        # Create the indexes using direct REST API
        success1 = await _create_index_with_rest(CONTENT_INDEX_NAME, CONTENT_FIELDS)
        success2 = await _create_index_with_rest(USERS_INDEX_NAME, USER_FIELDS)
        success3 = await _create_index_with_rest(PLANS_INDEX_NAME, PLAN_FIELDS)
        
        if success1 and success2 and success3:
            logger.info("🎉 All indexes created successfully")
            return True
        else:
            logger.error("Failed to create all indexes")
            return False
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(main())
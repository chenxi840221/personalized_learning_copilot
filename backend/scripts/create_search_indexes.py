#!/usr/bin/env python3
"""Create Azure AI Search indexes for the Personalized Learning Co‑pilot.

This script creates the necessary search indexes for LangChain integration
with Azure AI Search. It has been simplified to avoid direct vector management
since LangChain handles vectors and embeddings for us.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import List

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
)
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

###############################################################################
# Helpers                                                                     #
###############################################################################

async def _create_index(client: SearchIndexClient, index_name: str, fields: List):
    """Create an index, deleting it first if it already exists."""
    # Check if index exists
    existing = [idx.name async for idx in client.list_indexes()]
    if index_name in existing:
        logger.info("Index '%s' exists – deleting", index_name)
        await client.delete_index(index_name)

    # Create index
    index = SearchIndex(name=index_name, fields=fields)
    await client.create_index(index)
    logger.info("✅ Created index: %s", index_name)

###############################################################################
# Field definitions - simplified since LangChain handles vectors              #
###############################################################################

CONTENT_FIELDS = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SearchableField(name="description", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SimpleField(name="content_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="subject", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="topics", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
    SimpleField(name="url", type=SearchFieldDataType.String),
    SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="difficulty_level", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="grade_level", type=SearchFieldDataType.Collection(SearchFieldDataType.Int32), filterable=True, facetable=True),
    SimpleField(name="duration_minutes", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
    SimpleField(name="keywords", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
    SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    # Flattened metadata
    SearchableField(name="metadata_content_text", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SearchableField(name="metadata_transcription", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SimpleField(name="metadata_thumbnail_url", type=SearchFieldDataType.String),
    # LangChain will create and manage the vector field
]

USER_FIELDS = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SimpleField(name="username", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="full_name", type=SearchFieldDataType.String),
    SimpleField(name="email", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="grade_level", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
    SimpleField(name="learning_style", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="subjects_of_interest", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
    SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    # LangChain will create and manage the vector field
]

PLAN_FIELDS = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SimpleField(name="student_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="title", type=SearchFieldDataType.String),
    SearchableField(name="description", type=SearchFieldDataType.String),
    SimpleField(name="subject", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="topics", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
    # Activities complex collection
    SimpleField(name="status", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="progress_percentage", type=SearchFieldDataType.Double, filterable=True, sortable=True),
    SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    SimpleField(name="start_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
    SimpleField(name="end_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
    # LangChain will create and manage the vector field
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
        # Initialize the search client
        client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_SEARCH_KEY))
        
        # Create the indexes
        await _create_index(client, CONTENT_INDEX_NAME, CONTENT_FIELDS)
        await _create_index(client, USERS_INDEX_NAME, USER_FIELDS)
        await _create_index(client, PLANS_INDEX_NAME, PLAN_FIELDS)
        
        # Close the client
        await client.close()
        
        logger.info("🎉 All indexes created successfully")
        logger.info("Note: Vector fields will be created by LangChain when data is first added")
        return True
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(main())
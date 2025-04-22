#!/usr/bin/env python3
"""
Create Azure AI Search Index for educational content.
"""

import asyncio
import logging
import sys
import os
import re
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField,
    VectorSearch,
    VectorSearchProfile,
    VectorSearchHnswAlgorithmConfiguration,
    VectorSearchHnswParameters
)

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Settings
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("search_index_setup")
settings = Settings()

async def create_search_index():
    """Create Azure AI Search index for educational content."""
    try:
        # Initialize the search index client
        client = SearchIndexClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        # Check if index already exists
        index_name = settings.AZURE_SEARCH_INDEX_NAME
        existing_indexes = [index.name async for index in client.list_indexes()]
        
        if index_name in existing_indexes:
            logger.warning(f"Index '{index_name}' already exists. Deleting and recreating.")
            await client.delete_index(index_name)
        
        # Define vector search configuration
        vector_search_config = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="embedding-profile",
                    algorithm_configuration_name="embedding-config"
                )
            ],
            algorithms=[
                VectorSearchHnswAlgorithmConfiguration(
                    name="embedding-config",
                    parameters=VectorSearchHnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine"
                    )
                )
            ]
        )
        
        # Define fields for the search index
        fields = [
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
            
            # Additional content details
            ComplexField(name="additional_content", fields=[
                SearchableField(name="transcript", type=SearchFieldDataType.String),
                SearchableField(name="full_text", type=SearchFieldDataType.String),
                SimpleField(name="additional_topics", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
                SimpleField(name="entities", type=SearchFieldDataType.Collection(SearchFieldDataType.String))
            ]),
            
            # Vector embedding field for semantic search
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,  # For text-embedding-ada-002
                vector_search_profile_name="embedding-profile"
            )
        ]
        
        # Create index
        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search_config)
        
        logger.info(f"Creating index '{index_name}'...")
        await client.create_index(index)
        logger.info(f"Index '{index_name}' created successfully.")
        
        # Close the client
        await client.close()
        
    except Exception as e:
        logger.error(f"Error creating search index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_search_index())
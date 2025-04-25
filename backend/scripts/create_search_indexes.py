#!/usr/bin/env python3
"""
Create Azure Search indexes for the Personalized Learning Co-pilot project.
This script creates the necessary vector-enabled indexes for content, users, and learning plans.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    HnswParameters
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")

print(f"Using search endpoint: {AZURE_SEARCH_ENDPOINT}")
print(f"Index names: {CONTENT_INDEX_NAME}, {USERS_INDEX_NAME}, {PLANS_INDEX_NAME}")

async def create_index(client, index_name, fields):
    try:
        existing_indexes = [index.name async for index in client.list_indexes()]
        if index_name in existing_indexes:
            print(f"Index '{index_name}' exists. Deleting...")
            await client.delete_index(index_name)

        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="embedding-profile",
                    algorithm_configuration_name="embedding-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="embedding-config",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine"
                    )
                )
            ]
        )

        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search
        )

        await client.create_index(index)
        print(f"✅ Created index: {index_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating {index_name}: {e}")
        return False

async def main():
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        print("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False

    print("Creating Azure Search indexes...")

    client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(AZURE_SEARCH_KEY)
    )

    try:
        content_fields = [
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
            ComplexField(name="metadata", fields=[
                SearchableField(name="content_text", type=SearchFieldDataType.String),
                SearchableField(name="transcription", type=SearchFieldDataType.String),
                SimpleField(name="thumbnail_url", type=SearchFieldDataType.String)
            ]),
            SearchableField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile="embedding-profile"
            )
        ]

        user_fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(name="username", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="full_name", type=SearchFieldDataType.String),
            SimpleField(name="email", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="grade_level", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
            SimpleField(name="learning_style", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="subjects_of_interest", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
            SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SearchableField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile="embedding-profile"
            )
        ]

        learning_plan_fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(name="student_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SimpleField(name="subject", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="topics", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
            ComplexField(name="activities", fields=[
                SimpleField(name="id", type=SearchFieldDataType.String),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="description", type=SearchFieldDataType.String),
                SimpleField(name="content_id", type=SearchFieldDataType.String),
                SimpleField(name="duration_minutes", type=SearchFieldDataType.Int32),
                SimpleField(name="order", type=SearchFieldDataType.Int32),
                SimpleField(name="status", type=SearchFieldDataType.String),
                SimpleField(name="completed_at", type=SearchFieldDataType.DateTimeOffset)
            ]),
            SimpleField(name="status", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="progress_percentage", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="start_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
            SimpleField(name="end_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
            SearchableField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile="embedding-profile"
            )
        ]

        content_index_created = await create_index(client, CONTENT_INDEX_NAME, content_fields)
        users_index_created = await create_index(client, USERS_INDEX_NAME, user_fields)
        plans_index_created = await create_index(client, PLANS_INDEX_NAME, learning_plan_fields)

        if content_index_created and users_index_created and plans_index_created:
            print("✅ Successfully created all indexes.")
            return True
        else:
            print("❌ Some indexes failed. Check above errors.")
            return False

    except Exception as e:
        print(f"Error creating indexes: {e}")
        return False
    finally:
        await client.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        exit(1)
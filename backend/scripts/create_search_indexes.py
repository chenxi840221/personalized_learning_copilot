# scripts/create_search_indexes.py
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Now we can import from the project
try:
    from config.settings import Settings
except ImportError:
    # Create a minimal Settings class if the import fails
    class Settings:
        def __init__(self):
            self.AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
            self.AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
            self.CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_CONTENT_INDEX", "educational-content")
            self.USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
            self.PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField
)

# Initialize settings
settings = Settings()

async def create_content_index():
    """Create search index for educational content."""
    client = SearchIndexClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )
    
    try:
        # Check if index exists
        index_name = settings.CONTENT_INDEX_NAME
        existing_indexes = [index.name async for index in client.list_indexes()]
        
        if index_name in existing_indexes:
            print(f"Index '{index_name}' already exists. Will recreate it.")
            await client.delete_index(index_name)
    except Exception as e:
        print(f"Error checking existing indexes: {e}")
    
    # Define fields for content index
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
        ComplexField(name="additional_content", fields=[
            SearchableField(name="transcript", type=SearchFieldDataType.String),
            SearchableField(name="full_text", type=SearchFieldDataType.String),
            SimpleField(name="additional_topics", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SimpleField(name="entities", type=SearchFieldDataType.Collection(SearchFieldDataType.String))
        ])
    ]
    
    # Add vector field if using Azure AI Search that supports it
    try:
        # This approach is for newer SDK versions
        fields.append(
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                dimensions=1536,
                vector_search_configuration="default"
            )
        )
    except Exception as e:
        print(f"Notice: Could not add vector field with modern syntax: {e}")
        print("Adding embedding field without vector configuration")
        # Fallback for older SDKs
        fields.append(
            SimpleField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single))
        )
    
    # Create index for content
    content_index = SearchIndex(
        name=settings.CONTENT_INDEX_NAME,
        fields=fields
    )
    
    try:
        await client.create_index(content_index)
        print(f"Created content index: {settings.CONTENT_INDEX_NAME}")
    except Exception as e:
        print(f"Error creating content index: {e}")
    
    await client.close()

async def create_users_index():
    """Create search index for user profiles."""
    client = SearchIndexClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )
    
    try:
        # Check if index exists
        index_name = settings.USERS_INDEX_NAME
        existing_indexes = [index.name async for index in client.list_indexes()]
        
        if index_name in existing_indexes:
            print(f"Index '{index_name}' already exists. Will recreate it.")
            await client.delete_index(index_name)
    except Exception as e:
        print(f"Error checking existing indexes: {e}")
    
    # Define fields for users index
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="ms_object_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="username", type=SearchFieldDataType.String),
        SearchableField(name="email", type=SearchFieldDataType.String),
        SearchableField(name="full_name", type=SearchFieldDataType.String),
        SimpleField(name="grade_level", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
        SimpleField(name="learning_style", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="subjects_of_interest", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
        SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True)
    ]
    
    # Add vector field if using Azure AI Search that supports it
    try:
        # This approach is for newer SDK versions
        fields.append(
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                dimensions=1536,
                vector_search_configuration="default"
            )
        )
    except Exception as e:
        print(f"Notice: Could not add vector field with modern syntax: {e}")
        print("Adding embedding field without vector configuration")
        # Fallback for older SDKs
        fields.append(
            SimpleField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single))
        )
    
    # Create index for users
    users_index = SearchIndex(
        name=settings.USERS_INDEX_NAME,
        fields=fields
    )
    
    try:
        await client.create_index(users_index)
        print(f"Created users index: {settings.USERS_INDEX_NAME}")
    except Exception as e:
        print(f"Error creating users index: {e}")
    
    await client.close()

async def create_learning_plans_index():
    """Create search index for learning plans."""
    client = SearchIndexClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )
    
    try:
        # Check if index exists
        index_name = settings.PLANS_INDEX_NAME
        existing_indexes = [index.name async for index in client.list_indexes()]
        
        if index_name in existing_indexes:
            print(f"Index '{index_name}' already exists. Will recreate it.")
            await client.delete_index(index_name)
    except Exception as e:
        print(f"Error checking existing indexes: {e}")
    
    # Define fields for learning plans index
    fields = [
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
        SimpleField(name="end_date", type=SearchFieldDataType.DateTimeOffset, filterable=True)
    ]
    
    # Add vector field if using Azure AI Search that supports it
    try:
        # This approach is for newer SDK versions
        fields.append(
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                dimensions=1536,
                vector_search_configuration="default"
            )
        )
    except Exception as e:
        print(f"Notice: Could not add vector field with modern syntax: {e}")
        print("Adding embedding field without vector configuration")
        # Fallback for older SDKs
        fields.append(
            SimpleField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single))
        )
    
    # Create index for learning plans
    plans_index = SearchIndex(
        name=settings.PLANS_INDEX_NAME,
        fields=fields
    )
    
    try:
        await client.create_index(plans_index)
        print(f"Created learning plans index: {settings.PLANS_INDEX_NAME}")
    except Exception as e:
        print(f"Error creating learning plans index: {e}")
    
    await client.close()

async def main():
    """Create all search indexes."""
    # Create content index
    await create_content_index()
    
    # Create users index
    await create_users_index()
    
    # Create learning plans index
    await create_learning_plans_index()

if __name__ == "__main__":
    # Update settings module to include the index names
    if not hasattr(settings, 'CONTENT_INDEX_NAME'):
        settings.CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_CONTENT_INDEX", "educational-content")
    if not hasattr(settings, 'USERS_INDEX_NAME'):
        settings.USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles") 
    if not hasattr(settings, 'PLANS_INDEX_NAME'):
        settings.PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")
    
    asyncio.run(main())
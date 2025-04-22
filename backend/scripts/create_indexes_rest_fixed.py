# scripts/create_indexes_rest_fixed.py
import asyncio
import os
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get settings from environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_CONTENT_INDEX", "educational-content")
USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")

print(f"Using search endpoint: {AZURE_SEARCH_ENDPOINT}")
print(f"Index names: {CONTENT_INDEX_NAME}, {USERS_INDEX_NAME}, {PLANS_INDEX_NAME}")

async def create_index(session, index_name, index_definition):
    """Create a search index using REST API."""
    url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version=2023-07-01-Preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_KEY
    }
    
    # Check if index exists
    try:
        async with session.get(url, headers=headers) as response:
            exists = response.status == 200
            if exists:
                print(f"Index '{index_name}' already exists. Deleting...")
                async with session.delete(url, headers=headers) as delete_response:
                    if delete_response.status == 204:
                        print(f"Successfully deleted index '{index_name}'")
                    else:
                        error_text = await delete_response.text()
                        print(f"Error deleting index: {delete_response.status} {error_text}")
                        return False
    except Exception as e:
        print(f"Error checking index existence: {e}")
    
    # Create index
    try:
        async with session.put(url, json=index_definition, headers=headers) as response:
            if response.status == 201:
                print(f"Successfully created index '{index_name}'")
                return True
            else:
                error_text = await response.text()
                print(f"Error creating index: {response.status} {error_text}")
                return False
    except Exception as e:
        print(f"Error creating index: {e}")
        return False

async def create_all_indexes():
    """Create all search indexes."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        print("Error: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY environment variables must be set")
        return

    # Define content index
    content_index = {
        "name": CONTENT_INDEX_NAME,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True, "analyzer": "en.microsoft"},
            {"name": "description", "type": "Edm.String", "searchable": True, "analyzer": "en.microsoft"},
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
            {
                "name": "additional_content",
                "type": "Edm.ComplexType",
                "fields": [
                    {"name": "transcript", "type": "Edm.String", "searchable": True},
                    {"name": "full_text", "type": "Edm.String", "searchable": True},
                    {"name": "additional_topics", "type": "Collection(Edm.String)"},
                    {"name": "entities", "type": "Collection(Edm.String)"}
                ]
            },
            {
                "name": "embedding",
                "type": "Collection(Edm.Single)",
                "dimensions": 1536,
                "vectorSearchConfiguration": "embedding-config"
            }
        ],
        "vectorSearch": {
            "profiles": [
                {
                    "name": "embedding-config",
                    "algorithm": "hnsw",
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            ]
        }
    }

    # Define users index
    users_index = {
        "name": USERS_INDEX_NAME,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "ms_object_id", "type": "Edm.String", "filterable": True},
            {"name": "username", "type": "Edm.String", "searchable": True},
            {"name": "email", "type": "Edm.String", "searchable": True},
            {"name": "full_name", "type": "Edm.String", "searchable": True},
            {"name": "grade_level", "type": "Edm.Int32", "filterable": True, "facetable": True},
            {"name": "learning_style", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "subjects_of_interest", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
            {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {
                "name": "embedding",
                "type": "Collection(Edm.Single)",
                "dimensions": 1536,
                "vectorSearchConfiguration": "embedding-config"
            }
        ],
        "vectorSearch": {
            "profiles": [
                {
                    "name": "embedding-config",
                    "algorithm": "hnsw",
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            ]
        }
    }

    # Define learning plans index
    plans_index = {
        "name": PLANS_INDEX_NAME,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "student_id", "type": "Edm.String", "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True},
            {"name": "description", "type": "Edm.String", "searchable": True},
            {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
            {
                "name": "activities",
                "type": "Collection(Edm.ComplexType)",
                "fields": [
                    {"name": "id", "type": "Edm.String"},
                    {"name": "title", "type": "Edm.String", "searchable": True},
                    {"name": "description", "type": "Edm.String", "searchable": True},
                    {"name": "content_id", "type": "Edm.String"},
                    {"name": "duration_minutes", "type": "Edm.Int32"},
                    {"name": "order", "type": "Edm.Int32"},
                    {"name": "status", "type": "Edm.String"},
                    {"name": "completed_at", "type": "Edm.DateTimeOffset"}
                ]
            },
            {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True},
            {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True},
            {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True},
            {
                "name": "embedding",
                "type": "Collection(Edm.Single)",
                "dimensions": 1536,
                "vectorSearchConfiguration": "embedding-config"
            }
        ],
        "vectorSearch": {
            "profiles": [
                {
                    "name": "embedding-config",
                    "algorithm": "hnsw",
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            ]
        }
    }

    print("Creating Azure AI Search indexes...")
    
    async with aiohttp.ClientSession() as session:
        # Create content index
        content_success = await create_index(session, CONTENT_INDEX_NAME, content_index)
        
        # Create users index
        users_success = await create_index(session, USERS_INDEX_NAME, users_index)
        
        # Create learning plans index
        plans_success = await create_index(session, PLANS_INDEX_NAME, plans_index)
        
        if content_success and users_success and plans_success:
            print("Successfully created all indexes!")
        else:
            print("Some indexes could not be created. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(create_all_indexes())
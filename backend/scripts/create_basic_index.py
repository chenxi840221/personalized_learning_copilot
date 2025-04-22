# scripts/create_basic_index.py
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

print(f"Using search endpoint: {AZURE_SEARCH_ENDPOINT}")
print(f"Index name: {CONTENT_INDEX_NAME}")

async def create_basic_index():
    """Create a very basic search index without vector search to check API compatibility."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        print("Error: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY environment variables must be set")
        return
    
    # Define URL and headers
    url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{CONTENT_INDEX_NAME}?api-version=2023-07-01-Preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_KEY
    }
    
    # Create a very basic index definition without vector search
    index_definition = {
        "name": CONTENT_INDEX_NAME,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True},
            {"name": "description", "type": "Edm.String", "searchable": True},
            {"name": "content_type", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        # Check if index exists
        try:
            async with session.get(url, headers=headers) as response:
                exists = response.status == 200
                if exists:
                    print(f"Index '{CONTENT_INDEX_NAME}' already exists. Deleting...")
                    async with session.delete(url, headers=headers) as delete_response:
                        if delete_response.status == 204:
                            print(f"Successfully deleted index '{CONTENT_INDEX_NAME}'")
                        else:
                            error_text = await delete_response.text()
                            print(f"Error deleting index: {delete_response.status} {error_text}")
                            return
        except Exception as e:
            print(f"Error checking index existence: {e}")
        
        # Create index
        try:
            async with session.put(url, json=index_definition, headers=headers) as response:
                if response.status == 201:
                    print(f"Successfully created basic index '{CONTENT_INDEX_NAME}'")
                    print("Now we need to check Azure Portal to see the correct schema for vector search")
                else:
                    error_text = await response.text()
                    print(f"Error creating index: {response.status} {error_text}")
        except Exception as e:
            print(f"Error creating index: {e}")

if __name__ == "__main__":
    asyncio.run(create_basic_index())
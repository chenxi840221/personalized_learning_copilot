# scripts/standalone_create_indexes_vector.py
import asyncio
import os
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
    HnswAlgorithmConfiguration,
    HnswParameters
)
from dotenv import load_dotenv

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_CONTENT_INDEX", "educational-content")
USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")

print(f"Using search endpoint: {AZURE_SEARCH_ENDPOINT}")
print(f"Index names: {CONTENT_INDEX_NAME}, {USERS_INDEX_NAME}, {PLANS_INDEX_NAME}")

VECTOR_FIELD = SearchField(
    name="embedding",
    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
    searchable=True,
    vector_search_dimensions=1536,
    vector_search_profile="embedding-profile"
)

VECTOR_SEARCH_CONFIG = VectorSearch(
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

async def create_index(index_name, fields):
    client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_SEARCH_KEY))

    try:
        existing_indexes = [index.name async for index in client.list_indexes()]
        if index_name in existing_indexes:
            print(f"Index '{index_name}' exists. Deleting...")
            await client.delete_index(index_name)
    except Exception as e:
        print(f"Error checking existing indexes: {e}")

    try:
        index = SearchIndex(name=index_name, fields=fields, vector_search=VECTOR_SEARCH_CONFIG)
        await client.create_index(index)
        print(f"✅ Created index: {index_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating {index_name}: {e}")
        return False
    finally:
        await client.close()

async def create_content_index():
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
        ]),
        VECTOR_FIELD
    ]
    return await create_index(CONTENT_INDEX_NAME, fields)

async def create_users_index():
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
        SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        VECTOR_FIELD
    ]
    return await create_index(USERS_INDEX_NAME, fields)

async def create_learning_plans_index():
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
        SimpleField(name="end_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
        VECTOR_FIELD
    ]
    return await create_index(PLANS_INDEX_NAME, fields)

async def main():
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        print("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return

    print("Creating Azure Search indexes...")
    results = await asyncio.gather(
        create_content_index(),
        create_users_index(),
        create_learning_plans_index()
    )

    if all(results):
        print("✅ Successfully created all indexes.")
    else:
        print("❌ Some indexes failed. Check above errors.")

if __name__ == "__main__":
    asyncio.run(main())

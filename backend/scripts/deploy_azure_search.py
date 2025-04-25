#!/usr/bin/env python3
# backend/scripts/deploy_azure_search.py

"""
Deploy script for Azure Search indexes.
This script:
1. Creates the required Azure Search indexes
2. Rebuilds the index with the correct schema
3. Provides utilities for initial data loading
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any, List

# Add the project root to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

# Import the index creation script
from scripts.create_search_indexes import main as create_indexes
from config.settings import Settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deploy_azure_search.log')
    ]
)

logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Sample data for initial index population
SAMPLE_CONTENT = [
    {
        "id": "sample-math-001",
        "title": "Introduction to Algebra",
        "description": "Learn the basics of algebraic expressions and equations",
        "content_type": "video",
        "subject": "Mathematics",
        "topics": ["Algebra", "Equations"],
        "url": "https://example.com/algebra-intro",
        "source": "ABC Education",
        "difficulty_level": "beginner",
        "grade_level": [7, 8, 9],
        "duration_minutes": 15,
        "keywords": ["algebra", "expressions", "equations", "mathematics", "introduction"],
        "page_content": """
            Algebra is the branch of mathematics dealing with symbols and the rules for manipulating these symbols.
            In elementary algebra, those symbols (today written as Latin and Greek letters) represent quantities without
            fixed values, known as variables. The study of algebra combines the efficient language and symbolism of mathematics
            with the problem solving tools that make it useful for modeling real-world situations.
            
            This introduction to algebra covers:
            - Understanding variables and constants
            - Working with algebraic expressions
            - Solving basic equations
            - Real-world applications of algebra
        """
    },
    {
        "id": "sample-science-001",
        "title": "The Solar System",
        "description": "Explore our solar system and learn about planets",
        "content_type": "interactive",
        "subject": "Science",
        "topics": ["Astronomy", "Solar System"],
        "url": "https://example.com/solar-system",
        "source": "ABC Education",
        "difficulty_level": "intermediate",
        "grade_level": [6, 7, 8],
        "duration_minutes": 25,
        "keywords": ["astronomy", "planets", "solar system", "space", "science"],
        "page_content": """
            The Solar System is the gravitationally bound system of the Sun and the objects that orbit it.
            It formed 4.6 billion years ago from the gravitational collapse of a giant interstellar molecular cloud.
            
            The vast majority of the system's mass is contained within the Sun, with most of the remaining mass
            contained in Jupiter. The four smaller inner planets, Mercury, Venus, Earth and Mars, are terrestrial
            planets, being primarily composed of rock and metal. The four outer planets are giant planets, being
            substantially more massive than the terrestrials.
            
            This interactive exploration covers:
            - The Sun and its properties
            - The inner terrestrial planets
            - The outer gas giants
            - Dwarf planets and other objects
            - Space exploration missions
        """
    }
]

async def load_sample_data():
    """Load sample data into the Azure Search index."""
    logger.info("Loading sample data into Azure Search...")
    
    try:
        # Import these at runtime to avoid circular imports
        from azure.search.documents.aio import SearchClient
        from azure.core.credentials import AzureKeyCredential
        
        # Initialize search client
        search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        # Format dates properly for Azure Search
        from datetime import datetime
        current_time = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        
        # Process and index sample content
        for sample in SAMPLE_CONTENT:
            # Ensure proper fields for Azure Search
            document = sample.copy()
            
            # Add timestamps if not present
            if "created_at" not in document:
                document["created_at"] = current_time
            if "updated_at" not in document:
                document["updated_at"] = current_time
                
            # Add empty embedding (will be filled by LangChain when searching)
            if "embedding" not in document:
                document["embedding"] = [0.0] * 1536  # Standard dimension for OpenAI embeddings
             
            # Add metadata fields from the page_content
            if "page_content" in document:
                document["metadata_content_text"] = document["page_content"]
            
            # Upload the document
            result = await search_client.upload_documents(documents=[document])
            
            if result[0].succeeded:
                logger.info(f"Successfully indexed sample content: {sample['title']}")
            else:
                logger.warning(f"Failed to index sample content: {sample['title']} - {result[0].error_message}")
        
        # Close the client
        await search_client.close()
                
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        return False
        
    logger.info("Sample data loading completed")
    return True

async def verify_index():
    """Verify that the index is working by performing a simple search."""
    logger.info("Verifying Azure Search index functionality...")
    
    try:
        # Import these at runtime to avoid circular imports
        from azure.search.documents.aio import SearchClient
        from azure.core.credentials import AzureKeyCredential
        
        # Initialize search client
        search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
            
        # Perform a simple search
        results = await search_client.search(
            search_text="introduction", 
            select=["id", "title", "subject"],
            top=5
        )
        
        # Check if we got any results
        count = 0
        async for result in results:
            count += 1
            logger.info(f"Found document: {result['title']}")
            
        # Close the client
        await search_client.close()
        
        if count > 0:
            logger.info(f"Index verification successful. Found {count} results.")
            return True
        else:
            logger.warning("Index verification returned no results")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying index: {e}")
        return False

async def deploy_search_indexes(load_data: bool = True, verify: bool = True):
    """
    Deploy Azure Search indexes and optionally load sample data.
    
    Args:
        load_data: Whether to load sample data
        verify: Whether to verify the index after deployment
        
    Returns:
        Success status
    """
    logger.info("Starting Azure Search index deployment")
    
    # First, create the indexes
    logger.info("Creating Azure Search indexes...")
    success = await create_indexes()
    
    if not success:
        logger.error("Failed to create Azure Search indexes")
        return False
        
    logger.info("Azure Search indexes created successfully")
    
    # Load sample data if requested
    if load_data:
        sample_success = await load_sample_data()
        if not sample_success:
            logger.warning("Sample data loading had issues, but continuing with deployment")
    
    # Verify index if requested
    if verify:
        verify_success = await verify_index()
        if not verify_success:
            logger.warning("Index verification had issues, deployment may not be fully functional")
    
    logger.info("Azure Search index deployment completed")
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Azure Search indexes")
    parser.add_argument("--no-sample-data", action="store_true", help="Skip loading sample data")
    parser.add_argument("--no-verify", action="store_true", help="Skip index verification")
    
    args = parser.parse_args()
    
    result = asyncio.run(deploy_search_indexes(
        load_data=not args.no_sample_data,
        verify=not args.no_verify
    ))
    
    if result:
        print("✅ Azure Search deployment completed successfully")
        sys.exit(0)
    else:
        print("❌ Azure Search deployment had errors")
        sys.exit(1)
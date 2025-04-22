#!/usr/bin/env python3
"""
Test script for Azure OpenAI integration.
This script tests the connection to Azure OpenAI and the embedding generation.
"""

import asyncio
import sys
import os
import logging
from azure.core.credentials import AzureKeyCredential
from azure.ai.openai import OpenAIClient

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Settings

# Initialize settings
settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_azure_openai():
    """Test Azure OpenAI connection and embedding generation."""
    try:
        logger.info("Testing Azure OpenAI connection...")
        
        # Initialize Azure OpenAI client
        client = OpenAIClient(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_OPENAI_KEY)
        )
        
        # Test text embedding
        logger.info("Testing text embedding...")
        embedding_text = "This is a test to verify Azure OpenAI text embeddings are working."
        
        embedding_response = client.get_embeddings(
            deployment_id=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=[embedding_text]
        )
        
        # Check if the response contains data
        if embedding_response.data and len(embedding_response.data) > 0:
            embedding = embedding_response.data[0].embedding
            embedding_length = len(embedding)
            logger.info(f"Successfully generated an embedding with dimension: {embedding_length}")
            logger.info(f"First 5 values: {embedding[:5]}")
        else:
            logger.error("Failed to generate embedding - no data in response")
            return False
        
        # Test completions
        logger.info("Testing text completion...")
        completion_prompt = "Generate a short paragraph about learning mathematics."
        
        completion_response = client.get_completions(
            deployment_id=settings.AZURE_OPENAI_DEPLOYMENT,
            prompt=completion_prompt,
            max_tokens=150
        )
        
        if completion_response.choices and len(completion_response.choices) > 0:
            completion_text = completion_response.choices[0].text.strip()
            logger.info(f"Successfully generated completion. Sample: {completion_text[:100]}...")
        else:
            logger.error("Failed to generate completion - no choices in response")
            return False
        
        logger.info("All Azure OpenAI tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error testing Azure OpenAI: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_azure_openai())
    sys.exit(0 if success else 1)
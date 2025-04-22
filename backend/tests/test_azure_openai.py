#!/usr/bin/env python3
"""
Test script for Azure OpenAI integration.
This script tests the connection to Azure OpenAI and the embedding generation.
"""

import asyncio
import sys
import os
import logging
from unittest.mock import patch, MagicMock, AsyncMock
import openai

# Add the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test settings
from tests.test_settings import settings
from rag.openai_adapter import OpenAIAdapter, get_openai_adapter
from tests.run_tests import AsyncioTestCase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestAzureOpenAI(AsyncioTestCase):
    """Test Azure OpenAI integration using the standard openai package."""
    
    def setUp(self):
        super().setUp()
        # Initialize the OpenAI adapter
        self.adapter = OpenAIAdapter()
        
        # Configure OpenAI for Azure
        openai.api_type = "azure"
        openai.api_version = settings.AZURE_OPENAI_API_VERSION
        openai.api_base = settings.get_openai_endpoint()
        openai.api_key = settings.get_openai_key()
    
    @patch('openai.Embedding.acreate')
    def test_embedding_generation(self, mock_acreate):
        """Test generating embeddings."""
        # Configure mock
        mock_response = {
            "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}],
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 8, "total_tokens": 8}
        }
        mock_acreate.return_value = mock_response
        
        # Test embedding generation
        result = self.run_async(self.adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text="This is a test."
        ))
        
        # Assertions
        mock_acreate.assert_called_once()
        self.assertEqual(result, [0.1, 0.2, 0.3, 0.4])
    
    @patch('openai.ChatCompletion.acreate')
    def test_chat_completion(self, mock_acreate):
        """Test chat completion."""
        # Configure mock
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response about mathematics."
                    },
                    "finish_reason": "stop",
                    "index": 0
                }
            ]
        }
        mock_acreate.return_value = mock_response
        
        # Test parameters
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about mathematics."}
        ]
        
        # Test chat completion
        result = self.run_async(self.adapter.create_chat_completion(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0.7
        ))
        
        # Assertions
        mock_acreate.assert_called_once()
        self.assertIn("choices", result)
        self.assertEqual(result["choices"][0]["message"]["content"], "This is a test response about mathematics.")
    
    @patch('rag.openai_adapter.OpenAIAdapter')
    def test_get_openai_adapter(self, mock_adapter_class):
        """Test the singleton pattern for the OpenAI adapter."""
        # Configure mock
        mock_instance = MagicMock()
        mock_adapter_class.return_value = mock_instance
        
        # Call function twice to verify singleton behavior
        adapter1 = self.run_async(get_openai_adapter())
        adapter2 = self.run_async(get_openai_adapter())
        
        # Assertions
        mock_adapter_class.assert_called_once()  # Constructor should be called only once
        self.assertEqual(adapter1, adapter2)  # Should return the same instance

if __name__ == "__main__":
    unittest.main()
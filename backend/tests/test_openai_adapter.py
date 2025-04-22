import unittest
import asyncio
from unittest.mock import patch, MagicMock
import json
import sys
import os
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.openai_adapter import OpenAIAdapter, get_openai_adapter


class TestOpenAIAdapter(unittest.TestCase):
    """Test the OpenAI adapter with mocked API responses."""

    def setUp(self):
        """Set up test case."""
        self.adapter = OpenAIAdapter()
        # Reset the singleton
        import rag.openai_adapter
        rag.openai_adapter.openai_adapter = None
    
    @patch('openai.ChatCompletion.acreate')
    async def test_create_chat_completion(self, mock_acreate):
        """Test creating a chat completion."""
        # Configure the mock
        mock_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "gpt-4",
            "usage": {
                "prompt_tokens": 13,
                "completion_tokens": 7,
                "total_tokens": 20
            },
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response."
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
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Run the test
        result = await self.adapter.create_chat_completion(
            model="test-model",
            messages=messages,
            temperature=0.7
        )
        
        # Assertions
        mock_acreate.assert_called_once()
        self.assertEqual(result, mock_response)
        self.assertEqual(result["choices"][0]["message"]["content"], "This is a test response.")
    
    @patch('openai.Embedding.acreate')
    async def test_create_embedding(self, mock_acreate):
        """Test creating embeddings."""
        # Configure the mock
        mock_response = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3, 0.4],
                    "index": 0
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {
                "prompt_tokens": 8,
                "total_tokens": 8
            }
        }
        mock_acreate.return_value = mock_response
        
        # Run the test
        result = await self.adapter.create_embedding(
            model="test-embedding-model",
            text="This is a test."
        )
        
        # Assertions
        mock_acreate.assert_called_once()
        self.assertEqual(result, [0.1, 0.2, 0.3, 0.4])
    
    @patch('rag.openai_adapter.OpenAIAdapter')
    def test_get_openai_adapter(self, mock_adapter_class):
        """Test getting the OpenAI adapter singleton."""
        # Configure the mock
        mock_instance = MagicMock()
        mock_adapter_class.return_value = mock_instance
        
        # Call function twice to verify singleton behavior
        adapter1 = asyncio.run(get_openai_adapter())
        adapter2 = asyncio.run(get_openai_adapter())
        
        # Assertions
        mock_adapter_class.assert_called_once()  # Constructor should be called only once
        self.assertEqual(adapter1, adapter2)  # Should return the same instance
    
    @patch('openai.ChatCompletion.acreate')
    async def test_chat_completion_with_error(self, mock_acreate):
        """Test handling of errors during chat completion."""
        # Configure the mock to raise an exception
        mock_acreate.side_effect = Exception("Test error")
        
        # Test parameters
        messages = [{"role": "user", "content": "Hello"}]
        
        # Run the test and expect an exception
        with self.assertRaises(Exception):
            await self.adapter.create_chat_completion(
                model="test-model",
                messages=messages
            )
    
    @patch('openai.ChatCompletion.acreate')
    async def test_chat_completion_with_response_format(self, mock_acreate):
        """Test creating a chat completion with response_format."""
        # Configure the mock
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"answer": "This is a JSON response"}'
                    },
                    "index": 0
                }
            ]
        }
        mock_acreate.return_value = mock_response
        
        # Test parameters
        messages = [{"role": "user", "content": "Respond in JSON"}]
        
        # Run the test - we modified the adapter to always include response_format if provided
        result = await self.adapter.create_chat_completion(
            model="test-model",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        # Check that response_format was included in the API call
        kwargs = mock_acreate.call_args.kwargs
        self.assertIn("response_format", kwargs)
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
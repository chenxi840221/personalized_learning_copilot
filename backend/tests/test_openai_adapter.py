import unittest
from unittest.mock import patch, MagicMock
<<<<<<< HEAD
import json
=======
>>>>>>> dc2c151 (b)
import sys
import os
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

<<<<<<< HEAD
from rag.openai_adapter import OpenAIAdapter, get_openai_adapter
from config.settings import Settings
from tests.run_tests import AsyncioTestCase

=======
# Import the async test base with improved mocking
from tests.async_test_base import AsyncioTestCase, create_async_mock, AsyncMock

# Import test settings
from tests.test_settings import settings, USE_REAL_SERVICES
>>>>>>> dc2c151 (b)

class TestOpenAIAdapter(AsyncioTestCase):
    """Test the OpenAI adapter with mocked API responses."""

    def setUp(self):
        """Set up test case."""
        super().setUp()
<<<<<<< HEAD
        self.adapter = OpenAIAdapter()
=======
        
        # Patch settings in the module
        self.settings_patcher = patch('rag.openai_adapter.settings', settings)
        self.settings_patcher.start()
        
        # Import after patching settings
        from rag.openai_adapter import OpenAIAdapter
        self.adapter = OpenAIAdapter()
        
>>>>>>> dc2c151 (b)
        # Reset the singleton
        import rag.openai_adapter
        rag.openai_adapter.openai_adapter = None
    
<<<<<<< HEAD
    @patch('openai.ChatCompletion.acreate')
    def test_create_chat_completion(self, mock_acreate):
        """Test creating a chat completion."""
        # Configure the mock
=======
    def tearDown(self):
        """Clean up patchers."""
        self.settings_patcher.stop()
        super().tearDown()
    
    @patch('openai.ChatCompletion.acreate')
    def test_create_chat_completion(self, mock_acreate):
        """Test creating a chat completion."""
        # Configure the mock with a properly awaitable response
>>>>>>> dc2c151 (b)
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
<<<<<<< HEAD
        mock_acreate.return_value = mock_response
=======
        # Use create_async_mock to make it awaitable
        mock_acreate.return_value = create_async_mock(mock_response)
>>>>>>> dc2c151 (b)
        
        # Test parameters
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
<<<<<<< HEAD
        # Run the test
=======
        # Run the test using the async test case
>>>>>>> dc2c151 (b)
        result = self.run_async(self.adapter.create_chat_completion(
            model="test-model",
            messages=messages,
            temperature=0.7
        ))
        
        # Assertions
        mock_acreate.assert_called_once()
        self.assertEqual(result, mock_response)
        self.assertEqual(result["choices"][0]["message"]["content"], "This is a test response.")
    
    @patch('openai.Embedding.acreate')
    def test_create_embedding(self, mock_acreate):
        """Test creating embeddings."""
<<<<<<< HEAD
        # Configure the mock
=======
        # Configure the mock with a properly awaitable response
>>>>>>> dc2c151 (b)
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
<<<<<<< HEAD
        mock_acreate.return_value = mock_response
        
        # Run the test
=======
        # Use create_async_mock to make it awaitable
        mock_acreate.return_value = create_async_mock(mock_response)
        
        # Run the test using the async test case
>>>>>>> dc2c151 (b)
        result = self.run_async(self.adapter.create_embedding(
            model="test-embedding-model",
            text="This is a test."
        ))
        
        # Assertions
        mock_acreate.assert_called_once()
        self.assertEqual(result, [0.1, 0.2, 0.3, 0.4])
    
    @patch('rag.openai_adapter.OpenAIAdapter')
    def test_get_openai_adapter(self, mock_adapter_class):
        """Test getting the OpenAI adapter singleton."""
        # Configure the mock
        mock_instance = MagicMock()
        mock_adapter_class.return_value = mock_instance
        
<<<<<<< HEAD
        # Call function twice to verify singleton behavior
        adapter1 = self.run_async(get_openai_adapter())
        adapter2 = self.run_async(get_openai_adapter())
        
        # Assertions
        mock_adapter_class.assert_called_once()  # Constructor should be called only once
        self.assertEqual(adapter1, adapter2)  # Should return the same instance
=======
        # Import after patching
        from rag.openai_adapter import get_openai_adapter
        
        # Create an awaitable mock for the get_openai_adapter function
        async def mock_get_adapter():
            return mock_instance
            
        # Patch the get_openai_adapter function
        with patch('rag.openai_adapter.get_openai_adapter', mock_get_adapter):
            # Call function twice to verify singleton behavior
            adapter1 = self.run_async(get_openai_adapter())
            adapter2 = self.run_async(get_openai_adapter())
            
            # Assertions
            self.assertEqual(adapter1, adapter2)  # Should return the same instance
>>>>>>> dc2c151 (b)
    
    @patch('openai.ChatCompletion.acreate')
    def test_chat_completion_with_error(self, mock_acreate):
        """Test handling of errors during chat completion."""
<<<<<<< HEAD
        # Configure the mock to raise an exception
        mock_acreate.side_effect = Exception("Test error")
=======
        # Configure the mock to raise an exception when awaited
        async def raise_error(*args, **kwargs):
            raise Exception("Test error")
        mock_acreate.side_effect = raise_error
>>>>>>> dc2c151 (b)
        
        # Test parameters
        messages = [{"role": "user", "content": "Hello"}]
        
        # Run the test and expect an exception
        with self.assertRaises(Exception):
            self.run_async(self.adapter.create_chat_completion(
                model="test-model",
                messages=messages
            ))
    
    @patch('openai.ChatCompletion.acreate')
    def test_chat_completion_with_response_format(self, mock_acreate):
        """Test creating a chat completion with response_format."""
<<<<<<< HEAD
        # Configure the mock
=======
        # Configure the mock with a properly awaitable response
>>>>>>> dc2c151 (b)
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
<<<<<<< HEAD
        mock_acreate.return_value = mock_response
=======
        # Use create_async_mock to make it awaitable
        mock_acreate.return_value = create_async_mock(mock_response)
>>>>>>> dc2c151 (b)
        
        # Test parameters
        messages = [{"role": "user", "content": "Respond in JSON"}]
        
<<<<<<< HEAD
        # Run the test
=======
        # Run the test with a patched settings object
>>>>>>> dc2c151 (b)
        with patch('rag.openai_adapter.settings') as mock_settings:
            mock_settings.AZURE_OPENAI_API_VERSION = "2023-07-01-preview"
            result = self.run_async(self.adapter.create_chat_completion(
                model="test-model",
                messages=messages,
                response_format={"type": "json_object"}
            ))
        
        # Check that response_format was included in the API call
        kwargs = mock_acreate.call_args.kwargs
        self.assertIn("response_format", kwargs)
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
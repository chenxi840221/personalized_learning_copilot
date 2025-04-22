# backend/tests/async_test_base.py
"""
Improved async test base with better mock support.
"""

import unittest
import asyncio
from unittest.mock import MagicMock

class AsyncMock(MagicMock):
    """
    A mock class that can be used to mock async functions.
    This properly implements __await__ to make it awaitable.
    """
    def __init__(self, *args, return_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.return_value = return_value
        
    async def __call__(self, *args, **kwargs):
        return self.return_value
    
    def __await__(self):
        async def async_magic():
            return self.return_value
        return async_magic().__await__()

def create_async_mock(return_value=None):
    """
    Create a mock that can be properly awaited in async functions.
    This is a simpler function for creating AsyncMock instances.
    
    Args:
        return_value: The value to return when awaited
        
    Returns:
        An AsyncMock instance that can be properly awaited
    """
    return AsyncMock(return_value=return_value)

class AsyncioTestCase(unittest.TestCase):
    """
    A base class for tests that use asyncio.
    This is maintained for backward compatibility during the transition to sync tests.
    """
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        self.loop.close()
        
    def run_async(self, coroutine):
        """
        Run an async coroutine in a synchronous test.
        
        Args:
            coroutine: The coroutine to execute
            
        Returns:
            The result of the coroutine
        """
        return self.loop.run_until_complete(coroutine)
    
    def patch_return_async(self, mock_obj, method_name, return_value):
        """
        Patch a method on a mock object to return an async mock.
        
        Args:
            mock_obj: The mock object to patch
            method_name: The name of the method to patch
            return_value: The value to return when the patched method is awaited
            
        Returns:
            The patched mock object
        """
        # Create an async mock with the specified return value
        async_mock = create_async_mock(return_value)
        
        # Set the method on the mock object to the async mock
        setattr(mock_obj, method_name, async_mock)
        
        return mock_obj
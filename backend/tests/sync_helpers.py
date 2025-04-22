# backend/tests/sync_helpers.py
"""
Helper functions for synchronous testing of asynchronous code.
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
from functools import wraps

def run_async(coroutine):
    """
    Run an async coroutine in a synchronous context.
    This is a utility to help transition from async tests to sync tests.
    
    Args:
        coroutine: The coroutine to execute
        
    Returns:
        The result of the coroutine
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

def sync_wrapper(async_func):
    """
    Wrap an async function to make it synchronous for testing.
    
    Args:
        async_func: The async function to wrap
        
    Returns:
        A synchronous version of the function
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        return run_async(async_func(*args, **kwargs))
    return wrapper

def create_async_mock(return_value=None):
    """
    Create a mock that can be properly awaited in async functions.
    
    Args:
        return_value: The value to return when the mock is called
        
    Returns:
        A mock that can be awaited
    """
    mock = MagicMock()
    
    async def _async_magic():
        return return_value
        
    mock.__await__ = lambda *args, **kwargs: _async_magic().__await__()
    return mock

def patch_async(target, **kwargs):
    """
    Create a patch that works for async functions.
    This ensures that the patched function can be properly awaited.
    
    Args:
        target: The target to patch
        **kwargs: Additional arguments for patch
        
    Returns:
        A patch object that handles async properly
    """
    return_value = kwargs.pop('return_value', None)
    async_mock = create_async_mock(return_value)
    return patch(target, async_mock, **kwargs)

class SyncTestCase(unittest.TestCase):
    """
    A test case class that provides utilities for testing async code synchronously.
    This is a transitional class to help move from AsyncioTestCase to regular TestCase.
    """
    def run_async(self, coroutine):
        """
        Run an async coroutine in a synchronous test.
        
        Args:
            coroutine: The coroutine to execute
            
        Returns:
            The result of the coroutine
        """
        return run_async(coroutine)
    
    def create_async_mock(self, return_value=None):
        """
        Create a mock that can be properly awaited.
        
        Args:
            return_value: The value to return when the mock is called
            
        Returns:
            A mock that can be awaited
        """
        return create_async_mock(return_value)
    
    def patch_async(self, target, **kwargs):
        """
        Create a patch for an async function.
        
        Args:
            target: The target to patch
            **kwargs: Additional arguments for patch
            
        Returns:
            A patch context manager
        """
        return patch_async(target, **kwargs)
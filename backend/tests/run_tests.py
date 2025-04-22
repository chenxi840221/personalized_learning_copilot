#!/usr/bin/env python3
"""
Test runner for the Personalized Learning Co-pilot.
This script runs all test files in the tests directory.
"""

import unittest
import os
import sys
import argparse
import warnings
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import importlib.util

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create test settings module and add it to sys.modules
from tests.test_settings import settings

# Mock environment variables to use test values
mock_env = {
    'AZURE_COGNITIVE_ENDPOINT': settings.AZURE_COGNITIVE_ENDPOINT,
    'AZURE_COGNITIVE_KEY': settings.AZURE_COGNITIVE_KEY,
    'AZURE_OPENAI_ENDPOINT': settings.AZURE_OPENAI_ENDPOINT,
    'AZURE_OPENAI_KEY': settings.AZURE_OPENAI_KEY,
    'AZURE_OPENAI_API_VERSION': settings.AZURE_OPENAI_API_VERSION,
    'AZURE_OPENAI_DEPLOYMENT': settings.AZURE_OPENAI_DEPLOYMENT,
    'AZURE_OPENAI_EMBEDDING_DEPLOYMENT': settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    'AZURE_SEARCH_ENDPOINT': settings.AZURE_SEARCH_ENDPOINT,
    'AZURE_SEARCH_KEY': settings.AZURE_SEARCH_KEY,
    'AZURE_SEARCH_INDEX_NAME': settings.AZURE_SEARCH_INDEX_NAME,
    'SECRET_KEY': settings.SECRET_KEY,
    'ALGORITHM': settings.ALGORITHM,
    'ACCESS_TOKEN_EXPIRE_MINUTES': str(settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    'CORS_ORIGINS': ','.join(settings.CORS_ORIGINS)
}

# Apply the mock environment variables
for key, value in mock_env.items():
    os.environ[key] = value

class AsyncioTestCase(unittest.TestCase):
    """Base class for tests that use asyncio."""
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        self.loop.close()
        
    def run_async(self, coroutine):
        return self.loop.run_until_complete(coroutine)

def discover_tests(pattern=None):
    """Discover all test files in the current directory."""
    loader = unittest.TestLoader()
    if pattern:
        test_suite = loader.discover('.', pattern=pattern)
    else:
        test_suite = loader.discover('.')
    return test_suite

def create_async_mock_for_awaitable():
    """Create an AsyncMock that can be properly awaited."""
    async def mock_coroutine(*args, **kwargs):
        return AsyncMock()()
    
    mock = AsyncMock()
    mock.side_effect = mock_coroutine
    return mock

def run_tests(pattern=None, verbose=1):
    """Run all test files."""
    # Suppress ResourceWarning for unclosed sockets
    warnings.filterwarnings(action="ignore", category=ResourceWarning)
    
    # Fix the test name if it doesn't end with .py
    if pattern and not pattern.endswith('.py'):
        pattern = pattern + '.py'
    
    # Create patches for external services
    mocks = [
        # Mock OpenAI API calls
        patch('openai.ChatCompletion.acreate', 
              AsyncMock(return_value={'choices': [{'message': {'content': '{}'}}]})),
        patch('openai.Embedding.acreate', 
              AsyncMock(return_value={'data': [{'embedding': [0.1, 0.2, 0.3, 0.4]}]})),
        
        # Mock Azure Form Recognizer - use a proper async mock for awaitable
        patch('azure.ai.formrecognizer.DocumentAnalysisClient.begin_analyze_document_from_url',
             create_async_mock_for_awaitable()),
        
        # Other Azure services
        patch('azure.ai.textanalytics.TextAnalyticsClient'),
        patch('azure.cognitiveservices.vision.computervision.ComputerVisionClient'),
        
        # Mock aiohttp ClientSession
        patch('aiohttp.ClientSession')
    ]
    
    # Patch config settings in modules to use test settings
    config_patches = [
        patch('config.settings.settings', settings),
        patch('rag.openai_adapter.settings', settings),
        patch('rag.retriever.settings', settings),
        patch('rag.document_processor.settings', settings),
        patch('rag.learning_planner.settings', settings),
        patch('rag.generator.settings', settings),
        patch('scrapers.abc_edu_scraper.settings', settings)
    ]
    
    # Start all mocks
    for mock in mocks + config_patches:
        mock.start()
    
    try:
        # Run the tests
        test_suite = discover_tests(pattern)
        runner = unittest.TextTestRunner(verbosity=verbose)
        result = runner.run(test_suite)
        
        return result.wasSuccessful()
    finally:
        # Stop all mocks
        for mock in mocks + config_patches:
            mock.stop()

def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description='Run tests for the Personalized Learning Co-pilot')
    parser.add_argument('--pattern', '-p', type=str, help='Pattern to match test files')
    parser.add_argument('--verbose', '-v', action='count', default=1, 
                        help='Increase verbosity (specify multiple times for more)')
    args = parser.parse_args()
    
    success = run_tests(args.pattern, args.verbose)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
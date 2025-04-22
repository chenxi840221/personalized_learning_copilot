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
from unittest.mock import patch
import importlib.util

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables to use test values
mock_env = {
    'AZURE_COGNITIVE_ENDPOINT': 'https://test-cognitive.cognitiveservices.azure.com/',
    'AZURE_COGNITIVE_KEY': 'test-key',
    'AZURE_OPENAI_ENDPOINT': 'https://test-openai.openai.azure.com/',
    'AZURE_OPENAI_KEY': 'test-openai-key',
    'AZURE_OPENAI_API_VERSION': '2023-05-15',
    'AZURE_OPENAI_DEPLOYMENT': 'test-gpt4',
    'AZURE_OPENAI_EMBEDDING_DEPLOYMENT': 'text-embedding-ada-002',
    'AZURE_SEARCH_ENDPOINT': 'https://test-search.search.windows.net',
    'AZURE_SEARCH_KEY': 'test-search-key',
    'AZURE_SEARCH_INDEX_NAME': 'test-index',
    'SECRET_KEY': 'test-secret-key',
    'ALGORITHM': 'HS256',
    'ACCESS_TOKEN_EXPIRE_MINUTES': '60'
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

def run_tests(pattern=None, verbose=1):
    """Run all test files."""
    # Suppress ResourceWarning for unclosed sockets
    warnings.filterwarnings(action="ignore", category=ResourceWarning)
    
    # Mock various external modules to prevent actual API calls
    mocks = [
        patch('openai.ChatCompletion.acreate'),
        patch('openai.Embedding.acreate'),
        patch('azure.ai.formrecognizer.DocumentAnalysisClient'),
        patch('azure.ai.textanalytics.TextAnalyticsClient'),
        patch('azure.cognitiveservices.vision.computervision.ComputerVisionClient'),
        patch('azure.search.documents.aio.SearchClient'),
        patch('aiohttp.ClientSession')
    ]
    
    # Start all mocks
    for mock in mocks:
        mock.start()
    
    try:
        # Run the tests
        test_suite = discover_tests(pattern)
        runner = unittest.TextTestRunner(verbosity=verbose)
        result = runner.run(test_suite)
        
        return result.wasSuccessful()
    finally:
        # Stop all mocks
        for mock in mocks:
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
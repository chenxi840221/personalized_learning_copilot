# backend/tests/sync_adapters.py
"""
Synchronous adapter classes for testing async code.
These adapters wrap the async classes and provide synchronous methods.
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import sync helpers
from tests.sync_helpers import sync_wrapper

class SyncOpenAIAdapter:
    """Synchronous adapter for OpenAIAdapter."""
    
    def __init__(self, async_adapter=None):
        """
        Initialize the sync adapter.
        
        Args:
            async_adapter: The async adapter to wrap (if None, a new one will be created)
        """
        if async_adapter is None:
            # Import here to avoid circular imports
            from rag.openai_adapter import OpenAIAdapter
            async_adapter = OpenAIAdapter()
        
        self.async_adapter = async_adapter
        
        # Create sync wrappers for async methods
        self.create_chat_completion = sync_wrapper(async_adapter.create_chat_completion)
        self.create_embedding = sync_wrapper(async_adapter.create_embedding)

def get_sync_openai_adapter():
    """
    Get the synchronous OpenAI adapter singleton.
    
    Returns:
        A synchronous OpenAI adapter
    """
    # Import here to avoid circular imports
    from rag.openai_adapter import get_openai_adapter
    
    # Run the async function synchronously
    async_adapter = sync_wrapper(get_openai_adapter)()
    
    # Wrap the async adapter
    return SyncOpenAIAdapter(async_adapter)

class SyncDocumentProcessor:
    """Synchronous adapter for DocumentProcessor."""
    
    def __init__(self, async_processor=None):
        """
        Initialize the sync adapter.
        
        Args:
            async_processor: The async processor to wrap (if None, a new one will be created)
        """
        if async_processor is None:
            # Import here to avoid circular imports
            from rag.document_processor import DocumentProcessor
            async_processor = DocumentProcessor()
        
        self.async_processor = async_processor
        
        # Create sync wrappers for async methods
        self.process_content = sync_wrapper(async_processor.process_content)
        self.extract_content_from_document = sync_wrapper(async_processor.extract_content_from_document)
        self._extract_text_from_html = async_processor._extract_text_from_html  # This is already sync

def get_sync_document_processor():
    """
    Get the synchronous document processor singleton.
    
    Returns:
        A synchronous document processor
    """
    # Import here to avoid circular imports
    from rag.document_processor import get_document_processor
    
    # Run the async function synchronously
    async_processor = sync_wrapper(get_document_processor)()
    
    # Wrap the async processor
    return SyncDocumentProcessor(async_processor)

class SyncLearningPlanner:
    """Synchronous adapter for LearningPlanner."""
    
    def __init__(self, async_planner=None):
        """
        Initialize the sync adapter.
        
        Args:
            async_planner: The async planner to wrap (if None, a new one will be created)
        """
        if async_planner is None:
            # Import here to avoid circular imports
            from rag.learning_planner import LearningPlanner
            async_planner = LearningPlanner()
        
        self.async_planner = async_planner
        
        # Create sync wrappers for async methods
        self.create_learning_plan = sync_wrapper(async_planner.create_learning_plan)
        self.create_advanced_learning_path = sync_wrapper(async_planner.create_advanced_learning_path)
        self.adapt_plan_for_performance = sync_wrapper(async_planner.adapt_plan_for_performance)

def get_sync_learning_planner():
    """
    Get the synchronous learning planner singleton.
    
    Returns:
        A synchronous learning planner
    """
    # Import here to avoid circular imports
    from rag.learning_planner import get_learning_planner
    
    # Run the async function synchronously
    async_planner = sync_wrapper(get_learning_planner)()
    
    # Wrap the async planner
    return SyncLearningPlanner(async_planner)

class SyncContentRetriever:
    """Synchronous adapter for ContentRetriever."""
    
    def __init__(self, async_retriever=None):
        """
        Initialize the sync adapter.
        
        Args:
            async_retriever: The async retriever to wrap (if None, a new one will be created)
        """
        if async_retriever is None:
            # Import here to avoid circular imports
            from rag.retriever import ContentRetriever
            async_retriever = ContentRetriever()
            # Note: We would need to initialize this, but for testing we'll use mocks
        
        self.async_retriever = async_retriever
        
        # Create sync wrappers for async methods
        self.get_relevant_content = sync_wrapper(async_retriever.get_relevant_content)
        self.get_personalized_recommendations = sync_wrapper(async_retriever.get_personalized_recommendations)
        self.get_embedding = sync_wrapper(async_retriever.get_embedding)
        self.close = sync_wrapper(async_retriever.close)
        self.initialize = sync_wrapper(async_retriever.initialize)

def get_sync_content_retriever():
    """
    Get the synchronous content retriever singleton.
    
    Returns:
        A synchronous content retriever
    """
    # Import here to avoid circular imports
    from rag.retriever import get_content_retriever
    
    # Run the async function synchronously
    async_retriever = sync_wrapper(get_content_retriever)()
    
    # Wrap the async retriever
    return SyncContentRetriever(async_retriever)

class SyncABCEducationScraper:
    """Synchronous adapter for ABCEducationScraper."""
    
    def __init__(self, async_scraper=None):
        """
        Initialize the sync adapter.
        
        Args:
            async_scraper: The async scraper to wrap (if None, a new one will be created)
        """
        if async_scraper is None:
            # Import here to avoid circular imports
            from scrapers.abc_edu_scraper import ABCEducationScraper
            async_scraper = ABCEducationScraper()
        
        self.async_scraper = async_scraper
        
        # Create sync wrappers for async methods
        self.initialize = sync_wrapper(async_scraper.initialize)
        self.close = sync_wrapper(async_scraper.close)
        self.scrape_all_subjects = sync_wrapper(async_scraper.scrape_all_subjects)
        self.scrape_subject = sync_wrapper(async_scraper.scrape_subject)
        self.generate_embedding = sync_wrapper(async_scraper.generate_embedding)
        self.extract_video_content = sync_wrapper(async_scraper.extract_video_content)
        self.extract_document_content = sync_wrapper(async_scraper.extract_document_content)
        self.process_content_details = sync_wrapper(async_scraper.process_content_details)
        self.save_to_azure_search = sync_wrapper(async_scraper.save_to_azure_search)
        
        # Sync methods
        self._determine_content_type = async_scraper._determine_content_type
        self._determine_difficulty_and_grade = async_scraper._determine_difficulty_and_grade
        self._estimate_duration = async_scraper._estimate_duration
        self._extract_keywords = async_scraper._extract_keywords

def run_sync_scraper():
    """
    Run the scraper synchronously.
    
    Returns:
        The scraped content
    """
    # Import here to avoid circular imports
    from scrapers.abc_edu_scraper import run_scraper
    
    # Run the async function synchronously
    return sync_wrapper(run_scraper)()

# Add more sync adapters for other async classes as needed
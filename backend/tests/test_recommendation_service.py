import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recommendation_service import RecommendationService, get_recommendation_service
from models.user import User, LearningStyle
from models.content import Content, ContentType, DifficultyLevel


class TestRecommendationService(unittest.TestCase):
    """Test the Recommendation Service with mocked Azure AI Search."""

    def setUp(self):
        """Set up test case."""
        # Create a sample user
        self.user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            grade_level=8,
            subjects_of_interest=["Mathematics", "Science"],
            learning_style=LearningStyle.VISUAL
        )
        
        # Create a mock search client
        self.mock_search_client = AsyncMock()
        
        # Create the service
        self.service = RecommendationService()
        self.service.search_client = self.mock_search_client
        
        # Reset the singleton
        import services.recommendation_service
        services.recommendation_service.recommendation_service = None
    
    def test_generate_query_text(self):
        """Test generating query text for embedding."""
        # Generate query text
        query = self.service._generate_query_text(self.user, subject="Mathematics")
        
        # Assertions
        self.assertIn("grade 8", query)
        self.assertIn("visual learning style", query)
        self.assertIn("Mathematics", query)
        self.assertIn("Science", query)
    
    def test_build_filter_expression(self):
        """Test building filter expressions for Azure AI Search."""
        # Generate filter without subject
        filter1 = self.service._build_filter_expression(self.user)
        
        # Generate filter with subject
        filter2 = self.service._build_filter_expression(self.user, "Mathematics")
        
        # Assertions
        self.assertIn("grade_level/any(g: g eq 8)", filter1)
        self.assertIn("grade_level/any(g: g eq 7)", filter1)
        self.assertIn("grade_level/any(g: g eq 9)", filter1)
        self.assertIn("difficulty_level eq 'intermediate'", filter1)
        
        self.assertIn("subject eq 'Mathematics'", filter2)
    
    @patch('azure.search.documents.aio.SearchClient')
    @patch('rag.openai_adapter.get_openai_adapter')
    async def test_initialize(self, mock_get_adapter, mock_search_client_class):
        """Test initializing the recommendation service."""
        # Configure mocks
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter
        
        mock_search_client = AsyncMock()
        mock_search_client_class.return_value = mock_search_client
        
        # Initialize the service
        service = RecommendationService()
        await service.initialize()
        
        # Assertions
        self.assertIsNotNone(service.search_client)
        self.assertIsNotNone(service.openai_adapter)
    
    @patch('rag.openai_adapter.get_openai_adapter')
    async def test_generate_embedding(self, mock_get_adapter):
        """Test generating embeddings for a query."""
        # Configure mock
        mock_adapter = AsyncMock()
        mock_adapter.create_embedding.return_value = [0.1, 0.2, 0.3, 0.4]
        mock_get_adapter.return_value = mock_adapter
        
        # Set the adapter
        self.service.openai_adapter = mock_adapter
        
        # Generate embedding
        embedding = await self.service._generate_embedding("test query")
        
        # Assertions
        mock_adapter.create_embedding.assert_called_once()
        self.assertEqual(embedding, [0.1, 0.2, 0.3, 0.4])
    
    async def test_get_content_by_id(self):
        """Test getting content by ID."""
        # Configure mock
        self.mock_search_client.get_document.return_value = {
            "id": "content-1",
            "title": "Test Content",
            "description": "Test description",
            "content_type": "video",
            "subject": "Mathematics",
            "difficulty_level": "intermediate",
            "url": "https://example.com/test"
        }
        
        # Get content
        content = await self.service.get_content_by_id("content-1")
        
        # Assertions
        self.mock_search_client.get_document.assert_called_once_with(key="content-1")
        self.assertEqual(content.id, "content-1")
        self.assertEqual(content.title, "Test Content")
        self.assertEqual(content.content_type, ContentType.VIDEO)
        self.assertEqual(content.difficulty_level, DifficultyLevel.INTERMEDIATE)
    
    @patch('rag.openai_adapter.get_openai_adapter')
    async def test_get_personalized_recommendations(self, mock_get_adapter):
        """Test getting personalized recommendations."""
        # Configure mocks
        mock_adapter = AsyncMock()
        mock_adapter.create_embedding.return_value = [0.1, 0.2, 0.3, 0.4]
        mock_get_adapter.return_value = mock_adapter
        self.service.openai_adapter = mock_adapter
        
        # Mock search results
        mock_result1 = {
            "id": "content-1",
            "title": "Test Content 1",
            "description": "Test description 1",
            "content_type": "video",
            "subject": "Mathematics",
            "difficulty_level": "intermediate",
            "grade_level": [8, 9],
            "topics": ["Algebra"],
            "url": "https://example.com/test1",
            "duration_minutes": 20,
            "keywords": ["math", "algebra"]
        }
        
        mock_result2 = {
            "id": "content-2",
            "title": "Test Content 2",
            "description": "Test description 2",
            "content_type": "lesson",
            "subject": "Mathematics",
            "difficulty_level": "beginner",
            "grade_level": [7, 8],
            "topics": ["Geometry"],
            "url": "https://example.com/test2",
            "duration_minutes": 30,
            "keywords": ["math", "geometry"]
        }
        
        # Create an async iterator for the mock results
        class AsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0
                
            def __aiter__(self):
                return self
                
            async def __anext__(self):
                if self.index < len(self.items):
                    item = self.items[self.index]
                    self.index += 1
                    return item
                raise StopAsyncIteration
        
        mock_search_results = AsyncIterator([mock_result1, mock_result2])
        self.mock_search_client.search.return_value = mock_search_results
        
        # Get recommendations
        recommendations = await self.service.get_personalized_recommendations(
            user=self.user,
            subject="Mathematics",
            limit=10
        )
        
        # Assertions
        self.mock_search_client.search.assert_called_once()
        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0].id, "content-1")
        self.assertEqual(recommendations[0].content_type, ContentType.VIDEO)
        self.assertEqual(recommendations[1].id, "content-2")
        self.assertEqual(recommendations[1].content_type, ContentType.LESSON)
    
    @patch('services.recommendation_service.RecommendationService')
    async def test_get_recommendation_service(self, mock_service_class):
        """Test getting the recommendation service singleton."""
        # Configure mock
        mock_instance = AsyncMock()
        mock_service_class.return_value = mock_instance
        
        # Call function twice
        service1 = await get_recommendation_service()
        service2 = await get_recommendation_service()
        
        # Assertions
        self.assertEqual(service1, service2)  # Should return the same instance


if __name__ == "__main__":
    unittest.main()
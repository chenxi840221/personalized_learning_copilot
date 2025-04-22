"""
Test-specific settings that override the main settings module.
This module should be imported in test files instead of the main settings module.
"""

from pydantic import BaseSettings
from typing import List, Optional
import os

class TestSettings(BaseSettings):
    """Settings class specifically for tests with mock values."""
    
    # Application Settings
    APP_NAME: str = "Personalized Learning Co-pilot Test"
    API_VERSION: str = "v1"
    DEBUG: bool = True
    
    # Authentication
    SECRET_KEY: str = "test-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Microsoft Entra ID Settings (for authentication)
    TENANT_ID: str = "test-tenant-id"
    CLIENT_ID: str = "test-client-id"
    CLIENT_SECRET: str = "test-client-secret"
    
    # Azure Cognitive Services
    AZURE_COGNITIVE_ENDPOINT: str = "https://test-cognitive.cognitiveservices.azure.com/"
    AZURE_COGNITIVE_KEY: str = "test-cognitive-key"
    
    # Azure AI Search Settings
    AZURE_SEARCH_ENDPOINT: str = "https://test-search.search.windows.net"
    AZURE_SEARCH_KEY: str = "test-search-key"
    AZURE_SEARCH_INDEX_NAME: str = "test-content-index"
    
    # Azure AI Search Indexes
    CONTENT_INDEX_NAME: str = "test-content-index"
    USERS_INDEX_NAME: str = "test-users-index"
    PLANS_INDEX_NAME: str = "test-plans-index"
    
    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: str = "https://test-openai.openai.azure.com/"
    AZURE_OPENAI_KEY: str = "test-openai-key"
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"
    AZURE_OPENAI_DEPLOYMENT: str = "test-gpt4"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-ada-002"
    
    # Hard-coded for tests - no need for properties that might cause import issues
    FORM_RECOGNIZER_ENDPOINT: str = "https://test-cognitive.cognitiveservices.azure.com/formrecognizer/documentAnalysis"
    FORM_RECOGNIZER_KEY: str = "test-cognitive-key"
    TEXT_ANALYTICS_ENDPOINT: str = "https://test-cognitive.cognitiveservices.azure.com/text/analytics/v3.1"
    TEXT_ANALYTICS_KEY: str = "test-cognitive-key"
    COMPUTER_VISION_ENDPOINT: str = "https://test-cognitive.cognitiveservices.azure.com/vision/v3.2"
    COMPUTER_VISION_KEY: str = "test-cognitive-key"
    
    # CORS Settings - Hard-coded for tests
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Content Scraper Settings
    SCRAPER_RATE_LIMIT: float = 0.0  # No rate limiting in tests
    USER_AGENT: str = "PersonalizedLearningCopilot-Test/1.0"
    
    def get_openai_endpoint(self) -> str:
        """Get the OpenAI endpoint for tests."""
        return self.AZURE_OPENAI_ENDPOINT
    
    def get_openai_key(self) -> str:
        """Get the OpenAI key for tests."""
        return self.AZURE_OPENAI_KEY
    
    class Config:
        env_file = None  # Don't load from .env file in tests

# Create test settings instance
settings = TestSettings()
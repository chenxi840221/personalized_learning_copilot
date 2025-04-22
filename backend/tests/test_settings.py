<<<<<<< HEAD
"""
Test-specific settings that override the main settings module.
=======
# backend/tests/test_settings.py
"""
Test-specific settings that use real credentials from .env but with test-specific overrides.
>>>>>>> dc2c151 (b)
This module should be imported in test files instead of the main settings module.
"""

from pydantic import BaseSettings
from typing import List, Optional
import os
<<<<<<< HEAD

class TestSettings(BaseSettings):
    """Settings class specifically for tests with mock values."""
=======
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flag to determine whether to use real services or mocks in tests
# Set to False for most unit tests (faster, more isolated)
# Set to True for integration tests (tests real service behavior)
USE_REAL_SERVICES = False

class TestSettings(BaseSettings):
    """Settings class for tests with values from .env file and test-specific overrides."""
>>>>>>> dc2c151 (b)
    
    # Application Settings
    APP_NAME: str = "Personalized Learning Co-pilot Test"
    API_VERSION: str = "v1"
    DEBUG: bool = True
    
    # Authentication
<<<<<<< HEAD
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
=======
    SECRET_KEY: str = os.getenv("SECRET_KEY", "1234")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Microsoft Entra ID Settings (for authentication)
    TENANT_ID: str = os.getenv("MS_TENANT_ID", "94e1538a-3b46-4d3f-b78c-1f1613e4b6a2")
    CLIENT_ID: str = os.getenv("MS_CLIENT_ID", "aa03f3ae-a118-4866-905a-099bcfa5b716")
    CLIENT_SECRET: str = os.getenv("MS_CLIENT_SECRET", "TFe8Q~~wbMADwQi5kWCPnMbXmH-5k-lJ~VpLjbJm")
    
    # Azure Cognitive Services
    AZURE_COGNITIVE_ENDPOINT: str = os.getenv("AZURE_COGNITIVE_ENDPOINT", "https://aiservices-multi-persionalized-learning-copilot.cognitiveservices.azure.com/")
    AZURE_COGNITIVE_KEY: str = os.getenv("AZURE_COGNITIVE_KEY", "EQ5cvvkfGEzlJb7v5ahvdC0qeONZfMLIBKjLbDjghDUOQmvoViMdJQQJ99BDACL93NaXJ3w3AAAEACOG6pij")
    
    # Azure AI Search Settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "https://aisearch-personalized-learning-copilot.search.windows.net")
    AZURE_SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "PYvtAIFn0U4pGwCyEJY5x04yEFZAEct3ezHhezCOKiAzSeCZBrHw")
    AZURE_SEARCH_INDEX_NAME: str = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
    
    # Azure AI Search Indexes - use the same naming, but could be distinct for tests
    CONTENT_INDEX_NAME: str = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
    USERS_INDEX_NAME: str = "user-profiles-test"  # Use test-specific suffix
    PLANS_INDEX_NAME: str = "learning-plans-test"  # Use test-specific suffix
    
    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "https://australiaeast.api.cognitive.microsoft.com/")
    AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY", "2ece0e0981a949eba7ff8159f16e96de")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    
    # Hard-coded Cognitive Service endpoint paths for testing
    FORM_RECOGNIZER_ENDPOINT: str = "https://aiservices-multi-persionalized-learning-copilot.cognitiveservices.azure.com/formrecognizer/documentAnalysis"
    FORM_RECOGNIZER_KEY: str = os.getenv("AZURE_COGNITIVE_KEY", "EQ5cvvkfGEzlJb7v5ahvdC0qeONZfMLIBKjLbDjghDUOQmvoViMdJQQJ99BDACL93NaXJ3w3AAAEACOG6pij")
    TEXT_ANALYTICS_ENDPOINT: str = "https://aiservices-multi-persionalized-learning-copilot.cognitiveservices.azure.com/text/analytics/v3.1"
    TEXT_ANALYTICS_KEY: str = os.getenv("AZURE_COGNITIVE_KEY", "EQ5cvvkfGEzlJb7v5ahvdC0qeONZfMLIBKjLbDjghDUOQmvoViMdJQQJ99BDACL93NaXJ3w3AAAEACOG6pij")
    COMPUTER_VISION_ENDPOINT: str = "https://aiservices-multi-persionalized-learning-copilot.cognitiveservices.azure.com/vision/v3.2"
    COMPUTER_VISION_KEY: str = os.getenv("AZURE_COGNITIVE_KEY", "EQ5cvvkfGEzlJb7v5ahvdC0qeONZfMLIBKjLbDjghDUOQmvoViMdJQQJ99BDACL93NaXJ3w3AAAEACOG6pij")
    
    # CORS Settings
    @property
    def CORS_ORIGINS(self) -> List[str]:
        cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
        if cors_env:
            try:
                # Try to parse as comma-separated string
                origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
                return origins
            except Exception as e:
                import logging
                logging.warning(f"Error parsing CORS_ORIGINS: {e}")
        
        return ["http://localhost:3000", "http://localhost:8000"]
>>>>>>> dc2c151 (b)
    
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
<<<<<<< HEAD
        env_file = None  # Don't load from .env file in tests
=======
        env_file = ".env"
        case_sensitive = True
>>>>>>> dc2c151 (b)

# Create test settings instance
settings = TestSettings()
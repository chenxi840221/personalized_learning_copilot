from pydantic import BaseSettings
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Personalized Learning Co-pilot"
    API_VERSION: str = "v1"
    DEBUG: bool = True
    
    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Microsoft Entra ID Settings (for authentication)
    TENANT_ID: str = os.getenv("MS_TENANT_ID", "")
    CLIENT_ID: str = os.getenv("MS_CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("MS_CLIENT_SECRET", "")
    
    # Azure Cognitive Services Multi-Service Resource
    AZURE_COGNITIVE_ENDPOINT: str = os.getenv("AZURE_COGNITIVE_ENDPOINT", "")
    AZURE_COGNITIVE_KEY: str = os.getenv("AZURE_COGNITIVE_KEY", "")
    
    # Azure AI Search Settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "")
    AZURE_SEARCH_INDEX_NAME: str = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
    
    # Azure AI Search Indexes
    CONTENT_INDEX_NAME: str = os.getenv("AZURE_SEARCH_CONTENT_INDEX", "educational-content")
    USERS_INDEX_NAME: str = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
    PLANS_INDEX_NAME: str = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")
    
    # Azure OpenAI Settings (May be part of Cognitive Services or separate)
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    
    # Derived settings for individual services (using multi-service endpoint & key)
    @property
    def FORM_RECOGNIZER_ENDPOINT(self) -> str:
        from utils.cognitive_services import get_service_specific_endpoint
        return get_service_specific_endpoint(self.AZURE_COGNITIVE_ENDPOINT, "formrecognizer")
    
    @property
    def FORM_RECOGNIZER_KEY(self) -> str:
        return self.AZURE_COGNITIVE_KEY
        
    @property
    def TEXT_ANALYTICS_ENDPOINT(self) -> str:
        from utils.cognitive_services import get_service_specific_endpoint
        return get_service_specific_endpoint(self.AZURE_COGNITIVE_ENDPOINT, "textanalytics")
    
    @property
    def TEXT_ANALYTICS_KEY(self) -> str:
        return self.AZURE_COGNITIVE_KEY
        
    @property
    def COMPUTER_VISION_ENDPOINT(self) -> str:
        from utils.cognitive_services import get_service_specific_endpoint
        return get_service_specific_endpoint(self.AZURE_COGNITIVE_ENDPOINT, "computervision")
    
    @property
    def COMPUTER_VISION_KEY(self) -> str:
        return self.AZURE_COGNITIVE_KEY
    
    # If OpenAI is part of the same Cognitive Services resource
    def get_openai_endpoint(self) -> str:
        """Get the OpenAI endpoint, using Cognitive Services endpoint if OpenAI-specific is not provided."""
        if self.AZURE_OPENAI_ENDPOINT:
            return self.AZURE_OPENAI_ENDPOINT
        from utils.cognitive_services import get_service_specific_endpoint
        return get_service_specific_endpoint(self.AZURE_COGNITIVE_ENDPOINT, "openai", self.AZURE_OPENAI_API_VERSION)
    
    def get_openai_key(self) -> str:
        """Get the OpenAI key, using Cognitive Services key if OpenAI-specific is not provided."""
        if self.AZURE_OPENAI_KEY:
            return self.AZURE_OPENAI_KEY
        return self.AZURE_COGNITIVE_KEY
    
    # CORS Settings - Fix for the parsing error
    @property
    def CORS_ORIGINS(self) -> List[str]:
        default_origins = [
            "http://localhost:3000",  # React frontend
            "http://localhost:8000",  # FastAPI backend (for development)
        ]
        
        # Get additional origins from environment
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            try:
                # Try to parse as comma-separated string
                additional_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
                default_origins.extend(additional_origins)
            except Exception as e:
                import logging
                logging.warning(f"Error parsing CORS_ORIGINS: {e}")
        
        return default_origins
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Content Scraper Settings
    SCRAPER_RATE_LIMIT: float = 1.0  # seconds between requests
    USER_AGENT: str = "PersonalizedLearningCopilot/1.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()
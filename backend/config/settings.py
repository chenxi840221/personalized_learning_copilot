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
    # Azure AI Search Settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "")
    AZURE_SEARCH_INDEX_NAME: str = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    # Azure Form Recognizer Settings
    AZURE_FORM_RECOGNIZER_ENDPOINT: str = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT", "")
    AZURE_FORM_RECOGNIZER_KEY: str = os.getenv("AZURE_FORM_RECOGNIZER_KEY", "")
    # Azure Text Analytics Settings
    AZURE_TEXT_ANALYTICS_ENDPOINT: str = os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT", "")
    AZURE_TEXT_ANALYTICS_KEY: str = os.getenv("AZURE_TEXT_ANALYTICS_KEY", "")
    # Azure Computer Vision Settings
    AZURE_COMPUTER_VISION_ENDPOINT: str = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT", "")
    AZURE_COMPUTER_VISION_KEY: str = os.getenv("AZURE_COMPUTER_VISION_KEY", "")
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React frontend
        "http://localhost:8000",  # FastAPI backend (for development)
    ]
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
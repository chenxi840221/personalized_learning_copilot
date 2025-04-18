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
    
    # MongoDB Settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "learning_copilot")
    
    # Azure OpenAI Settings
    OPENAI_API_TYPE: str = os.getenv("OPENAI_API_TYPE", "azure")
    OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", "2023-05-15")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_DEPLOYMENT_NAME: str = os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4-turbo")
    
    # Embedding Model
    EMBEDDING_DEPLOYMENT_NAME: str = os.getenv("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React frontend
        "http://localhost:8000",  # FastAPI backend (for development)
    ]
    if os.getenv("CORS_ORIGINS"):
        CORS_ORIGINS.extend(os.getenv("CORS_ORIGINS").split(","))
    
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
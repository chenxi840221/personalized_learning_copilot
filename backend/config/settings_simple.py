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
    # CORS Settings - fixed default values
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React frontend
        "http://localhost:8000",  # FastAPI backend (for development)
    ]
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    # User agent
    USER_AGENT: str = "PersonalizedLearningCopilot/1.0"
    class Config:
        env_file = ".env"
        case_sensitive = True
# Create settings instance
settings = Settings()

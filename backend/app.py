# backend/app.py
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import logging
import os

# Import settings
from config.settings import Settings
settings = Settings()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot with Entra ID Authentication",
    version="0.2.0",
)

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import API routes
from api.auth_routes import router as auth_router
from api.learning_plan_routes import router as learning_plan_router

# Create user router for the /users/me endpoint
from auth.authentication import get_current_user
user_router = APIRouter(prefix="/users", tags=["users"])

@user_router.get("/me/")
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile information
    """
    return current_user

# Import AI routes if available
try:
    from api.content_endpoints import content_router
    has_content_endpoints = True
except ImportError:
    has_content_endpoints = False
    logger.warning("Content endpoints not available")

try:
    from api.azure_langchain_routes import azure_langchain_router
    has_langchain_endpoints = True
except ImportError:
    has_langchain_endpoints = False
    logger.warning("Azure LangChain endpoints not available")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Initialize Azure LangChain integration if available
    try:
        from rag.azure_langchain_integration import get_azure_langchain
        azure_langchain = await get_azure_langchain()
        logger.info("Azure LangChain integration initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Azure LangChain integration: {e}")
    
    # Initialize LangChain service if available
    try:
        from services.azure_langchain_service import get_azure_langchain_service
        langchain_service = await get_azure_langchain_service()
        logger.info("Azure LangChain service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Azure LangChain service: {e}")
    
    # Initialize Learning Plan service
    try:
        from services.azure_learning_plan_service import get_learning_plan_service
        learning_plan_service = await get_learning_plan_service()
        logger.info("Azure Learning Plan service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Learning Plan service: {e}")
    
    logger.info(f"Server started with Entra ID authentication")
    logger.info(f"Client ID: {settings.CLIENT_ID}")
    logger.info(f"Tenant ID: {settings.TENANT_ID}")

# Include routers
app.include_router(auth_router)
app.include_router(learning_plan_router)
app.include_router(user_router)  # Include the user router

# Include optional routers if available
if has_content_endpoints:
    app.include_router(content_router)
    logger.info("Content router included")

if has_langchain_endpoints:
    app.include_router(azure_langchain_router)
    logger.info("Azure LangChain router included")

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "ok",
        "version": "0.2.0",
        "services": {
            "entra_id": settings.CLIENT_ID != "",
            "azure_search": settings.AZURE_SEARCH_ENDPOINT != "",
            "azure_openai": settings.AZURE_OPENAI_ENDPOINT != ""
        }
    }

# Main entrypoint
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
import os
import json
import logging
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Environment variables loaded from .env file.")
except ImportError:
    print("python-dotenv not installed. Environment variables should be set manually.")

from student_report_system import StudentReportSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Get environment variables
form_recognizer_endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT", "")
form_recognizer_key = os.environ.get("FORM_RECOGNIZER_KEY", "")
openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
openai_key = os.environ.get("OPENAI_KEY", "")
openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "")

# Print environment variable status
logger.info("Environment variable status:")
logger.info(f"FORM_RECOGNIZER_ENDPOINT: {'Set' if form_recognizer_endpoint else 'Not set'}")
logger.info(f"FORM_RECOGNIZER_KEY: {'Set' if form_recognizer_key else 'Not set'}")
logger.info(f"OPENAI_ENDPOINT: {'Set' if openai_endpoint else 'Not set'}")
logger.info(f"OPENAI_KEY: {'Set' if openai_key else 'Not set'}")
logger.info(f"OPENAI_DEPLOYMENT: {openai_deployment if openai_deployment else 'Not set'}")

# Initialize the student report system
student_report_system = StudentReportSystem(
    form_recognizer_endpoint,
    form_recognizer_key,
    openai_endpoint,
    openai_key,
    openai_deployment
)

# Create FastAPI app
app = FastAPI(
    title="Student Report Synthesis System",
    description="API for generating synthetic student reports based on templates",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    api_status = {
        "status": "healthy",
        "timestamp": "2023-01-01T00:00:00Z",
        "document_client": student_report_system.document_client is not None,
        "openai_client": student_report_system.openai_client is not None,
        "libreoffice_available": student_report_system.libreoffice_path is not None
    }
    
    # If any essential service is unavailable, mark as unhealthy
    if not student_report_system.document_client or not student_report_system.openai_client:
        api_status["status"] = "unhealthy"
        
    return api_status

# Simple root endpoint
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Student Report Synthesis System...")
    
    # Start the FastAPI application
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        log_level="info"
    )
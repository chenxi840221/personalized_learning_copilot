import os
import io
import json
import uuid
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

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
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

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

# Ensure directories exist
os.makedirs("templates", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    api_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
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

# Upload template endpoint
@app.post("/templates/upload/")
async def upload_template(
    template_name: str = Form(...),
    template_file: UploadFile = File(...)
):
    """Upload a new report template file."""
    logger.info(f"Uploading template: {template_name}, file: {template_file.filename}")
    
    try:
        # Validate file extension
        file_ext = os.path.splitext(template_file.filename)[1].lower()
        if file_ext not in ['.pdf', '.docx', '.doc']:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_ext}. Only PDF and Word documents (.pdf, .docx, .doc) are supported."
            )
        
        # Create a unique identifier for the template
        template_id = f"{template_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        template_dir = Path("templates") / template_id
        os.makedirs(template_dir, exist_ok=True)
        
        # Save the uploaded file
        file_path = template_dir / template_file.filename
        with open(file_path, "wb") as buffer:
            content = await template_file.read()
            buffer.write(content)
        
        # Convert Word documents to PDF if needed
        pdf_path = file_path
        if file_ext in ['.docx', '.doc']:
            pdf_result = student_report_system.convert_word_to_pdf(str(file_path))
            if pdf_result:
                pdf_path = Path(pdf_result)
            else:
                logger.warning(f"Failed to convert Word document to PDF: {file_path}")
        
        # Create metadata file for the template
        metadata = {
            "id": template_id,
            "name": template_name,
            "original_filename": template_file.filename,
            "file_path": str(pdf_path),
            "upload_date": datetime.now().isoformat(),
            "status": "ready"
        }
        
        with open(template_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Return success response
        return {
            "success": True,
            "template_id": template_id,
            "name": template_name,
            "status": "ready"
        }
    
    except Exception as e:
        logger.error(f"Error uploading template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload template: {str(e)}")

# List available templates
@app.get("/templates/")
async def list_templates():
    """List all available report templates."""
    try:
        templates = student_report_system.list_templates()
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")

# Get template details
@app.get("/templates/{template_id}/")
async def get_template(template_id: str):
    """Get details for a specific template."""
    template_dir = Path("templates") / template_id
    metadata_file = template_dir / "metadata.json"
    
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
            return metadata
    except Exception as e:
        logger.error(f"Error loading template metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load template metadata: {str(e)}")

# Generate reports endpoint
@app.post("/reports/generate/")
async def generate_reports(
    template_id: str = Form(...),
    num_reports: int = Form(5),
    background_tasks: BackgroundTasks = None
):
    """Generate synthetic student reports based on a template."""
    try:
        # Check if template exists
        template_dir = Path("templates") / template_id
        if not template_dir.exists():
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
        
        # Generate batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        output_dir = Path("output") / batch_id
        os.makedirs(output_dir, exist_ok=True)
        
        # Create batch metadata
        batch_metadata = {
            "batch_id": batch_id,
            "template_id": template_id,
            "num_reports": num_reports,
            "status": "processing",
            "start_time": datetime.now().isoformat()
        }
        
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(batch_metadata, f, indent=2)
        
        # Start generation in background if available
        if background_tasks:
            background_tasks.add_task(
                student_report_system.generate_reports,
                template_id=template_id,
                num_reports=num_reports,
                batch_id=batch_id
            )
            return {
                "batch_id": batch_id,
                "status": "processing",
                "message": f"Generating {num_reports} reports in the background"
            }
        else:
            # Synchronous generation
            result = student_report_system.generate_reports(
                template_id=template_id,
                num_reports=num_reports,
                batch_id=batch_id
            )
            return result
            
    except Exception as e:
        logger.error(f"Error generating reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate reports: {str(e)}")

# Check generation status
@app.get("/reports/status/{batch_id}/")
async def check_report_status(batch_id: str):
    """Check the status of a report generation batch."""
    batch_dir = Path("output") / batch_id
    metadata_file = batch_dir / "metadata.json"
    
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
    
    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
            return metadata
    except Exception as e:
        logger.error(f"Error loading batch metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load batch metadata: {str(e)}")

# Download specific report
@app.get("/reports/{batch_id}/{report_id}/download/")
async def download_report(batch_id: str, report_id: str):
    """Download a specific generated report."""
    batch_dir = Path("output") / batch_id
    report_file = batch_dir / f"{report_id}.pdf"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail=f"Report not found: {batch_id}/{report_id}")
    
    return FileResponse(
        path=report_file,
        filename=f"{report_id}.pdf",
        media_type="application/pdf"
    )

# Download all reports in a batch as ZIP
@app.get("/reports/{batch_id}/download-all/")
async def download_all_reports(batch_id: str):
    """Download all reports in a batch as a ZIP file."""
    batch_dir = Path("output") / batch_id
    
    if not batch_dir.exists():
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
    
    try:
        # Load batch metadata
        metadata_file = batch_dir / "metadata.json"
        with open(metadata_file, "r") as f:
            batch_metadata = json.load(f)
        
        # Check if any reports are available
        reports = batch_metadata.get("reports", [])
        if not reports:
            raise HTTPException(status_code=404, detail=f"No reports found in batch: {batch_id}")
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add metadata as JSON
            zip_file.writestr('batch-info.json', json.dumps(batch_metadata, indent=2))
            
            # Add each report PDF
            for report in reports:
                if report.get("status") == "generated":
                    report_path = report.get("path") 
                    if report_path and os.path.exists(report_path):
                        # Extract filename from path
                        filename = os.path.basename(report_path)
                        # Add student name to filename if available
                        if report.get("student_name"):
                            student_name = report.get("student_name").replace(" ", "_")
                            filename = f"{student_name}_{filename}"
                        
                        # Add file to ZIP
                        zip_file.write(report_path, filename)
        
        # Reset buffer position
        zip_buffer.seek(0)
        
        # Return the ZIP file as a streaming response
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=student_reports_{batch_id}.zip"
            }
        )
        
    except Exception as e:
        logger.error(f"Error creating ZIP file for batch {batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP file: {str(e)}")

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
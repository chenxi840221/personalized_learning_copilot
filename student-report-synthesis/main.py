import os
import json
import uuid
import shutil
import logging
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from tempfile import NamedTemporaryFile

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

# Azure service credentials would be loaded from environment variables in production
form_recognizer_endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT", "")
form_recognizer_key = os.environ.get("FORM_RECOGNIZER_KEY", "")
openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
openai_key = os.environ.get("OPENAI_KEY", "")
openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")

# Initialize the student report system
logger.info("Initializing StudentReportSystem with available credentials")
report_system = StudentReportSystem(
    form_recognizer_endpoint, 
    form_recognizer_key,
    openai_endpoint,
    openai_key,
    openai_deployment
)

# Create directories
os.makedirs("templates", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Define models
class TemplateInfo(BaseModel):
    template_id: str
    name: str
    status: str
    extraction_date: str
    file_type: str = "pdf"  # Added to track file type

class StudentProfile(BaseModel):
    full_name: str
    age: int
    grade_level: int
    gender: str = Field(description="Male, Female, or Other")
    subjects: List[dict] = []
    social_development: List[dict] = []
    strengths: List[str] = []
    areas_for_improvement: List[str] = []
    attendance: dict = {}

class ReportGenerationRequest(BaseModel):
    template_id: str
    num_samples: int = Field(default=1, ge=1, le=20)
    student_profiles: Optional[List[StudentProfile]] = None

class ReportInfo(BaseModel):
    report_id: str
    student_name: str
    grade_level: int
    generation_date: str
    pdf_path: str
    compliance_score: float

# Create FastAPI app
app = FastAPI(
    title="Student Report Synthesis System",
    description="API for generating synthetic student reports based on templates",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html as the main page
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Processing queue for background tasks
processing_queue = {}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    api_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "document_client": report_system.document_client is not None,
        "openai_client": report_system.openai_client is not None,
        "libreoffice_available": report_system.libreoffice_path is not None
    }
    return api_status

# Endpoints
@app.post("/templates/upload/", response_model=TemplateInfo)
async def upload_template(
    background_tasks: BackgroundTasks,
    template_file: UploadFile = File(...),
    template_name: str = Form(...)
):
    """Upload a new report template for analysis (supports PDF and Word documents)."""
    logger.info(f"Received template upload request: {template_name}")
    
    if not template_file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    filename = template_file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith('.docx') or filename.endswith('.doc')):
        raise HTTPException(status_code=400, detail="Only PDF and Word (.docx, .doc) files are accepted")
    
    # Determine file type
    file_type = "pdf" if filename.endswith('.pdf') else "word"
    
    # Generate a unique ID for the template
    template_id = f"template_{uuid.uuid4().hex[:8]}"
    
    # Set the appropriate file extension
    extension = os.path.splitext(filename)[1]
    template_path = f"templates/{template_id}{extension}"
    
    try:
        # First read the content to verify it's a valid file
        contents = await template_file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file")
            
        # Write the file
        with open(template_path, "wb") as f:
            f.write(contents)
            
        logger.info(f"Template saved to {template_path}")
        
        # Process the template in the background
        background_tasks.add_task(
            process_template_background,
            template_id,
            template_path,
            template_name,
            file_type
        )
        
        return {
            "template_id": template_id,
            "name": template_name,
            "status": "processing",
            "extraction_date": datetime.now().isoformat(),
            "file_type": file_type
        }
    except Exception as e:
        logger.error(f"Error saving template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save template: {str(e)}")

@app.get("/templates/", response_model=List[TemplateInfo])
async def get_templates():
    """Get a list of all available templates."""
    templates = []
    
    try:
        for filename in os.listdir("templates"):
            if filename.endswith((".pdf", ".docx", ".doc")) and not filename.endswith(".json"):
                template_id = os.path.splitext(filename)[0]
                file_type = "pdf" if filename.endswith('.pdf') else "word"
                
                # Check if we have metadata
                metadata_path = f"templates/{template_id}.json"
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        templates.append({
                            "template_id": template_id,
                            "name": metadata.get("name", "Unknown"),
                            "status": metadata.get("status", "unknown"),
                            "extraction_date": metadata.get("extraction_date", ""),
                            "file_type": metadata.get("file_type", file_type)
                        })
                else:
                    templates.append({
                        "template_id": template_id,
                        "name": template_id,
                        "status": "unknown",
                        "extraction_date": "",
                        "file_type": file_type
                    })
    except Exception as e:
        logger.error(f"Error retrieving templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve templates: {str(e)}")
    
    return templates

@app.get("/templates/{template_id}/", response_model=dict)
async def get_template_details(template_id: str):
    """Get details of a specific template."""
    # Check for both PDF and Word template files
    potential_paths = [
        f"templates/{template_id}.pdf",
        f"templates/{template_id}.docx",
        f"templates/{template_id}.doc"
    ]
    
    template_path = None
    for path in potential_paths:
        if os.path.exists(path):
            template_path = path
            break
            
    if not template_path:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if we have extracted structure
    metadata_path = f"templates/{template_id}.json"
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            return json.load(f)
    
    # If no metadata, return basic info
    raise HTTPException(status_code=404, detail="Template details not available")

@app.post("/reports/generate/", response_model=dict)
async def generate_reports(
    background_tasks: BackgroundTasks,
    request: ReportGenerationRequest
):
    """Generate student reports based on a template."""
    # Check for both PDF and Word template files
    potential_paths = [
        f"templates/{request.template_id}.pdf",
        f"templates/{request.template_id}.docx",
        f"templates/{request.template_id}.doc"
    ]
    
    template_path = None
    for path in potential_paths:
        if os.path.exists(path):
            template_path = path
            break
            
    if not template_path:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate a unique ID for this batch
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    output_dir = f"output/{batch_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Start background task for generation
    processing_queue[batch_id] = {
        "status": "processing",
        "progress": 0,
        "total": request.num_samples,
        "completed": 0,
        "reports": []
    }
    
    background_tasks.add_task(
        generate_reports_background,
        batch_id,
        request.template_id,
        template_path,
        request.num_samples,
        request.student_profiles,
        output_dir
    )
    
    return {
        "batch_id": batch_id,
        "status": "processing",
        "message": f"Generation of {request.num_samples} reports started"
    }

@app.get("/reports/status/{batch_id}/", response_model=dict)
async def get_generation_status(batch_id: str):
    """Get the status of a report generation batch."""
    if batch_id not in processing_queue:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return processing_queue[batch_id]

@app.get("/reports/{batch_id}/{report_id}/download/")
async def download_report(batch_id: str, report_id: str):
    """Download a generated report."""
    status = processing_queue.get(batch_id, {})
    reports = status.get("reports", [])
    
    # Find the report
    report = None
    for r in reports:
        if r.get("report_id") == report_id:
            report = r
            break
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    pdf_path = report.get("pdf_path")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        pdf_path, 
        media_type="application/pdf",
        filename=f"student_report_{report.get('student_name', 'unnamed')}.pdf"
    )

@app.get("/reports/{batch_id}/download-all/")
async def download_all_reports(batch_id: str):
    """Download all reports in a batch as a zip file."""
    if batch_id not in processing_queue:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    status = processing_queue[batch_id]
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Reports generation not completed")
    
    # Create a zip file
    output_dir = f"output/{batch_id}"
    zip_path = f"output/{batch_id}.zip"
    
    try:
        shutil.make_archive(
            base_name=output_dir,  # prefix for the archive
            format='zip',          # format
            root_dir=output_dir    # root directory to archive
        )
        
        zip_file = f"{output_dir}.zip"
        if not os.path.exists(zip_file):
            raise HTTPException(status_code=500, detail="Failed to create ZIP file")
            
        return FileResponse(
            zip_file, 
            media_type="application/zip",
            filename=f"student_reports_{batch_id}.zip"
        )
    except Exception as e:
        logger.error(f"Error creating ZIP file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP file: {str(e)}")

@app.get("/system/assessment-scales/", response_model=dict)
async def get_assessment_scales():
    """Get the assessment scales used in the system."""
    if not report_system.assessment_scales:
        # If not analyzed yet, return default scales
        return {
            "achievement": {
                "A": "Outstanding",
                "B": "High",
                "C": "Expected",
                "D": "Basic",
                "E": "Limited"
            },
            "effort": {
                "High": "Consistently applies themselves",
                "Satisfactory": "Generally applies themselves",
                "Low": "Inconsistently applies themselves"
            }
        }
    
    return report_system.assessment_scales

# Background tasks
async def process_template_background(template_id, template_path, template_name, file_type):
    """Process a template in the background."""
    logger.info(f"Starting background processing of template: {template_name} ({template_id})")
    
    try:
        # Extract template structure
        template_data = report_system.extract_template_structure(template_path, template_name)
        
        # Save metadata
        metadata = {
            "template_id": template_id,
            "name": template_name,
            "status": "completed",
            "extraction_date": datetime.now().isoformat(),
            "file_type": file_type,
            "structure": template_data
        }
        
        metadata_path = f"templates/{template_id}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Completed processing template: {template_name} ({template_id})")
        
    except Exception as e:
        logger.error(f"Error processing template {template_name}: {str(e)}")
        
        # Save error metadata
        metadata = {
            "template_id": template_id,
            "name": template_name,
            "status": "failed",
            "extraction_date": datetime.now().isoformat(),
            "file_type": file_type,
            "error": str(e)
        }
        
        metadata_path = f"templates/{template_id}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

async def generate_reports_background(
    batch_id, 
    template_id,
    template_path,
    num_samples,
    student_profiles,
    output_dir
):
    """Generate reports in the background."""
    logger.info(f"Starting background generation of {num_samples} reports for batch: {batch_id}")
    
    try:
        # Make sure template is analyzed
        if template_id not in report_system.report_templates:
            report_system.extract_template_structure(template_path, template_id)
        
        # Analyze report structure if not already done
        if not report_system.report_structure:
            report_system.analyze_report_structure()
        
        # Generate student data if not provided
        if not student_profiles:
            students = report_system.generate_student_data(num_samples)
        else:
            students = [profile.dict() for profile in student_profiles]
        
        # Generate reports
        reports = []
        for i, student in enumerate(students):
            # Update progress
            processing_queue[batch_id]["progress"] = (i / len(students)) * 100
            
            try:
                # Generate report
                report_content = report_system.generate_student_report(student)
                
                if report_content:
                    # Verify compliance
                    compliance = report_system.verify_report_compliance(report_content)
                    
                    # Create PDF (always create PDF regardless of compliance score)
                    report_id = f"report_{uuid.uuid4().hex[:8]}"
                    pdf_path = f"{output_dir}/{report_id}.pdf"
                    created_pdf = report_system.create_pdf_report(report_content, pdf_path)
                    
                    if created_pdf:
                        # Store report info
                        report_info = {
                            "report_id": report_id,
                            "student_name": student.get("full_name", ""),
                            "grade_level": student.get("grade_level", 0),
                            "generation_date": datetime.now().isoformat(),
                            "pdf_path": pdf_path,
                            "compliance_score": compliance.get("compliance_score", 0)
                        }
                        
                        reports.append(report_info)
                        processing_queue[batch_id]["reports"].append(report_info)
                        processing_queue[batch_id]["completed"] += 1
                        
                        logger.info(f"Generated report {i+1}/{num_samples} for batch {batch_id}")
                    else:
                        logger.error(f"Failed to create PDF for student {i+1} in batch {batch_id}")
                else:
                    logger.error(f"Failed to generate report content for student {i+1} in batch {batch_id}")
            except Exception as e:
                logger.error(f"Error generating report {i+1} in batch {batch_id}: {str(e)}")
        
        # Save metadata even if some reports failed
        if reports:
            metadata_path = f"{output_dir}/metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(reports, f, indent=2)
        
        # Update status
        processing_queue[batch_id]["status"] = "completed"
        processing_queue[batch_id]["progress"] = 100
        
        logger.info(f"Completed generation of {len(reports)} reports for batch: {batch_id}")
        
    except Exception as e:
        logger.error(f"Error generating reports for batch {batch_id}: {str(e)}")
        
        # Update status with error
        processing_queue[batch_id]["status"] = "failed"
        processing_queue[batch_id]["error"] = str(e)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Student Report Synthesis System...")
    logger.info(f"Template directory: {os.path.abspath('templates')}")
    logger.info(f"Output directory: {os.path.abspath('output')}")
    
    # Start the FastAPI application
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        reload=True
    )
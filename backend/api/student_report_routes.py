# backend/api/student_report_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import os
import shutil

from models.student_report import StudentReport, ReportType
from auth.entra_auth import get_current_user
from utils.report_processor import get_report_processor
from config.settings import Settings
from services.search_service import get_search_service

# Initialize settings
settings = Settings()

# Create router
router = APIRouter(prefix="/student-reports", tags=["student-reports"])

@router.post("/upload")
async def upload_student_report(
    file: UploadFile = File(...),
    report_type: ReportType = Form(ReportType.PRIMARY),
    current_user: Dict = Depends(get_current_user)
):
    """Upload and process a student report document."""
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Create a temporary file to store the uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        # Copy uploaded file to temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
    
    try:
        # Get report processor
        report_processor = await get_report_processor()
        
        # Process the report
        student_id = current_user["id"]
        processed_report = await report_processor.process_report_document(temp_path, student_id)
        
        if not processed_report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process the student report"
            )
        
        # Get search service
        search_service = await get_search_service()
        
        # Index the report
        success = await search_service.index_document(
            index_name=settings.REPORTS_INDEX_NAME,
            document=processed_report
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to index the student report"
            )
        
        # Return the processed report
        return processed_report
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing student report: {str(e)}"
        )
    finally:
        # Clean up temporary file
        os.unlink(temp_path)

@router.get("/")
async def get_student_reports(
    current_user: Dict = Depends(get_current_user),
    limit: int = Query(10, description="Maximum number of reports to return"),
    skip: int = Query(0, description="Number of reports to skip"),
    school_year: Optional[str] = Query(None, description="Filter by school year"),
    term: Optional[str] = Query(None, description="Filter by term"),
    report_type: Optional[ReportType] = Query(None, description="Filter by report type")
):
    """Get all student reports for the current user."""
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Build filter expression
        filter_parts = [f"student_id eq '{current_user['id']}'"]
        
        if school_year:
            filter_parts.append(f"school_year eq '{school_year}'")
        
        if term:
            filter_parts.append(f"term eq '{term}'")
        
        if report_type:
            filter_parts.append(f"report_type eq '{report_type}'")
        
        filter_expression = " and ".join(filter_parts)
        
        # Get search service
        search_service = await get_search_service()
        
        # Search for reports
        reports = await search_service.search_documents(
            index_name=settings.REPORTS_INDEX_NAME,
            query="*",
            filter=filter_expression,
            top=limit,
            skip=skip
        )
        
        # Decrypt PII fields
        report_processor = await get_report_processor()
        for report in reports:
            if "encrypted_fields" in report:
                for field, encrypted_value in report["encrypted_fields"].items():
                    try:
                        report[field] = await report_processor.decrypt_pii(encrypted_value)
                    except Exception as e:
                        # If decryption fails, leave the field empty
                        report[field] = None
        
        return reports
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting student reports: {str(e)}"
        )

@router.get("/{report_id}")
async def get_student_report(
    report_id: str = Path(..., description="Report ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific student report."""
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Get the report
        filter_expression = f"id eq '{report_id}' and student_id eq '{current_user['id']}'"
        reports = await search_service.search_documents(
            index_name=settings.REPORTS_INDEX_NAME,
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not reports:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID {report_id} not found"
            )
        
        report = reports[0]
        
        # Decrypt PII fields
        report_processor = await get_report_processor()
        if "encrypted_fields" in report:
            for field, encrypted_value in report["encrypted_fields"].items():
                try:
                    report[field] = await report_processor.decrypt_pii(encrypted_value)
                except Exception as e:
                    # If decryption fails, leave the field empty
                    report[field] = None
        
        return report
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting student report: {str(e)}"
        )

@router.delete("/{report_id}")
async def delete_student_report(
    report_id: str = Path(..., description="Report ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a student report."""
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Verify the report exists and belongs to the user
        filter_expression = f"id eq '{report_id}' and student_id eq '{current_user['id']}'"
        reports = await search_service.search_documents(
            index_name=settings.REPORTS_INDEX_NAME,
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not reports:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID {report_id} not found"
            )
        
        # Delete the report
        success = await search_service.delete_document(
            index_name=settings.REPORTS_INDEX_NAME,
            document_id=report_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete the student report"
            )
        
        return {"message": f"Report with ID {report_id} successfully deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting student report: {str(e)}"
        )

# Include router in app
student_report_router = router
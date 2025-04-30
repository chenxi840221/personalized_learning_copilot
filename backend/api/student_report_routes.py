# backend/api/student_report_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import os
import shutil
import json

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
    # Add detailed logging
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Upload request received for user: {current_user}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Create a temporary file to store the uploaded file
    logger.info(f"Creating temporary file for: {file.filename}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        # Copy uploaded file to temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
    
    logger.info(f"File saved to temporary path: {temp_path}")
    
    try:
        # Get report processor
        logger.info("Initializing report processor")
        report_processor = await get_report_processor()
        
        # Process the report
        student_id = current_user["id"]
        logger.info(f"Processing report for student ID: {student_id}")
        processed_report = await report_processor.process_report_document(temp_path, student_id)
        
        if not processed_report:
            logger.error("Report processing failed: no processed report returned")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process the student report. Check if Azure Document Intelligence is properly configured."
            )
        
        # Get search service
        logger.info("Initializing search service")
        search_service = await get_search_service()
        
        # Index the report
        index_status = "skipped"
        
        # Only attempt to index if we have a valid search service and index name
        if search_service and settings.REPORTS_INDEX_NAME:
            logger.info(f"Indexing report to {settings.REPORTS_INDEX_NAME}")
            try:
                # Check if the index exists, create it if it doesn't
                index_exists = await search_service.check_index_exists(settings.REPORTS_INDEX_NAME)
                if not index_exists:
                    logger.warning(f"Index {settings.REPORTS_INDEX_NAME} does not exist. Attempting to create it.")
                    
                    # Try to import and run the index creation script
                    try:
                        import sys
                        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
                        sys.path.append(script_path)
                        
                        # Try different import approaches
                        try:
                            from update_report_index import update_student_reports_index
                            success = update_student_reports_index()
                        except ImportError:
                            # Try alternative import path
                            from scripts.update_report_index import update_student_reports_index
                            success = update_student_reports_index()
                        if success:
                            logger.info("Successfully created reports index")
                        else:
                            logger.error("Failed to create reports index")
                    except Exception as script_err:
                        logger.error(f"Error running index creation script: {script_err}")
                
                # Add debugging info to the processed report
                processed_report["_debug_info"] = {
                    "id": processed_report.get("id"),
                    "student_id": processed_report.get("student_id"),
                    "upload_time": datetime.utcnow().isoformat(),
                    "report_type": processed_report.get("report_type")
                }
                
                # Log the document being indexed
                logger.info(f"Indexing document with ID: {processed_report.get('id')}")
                logger.info(f"Document has {len(processed_report.get('subjects', []))} subjects")
                
                success = await search_service.index_document(
                    index_name=settings.REPORTS_INDEX_NAME,
                    document=processed_report
                )
                
                if not success:
                    logger.warning("Report indexing failed but continuing with report processing")
                    index_status = "failed"
                else:
                    logger.info(f"Successfully indexed report with ID: {processed_report.get('id')}")
                    index_status = "success"
            except Exception as e:
                logger.error(f"Error indexing report: {e}")
                index_status = "error"
        else:
            logger.warning("Search service or report index name not configured. Skipping indexing.")
        
        # Add indexing status to the response
        processed_report["indexing_status"] = index_status
        
        logger.info("Report processing and indexing completed successfully")
        # Return the processed report
        return processed_report
    
    except Exception as e:
        logger.exception(f"Error processing student report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing student report: {str(e)}"
        )
    finally:
        # Clean up temporary file
        logger.info(f"Cleaning up temporary file: {temp_path}")
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
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available. Returning empty results.")
            return []
            
        # Check if reports index is configured    
        if not settings.REPORTS_INDEX_NAME:
            logger.warning("Reports index name not configured. Returning empty results.")
            return []
            
        logger.info(f"Searching for reports with filter: {filter_expression}")
        logger.info(f"Search index name: {settings.REPORTS_INDEX_NAME}")
        
        try:
            # Search for reports
            reports = await search_service.search_documents(
                index_name=settings.REPORTS_INDEX_NAME,
                query="*",
                filter=filter_expression,
                top=limit,
                skip=skip
            )
            
            logger.info(f"Found {len(reports)} reports for user {current_user['id']}")
            
            # If no reports found, let's check if the index exists
            if len(reports) == 0:
                logger.info("No reports found. Checking if index exists...")
                index_exists = await search_service.check_index_exists(settings.REPORTS_INDEX_NAME)
                if not index_exists:
                    logger.warning(f"Index {settings.REPORTS_INDEX_NAME} does not exist!")
                    
            return reports
        except Exception as e:
            logger.error(f"Error searching for reports: {e}")
            return []
        
        # Decrypt PII fields
        if len(reports) > 0:
            logger.info("Decrypting PII fields for reports")
            report_processor = await get_report_processor()
            
            for report in reports:
                try:
                    # Debug information
                    if "encrypted_fields" not in report:
                        logger.warning(f"Report {report.get('id', 'unknown')} has no encrypted_fields")
                    elif not report["encrypted_fields"]:
                        logger.warning(f"Report {report.get('id', 'unknown')} has empty encrypted_fields")
                    
                    if "encrypted_fields" in report and report["encrypted_fields"]:
                        try:
                            # Parse encrypted fields from JSON string
                            if isinstance(report["encrypted_fields"], str):
                                try:
                                    encrypted_fields = json.loads(report["encrypted_fields"])
                                    logger.info(f"Successfully parsed encrypted_fields JSON for report {report.get('id', 'unknown')}")
                                except json.JSONDecodeError as json_err:
                                    logger.error(f"Error parsing encrypted_fields as JSON: {json_err}")
                                    logger.error(f"Value: {report['encrypted_fields']}")
                                    encrypted_fields = {}
                            else:
                                # It's already a dict
                                encrypted_fields = report["encrypted_fields"]
                                logger.info(f"Encrypted fields is already a dict for report {report.get('id', 'unknown')}")
                            
                            # Log encrypted fields keys
                            logger.info(f"Encrypted fields keys: {list(encrypted_fields.keys())}")
                            
                            # Decrypt each field
                            for field, encrypted_value in encrypted_fields.items():
                                try:
                                    logger.info(f"Decrypting field {field} for report {report.get('id', 'unknown')}")
                                    report[field] = await report_processor.decrypt_pii(encrypted_value)
                                    logger.info(f"Successfully decrypted field {field}")
                                except Exception as e:
                                    # If decryption fails, leave the field empty
                                    logger.warning(f"Failed to decrypt field {field}: {e}")
                                    report[field] = None
                        except Exception as e:
                            logger.warning(f"Error processing encrypted fields: {e}")
                except Exception as e:
                    logger.error(f"Error processing report: {e}")
        else:
            logger.info("No reports to decrypt")
        
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
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
            
        # Check if reports index is configured    
        if not settings.REPORTS_INDEX_NAME:
            logger.warning("Reports index name not configured.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Report retrieval service is not properly configured."
            )
        
        try:
            # Get the report
            filter_expression = f"id eq '{report_id}' and student_id eq '{current_user['id']}'"
            reports = await search_service.search_documents(
                index_name=settings.REPORTS_INDEX_NAME,
                query="*",
                filter=filter_expression,
                top=1
            )
        except Exception as e:
            logger.error(f"Error retrieving report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving report: {str(e)}"
            )
        
        if not reports:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID {report_id} not found"
            )
        
        report = reports[0]
        
        # Decrypt PII fields
        logger.info(f"Decrypting PII fields for report {report_id}")
        report_processor = await get_report_processor()
        
        try:
            # Debug information
            if "encrypted_fields" not in report:
                logger.warning(f"Report {report_id} has no encrypted_fields")
            elif not report["encrypted_fields"]:
                logger.warning(f"Report {report_id} has empty encrypted_fields")
            
            if "encrypted_fields" in report and report["encrypted_fields"]:
                try:
                    # Parse encrypted fields from JSON string
                    if isinstance(report["encrypted_fields"], str):
                        try:
                            encrypted_fields = json.loads(report["encrypted_fields"])
                            logger.info(f"Successfully parsed encrypted_fields JSON for report {report_id}")
                        except json.JSONDecodeError as json_err:
                            logger.error(f"Error parsing encrypted_fields as JSON: {json_err}")
                            logger.error(f"Value: {report['encrypted_fields']}")
                            encrypted_fields = {}
                    else:
                        # It's already a dict
                        encrypted_fields = report["encrypted_fields"]
                        logger.info(f"Encrypted fields is already a dict for report {report_id}")
                    
                    # Log encrypted fields keys
                    logger.info(f"Encrypted fields keys: {list(encrypted_fields.keys())}")
                    
                    # Decrypt each field
                    for field, encrypted_value in encrypted_fields.items():
                        try:
                            logger.info(f"Decrypting field {field} for report {report_id}")
                            report[field] = await report_processor.decrypt_pii(encrypted_value)
                            logger.info(f"Successfully decrypted field {field}")
                        except Exception as e:
                            # If decryption fails, leave the field empty
                            logger.warning(f"Failed to decrypt field {field}: {e}")
                            report[field] = None
                except Exception as e:
                    logger.warning(f"Error processing encrypted fields: {e}")
        except Exception as e:
            logger.error(f"Error processing report: {e}")
        
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
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
            
        # Check if reports index is configured    
        if not settings.REPORTS_INDEX_NAME:
            logger.warning("Reports index name not configured.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Report deletion service is not properly configured."
            )
        
        try:
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
                logger.error("Report deletion failed")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete the student report"
                )
            
            return {"message": f"Report with ID {report_id} successfully deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during report deletion process: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting report: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting student report: {str(e)}"
        )

# Include router in app
student_report_router = router
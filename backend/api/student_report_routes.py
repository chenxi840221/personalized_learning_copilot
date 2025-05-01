# backend/api/student_report_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import os
import shutil
import json
import copy
import logging
import traceback

from models.student_report import StudentReport, ReportType
from auth.entra_auth import get_current_user
from utils.report_processor import get_report_processor
from config.settings import Settings
from services.search_service import get_search_service

# Initialize settings
settings = Settings()

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/student-reports", tags=["student-reports"])

@router.post("/upload")
async def upload_student_report(
    file: UploadFile = File(...),
    report_type: ReportType = Form(ReportType.PRIMARY),
    current_user: Dict = Depends(get_current_user)
):
    """Upload and process a student report document."""
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
                
                # Log debugging info but don't add it to the document
                debug_info = {
                    "id": processed_report.get("id"),
                    "student_id": processed_report.get("student_id"),
                    "upload_time": datetime.utcnow().isoformat(),
                    "report_type": processed_report.get("report_type")
                }
                logger.info(f"Debug info for report: {debug_info}")
                
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
    logger.info(f"===== START: get_student_reports endpoint for user_id={current_user.get('id', 'unknown')} =====")
    
    # Ensure the user is authorized
    logger.info("STEP 1: Checking user authentication")
    if not current_user or not current_user.get("id"):
        logger.warning("Authentication check failed: User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    logger.info(f"User authenticated successfully: user_id={current_user.get('id')}")
    
    try:
        # Build filter expression
        logger.info("STEP 2: Building filter expression")
        filter_parts = [f"student_id eq '{current_user['id']}'"]
        
        if school_year:
            filter_parts.append(f"school_year eq '{school_year}'")
            logger.info(f"Added school_year filter: {school_year}")
        
        if term:
            filter_parts.append(f"term eq '{term}'")
            logger.info(f"Added term filter: {term}")
        
        if report_type:
            filter_parts.append(f"report_type eq '{report_type}'")
            logger.info(f"Added report_type filter: {report_type}")
        
        filter_expression = " and ".join(filter_parts)
        logger.info(f"Final filter expression: {filter_expression}")
        
        # Get search service
        logger.info("STEP 3: Initializing search service")
        search_service = await get_search_service()
        logger.info(f"Search service initialized: {search_service is not None}")
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available. Returning empty results.")
            return []
            
        # Check if reports index is configured    
        logger.info("STEP 4: Checking reports index configuration")
        if not settings.REPORTS_INDEX_NAME:
            logger.warning("Reports index name not configured. Returning empty results.")
            return []
            
        logger.info(f"Searching for reports with filter: {filter_expression}")
        logger.info(f"Search index name: {settings.REPORTS_INDEX_NAME}")
        
        # Search for reports
        logger.info("STEP 5: Executing search query")
        reports = []
        try:
            reports = await search_service.search_documents(
                index_name=settings.REPORTS_INDEX_NAME,
                query="*",
                filter=filter_expression,
                top=limit,
                skip=skip
            )
            
            logger.info(f"Search completed: Found {len(reports)} documents")
            
            # If no reports found, let's check if the index exists
            if len(reports) == 0:
                logger.info("No reports found. Checking if index exists...")
                index_exists = await search_service.check_index_exists(settings.REPORTS_INDEX_NAME)
                if not index_exists:
                    logger.warning(f"Index {settings.REPORTS_INDEX_NAME} does not exist!")
                    
            if not reports:
                logger.info("No reports found - returning empty list")
                return []
                
        except Exception as e:
            logger.error(f"SEARCH FAILURE: Error searching for reports: {e}")
            logger.error(f"SEARCH TRACEBACK: {traceback.format_exc()}")
            return []
        
        # Decrypt PII fields
        logger.info("STEP 6: Beginning decryption of PII fields")
        if len(reports) > 0:
            logger.info(f"Preparing to decrypt PII fields for {len(reports)} reports")
            
            try:
                # Get the report processor for decryption
                logger.info("STEP 6.1: Initializing report processor")
                report_processor = await get_report_processor()
                if not report_processor:
                    logger.error("Failed to initialize report processor for decryption")
                    logger.info("Returning reports without decryption due to processor initialization failure")
                    return reports
                logger.info("Report processor initialized successfully")
                
                # Process each report separately to maintain robustness
                logger.info("STEP 6.2: Processing reports individually")
                for i, report in enumerate(reports):
                    logger.info(f"Processing report {i+1} of {len(reports)}")
                    report_id = report.get('id', 'unknown')
                    
                    # Use a deep copy of the report to avoid modifying the original in case of errors
                    try:
                        logger.info(f"Creating deep copy of report {report_id}")
                        report_copy = copy.deepcopy(report)
                        logger.info("Deep copy created successfully")
                    except Exception as copy_err:
                        logger.error(f"DEEP COPY ERROR: Failed to create deep copy for report {report_id}: {copy_err}")
                        logger.error(f"DEEP COPY TRACEBACK: {traceback.format_exc()}")
                        # Skip to next report
                        continue
                    
                    try:
                        # Check if encrypted_fields exists and is not empty
                        logger.info(f"Checking encrypted_fields for report {report_id}")
                        if "encrypted_fields" not in report_copy:
                            logger.warning(f"Report {report_id} has no encrypted_fields key - skipping")
                            continue
                            
                        if not report_copy["encrypted_fields"]:
                            logger.warning(f"Report {report_id} has empty encrypted_fields value - skipping")
                            continue
                        
                        # Parse encrypted fields with robust error handling
                        logger.info(f"Parsing encrypted_fields for report {report_id}")
                        encrypted_fields = {}
                        try:
                            # Handle string format (JSON string)
                            if isinstance(report_copy["encrypted_fields"], str):
                                logger.info("Parsing encrypted_fields from JSON string")
                                try:
                                    encrypted_fields = json.loads(report_copy["encrypted_fields"])
                                    logger.info(f"Successfully parsed encrypted_fields JSON for report {report_id}")
                                except json.JSONDecodeError as json_err:
                                    logger.error(f"JSON DECODE ERROR: Error parsing encrypted_fields as JSON: {json_err}")
                                    logger.error(f"JSON STRING: {report_copy['encrypted_fields'][:100]}...")  # Log a truncated version
                                    # Skip to next report
                                    continue
                            # Handle dict format
                            elif isinstance(report_copy["encrypted_fields"], dict):
                                logger.info("Using encrypted_fields directly (already a dict)")
                                encrypted_fields = report_copy["encrypted_fields"]
                            else:
                                # Unknown format
                                logger.warning(f"UNEXPECTED TYPE: encrypted_fields has type: {type(report_copy['encrypted_fields'])}")
                                # Skip to next report
                                continue
                            
                            # Log encrypted fields keys for debugging
                            logger.info(f"Found {len(encrypted_fields)} encrypted fields: {list(encrypted_fields.keys())}")
                            
                            # Process each field individually with separate error handling
                            decrypted_count = 0
                            error_count = 0
                            
                            for field, encrypted_value in encrypted_fields.items():
                                logger.info(f"Processing field: {field}")
                                
                                if not encrypted_value:
                                    logger.warning(f"Empty encrypted value for field {field} - skipping")
                                    continue
                                    
                                try:
                                    logger.info(f"Decrypting field {field} for report {report_id}")
                                    report_copy[field] = await report_processor.decrypt_pii(encrypted_value)
                                    logger.info(f"Successfully decrypted field {field}")
                                    decrypted_count += 1
                                except Exception as field_error:
                                    error_count += 1
                                    logger.error(f"FIELD DECRYPTION ERROR: Failed to decrypt field {field}: {field_error}")
                                    logger.error(f"FIELD ERROR TRACEBACK: {traceback.format_exc()}")
                                    report_copy[field] = f"[Decryption Error: {field}]"  # Set an error indicator
                            
                            logger.info(f"Decryption summary for report {report_id}: {decrypted_count} succeeded, {error_count} failed")
                        except Exception as parse_error:
                            logger.error(f"STRUCTURE ERROR: Error processing encrypted fields structure: {parse_error}")
                            logger.error(f"STRUCTURE ERROR TRACEBACK: {traceback.format_exc()}")
                            # Continue with other reports
                        
                        # Update the report in the original list
                        logger.info(f"Updating report {report_id} in result list")
                        reports[i] = report_copy
                    except Exception as report_error:
                        logger.error(f"REPORT PROCESSING ERROR: Error processing report {report.get('id', 'unknown')}: {report_error}")
                        logger.error(f"REPORT ERROR TRACEBACK: {traceback.format_exc()}")
                        # Keep original report in this case
            except Exception as e:
                logger.error(f"CRITICAL DECRYPTION ERROR: Critical error during batch decryption process: {e}")
                logger.error(f"CRITICAL ERROR TRACEBACK: {traceback.format_exc()}")
                # Continue with unmodified reports
        else:
            logger.info("No reports to decrypt")
        
        logger.info(f"===== END: get_student_reports endpoint - returning {len(reports)} reports =====")
        return reports
    
    except HTTPException as http_ex:
        logger.info(f"Raising HTTP exception: {http_ex.status_code} - {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: Unhandled exception in get_student_reports: {e}")
        logger.error(f"UNEXPECTED ERROR TRACEBACK: {traceback.format_exc()}")
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
    # Setup detailed logging
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    logger.info(f"===== START: get_student_report endpoint for report_id={report_id} =====")
    
    # Ensure the user is authorized
    logger.info("STEP 1: Checking user authentication")
    if not current_user or not current_user.get("id"):
        logger.warning("Authentication check failed: User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    logger.info(f"User authenticated successfully: user_id={current_user.get('id')}")
    
    try:
        # Get search service
        logger.info("STEP 2: Initializing search service")
        search_service = await get_search_service()
        logger.info(f"Search service initialized: {search_service is not None}")
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available - returning 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
            
        # Check if reports index is configured    
        logger.info(f"STEP 3: Checking reports index configuration: {settings.REPORTS_INDEX_NAME}")
        if not settings.REPORTS_INDEX_NAME:
            logger.warning("Reports index name not configured - returning 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Report retrieval service is not properly configured."
            )
        
        # Search for the report
        logger.info("STEP 4: Preparing to search for the report")
        filter_expression = f"id eq '{report_id}' and student_id eq '{current_user['id']}'"
        logger.info(f"Filter expression: {filter_expression}")
        logger.info(f"Index name: {settings.REPORTS_INDEX_NAME}")
        
        try:
            logger.info("STEP 5: Executing search query")
            reports = await search_service.search_documents(
                index_name=settings.REPORTS_INDEX_NAME,
                query="*",
                filter=filter_expression,
                top=1
            )
            logger.info(f"Search completed: Found {len(reports)} documents")
        except Exception as e:
            logger.error(f"SEARCH FAILURE: Error retrieving report: {e}")
            logger.error(f"SEARCH TRACEBACK: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving report: {str(e)}"
            )
        
        # Check if report was found
        logger.info("STEP 6: Checking search results")
        if not reports:
            logger.warning(f"Report not found: report_id={report_id}, user_id={current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID {report_id} not found"
            )
        
        # Extract report from results
        logger.info(f"STEP 7: Report found, preparing for decryption")
        report = reports[0]
        logger.debug(f"Report keys: {list(report.keys())}")
        
        # Create a deep copy to work with
        logger.info("STEP 8: Creating deep copy of report for safe modification")
        try:
            report_copy = copy.deepcopy(report)
            logger.info("Deep copy created successfully")
        except Exception as copy_err:
            logger.error(f"DEEP COPY ERROR: Failed to create deep copy: {copy_err}")
            logger.error(f"DEEP COPY TRACEBACK: {traceback.format_exc()}")
            # Fall back to using original report
            report_copy = report
            logger.info("Falling back to original report object")
        
        # Process encrypted fields
        logger.info(f"STEP 9: Beginning PII decryption for report {report_id}")
        
        try:
            # Initialize the report processor
            logger.info("STEP 9.1: Initializing report processor")
            report_processor = await get_report_processor()
            if not report_processor:
                logger.error("Failed to initialize report processor for decryption")
                logger.info("EARLY RETURN: Returning report without decryption due to processor init failure")
                return report_copy
            logger.info("Report processor initialized successfully")
            
            # Check encrypted_fields existence
            logger.info("STEP 9.2: Checking for encrypted_fields in report")
            if "encrypted_fields" not in report_copy:
                logger.warning(f"Report {report_id} has no encrypted_fields key")
                logger.info("EARLY RETURN: Returning report without decryption (no encrypted_fields key)")
                return report_copy
            
            # Check encrypted_fields not empty
            logger.info("STEP 9.3: Checking if encrypted_fields is not empty")
            if not report_copy["encrypted_fields"]:
                logger.warning(f"Report {report_id} has empty encrypted_fields value")
                logger.info("EARLY RETURN: Returning report without decryption (empty encrypted_fields)")
                return report_copy
            
            # Parse encrypted fields
            logger.info("STEP 9.4: Parsing encrypted fields")
            logger.debug(f"encrypted_fields type: {type(report_copy['encrypted_fields'])}")
            if isinstance(report_copy["encrypted_fields"], str):
                logger.debug(f"encrypted_fields preview: {report_copy['encrypted_fields'][:50]}...")
            
            encrypted_fields = {}
            try:
                # Handle string format (JSON string)
                if isinstance(report_copy["encrypted_fields"], str):
                    logger.info("STEP 9.4.1: Parsing encrypted_fields from JSON string")
                    try:
                        encrypted_fields = json.loads(report_copy["encrypted_fields"])
                        logger.info(f"Successfully parsed encrypted_fields JSON for report {report_id}")
                    except json.JSONDecodeError as json_err:
                        logger.error(f"JSON DECODE ERROR: Failed to parse encrypted_fields: {json_err}")
                        logger.error(f"JSON STRING: {report_copy['encrypted_fields'][:100]}...")  # Log a truncated version
                        logger.info("EARLY RETURN: Returning report without decryption (JSON parse failure)")
                        return report_copy
                # Handle dict format
                elif isinstance(report_copy["encrypted_fields"], dict):
                    logger.info("STEP 9.4.2: Using encrypted_fields directly (already a dict)")
                    encrypted_fields = report_copy["encrypted_fields"]
                else:
                    # Unknown format
                    logger.warning(f"UNEXPECTED TYPE: encrypted_fields has type: {type(report_copy['encrypted_fields'])}")
                    logger.info("EARLY RETURN: Returning report without decryption (unexpected type)")
                    return report_copy
                
                # Log encrypted fields for debugging
                logger.info(f"STEP 9.5: Found {len(encrypted_fields)} encrypted fields: {list(encrypted_fields.keys())}")
                
                # Process each field
                logger.info("STEP 9.6: Beginning decryption of individual fields")
                decrypted_count = 0
                error_count = 0
                
                for field, encrypted_value in encrypted_fields.items():
                    logger.info(f"Processing field: {field}")
                    
                    if not encrypted_value:
                        logger.warning(f"Empty encrypted value for field {field} - skipping")
                        continue
                    
                    try:
                        logger.info(f"STEP 9.6.1: Decrypting field {field}")
                        logger.debug(f"Encrypted value type: {type(encrypted_value)}")
                        if isinstance(encrypted_value, str):
                            logger.debug(f"Encrypted value preview: {encrypted_value[:20]}...")
                        
                        # Attempt decryption
                        report_copy[field] = await report_processor.decrypt_pii(encrypted_value)
                        logger.info(f"Successfully decrypted field {field}")
                        decrypted_count += 1
                    except Exception as field_error:
                        error_count += 1
                        logger.error(f"FIELD DECRYPTION ERROR: Failed to decrypt field {field}: {field_error}")
                        logger.error(f"FIELD ERROR TRACEBACK: {traceback.format_exc()}")
                        report_copy[field] = f"[Decryption Error: {field}]"  # Set an error indicator
                
                logger.info(f"STEP 9.7: Decryption summary: {decrypted_count} succeeded, {error_count} failed")
            except Exception as parse_error:
                logger.error(f"STRUCTURE ERROR: Error processing encrypted fields structure: {parse_error}")
                logger.error(f"STRUCTURE ERROR TRACEBACK: {traceback.format_exc()}")
                # Continue with unmodified report
        except Exception as e:
            logger.error(f"CRITICAL DECRYPTION ERROR: Error during overall decryption process: {e}")
            logger.error(f"CRITICAL ERROR TRACEBACK: {traceback.format_exc()}")
            # Return original report so the API call doesn't fail completely
        
        # Return the final result
        logger.info("STEP 10: Preparing to return processed report")
        logger.debug(f"Final report keys: {list(report_copy.keys())}")
        logger.info(f"===== END: get_student_report endpoint for report_id={report_id} =====")
        
        return report_copy  # Return the potentially modified copy
    
    except HTTPException as http_ex:
        logger.info(f"Raising HTTP exception: {http_ex.status_code} - {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: Unhandled exception in get_student_report: {e}")
        logger.error(f"UNEXPECTED ERROR TRACEBACK: {traceback.format_exc()}")
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
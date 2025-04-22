# Azure Function code (update_progress/__init__.py)
import logging
import json
import azure.functions as func
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing progress update request')
    
    try:
        # Get request body
        req_body = req.get_json()
        
        # Extract data
        plan_id = req_body.get('plan_id')
        activity_id = req_body.get('activity_id')
        status = req_body.get('status')
        student_id = req_body.get('student_id')
        
        if not all([plan_id, activity_id, status, student_id]):
            return func.HttpResponse(
                "Please provide plan_id, activity_id, status, and student_id",
                status_code=400
            )
        
        # Initialize Search client
        search_endpoint = "https://your-search-service.search.windows.net"
        search_key = "your-search-key"
        plans_index = "learning-plans"
        
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=plans_index,
            credential=AzureKeyCredential(search_key)
        )
        
        # Get the learning plan
        plan = search_client.get_document(key=plan_id)
        
        # Verify student ownership
        if plan.get('student_id') != student_id:
            return func.HttpResponse(
                "You don't have permission to update this plan",
                status_code=403
            )
        
        # Update activity status
        activity_found = False
        activities = plan.get('activities', [])
        
        for i, activity in enumerate(activities):
            if activity.get('id') == activity_id:
                activities[i]['status'] = status
                if status == 'completed':
                    activities[i]['completed_at'] = datetime.utcnow().isoformat()
                activity_found = True
                break
        
        if not activity_found:
            return func.HttpResponse(
                "Activity not found in learning plan",
                status_code=404
            )
        
        # Calculate progress percentage
        total_activities = len(activities)
        completed_activities = sum(1 for a in activities if a.get('status') == 'completed')
        progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
        
        # Determine plan status
        plan_status = 'not_started'
        if completed_activities == total_activities:
            plan_status = 'completed'
        elif completed_activities > 0:
            plan_status = 'in_progress'
        
        # Update plan in Azure AI Search
        plan['activities'] = activities
        plan['progress_percentage'] = progress_percentage
        plan['status'] = plan_status
        plan['updated_at'] = datetime.utcnow().isoformat()
        
        result = search_client.upload_documents(documents=[plan])
        
        if result[0].succeeded:
            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": "Activity status updated",
                    "progress_percentage": progress_percentage,
                    "plan_status": plan_status
                }),
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                "Failed to update activity status",
                status_code=500
            )
        
    except Exception as e:
        logging.error(f"Error updating progress: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )
# backend/api/content_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.user import User
from models.content import Content, ContentType
from auth.authentication import get_current_user
from services.enhanced_recommendation_service import get_recommendation_service
from utils.vector_store import get_vector_store
from utils.multimedia_content_processor import get_content_processor, process_and_index_content

# Create router
router = APIRouter(prefix="/content", tags=["content"])

@router.get("/recommendations")
async def get_content_recommendations(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    limit: int = Query(10, description="Maximum number of recommendations"),
    current_user: Dict = Depends(get_current_user)
):
    """Get personalized content recommendations."""
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get recommendation service
        recommendation_service = await get_recommendation_service()
        
        # Get recommendations
        recommendations = await recommendation_service.get_personalized_recommendations(
            user=user,
            subject=subject,
            content_type=content_type,
            limit=limit
        )
        
        # Return list of dictionaries for JSON response
        return [item.dict() for item in recommendations]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations: {str(e)}"
        )

@router.get("/recommendations/by-type")
async def get_recommendations_by_type(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    limit_per_type: int = Query(5, description="Maximum number of recommendations per type"),
    current_user: Dict = Depends(get_current_user)
):
    """Get personalized content recommendations organized by content type."""
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get recommendation service
        recommendation_service = await get_recommendation_service()
        
        # Get recommendations by type
        recommendations = await recommendation_service.get_recommendations_by_type(
            user=user,
            subject=subject,
            limit=limit_per_type
        )
        
        # Convert Content objects to dictionaries
        response = {}
        for content_type, items in recommendations.items():
            response[content_type] = [item.dict() for item in items]
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations by type: {str(e)}"
        )

@router.get("/similar/{content_id}")
async def get_similar_content(
    content_id: str = Path(..., description="Content ID to find similar items for"),
    limit: int = Query(5, description="Maximum number of similar items"),
    current_user: Dict = Depends(get_current_user)
):
    """Get content similar to a specified content item."""
    try:
        # Get recommendation service
        recommendation_service = await get_recommendation_service()
        
        # Get similar content
        similar_items = await recommendation_service.get_similar_content(
            content_id=content_id,
            limit=limit
        )
        
        # Return list of dictionaries for JSON response
        return [item.dict() for item in similar_items]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting similar content: {str(e)}"
        )

@router.get("/media/{media_type}")
async def get_content_by_media_type(
    media_type: str = Path(..., description="Media type (video, audio, text, interactive)"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    limit: int = Query(10, description="Maximum number of items"),
    current_user: Dict = Depends(get_current_user)
):
    """Get content of a specific media type."""
    try:
        # Validate media type
        valid_media_types = ["video", "audio", "text", "interactive"]
        if media_type.lower() not in valid_media_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid media type. Must be one of: {', '.join(valid_media_types)}"
            )
        
        # Get recommendation service
        recommendation_service = await get_recommendation_service()
        
        # Get content by media type
        content_items = await recommendation_service.get_content_by_media_type(
            media_type=media_type,
            subject=subject,
            limit=limit
        )
        
        # Return list of dictionaries for JSON response
        return [item.dict() for item in content_items]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting content by media type: {str(e)}"
        )

@router.get("/{content_id}")
async def get_content_by_id(
    content_id: str = Path(..., description="Content ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific content item by ID."""
    try:
        # Get vector store
        vector_store = await get_vector_store()
        
        # Get content
        content = await vector_store.get_content(content_id)
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found"
            )
        
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting content: {str(e)}"
        )

@router.post("/")
async def add_content(
    content_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Add new content to the system."""
    try:
        # Ensure current user has appropriate permissions
        # This would be more extensive in a production system
        if "admin" not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can add content"
            )
        
        # Get content processor
        content_processor = await get_content_processor()
        
        # Process the content
        content_url = content_data.get("url")
        if not content_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content URL is required"
            )
        
        # Process and index the content
        processed_content = await process_and_index_content(content_url, content_data)
        
        return processed_content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding content: {str(e)}"
        )

@router.put("/{content_id}")
async def update_content(
    content_id: str = Path(..., description="Content ID"),
    updated_fields: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Update specific fields of a content item."""
    try:
        # Ensure current user has appropriate permissions
        if "admin" not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can update content"
            )
        
        # Get vector store
        vector_store = await get_vector_store()
        
        # Verify content exists
        existing_content = await vector_store.get_content(content_id)
        if not existing_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found"
            )
        
        # Update the content
        success = await vector_store.update_content(content_id, updated_fields)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update content"
            )
        
        # Get and return the updated content
        updated_content = await vector_store.get_content(content_id)
        return updated_content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating content: {str(e)}"
        )

@router.delete("/{content_id}")
async def delete_content(
    content_id: str = Path(..., description="Content ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a content item."""
    try:
        # Ensure current user has appropriate permissions
        if "admin" not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can delete content"
            )
        
        # Get vector store
        vector_store = await get_vector_store()
        
        # Verify content exists
        existing_content = await vector_store.get_content(content_id)
        if not existing_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found"
            )
        
        # Delete the content
        success = await vector_store.delete_content(content_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete content"
            )
        
        return {"message": f"Content with ID {content_id} successfully deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting content: {str(e)}"
        )

@router.post("/search")
async def search_content(
    query: str = Body(..., embed=True),
    subject: Optional[str] = Body(None, embed=True),
    content_type: Optional[str] = Body(None, embed=True),
    limit: int = Body(10, embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """Search for content using vector similarity."""
    try:
        # Build filter expression
        filter_parts = []
        if subject:
            filter_parts.append(f"subject eq '{subject}'")
        if content_type:
            filter_parts.append(f"content_type eq '{content_type}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Get vector store
        vector_store = await get_vector_store()
        
        # Perform vector search
        results = await vector_store.vector_search(
            query_text=query,
            filter_expression=filter_expression,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching content: {str(e)}"
        )

@router.get("/metadata/{content_id}")
async def analyze_content_metadata(
    content_id: str = Path(..., description="Content ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Analyze content metadata for a specific content item."""
    try:
        # Get recommendation service
        recommendation_service = await get_recommendation_service()
        
        # Analyze content metadata
        metadata_analysis = await recommendation_service.analyze_content_metadata(content_id)
        
        return metadata_analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing content metadata: {str(e)}"
        )

# Export router
content_router = router
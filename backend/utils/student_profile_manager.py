"""Student Profile Manager module.

This module handles the creation, updating, and retrieval of student profiles
in the Azure AI Search index based on information extracted from student reports.
"""

import asyncio
import logging
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from services.search_service import get_search_service
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Configure logger
logger = logging.getLogger(__name__)

class StudentProfileManager:
    """Manager for student profiles in Azure AI Search."""
    
    def __init__(self):
        """Initialize the student profile manager."""
        self.search_service = None
        self.openai_client = None
        self.student_profiles_index_name = "student-profiles"
        
    async def ensure_initialized(self):
        """Ensure the profile manager is initialized."""
        if not self.search_service:
            self.search_service = await get_search_service()
            
        if not self.openai_client:
            self.openai_client = await get_openai_adapter()
            
        # Check if the student profiles index exists
        if self.search_service:
            exists = await self.search_service.check_index_exists(self.student_profiles_index_name)
            if not exists:
                logger.warning(f"Student profiles index '{self.student_profiles_index_name}' does not exist.")
                logger.info("Trying to create the index...")
                
                # Try to import and run the index creation script
                try:
                    import sys
                    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
                    sys.path.append(script_path)
                    
                    # Try different import approaches
                    try:
                        from create_student_profiles_index import create_student_profiles_index
                        success = await create_student_profiles_index()
                    except ImportError:
                        # Try alternative import path
                        from scripts.create_student_profiles_index import create_student_profiles_index
                        success = await create_student_profiles_index()
                    if success:
                        logger.info("Successfully created student profiles index")
                    else:
                        logger.error("Failed to create student profiles index")
                except Exception as script_err:
                    logger.error(f"Error running index creation script: {script_err}")
    
    async def extract_profile_from_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract profile information from a student report.
        
        Args:
            report_data: The processed student report data
            
        Returns:
            Dictionary containing extracted profile information
        """
        await self.ensure_initialized()
        
        if not self.openai_client:
            logger.error("OpenAI client not available, cannot extract profile information")
            return {}
        
        try:
            # Extract student name from report if available
            student_name = None
            if "student_name" in report_data and report_data["student_name"]:
                student_name = report_data["student_name"]
            
            # Generate a prompt to extract student profile information
            raw_text = report_data.get("raw_extracted_text", "")
            subjects = report_data.get("subjects", [])
            general_comments = report_data.get("general_comments", "")
            
            # Prepare subject data for the prompt
            subject_text = ""
            for subject in subjects:
                subject_text += f"Subject: {subject.get('name', '')}\n"
                subject_text += f"Achievement: {subject.get('achievement_level', '')}\n"
                subject_text += f"Comments: {subject.get('comments', '')}\n"
                
                strengths = subject.get('strengths', [])
                if strengths:
                    subject_text += "Strengths:\n"
                    for strength in strengths:
                        subject_text += f"- {strength}\n"
                
                areas_for_improvement = subject.get('areas_for_improvement', [])
                if areas_for_improvement:
                    subject_text += "Areas for Improvement:\n"
                    for area in areas_for_improvement:
                        subject_text += f"- {area}\n"
                
                subject_text += "\n"
            
            # Build the prompt
            prompt = f"""
            Extract student profile information from the following student report.
            
            Based on the report, identify the following:
            - full_name: The student's full name
            - gender: The student's gender (male, female, or unknown if not clear)
            - grade_level: The student's grade level as a number (e.g., 3 for 3rd grade)
            - learning_style: The student's learning style based on the report (e.g., visual, auditory, kinesthetic, etc.)
            - strengths: A list of the student's academic and personal strengths
            - areas_for_improvement: A list of areas where the student needs to improve
            - interests: A list of the student's interests and subjects they engage with most
            
            IMPORTANT FORMATTING INSTRUCTIONS:
            1. Format the response as a valid JSON object
            2. For lists like strengths, areas_for_improvement, and interests, always use proper JSON array syntax like ["item1", "item2"]
            3. Do not use single strings where arrays are expected
            4. For grade_level, provide a numeric value (e.g., 5 for 5th grade)
            5. If you cannot determine a value with confidence, use null
            
            School Information:
            School Name: {report_data.get('school_name', '')}
            School Year: {report_data.get('school_year', '')}
            Term: {report_data.get('term', '')}
            Grade Level: {report_data.get('grade_level', '')}
            
            Subject Assessments:
            {subject_text}
            
            General Comments:
            {general_comments}
            
            Raw Report Text (Excerpt):
            {raw_text[:2000]}  # Truncate to stay within token limits
            """
            
            # Get the completion
            response = await self.openai_client.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            content = response["choices"][0]["message"]["content"]
            profile_data = json.loads(content)
            
            # Add report information
            profile_data["school_name"] = report_data.get("school_name")
            profile_data["teacher_name"] = report_data.get("teacher_name")
            
            # Ensure profile_data has required fields
            if "strengths" not in profile_data or not profile_data["strengths"]:
                profile_data["strengths"] = []
            
            if "areas_for_improvement" not in profile_data or not profile_data["areas_for_improvement"]:
                profile_data["areas_for_improvement"] = []
            
            if "interests" not in profile_data or not profile_data["interests"]:
                profile_data["interests"] = []
            
            # Use the original report data's student_name if extracted name is None
            if not profile_data.get("full_name") and student_name:
                profile_data["full_name"] = student_name
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error extracting profile from report: {e}")
            return {}
    
    async def find_student_profile_by_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a student profile by name in the Azure AI Search index.
        
        Args:
            full_name: The student's full name to search for
            
        Returns:
            Student profile dictionary or None if not found
        """
        if not full_name:
            logger.warning("Cannot search for student profile: no name provided")
            return None
        
        await self.ensure_initialized()
        
        if not self.search_service:
            logger.error("Search service not available, cannot find student profile")
            return None
        
        try:
            # Create a filter expression to search for the exact name
            filter_expression = f"full_name eq '{full_name}'"
            
            # Search for the student profile
            profiles = await self.search_service.search_documents(
                index_name=self.student_profiles_index_name,
                query="*",
                filter=filter_expression,
                top=1
            )
            
            if not profiles or len(profiles) == 0:
                logger.info(f"No student profile found for: {full_name}")
                return None
            
            logger.info(f"Found student profile for: {full_name}")
            return profiles[0]
            
        except Exception as e:
            logger.error(f"Error finding student profile by name: {e}")
            return None
    
    async def create_or_update_student_profile(
        self, 
        report_data: Dict[str, Any], 
        report_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new student profile or update an existing one.
        
        Args:
            report_data: The processed student report data
            report_id: The ID of the report used to extract profile
            
        Returns:
            Created or updated student profile, or None if failed
        """
        await self.ensure_initialized()
        
        if not self.search_service:
            logger.error("Search service not available, cannot create/update student profile")
            return None
        
        try:
            # Extract profile information from report
            profile_data = await self.extract_profile_from_report(report_data)
            
            if not profile_data or "full_name" not in profile_data or not profile_data["full_name"]:
                logger.error("Failed to extract student name from report")
                return None
            
            # Check if the student profile already exists
            existing_profile = await self.find_student_profile_by_name(profile_data["full_name"])
            
            if existing_profile:
                logger.info(f"Updating existing student profile for: {profile_data['full_name']}")
                
                # Update existing profile
                profile_id = existing_profile["id"]
                
                # Merge the profile data
                updated_profile = self._merge_profile_data(existing_profile, profile_data, report_id)
                
                # Generate embedding for the profile
                embedding = await self._generate_profile_embedding(updated_profile)
                if embedding:
                    updated_profile["embedding"] = embedding
                
                # Update the profile in the index
                success = await self.search_service.index_document(
                    index_name=self.student_profiles_index_name,
                    document=updated_profile
                )
                
                if success:
                    logger.info(f"Successfully updated student profile with ID: {profile_id}")
                    return updated_profile
                else:
                    logger.error(f"Failed to update student profile with ID: {profile_id}")
                    return None
            
            else:
                logger.info(f"Creating new student profile for: {profile_data['full_name']}")
                
                # Create a new profile
                profile_id = str(uuid.uuid4())
                
                # Prepare the profile document
                new_profile = {
                    "id": profile_id,
                    "full_name": profile_data["full_name"],
                    "gender": profile_data.get("gender"),
                    "grade_level": profile_data.get("grade_level"),
                    "learning_style": profile_data.get("learning_style"),
                    "strengths": profile_data.get("strengths", []),
                    "interests": profile_data.get("interests", []),
                    "areas_for_improvement": profile_data.get("areas_for_improvement", []),
                    "school_name": profile_data.get("school_name"),
                    "teacher_name": profile_data.get("teacher_name"),
                    "report_ids": [report_id],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "last_report_date": datetime.utcnow().isoformat()
                }
                
                # Generate embedding for the profile
                embedding = await self._generate_profile_embedding(new_profile)
                if embedding:
                    new_profile["embedding"] = embedding
                
                # Index the profile
                success = await self.search_service.index_document(
                    index_name=self.student_profiles_index_name,
                    document=new_profile
                )
                
                if success:
                    logger.info(f"Successfully created student profile with ID: {profile_id}")
                    return new_profile
                else:
                    logger.error(f"Failed to create student profile with ID: {profile_id}")
                    return None
                
        except Exception as e:
            logger.error(f"Error creating/updating student profile: {e}")
            return None
    
    def _merge_profile_data(
        self, 
        existing_profile: Dict[str, Any], 
        new_profile_data: Dict[str, Any],
        report_id: str
    ) -> Dict[str, Any]:
        """
        Merge existing profile with new profile data from a report.
        
        Args:
            existing_profile: The existing student profile from the index
            new_profile_data: The new profile data extracted from the report
            report_id: The ID of the report used to extract new profile data
            
        Returns:
            Merged profile data
        """
        merged_profile = existing_profile.copy()
        
        # Update non-list fields if they have values in the new profile
        for field in ["gender", "grade_level", "learning_style", "school_name", "teacher_name"]:
            if field in new_profile_data and new_profile_data[field]:
                merged_profile[field] = new_profile_data[field]
        
        # Update list fields by adding new unique items
        for field in ["strengths", "interests", "areas_for_improvement"]:
            if field in new_profile_data and new_profile_data[field]:
                # Ensure the field exists in the merged profile
                if field not in merged_profile or not merged_profile[field]:
                    merged_profile[field] = []
                
                # Get the existing items as a set for quick lookup
                existing_items = set(merged_profile[field])
                
                # Add new unique items
                for item in new_profile_data[field]:
                    if item not in existing_items:
                        merged_profile[field].append(item)
                        existing_items.add(item)
        
        # Add the report ID to the list of report IDs
        if "report_ids" not in merged_profile or not merged_profile["report_ids"]:
            merged_profile["report_ids"] = []
        
        if report_id not in merged_profile["report_ids"]:
            merged_profile["report_ids"].append(report_id)
        
        # Update timestamps
        merged_profile["updated_at"] = datetime.utcnow().isoformat()
        merged_profile["last_report_date"] = datetime.utcnow().isoformat()
        
        return merged_profile
    
    async def _generate_profile_embedding(self, profile_data: Dict[str, Any]) -> Optional[List[float]]:
        """
        Generate an embedding for the student profile.
        
        Args:
            profile_data: The student profile data
            
        Returns:
            Embedding vector or None if generation failed
        """
        if not self.openai_client:
            logger.error("OpenAI client not available, cannot generate profile embedding")
            return None
        
        try:
            # Prepare text for embedding
            text_parts = [
                f"Student Profile for: {profile_data.get('full_name', 'Unknown Student')}",
                f"Gender: {profile_data.get('gender', 'Unknown')}",
                f"Grade Level: {profile_data.get('grade_level', 'Unknown')}",
                f"Learning Style: {profile_data.get('learning_style', 'Unknown')}",
                f"School: {profile_data.get('school_name', 'Unknown')}",
            ]
            
            # Add strengths
            strengths = profile_data.get("strengths", [])
            if strengths:
                text_parts.append("Strengths:")
                for strength in strengths:
                    text_parts.append(f"- {strength}")
            
            # Add interests
            interests = profile_data.get("interests", [])
            if interests:
                text_parts.append("Interests:")
                for interest in interests:
                    text_parts.append(f"- {interest}")
            
            # Add areas for improvement
            areas_for_improvement = profile_data.get("areas_for_improvement", [])
            if areas_for_improvement:
                text_parts.append("Areas for Improvement:")
                for area in areas_for_improvement:
                    text_parts.append(f"- {area}")
            
            # Combine text parts
            text = "\n".join(text_parts)
            
            # Generate embedding
            embedding = await self.openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating profile embedding: {e}")
            return None

# Create a singleton instance
_profile_manager_instance = None

async def get_student_profile_manager():
    """Get or create the student profile manager singleton."""
    global _profile_manager_instance
    
    if _profile_manager_instance is None:
        _profile_manager_instance = StudentProfileManager()
        await _profile_manager_instance.ensure_initialized()
    
    return _profile_manager_instance
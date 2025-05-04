# Debugging Student Profile Indexing

## Issue Summary
After uploading student reports, the information was successfully being injected into the `student-reports` index, but not into the `student-profiles` index.

## Root Cause Analysis
Several potential issues were identified that could prevent student profile information from being properly indexed:

1. The `student-profiles` index might not exist when attempting to index profiles
2. There could be import errors when trying to create the index
3. Potential errors in the document structure causing schema mismatches
4. Inadequate error logging preventing identification of the specific issue

## Changes Made

### 1. Enhanced Error Handling in Profile Manager
- Added robust error handling in the `create_or_update_student_profile` method
- Added detailed logging to identify schema mismatches and other errors
- Improved index existence verification before attempting to index

### 2. Fixed Import Issues
- Added proper import paths in `create_student_profiles_index.py` script
- Added missing `traceback` import in `student_profile_manager.py`
- Enhanced the mechanism for creating the student-profiles index when it doesn't exist
- Added subprocess execution capability if standard imports fail

### 3. Added Debug Endpoints
- Enhanced debug API endpoints to check and recreate indexes
- Added new endpoint for directly extracting profiles from reports
- Added more detailed logging to track the profile creation and indexing process

### 4. Schema Consistency
- Ensured all necessary fields are defined in the index schema
- Added error reporting to identify any problematic fields in the document structure

## Debug Tools for Verifying
The following debug endpoints can be used to verify and fix issues:

1. `GET /debug/check-indexes` - Check status of all Azure AI Search indexes
2. `POST /debug/recreate-index/student-profiles` - Recreate the student-profiles index
3. `POST /debug/extract-profile/{report_id}` - Attempt to extract and index a profile from a specific report

## How to Use These Tools

### 1. Check Index Status
```bash
curl -X GET "http://localhost:8000/debug/check-indexes" -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Recreate the Student Profiles Index
```bash
curl -X POST "http://localhost:8000/debug/recreate-index/student-profiles" -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Extract a Profile from an Existing Report
```bash
curl -X POST "http://localhost:8000/debug/extract-profile/YOUR_REPORT_ID" -H "Authorization: Bearer YOUR_TOKEN"
```

## Next Steps
If the issue persists, check the application logs for any of these patterns:
- `DEBUG: Exception during profile indexing:` - Look for specific error messages that would indicate schema mismatches
- `CRITICAL ERROR: Index 'student-profiles' does not exist` - This would indicate the index wasn't created properly
- `DEBUG: Field value:` - Look for any problematic field values that might be causing issues

You can also:
1. Try manually recreating the index via the debug endpoint
2. Extract a profile from a known good report to see if it works
3. Check the Azure AI Search portal to verify the index structure
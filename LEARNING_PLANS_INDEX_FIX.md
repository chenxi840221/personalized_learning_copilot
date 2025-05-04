# Learning Plans Index Fix

This document outlines the issues with the learning plans index and provides solutions to fix them.

## Issue Description

The application encounters an error when creating profile-based learning plans:

```
INFO:services.azure_learning_plan_service:Sending update request to Azure Search index: learning-plans
ERROR:services.azure_learning_plan_service:Azure Search error: 400 - {"error":{"code":"","message":"The request is invalid. Details: The property 'activities_week_1' does not exist on type 'search.documentFields' or is not present in the API version '2023-07-01-Preview'. Make sure to only use property names that are defined by the type."}}
```

This error occurs because the Azure Learning Plan Service attempts to use a chunking approach where activities are split by week into fields like 'activities_week_1', 'activities_week_2', etc. However, these fields are not defined in the Azure Search index schema.

## Solution

We've implemented a two-part solution:

1. **Update Index Schema**: Create a new script that updates the learning plans index to include the chunking fields.
2. **Improve Error Handling**: Modify the Azure Learning Plan Service to handle cases where the chunking fields aren't available.

## Implementation Details

### 1. Index Schema Update Script

The new script `backend/scripts/update_learning_plans_index.py` will:

- Update the learning-plans index to include fields for chunking
- Add fields like activities_chunking, activities_weeks, and activities_week_1 through activities_week_8
- Migrate existing data to the new schema
- Handle any existing chunked data appropriately

### 2. Service Layer Updates

Modified the Azure Learning Plan Service in `backend/services/azure_learning_plan_service.py` to:

- Use a try-catch block around the chunking logic
- Only use valid week fields (1-8) as defined in the schema
- Store any overflow weeks in the activities_json field
- Fall back to using activities_json if any errors occur during chunking

## How to Apply the Fix

1. Run the update script to modify the index schema:

```bash
cd /mnt/c/workspace/code/personalized_learning_copilot
python backend/scripts/update_learning_plans_index.py
```

2. After updating the schema, the code changes will automatically handle the fallback mechanism if needed.

## Verification

To verify the fix:

1. Create a profile-based learning plan with a long learning period (e.g., one month or two months).
2. Check that the learning plan is created successfully without errors.
3. Retrieve the learning plan and verify that all activities are accessible.

## Additional Notes

- The maximum supported number of week chunks is 8 (activities_week_1 through activities_week_8).
- For learning periods longer than 8 weeks, activities beyond week 8 will be stored in the activities_json field.
- The service will automatically handle mixed storage of activities across week chunks and the activities_json field.

## Troubleshooting

If issues persist:

1. Check the logs for any errors during the schema update process
2. Verify that the chunking fields were properly added to the index
3. Ensure the updated code is deployed and running
4. Try using a shorter learning period (1-2 weeks) to see if the issue is related to the number of activities

For any persistent issues, consider temporarily disabling chunking by modifying the `use_weekly_chunking` condition in the Azure Learning Plan Service.
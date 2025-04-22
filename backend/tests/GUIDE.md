# Test Fix Guide for Personalized Learning Co-pilot

This guide explains the changes made to fix the test failures in the Personalized Learning Co-pilot codebase. The main issues were:

1. Settings initialization errors with CORS_ORIGINS environment variable
2. Import error for `VideoAnalysisParams` in the ABC Education scraper
3. Configuration problems in the test environment

## Summary of Changes

### 1. Fixed Settings Configuration (config/settings.py)
- Modified the CORS_ORIGINS handling to be more robust 
- Changed it to be a property method that handles parsing errors
- Added proper error handling for initialization failures
- Fixed circular import issues with cognitive services utils

### 2. Fixed ABC Education Scraper (scrapers/abc_edu_scraper.py)
- Removed problematic import: `VideoAnalysisParams` 
- Added null checks for Azure service clients
- Made service initialization more robust
- Improved error handling in `extract_video_content` and other methods
- Made `run_scraper()` return the content items for testing

### 3. Created Test Settings Module (tests/test_settings.py)
- Created a dedicated `TestSettings` class for tests
- Pre-configured all settings with test values
- Used hardcoded values for properties to avoid import issues
- Disabled loading from .env file in test environment

### 4. Updated Test Files
- Modified ABC Education Scraper tests to use test settings
- Added proper patching to avoid environment variable issues
- Fixed imports and test assertions

### 5. Enhanced Test Runner (tests/run_tests.py)
- Updated to use the test settings module
- Added proper patching for external services
- Improved test discovery and execution

## How to Apply These Changes

### Step 1: Update settings.py
Replace your current `config/settings.py` with the fixed version. The key change is making `CORS_ORIGINS` a property method that properly handles parsing errors.

### Step 2: Update ABC Education Scraper
Replace your current `scrapers/abc_edu_scraper.py` with the fixed version. The main fixes are:
- Removed the problematic `VideoAnalysisParams` import
- Added null checks for Azure clients
- Improved error handling

### Step 3: Add Test Settings
Add the new `tests/test_settings.py` file to your project. This provides a consistent test environment.

### Step 4: Update Test Runner
Replace your `tests/run_tests.py` with the fixed version. This ensures proper patching and environment setup.

### Step 5: Update ABC Education Scraper Test
Replace your `tests/test_abc_edu_scraper.py` with the fixed version. The key change is using the test settings and proper mocking.

## Running the Tests

After applying these changes, you can run the tests using:

```bash
cd backend/tests
python run_tests.py
```

To run a specific test:

```bash
python run_tests.py --pattern test_abc_edu_scraper
```

## Important Notes

1. **Environment Variables**: The fixes ensure that tests don't rely on actual environment variables, which provides more consistent test results.

2. **Mocking Approach**: External services are now properly mocked to prevent actual API calls during testing.

3. **Circular Imports**: The fixes resolve circular import issues in the codebase.

4. **Error Handling**: Improved error handling ensures that services degrade gracefully if initialization fails.

5. **Future Improvements**: Consider using a proper dependency injection approach for services to make testing even easier.

## Troubleshooting

If you encounter further issues:

1. **Check for Missing Dependencies**: Ensure all required packages are installed.
2. **Verify Settings**: Make sure test settings are being properly used in all test files.
3. **Check Patching**: Ensure all external services are properly patched in tests.
4. **Debug Mode**: Use the `--verbose` flag for more detailed test output:
   ```bash
   python run_tests.py --verbose
   ```

These changes should resolve the immediate test failures. For further assistance, please consult the project documentation or reach out to the DevOps team.
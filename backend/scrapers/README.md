# ABC Education Scraper

A robust web scraper for extracting educational content from the ABC Education website to populate the Personalized Learning Co-pilot database.

## Overview

This scraper is designed to collect educational content from the [ABC Education website](https://www.abc.net.au/education/subjects-and-topics) including:

- Subjects (Mathematics, Science, English, etc.)
- Year levels (Years F-2, 3-4, 5-6, etc.)
- Topics (within each subject)
- Educational content (videos, articles, quizzes, worksheets, etc.)

The scraper intelligently handles dynamic content loading by interacting with "Load More" buttons until all content is retrieved. It also accurately categorizes content by type, difficulty level, and appropriate grade levels.

## Features

- **Dynamic Content Handling**: Properly handles JavaScript-rendered content and pagination through "Load More" buttons
- **Year Level Navigation**: Identifies and navigates different year level sections within subjects
- **Content Classification**: Automatically categorizes content by type, difficulty, and grade level
- **Embedding Generation**: Creates vector embeddings for all content using Azure OpenAI
- **Azure AI Search Integration**: Uploads processed content directly to Azure AI Search for the learning co-pilot application
- **Comprehensive Logging**: Detailed logging of the scraping process

## Installation

### Prerequisites

- Python 3.8+
- Azure OpenAI access (for embeddings)
- Azure AI Search service (for storing content)

### Setup

1. Ensure the scraper code is in your project's `backend/scrapers` directory
2. Install the required dependencies:

```bash
pip install -r scraper_dependencies.txt
# Or add the dependencies to your main requirements.txt
```

3. Install Playwright and browser binaries:

```bash
pip install playwright
playwright install chromium
```

4. Configure your environment variables in `.env` file:

```
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-service.openai.azure.com/
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=your-gpt-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your-embedding-deployment-name

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=educational-content
```

## Usage

### Command Line Interface

The scraper can be run directly from the command line using the provided CLI tool:

```bash
python backend/scraper_cli.py [options]
```

#### Options

- `--subjects N`: Limit scraping to N subjects (default: all subjects)
- `--save`: Save content to Azure AI Search
- `--output FILE`: Save scraped content to a JSON file
- `--verbose`: Enable verbose logging
- `--headless`: Run browser in headless mode (default: true)
- `--install-deps`: Install required dependencies (Playwright)

### Examples

Run the scraper for all subjects and save to Azure AI Search:

```bash
python backend/scraper_cli.py --save
```

Run the scraper for 2 subjects and save output to a file:

```bash
python backend/scraper_cli.py --subjects 2 --output ./data/abc_content.json
```

Install dependencies and run with verbose logging:

```bash
python backend/scraper_cli.py --install-deps --verbose
```

### Integration with Learning Co-pilot

The scraper can also be imported and used directly in Python code:

```python
from scrapers.abc_edu_scraper_playwright import run_scraper

async def update_content_database():
    # Run the scraper
    content_items = await run_scraper(subject_limit=None)
    print(f"Scraped {len(content_items)} items")
    
    # Content is automatically saved to Azure AI Search if credentials are provided
```

## Structure of Scraped Data

Each content item includes:

```json
{
  "id": "unique-uuid",
  "title": "Content Title",
  "description": "Content Description",
  "content_type": "video|article|interactive|quiz|worksheet|lesson|activity",
  "subject": "Subject Name",
  "topics": ["Topic 1", "Topic 2"],
  "url": "https://www.abc.net.au/education/...",
  "source": "ABC Education",
  "difficulty_level": "beginner|intermediate|advanced",
  "grade_level": [3, 4, 5],
  "duration_minutes": 15,
  "keywords": ["keyword1", "keyword2"],
  "created_at": "2023-04-23T12:34:56.789Z",
  "updated_at": "2023-04-23T12:34:56.789Z",
  "embedding": [0.123, 0.456, ...] // Vector embedding for search
}
```

## Scheduling Regular Updates

For production use, consider scheduling the scraper to run periodically to keep the content database updated. You can use the existing scheduler component:

1. Add the scraper to the `backend/scheduler/scheduler.py` file:

```python
# Add to existing imports
from scrapers.abc_edu_scraper_playwright import run_scraper

# Add to the SchedulerManager.start() method
scraper_job = aiocron.crontab('0 3 * * 0', func=self._run_abc_scraper, start=True)
self.jobs.append(scraper_job)
logger.info(f"Scheduled ABC Education scraper to run weekly on Sunday at 3 AM")

# Add this method to the SchedulerManager class
async def _run_abc_scraper(self):
    """Run the ABC Education scraper."""
    logger.info(f"Starting scheduled ABC Education scraper at {datetime.now()}")
    try:
        await run_scraper()
        logger.info(f"Completed scheduled ABC Education scraper at {datetime.now()}")
    except Exception as e:
        logger.error(f"Error running scheduled ABC Education scraper: {e}")
```

2. Start the scheduler service as documented in the main application README.

## Troubleshooting

### Common Issues

1. **Playwright Errors**: If you encounter browser-related issues, try installing the latest browser binaries:
   ```bash
   playwright install --with-deps chromium
   ```

2. **Rate Limiting**: If you're experiencing rate limiting, try adjusting the delay between requests by modifying the sleep timers in the code.

3. **Azure AI Search Upload Failures**: If content uploads fail, check that your index schema matches the content structure. The scraper expects an index with an embedding field of 1536 dimensions.

4. **Missing Content**: The ABC Education website structure may change. If the scraper fails to find content, check the selectors in the code and update them as needed.

### Logging

Logs are stored in the `logs` directory. Check these logs for detailed information about the scraping process and any errors that occur.

## License

This scraper is part of the Personalized Learning Co-pilot project and is subject to the same licensing terms.

## Contributing

If the website structure changes, please update the scraper code accordingly to maintain functionality.
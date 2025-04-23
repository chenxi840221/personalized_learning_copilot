#!/usr/bin/env python3
"""
ABC Education Scraper CLI tool
This script provides a command-line interface to the ABC Education scraper
which can scrape subjects and topics from the ABC Education website and
save them to Azure AI Search for the Personalized Learning Co-pilot.
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Set up project path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the scraper CLI."""
    parser = argparse.ArgumentParser(description="ABC Education Content Scraper")
    
    # Define command-line arguments
    parser.add_argument(
        "--subjects", 
        type=int, 
        default=None, 
        help="Limit the number of subjects to scrape (default: all)"
    )
    parser.add_argument(
        "--save", 
        action="store_true", 
        help="Save content to Azure AI Search"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        help="Output file path to save scraped content as JSON"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install required dependencies (Playwright)"
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Install dependencies if requested
    if args.install_deps:
        try:
            logger.info("Installing Playwright and dependencies...")
            
            # First install playwright package
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            
            # Then install browser binaries
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            logger.info("Dependencies installed successfully")
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return 1
    
    try:
        # Import the scraper module
        from scrapers.abc_edu_scraper_playwright import ABCEducationScraperPlaywright, run_scraper
        
        # Run the scraper
        logger.info(f"Starting ABC Education scraper {f'with limit {args.subjects}' if args.subjects else 'for all subjects'}")
        
        start_time = datetime.now()
        content_items = await run_scraper(subject_limit=args.subjects)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds() / 60.0
        logger.info(f"Scraping completed in {duration:.2f} minutes. Found {len(content_items)} content items.")
        
        # Save content to file if output path provided
        if args.output and content_items:
            try:
                import json
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                logger.info(f"Saving content to {output_path}")
                with open(output_path, 'w', encoding='utf-8') as f:
                    # Remove embeddings before saving to file to reduce size
                    content_for_save = []
                    for item in content_items:
                        item_copy = item.copy()
                        if 'embedding' in item_copy:
                            del item_copy['embedding']
                        content_for_save.append(item_copy)
                    
                    json.dump(content_for_save, f, indent=2)
                
                logger.info(f"Content saved to {output_path}")
            except Exception as e:
                logger.error(f"Error saving output to file: {e}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error running scraper: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    # Get OS info
    import platform
    logger.info(f"Running on {platform.system()} {platform.release()} ({platform.version()})")
    logger.info(f"Python version: {platform.python_version()}")
    
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
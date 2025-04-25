# backend/scraper_cli.py
#!/usr/bin/env python3
"""
Education Content Scraper CLI using LangChain
This script provides a command-line interface to the education content scrapers
with LangChain integration for improved content processing.
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
    parser = argparse.ArgumentParser(description="Education Content Scraper with LangChain")
    
    # Define command-line arguments
    parser.add_argument(
        "--type",
        type=str,
        choices=["legacy", "langchain"],
        default="langchain",
        help="Scraper type to use: 'legacy' for traditional scraper, 'langchain' for LangChain-enhanced (default)"
    )
    
    parser.add_argument(
        "--subjects", 
        type=int, 
        default=None, 
        help="Limit the number of subjects to scrape (default: all)"
    )
    
    parser.add_argument(
        "--resources",
        type=int,
        default=None,
        help="Limit the number of resources per subject/age group (default: all)"
    )
    
    parser.add_argument(
        "--no-content",
        action="store_true",
        help="Skip detailed content processing"
    )
    
    parser.add_argument(
        "--visible", 
        action="store_true", 
        help="Run browser in visible mode (not headless)"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        help="Output directory for scraped content"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
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
    
    # Set output directory if specified
    if args.output:
        os.environ["EDUCATION_CONTENT_OUTPUT"] = args.output
    
    try:
        # Run the appropriate scraper based on type
        if args.type == "legacy":
            # Import and run legacy scraper
            from scrapers.two_step_scraper import run_two_step_scraper
            
            start_time = datetime.now()
            result = await run_two_step_scraper(
                step="both",
                subject_limit=args.subjects,
                resource_limit=args.resources,
                headless=not args.visible
            )
            end_time = datetime.now()
            
        else:  # LangChain scraper
            # Import and run LangChain-enhanced scraper
            from scrapers.langchain_scraper import run_langchain_scraper
            
            start_time = datetime.now()
            result = await run_langchain_scraper(
                subject_limit=args.subjects,
                resource_limit=args.resources,
                process_content=not args.no_content,
                headless=not args.visible
            )
            end_time = datetime.now()
        
        # Calculate duration
        duration = (end_time - start_time).total_seconds() / 60.0
        logger.info(f"Scraping completed in {duration:.2f} minutes.")
        
        # Display results
        if isinstance(result, dict):
            logger.info("Scraping Results:")
            for key, value in result.items():
                logger.info(f"  {key}: {value}")
        
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
# backend/scrapers/two_step_scraper.py
import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('two_step_scraper.log')
    ]
)

logger = logging.getLogger(__name__)

# Import the two steps
from edu_resource_indexer import run_indexer
from content_extractor import run_extractor

async def run_two_step_scraper(
    step: str = "both",
    subject_limit: Optional[int] = None,
    resource_limit: Optional[int] = None,
    headless: bool = True,
    max_pages_per_subject: int = 10
) -> Dict[str, Any]:
    """
    Run the two-step scraper process.
    
    Args:
        step: Which step to run ('index', 'extract', or 'both')
        subject_limit: Maximum number of subjects to process
        resource_limit: Maximum number of resources per subject to process
        headless: Whether to run browser in headless mode
        max_pages_per_subject: Maximum pages to process per subject in indexing step
        
    Returns:
        Dictionary with results
    """
    results = {
        "step_1_results": None,
        "step_2_results": None
    }
    
    # Always ensure the output directory exists
    output_dir = os.path.join(os.getcwd(), "education_resources")
    os.makedirs(output_dir, exist_ok=True)
    
    # Define index path
    index_path = os.path.join(output_dir, "resource_index.json")
    
    # Step 1: Index resources
    if step in ["index", "both"]:
        logger.info("Starting Step 1: Indexing education resources...")
        
        results["step_1_results"] = await run_indexer(
            subject_limit=subject_limit,
            headless=headless,
            max_pages_per_subject=max_pages_per_subject
        )
        
        logger.info(f"Step 1 completed. Results: {results['step_1_results'].get('total_resources', 0)} resources indexed.")
    
    # Step 2: Extract content from resources
    if step in ["extract", "both"]:
        logger.info("Starting Step 2: Extracting content from education resources...")
        
        # Check if index file exists
        if not os.path.exists(index_path):
            logger.error(f"Index file not found: {index_path}")
            if step == "extract":
                return {"error": f"Index file not found: {index_path}. Run the indexer step first."}
        else:
            results["step_2_results"] = await run_extractor(
                index_path=index_path,
                subject_limit=subject_limit,
                resource_limit=resource_limit,
                headless=headless
            )
            
            logger.info(f"Step 2 completed. Results: {results['step_2_results'].get('processed_count', 0)} resources processed.")
    
    return results

def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(description="Two-step education resource scraper")
    
    parser.add_argument(
        "--step",
        type=str,
        choices=["index", "extract", "both"],
        default="both",
        help="Which step to run: 'index', 'extract', or 'both' (default: both)"
    )
    
    parser.add_argument(
        "--subject-limit",
        type=int,
        help="Maximum number of subjects to process (default: all)"
    )
    
    parser.add_argument(
        "--resource-limit",
        type=int,
        help="Maximum number of resources per subject to process (default: all)"
    )
    
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run with visible browser (not headless)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum pages to process per subject in indexing step (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Run the scraper
    result = asyncio.run(run_two_step_scraper(
        step=args.step,
        subject_limit=args.subject_limit,
        resource_limit=args.resource_limit,
        headless=not args.visible,
        max_pages_per_subject=args.max_pages
    ))
    
    # Print summary
    print("\n===== Scraping Summary =====")
    if args.step in ["index", "both"] and "step_1_results" in result:
        if isinstance(result["step_1_results"], dict) and "total_resources" in result["step_1_results"]:
            print(f"Step 1 (Indexing): {result['step_1_results']['total_resources']} resources indexed across {len(result['step_1_results'].get('subjects', {}))} subjects")
        else:
            print(f"Step 1 (Indexing): Completed with issues.")
    
    if args.step in ["extract", "both"] and "step_2_results" in result:
        if isinstance(result["step_2_results"], dict) and "processed_count" in result["step_2_results"]:
            print(f"Step 2 (Extraction): {result['step_2_results']['processed_count']} resources processed across {result['step_2_results']['subjects_processed']} subjects")
        else:
            print(f"Step 2 (Extraction): Completed with issues.")
    
    print(f"\nOutput files saved to: {os.path.abspath('education_resources')}")

if __name__ == "__main__":
    main()
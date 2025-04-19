#!/usr/bin/env python3
"""
Command-line interface for the Student Report Generation System.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# Import from the refactored structure
from src.report_engine.enhanced_report_generator import EnhancedReportGenerator
from src.report_engine.styles.report_styles import get_style_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/report_generator.log"),
        logging.StreamHandler()
    ]
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the report generator CLI."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get environment variables
    form_recognizer_endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT", "")
    form_recognizer_key = os.environ.get("FORM_RECOGNIZER_KEY", "")
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
    openai_key = os.environ.get("OPENAI_KEY", "")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate student reports with AI-generated content")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Single report generator
    single_parser = subparsers.add_parser("single", help="Generate a single student report")
    single_parser.add_argument("--style", type=str, default="generic", help="Report style (generic, act, nsw, etc.)")
    single_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    single_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    single_parser.add_argument("--output", type=str, help="Output file path")
    
    # Batch report generator
    batch_parser = subparsers.add_parser("batch", help="Generate a batch of student reports")
    batch_parser.add_argument("--num", type=int, required=True, help="Number of reports to generate")
    batch_parser.add_argument("--style", type=str, default="generic", help="Report style (generic, act, nsw, etc.)")
    batch_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    batch_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    batch_parser.add_argument("--batch-id", type=str, help="Batch ID (generated if not provided)")
    
    # List available styles
    styles_parser = subparsers.add_parser("styles", help="List available report styles")
    
    # Add a new subparser for validating the setup
    validate_parser = subparsers.add_parser("validate", help="Validate the setup and configuration")
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 1
    
    # Execute the requested command
    if args.command == "styles":
        # List available styles
        style_handler = get_style_handler()
        available_styles = style_handler.get_available_styles()
        
        print("Available report styles:")
        for style_name in available_styles:
            style_config = style_handler.get_style(style_name)
            print(f"  - {style_name}: {style_config.get('name', style_name)}")
        
        return 0
        
    elif args.command == "validate":
        # Validate the setup
        return validate_setup(
            openai_endpoint=openai_endpoint,
            openai_key=openai_key,
            form_recognizer_endpoint=form_recognizer_endpoint,
            form_recognizer_key=form_recognizer_key
        )
    
    # Check if OpenAI credentials are set for commands that need them
    if not openai_endpoint or not openai_key:
        logger.error("OpenAI credentials are required. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        print("❌ OpenAI credentials are required. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        print("   You can create a .env file based on .env.example.")
        return 1
    
    # Initialize the report generator
    report_generator = EnhancedReportGenerator(
        form_recognizer_endpoint=form_recognizer_endpoint,
        form_recognizer_key=form_recognizer_key,
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment
    )
    
    if args.command == "single":
        # Generate a single report
        output_path = report_generator.generate_report(
            style=args.style,
            output_format=args.format,
            comment_length=args.comment_length,
            output_path=args.output
        )
        
        if output_path:
            print(f"✅ Report generated successfully: {output_path}")
            return 0
        else:
            print("❌ Failed to generate report.")
            return 1
            
    elif args.command == "batch":
        # Generate a batch of reports
        result = report_generator.generate_batch_reports(
            num_reports=args.num,
            style=args.style,
            output_format=args.format,
            comment_length=args.comment_length,
            batch_id=args.batch_id
        )
        
        if result["status"] == "completed":
            successful = len([r for r in result["reports"] if r["status"] == "generated"])
            print(f"✅ Generated {successful} out of {args.num} reports.")
            print(f"📁 Batch ID: {result['batch_id']}")
            
            # Create a ZIP archive
            zip_path = report_generator.create_zip_archive(result["batch_id"])
            if zip_path:
                print(f"📦 Created ZIP archive: {zip_path}")
            
            return 0
        else:
            print("❌ Failed to generate batch reports.")
            return 1
    
    else:
        parser.print_help()
        return 1

def validate_setup(openai_endpoint, openai_key, form_recognizer_endpoint, form_recognizer_key):
    """Validate the setup and configuration."""
    print("Validating setup and configuration...")
    
    # Check directories
    required_dirs = ["templates", "output", "logs", "src"]
    for directory in required_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            print(f"✅ Directory exists: {directory}")
        else:
            print(f"❌ Directory missing: {directory}")
    
    # Check environment variables
    if openai_endpoint:
        print(f"✅ OPENAI_ENDPOINT is set")
    else:
        print(f"❌ OPENAI_ENDPOINT is not set")
    
    if openai_key:
        print(f"✅ OPENAI_KEY is set")
    else:
        print(f"❌ OPENAI_KEY is not set")
    
    if form_recognizer_endpoint:
        print(f"✅ FORM_RECOGNIZER_ENDPOINT is set")
    else:
        print(f"⚠️ FORM_RECOGNIZER_ENDPOINT is not set (optional)")
    
    if form_recognizer_key:
        print(f"✅ FORM_RECOGNIZER_KEY is set")
    else:
        print(f"⚠️ FORM_RECOGNIZER_KEY is not set (optional)")
    
    # Check template files
    try:
        style_handler = get_style_handler()
        available_styles = style_handler.get_available_styles()
        
        print(f"✅ Found {len(available_styles)} style configurations: {', '.join(available_styles)}")
        
        # Check template files for each style
        for style in available_styles:
            style_config = style_handler.get_style(style)
            template_file = style_config.get("template_file")
            
            if template_file:
                template_path = os.path.join("templates", template_file)
                if os.path.exists(template_path):
                    print(f"✅ Template file exists for style '{style}': {template_path}")
                else:
                    print(f"⚠️ Template file missing for style '{style}': {template_path}")
    except Exception as e:
        print(f"❌ Error checking style configurations: {str(e)}")
    
    # Check Python dependencies
    try:
        # Check key dependencies
        dependencies = {
            "openai": "openai",
            "jinja2": "jinja2",
            "xhtml2pdf": "xhtml2pdf.pisa",
            "reportlab": "reportlab"
        }
        
        for name, module in dependencies.items():
            try:
                __import__(module.split(".")[0])
                print(f"✅ Dependency installed: {name}")
            except ImportError:
                print(f"❌ Dependency missing: {name}")
    except Exception as e:
        print(f"❌ Error checking dependencies: {str(e)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
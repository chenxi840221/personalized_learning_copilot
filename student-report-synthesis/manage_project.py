#!/usr/bin/env python3
"""
Project management script for Student Report Generation System.

This script provides utilities for managing the project file structure,
including creating, updating, and cleaning files and directories.
"""

import os
import sys
import shutil
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manager for Student Report Generation System project file structure."""
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize the project manager.
        
        Args:
            base_dir: Base directory for the project
        """
        self.base_dir = Path(base_dir)
        
        # Define directories to manage
        self.directories = {
            "src": self.base_dir / "src",
            "src/report_engine": self.base_dir / "src/report_engine",
            "src/report_engine/ai": self.base_dir / "src/report_engine/ai", 
            "src/report_engine/styles": self.base_dir / "src/report_engine/styles",
            "src/report_engine/templates": self.base_dir / "src/report_engine/templates",
            "src/report_engine/utils": self.base_dir / "src/report_engine/utils",
            "templates": self.base_dir / "templates",
            "output": self.base_dir / "output",
            "static": self.base_dir / "static",
            "static/images": self.base_dir / "static/images",
            "static/images/logos": self.base_dir / "static/images/logos",
            "logs": self.base_dir / "logs",
            "tests": self.base_dir / "tests",
            "docs": self.base_dir / "docs",
            "_deprecated": self.base_dir / "_deprecated"
        }
        
        # Define Python modules and their content
        self.python_modules = {
            # Main modules
            "main.py": self._get_main_py_content(),
            "generate_reports.py": self._get_generate_reports_py_content(),
            "generate_dalle_reports.py": self._get_generate_dalle_reports_content(),
            "enhanced_pdf_converter.py": self._get_enhanced_pdf_converter_content(),
            
            # src package
            "src/__init__.py": '"""Student Report Generation System package."""\n',
            
            # report_engine package
            "src/report_engine/__init__.py": self._get_report_engine_init_content(),
            "src/report_engine/enhanced_report_generator.py": None,  # Large file, load from source
            "src/report_engine/student_data_generator.py": None,  # Large file, load from source
            
            # AI module
            "src/report_engine/ai/__init__.py": self._get_ai_init_content(),
            "src/report_engine/ai/ai_content_generator.py": None,  # Large file, load from source
            "src/report_engine/ai/dalle_image_generator.py": self._get_dalle_image_generator_content(),
            
            # Styles module
            "src/report_engine/styles/__init__.py": '"""Styles package for report styles."""\n\nfrom src.report_engine.styles.report_styles import ReportStyle, ReportStyleHandler, get_style_handler\n',
            "src/report_engine/styles/report_styles.py": None,  # Large file, load from source
            
            # Templates module
            "src/report_engine/templates/__init__.py": '"""Templates package for report templates."""\n\nfrom src.report_engine.templates.template_handler import TemplateHandler\n',
            "src/report_engine/templates/template_handler.py": None,  # Large file, load from source
            
            # Utils module
            "src/report_engine/utils/__init__.py": '"""Utils package for utility functions."""\n\nfrom src.report_engine.utils.pdf_utils import convert_html_to_pdf\n',
            "src/report_engine/utils/pdf_utils.py": self._get_pdf_utils_content(),
        }
        
        # Define templates
        self.templates = {
            "templates/act_template.html": self._get_act_template_content(),
            "templates/nsw_template.html": self._get_nsw_template_content()
        }
        
        # Define configuration files
        self.config_files = {
            ".env.example": self._get_env_example_content(),
            "requirements.txt": self._get_requirements_content(),
            "setup.py": None,          # Load from source
            "README.md": None,         # Load from source
            "DALLE_INTEGRATION.md": self._get_dalle_integration_readme()
        }
    
    def _get_main_py_content(self) -> str:
        """Get content for main.py."""
        return '''#!/usr/bin/env python3
"""
Main entry point for the Student Report Generation System.
"""

import os
import sys
import logging
from dotenv import load_dotenv

from src.report_engine.enhanced_report_generator import EnhancedReportGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run the report generator."""
    # Load environment variables
    load_dotenv()
    
    # Get API keys from environment variables
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
    openai_key = os.environ.get("OPENAI_KEY", "")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    
    # Check if OpenAI credentials are set
    if not openai_endpoint or not openai_key:
        logger.error("OpenAI credentials are not set. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        return 1
    
    # Initialize the report generator with DALL-E integration enabled
    report_generator = EnhancedReportGenerator(
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        templates_dir="templates",
        output_dir="output",
        report_styles_dir="report_styles",
        static_dir="static",
        enable_images=True  # Enable DALL-E image generation
    )
    
    # Generate a sample report
    output_path = report_generator.generate_report(
        style="act",
        output_format="pdf",
        comment_length="standard",
        generate_images=True,
        image_options={
            "badge_style": "modern",
            "badge_colors": ["navy blue", "gold"],
            "photo_style": "school portrait",
            "photo_size": "512x512"
        }
    )
    
    if output_path:
        logger.info(f"Report generated successfully: {output_path}")
        print(f"✅ Report generated successfully: {output_path}")
        return 0
    else:
        logger.error("Failed to generate report.")
        print("❌ Failed to generate report.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    def _get_report_engine_init_content(self) -> str:
        """Get content for src/report_engine/__init__.py."""
        return '''"""
Report Engine Package for Student Report Generation System.

This package contains the core components for generating student reports
with AI-powered content using Azure OpenAI.

Modules:
- enhanced_report_generator: Main report generation class
- student_data_generator: Student data generation with realistic profiles
- styles: Report style configurations and handling
- ai: AI integration for content generation
- templates: HTML template handling
- utils: Utility functions for report generation
"""

from src.report_engine.enhanced_report_generator import EnhancedReportGenerator
from src.report_engine.student_data_generator import StudentProfile, SchoolProfile, StudentDataGenerator

__version__ = "1.1.0"
'''

    def _get_ai_init_content(self) -> str:
        """Get content for src/report_engine/ai/__init__.py."""
        return '''"""
AI package for content generation using Azure OpenAI.

This package provides integration with Azure OpenAI services
for generating personalized student report content and images.
"""

from src.report_engine.ai.ai_content_generator import AIContentGenerator
from src.report_engine.ai.dalle_image_generator import DallEImageGenerator
'''
    
    def _get_env_example_content(self) -> str:
        """Get content for .env.example."""
        return '''# Azure OpenAI API credentials
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_KEY=your-openai-key
OPENAI_DEPLOYMENT=gpt-4o

# Azure Form Recognizer / Document Intelligence credentials (optional)
FORM_RECOGNIZER_ENDPOINT=https://your-form-recognizer.cognitiveservices.azure.com/
FORM_RECOGNIZER_KEY=your-form-recognizer-key
'''
    
    def _get_generate_reports_py_content(self) -> str:
        """Get content for generate_reports.py."""
        return '''#!/usr/bin/env python3
"""
Command-line interface for the Student Report Generation System.

This script provides a command-line interface for generating student reports
with AI-generated content and images using Azure OpenAI.
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
    single_parser.add_argument("--images", action="store_true", help="Generate images using DALL-E")
    single_parser.add_argument("--badge-style", type=str, default="modern", help="Style for school badge")
    
    # Batch report generator
    batch_parser = subparsers.add_parser("batch", help="Generate a batch of student reports")
    batch_parser.add_argument("--num", type=int, required=True, help="Number of reports to generate")
    batch_parser.add_argument("--style", type=str, default="generic", help="Report style (generic, act, nsw, etc.)")
    batch_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    batch_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    batch_parser.add_argument("--batch-id", type=str, help="Batch ID (generated if not provided)")
    batch_parser.add_argument("--images", action="store_true", help="Generate images using DALL-E")
    
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
            openai_key=openai_key
        )
    
    # Check if OpenAI credentials are set for commands that need them
    if not openai_endpoint or not openai_key:
        logger.error("OpenAI credentials are required. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        print("❌ OpenAI credentials are required. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        print("   You can create a .env file based on .env.example.")
        return 1
    
    # Initialize the report generator
    report_generator = EnhancedReportGenerator(
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        enable_images=getattr(args, "images", False)
    )
    
    if args.command == "single":
        # Generate a single report
        image_options = None
        if getattr(args, "images", False):
            image_options = {
                "badge_style": getattr(args, "badge_style", "modern"),
                "badge_colors": ["navy blue", "gold"],
                "photo_style": "school portrait",
                "photo_size": "512x512"
            }
            
        output_path = report_generator.generate_report(
            style=args.style,
            output_format=args.format,
            comment_length=args.comment_length,
            output_path=args.output,
            generate_images=getattr(args, "images", False),
            image_options=image_options
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
            batch_id=args.batch_id,
            generate_images=getattr(args, "images", False)
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


def validate_setup(openai_endpoint, openai_key):
    """Validate the setup and configuration."""
    print("Validating setup and configuration...")
    
    # Check directories
    required_dirs = ["templates", "output", "logs", "src", "static/images/logos"]
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
    
    # Check for logo files
    logo_dir = "static/images/logos"
    if os.path.exists(logo_dir) and os.path.isdir(logo_dir):
        print(f"✅ Logo directory exists: {logo_dir}")
        # Check for specific logo files
        act_logo = os.path.join(logo_dir, "act_education_logo.png")
        nsw_logo = os.path.join(logo_dir, "nsw_government_logo.png")
        
        if os.path.exists(act_logo):
            print(f"✅ ACT Education logo exists: {act_logo}")
        else:
            print(f"⚠️ ACT Education logo missing: {act_logo}")
            
        if os.path.exists(nsw_logo):
            print(f"✅ NSW Government logo exists: {nsw_logo}")
        else:
            print(f"⚠️ NSW Government logo missing: {nsw_logo}")
    else:
        print(f"❌ Logo directory missing: {logo_dir}")
    
    # Check Python dependencies
    try:
        # Check key dependencies
        dependencies = {
            "openai": "openai",
            "jinja2": "jinja2",
            "xhtml2pdf": "xhtml2pdf.pisa",
            "reportlab": "reportlab",
            "weasyprint": "weasyprint",
            "beautifulsoup4": "bs4",
            "PIL": "PIL",
            "requests": "requests"
        }
        
        for name, module in dependencies.items():
            try:
                __import__(module.split(".")[0])
                print(f"✅ Dependency installed: {name}")
            except ImportError:
                print(f"⚠️ Dependency missing or optional: {name}")
    except Exception as e:
        print(f"❌ Error checking dependencies: {str(e)}")
    
    print("\n📋 DALL-E Integration Status:")
    print("To use DALL-E for image generation, make sure your Azure OpenAI account has access to DALL-E models.")
    print("Use the --images flag when generating reports to enable DALL-E image generation.")
    print("Alternatively, use the dedicated script: python generate_dalle_reports.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
    
    def _get_generate_dalle_reports_content(self) -> str:
        """Get content for generate_dalle_reports.py."""
        return '''#!/usr/bin/env python3
"""
Demo script for generating school reports with DALL-E generated images.

This script demonstrates the integrated report generation process using
DALL-E to create school badges and student photos.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import the enhanced report generator
from src.report_engine.enhanced_report_generator import EnhancedReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dalle_demo.log"),
        logging.StreamHandler()
    ]
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger(__name__)

def generate_single_report(args, report_generator):
    """Generate a single report with DALL-E images."""
    print(f"Generating a single {args.style} report with DALL-E images...")
    
    output_path = args.output if args.output else None
    
    # Generate the report
    report_path = report_generator.generate_report(
        style=args.style,
        output_format=args.format,
        comment_length=args.comment_length,
        output_path=output_path,
        generate_images=True,
        image_options={
            "badge_style": args.badge_style,
            "badge_colors": args.badge_colors.split(",") if args.badge_colors else ["navy blue", "gold"],
            "photo_style": "school portrait",
            "photo_size": args.image_size
        }
    )
    
    if report_path:
        print(f"✅ Report successfully generated: {report_path}")
        return 0
    else:
        print("❌ Failed to generate report")
        return 1

def generate_batch_reports(args, report_generator):
    """Generate a batch of reports with DALL-E images."""
    print(f"Generating {args.num} {args.style} reports with DALL-E images...")
    
    # Generate the batch
    batch_result = report_generator.generate_batch_reports(
        num_reports=args.num,
        style=args.style,
        output_format=args.format,
        comment_length=args.comment_length,
        batch_id=args.batch_id,
        generate_images=True
    )
    
    if batch_result["status"] == "completed":
        successful = len([r for r in batch_result["reports"] if r["status"] == "generated"])
        print(f"✅ Generated {successful} out of {args.num} reports")
        print(f"📁 Batch ID: {batch_result['batch_id']}")
        
        if "zip_path" in batch_result:
            print(f"📦 ZIP archive: {batch_result['zip_path']}")
            
        return 0
    else:
        print("❌ Failed to generate batch reports")
        return 1

def main():
    """Main entry point for the demo script."""
    # Load environment variables
    load_dotenv()
    
    # Get OpenAI credentials
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT")
    openai_key = os.environ.get("OPENAI_KEY")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    
    # Check if OpenAI credentials are set
    if not openai_endpoint or not openai_key:
        print("❌ OpenAI credentials are required. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        return 1
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate school reports with DALL-E images")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Single report generator
    single_parser = subparsers.add_parser("single", help="Generate a single report with DALL-E images")
    single_parser.add_argument("--style", type=str, default="act", help="Report style (e.g., act, nsw, generic)")
    single_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    single_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    single_parser.add_argument("--output", type=str, help="Output file path")
    single_parser.add_argument("--badge-style", type=str, default="modern", help="Style for school badge (modern, traditional, minimalist, elegant)")
    single_parser.add_argument("--badge-colors", type=str, help="Comma-separated colors for badge (e.g., 'navy blue,gold')")
    single_parser.add_argument("--image-size", type=str, default="1024x1024", help="Image size (1024x1024, 512x512)")
    
    # Batch report generator
    batch_parser = subparsers.add_parser("batch", help="Generate multiple reports with DALL-E images")
    batch_parser.add_argument("--num", type=int, required=True, help="Number of reports to generate")
    batch_parser.add_argument("--style", type=str, default="act", help="Report style (e.g., act, nsw, generic)")
    batch_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    batch_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    batch_parser.add_argument("--batch-id", type=str, help="Batch ID (generated if not provided)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command provided, show help
    if args.command is None:
        parser.print_help()
        return 1
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Initialize the report generator with DALL-E integration
    report_generator = EnhancedReportGenerator(
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        templates_dir="templates",
        output_dir="output",
        report_styles_dir="report_styles",
        static_dir="static",
        enable_images=True
    )
    
    # Execute the requested command
    if args.command == "single":
        return generate_single_report(args, report_generator)
    elif args.command == "batch":
        return generate_batch_reports(args, report_generator)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    def _get_dalle_image_generator_content(self) -> str:
        """Get content for the DALL-E image generator module."""
        return '''"""
DALL-E Image Generator module for creating realistic school badges and student photos.

This module uses Azure OpenAI's DALL-E model to generate realistic images
for school badges and student photos, integrated directly with the report generator.
"""

import logging
import base64
import os
import requests
import tempfile
from typing import Dict, Any, Optional, Tuple, List
from io import BytesIO
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)

class DallEImageGenerator:
    """Class for generating synthetic images using Azure OpenAI's DALL-E."""
    
    def __init__(self, openai_client):
        """
        Initialize the DALL-E Image Generator.
        
        Args:
            openai_client: An instance of OpenAI client
        """
        self.openai_client = openai_client
    
    def generate_school_badge(
        self, 
        school_name: str, 
        school_type: str = "Primary School",
        style: str = "modern",
        colors: Optional[List[str]] = None,
        motto: Optional[str] = None,
        image_size: str = "1024x1024"
    ) -> str:
        """
        Generate a school badge using DALL-E.
        
        Args:
            school_name: Name of the school
            school_type: Type of school (Primary School, High School, etc.)
            style: Style of the badge (modern, traditional, minimalist)
            colors: Optional list of color descriptions
            motto: Optional school motto
            image_size: Size of the generated image
            
        Returns:
            Base64 encoded image data URI
        """
        # Default colors if not provided
        if not colors:
            colors = ["navy blue", "gold"]
            
        # Construct colors prompt
        color_prompt = f" with colors {', '.join(colors)},"
        
        # Construct motto prompt
        motto_prompt = ""
        if motto:
            motto_prompt = f" with the motto '{motto}',"
        
        # Construct the prompt
        prompt = f"A professional, high-quality school logo for {school_name}, a {school_type}, in a {style} style{color_prompt}{motto_prompt} with educational symbols. The logo should be on a plain white background with no text, only the emblem."
        
        try:
            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model="dall-e-3",  # Using DALL-E 3 model
                prompt=prompt,
                n=1,
                size=image_size,
                quality="standard"
            )
            
            # Get the image URL
            image_url = response.data[0].url
            
            # Download the image
            image_data = self._download_image(image_url)
            
            # Convert to base64 data URI
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            data_uri = f"data:image/png;base64,{image_base64}"
            
            logger.info(f"Generated school badge for {school_name}")
            return data_uri
            
        except Exception as e:
            logger.error(f"Failed to generate school badge with DALL-E: {str(e)}")
            # Return a fallback image
            return self._get_fallback_school_badge(school_name, school_type, motto)
    
    def generate_student_photo(
        self,
        gender: str = "neutral",
        age: int = 10,
        ethnicity: Optional[str] = None,
        hair_description: Optional[str] = None,
        style: str = "school portrait",
        image_size: str = "1024x1024"
    ) -> str:
        """
        Generate a student photo using DALL-E.
        
        Args:
            gender: Gender of the student (male, female, neutral)
            age: Age of the student (6-18)
            ethnicity: Optional ethnicity description
            hair_description: Optional hair description
            style: Style of the photo
            image_size: Size of the generated image
            
        Returns:
            Base64 encoded image data URI
        """
        # Ensure age is within school range
        age = max(6, min(18, age))
        
        # Determine school level based on age
        if age <= 12:
            school_level = "primary school"
        else:
            school_level = "high school"
        
        # Construct ethnicity prompt
        ethnicity_prompt = ""
        if ethnicity:
            ethnicity_prompt = f" {ethnicity}"
        
        # Construct hair prompt
        hair_prompt = ""
        if hair_description:
            hair_prompt = f" with {hair_description} hair,"
        
        # Use "child" or "teenager" based on age
        age_term = "child" if age <= 12 else "teenager"
        
        # Construct the prompt - being careful to generate appropriate images
        prompt = f"A professional, appropriate school portrait photograph of a {age} year old {ethnicity_prompt} {gender} {age_term}{hair_prompt} wearing a {school_level} uniform, with a plain blue background, looking directly at the camera with a small smile. The image should be suitable for a school report card."
        
        try:
            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model="dall-e-3",  # Using DALL-E 3 model
                prompt=prompt,
                n=1,
                size=image_size,
                quality="standard"
            )
            
            # Get the image URL
            image_url = response.data[0].url
            
            # Download the image
            image_data = self._download_image(image_url)
            
            # Convert to base64 data URI
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            data_uri = f"data:image/png;base64,{image_base64}"
            
            logger.info(f"Generated student photo for {gender} {age_term}")
            return data_uri
            
        except Exception as e:
            logger.error(f"Failed to generate student photo with DALL-E: {str(e)}")
            # Return a fallback image
            return self._get_fallback_student_photo(gender, age)
    
    def _download_image(self, image_url: str) -> bytes:
        """
        Download an image from a URL.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Image data as bytes
        """
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return response.content
    
    def _get_fallback_school_badge(self, school_name: str, school_type: str, motto: Optional[str] = None) -> str:
        """
        Generate a fallback school badge.
        
        Args:
            school_name: Name of the school
            school_type: Type of school
            motto: Optional school motto
            
        Returns:
            Base64 encoded image data URI
        """
        try:
            # Create a simple badge using PIL
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a new image with a white background
            img = Image.new('RGB', (500, 500), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw a circle for the badge
            draw.ellipse((50, 50, 450, 450), fill='navy')
            draw.ellipse((60, 60, 440, 440), fill='lightblue')
            
            # Draw school name
            try:
                # Try to get a font
                font_large = ImageFont.truetype("arial.ttf", 40)
                font_small = ImageFont.truetype("arial.ttf", 30)
            except IOError:
                # Fallback to default font
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Get text sizes for centering
            text_width = draw.textlength(school_name, font=font_large)
            text_width2 = draw.textlength(school_type, font=font_small)
            
            # Draw text
            draw.text(
                (250 - text_width/2, 200),
                school_name,
                font=font_large,
                fill='white'
            )
            
            draw.text(
                (250 - text_width2/2, 250),
                school_type,
                font=font_small,
                fill='white'
            )
            
            # Add motto if provided
            if motto:
                text_width3 = draw.textlength(motto, font=font_small)
                draw.text(
                    (250 - text_width3/2, 300),
                    motto,
                    font=font_small,
                    fill='white'
                )
            
            # Save the image to a bytes buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Encode as base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Failed to create fallback badge: {str(e)}")
            
            # Return an empty transparent PNG
            empty_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            return f"data:image/png;base64,{empty_png}"
    
    def _get_fallback_student_photo(self, gender: str, age: int) -> str:
        """
        Generate a fallback student photo.
        
        Args:
            gender: Gender of the student
            age: Age of the student
            
        Returns:
            Base64 encoded image data URI
        """
        try:
            # Create a simple avatar using PIL
            from PIL import Image, ImageDraw
            
            # Create a new image with a light blue background
            img = Image.new('RGB', (500, 500), color='lightblue')
            draw = ImageDraw.Draw(img)
            
            # Draw a simple avatar
            # Face
            draw.ellipse((150, 100, 350, 300), fill='peachpuff')
            
            # Eyes
            draw.ellipse((200, 170, 220, 190), fill='white')
            draw.ellipse((280, 170, 300, 190), fill='white')
            draw.ellipse((206, 176, 214, 184), fill='black')
            draw.ellipse((286, 176, 294, 184), fill='black')
            
            # Mouth
            draw.arc((220, 220, 280, 260), start=0, end=180, fill='black', width=3)
            
            # Hair - different based on gender
            if gender.lower() == 'male':
                draw.rectangle((150, 100, 350, 140), fill='brown')
            elif gender.lower() == 'female':
                draw.ellipse((140, 90, 360, 160), fill='brown')
                draw.rectangle((140, 130, 360, 300), fill='brown')
            else:
                # Neutral
                draw.ellipse((140, 90, 360, 150), fill='brown')
            
            # Body/shoulders
            draw.rectangle((175, 300, 325, 400), fill='navy')
            
            # Save the image to a bytes buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Encode as base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Failed to create fallback photo: {str(e)}")
            
            # Return an empty transparent PNG
            empty_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            return f"data:image/png;base64,{empty_png}"
'''
    
    def _get_enhanced_pdf_converter_content(self) -> str:
        """Get content for enhanced_pdf_converter.py."""
        return '''#!/usr/bin/env python3
"""
Enhanced HTML to PDF Converter

This script provides multiple methods to convert HTML reports to PDF with
improved formatting preservation. It tries multiple libraries in succession
until one succeeds.

Usage:
    python enhanced_pdf_converter.py [--dir OUTPUT_DIR] [--file SPECIFIC_HTML_FILE]

Requirements:
    pip install weasyprint xhtml2pdf beautifulsoup4
    
    # Optional but recommended:
    # Install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Callable

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_html_to_pdf_with_weasyprint(html_path, pdf_path=None):
    """
    Convert HTML to PDF using WeasyPrint for better CSS support.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Import WeasyPrint
        from weasyprint import HTML, CSS
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Set up custom CSS to improve PDF rendering
        custom_css = CSS(string="""
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            .rating {
                text-align: center;
                display: inline-block;
                height: 25px;
                line-height: 25px;
                vertical-align: middle;
                border: 1px solid #ddd;
                min-width: 25px;
                padding: 0 5px;
                margin: 0 2px;
            }
            .rating.selected {
                background-color: #003366;
                color: white;
            }
            .achievement-code, .effort-code {
                font-weight: bold;
                padding: 2px 5px;
                border-radius: 3px;
                display: inline-block;
            }
            .achievement-code {
                background-color: #e6f2ff;
            }
            .effort-code {
                background-color: #e6f7e6;
            }
            .subject-name {
                font-weight: bold;
            }
            .general-comment {
                padding: 10px;
                margin: 15px 0;
                border-left: 5px solid #003366;
                background-color: #f8f9fa;
            }
            .signature-box {
                width: 45%;
                text-align: center;
                display: inline-block;
            }
            .signature-line {
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
            }
            .student-photo {
                max-width: 120px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 3px;
            }
            .school-logo {
                max-height: 100px;
                margin-bottom: 10px;
            }
        """)
        
        # Convert HTML to PDF
        HTML(filename=html_path).write_pdf(
            pdf_path,
            stylesheets=[custom_css]
        )
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using WeasyPrint")
        return True
        
    except ImportError:
        logger.warning("WeasyPrint not installed. Try: pip install weasyprint")
        return False
    except Exception as e:
        logger.error(f"Error with WeasyPrint: {str(e)}")
        return False

def convert_html_to_pdf_with_xhtml2pdf(html_path, pdf_path=None):
    """
    Convert HTML to PDF using xhtml2pdf with enhanced styling.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import xhtml2pdf.pisa as pisa
        from bs4 import BeautifulSoup
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Read HTML content
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Parse HTML to add special CSS
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find or create style tag
        style_tag = soup.find('style')
        if not style_tag:
            style_tag = soup.new_tag('style')
            head_tag = soup.find('head')
            if head_tag:
                head_tag.append(style_tag)
            else:
                # Create head if it doesn't exist
                head_tag = soup.new_tag('head')
                soup.html.insert(0, head_tag)
                head_tag.append(style_tag)
        
        # Add PDF-specific CSS
        style_tag.string = (style_tag.string if style_tag.string else "") + """
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                page-break-inside: avoid;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            .rating {
                border: 1px solid #ddd;
                padding: 3px 5px;
                margin: 0 1px;
                display: inline-block;
            }
            .rating.selected {
                background-color: #003366;
                color: white;
            }
            .signature-box {
                width: 45%;
                float: left;
                text-align: center;
                margin: 0 2.5%;
            }
            .signature-line {
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
            }
            .general-comment {
                padding: 10px;
                margin: 15px 0;
                border-left: 5px solid #003366;
                background-color: #f8f9fa;
            }
            .section-header {
                background-color: #f0f0f0;
                padding: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            .subject-name {
                font-weight: bold;
            }
            .student-photo {
                max-width: 120px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 3px;
            }
            .school-logo {
                max-height: 100px;
                margin-bottom: 10px;
            }
        """
        
        # Pre-process the HTML for xhtml2pdf compatibility
        # Fix inline styling that xhtml2pdf doesn't handle well
        for element in soup.select('.selected'):
            element['style'] = 'background-color: #003366; color: white;'
        
        for element in soup.select('.signature-box'):
            element['style'] = 'width: 45%; display: inline-block; text-align: center; margin: 0 2%;'
        
        for element in soup.select('.signature-line'):
            element['style'] = 'border-top: 1px solid #000; margin-top: 30px; padding-top: 5px;'
        
        # Update HTML content with modifications
        enhanced_html = str(soup)
        
        # Create PDF
        with open(pdf_path, "wb") as pdf_file:
            result = pisa.CreatePDF(
                src=enhanced_html,
                dest=pdf_file,
                encoding="utf-8"
            )
        
        if result.err:
            logger.error(f"Error converting HTML to PDF with xhtml2pdf: {result.err}")
            return False
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using xhtml2pdf")
        return True
    
    except ImportError:
        logger.warning("xhtml2pdf or BeautifulSoup not installed. Try: pip install xhtml2pdf beautifulsoup4")
        return False
    except Exception as e:
        logger.error(f"Failed to convert {html_path} to PDF with xhtml2pdf: {str(e)}")
        return False

def convert_html_to_pdf_with_wkhtmltopdf(html_path, pdf_path=None):
    """
    Convert HTML to PDF using wkhtmltopdf command line tool.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import subprocess
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Check if wkhtmltopdf is installed
        wkhtmltopdf_paths = [
            'wkhtmltopdf',  # If in PATH
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
        ]
        
        wkhtmltopdf_cmd = None
        for path in wkhtmltopdf_paths:
            try:
                subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                wkhtmltopdf_cmd = path
                break
            except (FileNotFoundError, subprocess.SubprocessError):
                continue
        
        if wkhtmltopdf_cmd is None:
            logger.warning("wkhtmltopdf not found. Install from https://wkhtmltopdf.org/downloads.html")
            return False
        
        # Convert HTML to PDF using wkhtmltopdf
        cmd = [
            wkhtmltopdf_cmd,
            '--enable-local-file-access',
            '--encoding', 'utf-8',
            '--page-size', 'A4',
            '--margin-top', '10mm',
            '--margin-bottom', '10mm',
            '--margin-left', '10mm',
            '--margin-right', '10mm',
            html_path,
            pdf_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logger.error(f"Error with wkhtmltopdf: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using wkhtmltopdf")
        return True
    
    except Exception as e:
        logger.error(f"Failed to convert {html_path} to PDF with wkhtmltopdf: {str(e)}")
        return False

def convert_html_to_pdf(html_path, pdf_path=None):
    """
    Convert HTML to PDF using the best available method.
    Tries multiple methods in succession until one succeeds.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    # Set PDF path if not provided
    if pdf_path is None:
        pdf_path = html_path.replace('.html', '.pdf')
    
    # List of conversion methods to try in order
    conversion_methods: List[Callable] = [
        convert_html_to_pdf_with_weasyprint,  # Best CSS support
        convert_html_to_pdf_with_wkhtmltopdf,  # Good rendering
        convert_html_to_pdf_with_xhtml2pdf    # Fallback option
    ]
    
    # Try each method in succession
    for method in conversion_methods:
        try:
            if method(html_path, pdf_path):
                return True
        except Exception as e:
            logger.warning(f"Method {method.__name__} failed: {str(e)}")
            continue
    
    logger.error(f"All PDF conversion methods failed for {html_path}")
    return False

def process_directory(directory_path):
    """Process all HTML files in a directory and convert them to PDF."""
    logger.info(f"Processing directory: {directory_path}")
    
    # Check if directory exists
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        logger.error(f"Directory not found: {directory_path}")
        return False
    
    # Find all HTML files
    html_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    if not html_files:
        logger.info(f"No HTML files found in {directory_path}")
        return True
    
    logger.info(f"Found {len(html_files)} HTML files")
    
    # Process each HTML file
    success_count = 0
    failed_count = 0
    
    for html_file in html_files:
        pdf_file = html_file.replace('.html', '.pdf')
        
        # Skip if PDF already exists and is newer than HTML
        if os.path.exists(pdf_file) and os.path.getmtime(pdf_file) > os.path.getmtime(html_file):
            logger.info(f"Skipping {html_file} - PDF already exists and is up to date")
            success_count += 1
            continue
        
        if convert_html_to_pdf(html_file, pdf_file):
            success_count += 1
        else:
            failed_count += 1
    
    logger.info(f"Conversion complete: {success_count} succeeded, {failed_count} failed")
    return failed_count == 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Enhanced HTML to PDF Converter")
    parser.add_argument("--dir", default="output", help="Directory containing HTML files")
    parser.add_argument("--file", help="Single HTML file to convert")
    
    args = parser.parse_args()
    
    if args.file:
        if not os.path.exists(args.file):
            logger.error(f"File not found: {args.file}")
            return 1
        
        pdf_path = args.file.replace('.html', '.pdf')
        if convert_html_to_pdf(args.file, pdf_path):
            print(f"Successfully converted {args.file} to {pdf_path}")
            return 0
        else:
            print(f"Failed to convert {args.file}")
            return 1
    else:
        if process_directory(args.dir):
            print(f"Successfully processed all HTML files in {args.dir}")
            return 0
        else:
            print(f"Some conversions failed in {args.dir}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
'''

    def _get_pdf_utils_content(self) -> str:
        """Get content for pdf_utils.py."""
        return '''"""
PDF Utilities Module for converting HTML to PDF.

This module provides functions for converting HTML to PDF using various methods.
"""

import os
import logging
from typing import List, Callable, Optional

# Set up logging
logger = logging.getLogger(__name__)

def convert_html_to_pdf_with_weasyprint(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using WeasyPrint for better CSS support.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Import WeasyPrint
        from weasyprint import HTML, CSS
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Set up custom CSS to improve PDF rendering
        custom_css = CSS(string="""
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            .rating {
                text-align: center;
                display: inline-block;
                height: 25px;
                line-height: 25px;
                vertical-align: middle;
                border: 1px solid #ddd;
                min-width: 25px;
                padding: 0 5px;
                margin: 0 2px;
            }
            .rating.selected {
                background-color: #003366;
                color: white;
            }
            .achievement-code, .effort-code {
                font-weight: bold;
                padding: 2px 5px;
                border-radius: 3px;
                display: inline-block;
            }
            .achievement-code {
                background-color: #e6f2ff;
            }
            .effort-code {
                background-color: #e6f7e6;
            }
            .subject-name {
                font-weight: bold;
            }
            .general-comment {
                padding: 10px;
                margin: 15px 0;
                border-left: 5px solid #003366;
                background-color: #f8f9fa;
            }
            .signature-box {
                width: 45%;
                text-align: center;
                display: inline-block;
            }
            .signature-line {
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
            }
            .student-photo {
                max-width: 120px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 3px;
            }
            .school-logo {
                max-height: 100px;
                margin-bottom: 10px;
            }
        """)
        
        # Convert HTML to PDF
        HTML(filename=html_path).write_pdf(
            pdf_path,
            stylesheets=[custom_css]
        )
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using WeasyPrint")
        return True
        
    except ImportError:
        logger.warning("WeasyPrint not installed. Try: pip install weasyprint")
        return False
    except Exception as e:
        logger.error(f"Error with WeasyPrint: {str(e)}")
        return False

def convert_html_to_pdf_with_xhtml2pdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using xhtml2pdf with enhanced styling.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import xhtml2pdf.pisa as pisa
        from bs4 import BeautifulSoup
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Read HTML content
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Parse HTML to add special CSS
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find or create style tag
        style_tag = soup.find('style')
        if not style_tag:
            style_tag = soup.new_tag('style')
            head_tag = soup.find('head')
            if head_tag:
                head_tag.append(style_tag)
            else:
                # Create head if it doesn't exist
                head_tag = soup.new_tag('head')
            soup.html.insert(0, head_tag)
                head_tag.append(style_tag)
        
        # Add PDF-specific CSS
        style_tag.string = (style_tag.string if style_tag.string else "") + """
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                page-break-inside: avoid;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            .rating {
                border: 1px solid #ddd;
                padding: 3px 5px;
                margin: 0 1px;
                display: inline-block;
            }
            .rating.selected {
                background-color: #003366;
                color: white;
            }
            .signature-box {
                width: 45%;
                float: left;
                text-align: center;
                margin: 0 2.5%;
            }
            .signature-line {
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
            }
            .general-comment {
                padding: 10px;
                margin: 15px 0;
                border-left: 5px solid #003366;
                background-color: #f8f9fa;
            }
            .section-header {
                background-color: #f0f0f0;
                padding: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            .subject-name {
                font-weight: bold;
            }
            .student-photo {
                max-width: 120px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 3px;
            }
            .school-logo {
                max-height: 100px;
                margin-bottom: 10px;
            }
        """
        
        # Pre-process the HTML for xhtml2pdf compatibility
        # Fix inline styling that xhtml2pdf doesn't handle well
        for element in soup.select('.selected'):
            element['style'] = 'background-color: #003366; color: white;'
        
        for element in soup.select('.signature-box'):
            element['style'] = 'width: 45%; display: inline-block; text-align: center; margin: 0 2%;'
        
        for element in soup.select('.signature-line'):
            element['style'] = 'border-top: 1px solid #000; margin-top: 30px; padding-top: 5px;'
        
        # Update HTML content with modifications
        enhanced_html = str(soup)
        
        # Create PDF
        with open(pdf_path, "wb") as pdf_file:
            result = pisa.CreatePDF(
                src=enhanced_html,
                dest=pdf_file,
                encoding="utf-8"
            )
        
        if result.err:
            logger.error(f"Error converting HTML to PDF with xhtml2pdf: {result.err}")
            return False
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using xhtml2pdf")
        return True
    
    except ImportError:
        logger.warning("xhtml2pdf or BeautifulSoup not installed. Try: pip install xhtml2pdf beautifulsoup4")
        return False
    except Exception as e:
        logger.error(f"Failed to convert {html_path} to PDF with xhtml2pdf: {str(e)}")
        return False

def convert_html_to_pdf_with_wkhtmltopdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using wkhtmltopdf command line tool.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import subprocess
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Check if wkhtmltopdf is installed
        wkhtmltopdf_paths = [
            'wkhtmltopdf',  # If in PATH
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
        ]
        
        wkhtmltopdf_cmd = None
        for path in wkhtmltopdf_paths:
            try:
                subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                wkhtmltopdf_cmd = path
                break
            except (FileNotFoundError, subprocess.SubprocessError):
                continue
        
        if wkhtmltopdf_cmd is None:
            logger.warning("wkhtmltopdf not found. Install from https://wkhtmltopdf.org/downloads.html")
            return False
        
        # Convert HTML to PDF using wkhtmltopdf
        cmd = [
            wkhtmltopdf_cmd,
            '--enable-local-file-access',
            '--encoding', 'utf-8',
            '--page-size', 'A4',
            '--margin-top', '10mm',
            '--margin-bottom', '10mm',
            '--margin-left', '10mm',
            '--margin-right', '10mm',
            html_path,
            pdf_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logger.error(f"Error with wkhtmltopdf: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using wkhtmltopdf")
        return True
    
    except Exception as e:
        logger.error(f"Failed to convert {html_path} to PDF with wkhtmltopdf: {str(e)}")
        return False

def convert_html_to_pdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using the best available method.
    Tries multiple methods in succession until one succeeds.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    # Set PDF path if not provided
    if pdf_path is None:
        pdf_path = html_path.replace('.html', '.pdf')
    
    # List of conversion methods to try in order
    conversion_methods: List[Callable] = [
        convert_html_to_pdf_with_weasyprint,  # Best CSS support
        convert_html_to_pdf_with_wkhtmltopdf,  # Good rendering
        convert_html_to_pdf_with_xhtml2pdf    # Fallback option
    ]
    
    # Try each method in succession
    for method in conversion_methods:
        try:
            if method(html_path, pdf_path):
                return True
        except Exception as e:
            logger.warning(f"Method {method.__name__} failed: {str(e)}")
            continue
    
    logger.error(f"All PDF conversion methods failed for {html_path}")
    return False
'''

def _get_act_template_content(self) -> str:
        """Get content for ACT template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.student.name.full_name }} - ACT School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
            border-bottom: 2px solid #003366;
            padding-bottom: 1rem;
        }
        .logo {
            max-height: 80px;
            margin-bottom: 15px;
        }
        .school-logo {
            max-height: 100px;
            margin-bottom: 10px;
        }
        .student-photo {
            max-width: 120px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 3px;
        }
        .school-name {
            font-size: 2rem;
            font-weight: bold;
            color: #003366;
        }
        .report-title {
            font-size: 1.5rem;
            margin: 0.5rem 0;
        }
        .student-info {
            margin: 2rem 0;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .section-title {
            background-color: #003366;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .subject-table th {
            background-color: #e6f2ff;
        }
        .comment {
            font-size: 0.9rem;
            padding: 0.5rem;
        }
        .achievement-code {
            font-weight: bold;
            background-color: #e6f2ff;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .effort-code {
            font-weight: bold;
            background-color: #e6f7e6;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .general-comment {
            margin: 2rem 0;
            padding: 1.5rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 5px solid #003366;
        }
        .signatures {
            margin-top: 3rem;
            display: flex;
            justify-content: space-around;
        }
        .signature-box {
            text-align: center;
            width: 40%;
        }
        .signature-line {
            border-top: 1px solid #000;
            margin-top: 2rem;
            padding-top: 0.5rem;
        }
        .legend {
            font-size: 0.8rem;
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .footer {
            margin-top: 3rem;
            text-align: center;
            font-size: 0.8rem;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="row">
                <div class="col-md-3 text-start">
                    <img src="{{ get_image_base64('images/logos/act_education_logo.png') }}" alt="ACT Education" class="logo">
                </div>
                <div class="col-md-6 text-center">
                    {% if data.school.logo_data %}
                    <img src="{{ data.school.logo_data }}" alt="{{ data.school.name }}" class="school-logo">
                    {% endif %}
                    <div class="school-name">{{ data.school.name }}</div>
                    <div class="report-title">Student Progress Report</div>
                    <div>Semester {{ data.semester }} {{ data.year }}</div>
                </div>
                <div class="col-md-3 text-end">
                    {% if data.student.photo_data %}
                    <img src="{{ data.student.photo_data }}" alt="{{ data.student.name.full_name }}" class="student-photo">
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{ data.student.name.full_name }}</p>
                    <p><strong>Grade:</strong> {{ data.student.grade }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{ data.student.class }}</p>
                    <p><strong>Teacher:</strong> {{ data.student.teacher.full_name }}</p>
                </div>
            </div>
        </div>
        
        <div class="section-title">Academic Performance</div>
        <table class="table table-bordered subject-table">
            <thead>
                <tr>
                    <th>Subject</th>
                    <th class="text-center">Achievement</th>
                    <th class="text-center">Effort</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {% for subject in data.subjects %}
                <tr>
                    <td><strong>{{ subject.subject }}</strong></td>
                    <td class="text-center">
                        <span class="achievement-code">{{ subject.achievement.code }}</span>
                        <div class="small mt-1">{{ subject.achievement.label }}</div>
                    </td>
                    <td class="text-center">
                        <span class="effort-code">{{ subject.effort.code }}</span>
                        <div class="small mt-1">{{ subject.effort.label }}</div>
                    </td>
                    <td class="comment">{{ subject.comment }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="section-title">Attendance</div>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th class="text-center">Days Present</th>
                    <th class="text-center">Days Absent</th>
                    <th class="text-center">Days Late</th>
                    <th class="text-center">Attendance Rate</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="text-center">{{ data.attendance.present_days }}</td>
                    <td class="text-center">{{ data.attendance.absent_days }}</td>
                    <td class="text-center">{{ data.attendance.late_days }}</td>
                    <td class="text-center">{{ data.attendance.attendance_rate }}%</td>
                </tr>
            </tbody>
        </table>
        
        <div class="section-title">General Comment</div>
        <div class="general-comment">
            {{ data.general_comment }}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{ data.student.teacher.full_name }}</div>
                <div>Class Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ data.school.principal }}</div>
                <div>School Principal</div>
            </div>
        </div>
        
        <div class="legend">
            <div><strong>Achievement Scale:</strong></div>
            <div class="row">
                <div class="col-md-3"><span class="achievement-code">O</span> - Outstanding</div>
                <div class="col-md-3"><span class="achievement-code">H</span> - High</div>
                <div class="col-md-2"><span class="achievement-code">A</span> - At Standard</div>
                <div class="col-md-2"><span class="achievement-code">P</span> - Partial</div>
                <div class="col-md-2"><span class="achievement-code">L</span> - Limited</div>
            </div>
            <div class="mt-2"><strong>Effort Scale:</strong></div>
            <div class="row">
                <div class="col-md-3"><span class="effort-code">C</span> - Consistently</div>
                <div class="col-md-3"><span class="effort-code">U</span> - Usually</div>
                <div class="col-md-3"><span class="effort-code">S</span> - Sometimes</div>
                <div class="col-md-3"><span class="effort-code">R</span> - Rarely</div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report generated on {{ data.report_date }}</p>
            <p>{{ data.school.name }} | {{ data.school.suburb }}, {{ data.school.state|upper }}</p>
        </div>
    </div>
</body>
</html>
'''

def _get_nsw_template_content(self) -> str:
        """Get content for NSW template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.student.name.full_name }} - NSW School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
            border-bottom: 2px solid #00539b;
            padding-bottom: 1rem;
        }
        .logo {
            max-height: 80px;
            margin-bottom: 15px;
        }
        .school-logo {
            max-height: 100px;
            margin-bottom: 10px;
        }
        .student-photo {
            max-width: 120px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 3px;
        }
        .school-name {
            font-size: 2rem;
            font-weight: bold;
            color: #00539b;
        }
        .report-title {
            font-size: 1.5rem;
            margin: 0.5rem 0;
        }
        .student-info {
            margin: 2rem 0;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .section-title {
            background-color: #00539b;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .subject-table th {
            background-color: #e6f2ff;
        }
        .comment {
            font-size: 0.9rem;
            padding: 0.5rem;
        }
        .achievement-code {
            font-weight: bold;
            background-color: #e6f2ff;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .effort-code {
            font-weight: bold;
            background-color: #e6f7e6;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .general-comment {
            margin: 2rem 0;
            padding: 1.5rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 5px solid #00539b;
        }
        .signatures {
            margin-top: 3rem;
            display: flex;
            justify-content: space-around;
        }
        .signature-box {
            text-align: center;
            width: 40%;
        }
        .signature-line {
            border-top: 1px solid #000;
            margin-top: 2rem;
            padding-top: 0.5rem;
        }
        .legend {
            font-size: 0.8rem;
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .footer {
            margin-top: 3rem;
            text-align: center;
            font-size: 0.8rem;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="row">
                <div class="col-md-3 text-start">
                    <img src="{{ get_image_base64('images/logos/nsw_government_logo.png') }}" alt="NSW Government" class="logo">
                </div>
                <div class="col-md-6 text-center">
                    {% if data.school.logo_data %}
                    <img src="{{ data.school.logo_data }}" alt="{{ data.school.name }}" class="school-logo">
                    {% endif %}
                    <div class="school-name">{{ data.school.name }}</div>
                    <div class="report-title">Student Achievement Report</div>
                    <div>Semester {{ data.semester }} {{ data.year }}</div>
                </div>
                <div class="col-md-3 text-end">
                    {% if data.student.photo_data %}
                    <img src="{{ data.student.photo_data }}" alt="{{ data.student.name.full_name }}" class="student-photo">
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{ data.student.name.full_name }}</p>
                    <p><strong>Grade:</strong> {{ data.student.grade }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{ data.student.class }}</p>
                    <p><strong>Teacher:</strong> {{ data.student.teacher.full_name }}</p>
                </div>
            </div>
        </div>
        
        <div class="section-title">Key Learning Areas</div>
        <table class="table table-bordered subject-table">
            <thead>
                <tr>
                    <th>Subject</th>
                    <th class="text-center">Achievement</th>
                    <th class="text-center">Effort</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {% for subject in data.subjects %}
                <tr>
                    <td><strong>{{ subject.subject }}</strong></td>
                    <td class="text-center">
                        <span class="achievement-code">{{ subject.achievement.code }}</span>
                        <div class="small mt-1">{{ subject.achievement.label }}</div>
                    </td>
                    <td class="text-center">
                        <span class="effort-code">{{ subject.effort.code }}</span>
                        <div class="small mt-1">{{ subject.effort.label }}</div>
                    </td>
                    <td class="comment">{{ subject.comment }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="section-title">Attendance</div>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th class="text-center">Days Present</th>
                    <th class="text-center">Days Absent</th>
                    <th class="text-center">Days Late</th>
                    <th class="text-center">Attendance Rate</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="text-center">{{ data.attendance.present_days }}</td>
                    <td class="text-center">{{ data.attendance.absent_days }}</td>
                    <td class="text-center">{{ data.attendance.late_days }}</td>
                    <td class="text-center">{{ data.attendance.attendance_rate }}%</td>
                </tr>
            </tbody>
        </table>
        
        <div class="section-title">General Comment</div>
        <div class="general-comment">
            {{ data.general_comment }}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{ data.student.teacher.full_name }}</div>
                <div>Class Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ data.school.principal }}</div>
                <div>Principal</div>
            </div>
        </div>
        
        <div class="legend">
            <div><strong>Achievement Scale:</strong></div>
            <div class="row">
                <div class="col-md-4"><span class="achievement-code">A</span> - Outstanding</div>
                <div class="col-md-4"><span class="achievement-code">B</span> - High</div>
                <div class="col-md-4"><span class="achievement-code">C</span> - Sound</div>
            </div>
            <div class="row mt-1">
                <div class="col-md-4"><span class="achievement-code">D</span> - Basic</div>
                <div class="col-md-4"><span class="achievement-code">E</span> - Limited</div>
                <div class="col-md-4"></div>
            </div>
            <div class="mt-2"><strong>Effort Scale:</strong></div>
            <div class="row">
                <div class="col-md-4"><span class="effort-code">H</span> - High</div>
                <div class="col-md-4"><span class="effort-code">S</span> - Satisfactory</div>
                <div class="col-md-4"><span class="effort-code">L</span> - Low</div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report generated on {{ data.report_date }}</p>
            <p>{{ data.school.name }} | {{ data.school.suburb }}, {{ data.school.state|upper }}</p>
        </div>
    </div>
</body>
</html>
'''

def create_files(self) -> None:
        """Create all project files."""
        logger.info("Creating project files...")
        
        # Create Python modules
        for file_path, content in self.python_modules.items():
            full_path = self.base_dir / file_path
            
            # Create directory if it doesn't exist
            os.makedirs(full_path.parent, exist_ok=True)
            
            # Check if file already exists
            if full_path.exists():
                logger.info(f"File already exists: {file_path}")
                continue
            
            if content is not None:
                # Create from provided content
                with open(full_path, "w") as f:
                    f.write(content)
                logger.info(f"Created file: {file_path}")
            else:
                # Check if source file exists
                source_path = Path(file_path)
                if source_path.exists():
                    # Copy from source
                    shutil.copy2(source_path, full_path)
                    logger.info(f"Copied file: {file_path}")
                else:
                    # Create empty placeholder file with header comment
                    module_name = os.path.splitext(os.path.basename(file_path))[0]
                    placeholder_content = f'''"""
{module_name} module.

This is a placeholder file created by the project setup script.
Replace this with the actual implementation.
"""

# TODO: Implement {module_name}
'''
                    with open(full_path, "w") as f:
                        f.write(placeholder_content)
                    logger.info(f"Created placeholder file: {file_path}")
        
        # Create templates
        for file_path, content in self.templates.items():
            full_path = self.base_dir / file_path
            
            # Create directory if it doesn't exist
            os.makedirs(full_path.parent, exist_ok=True)
            
            # Check if file already exists
            if full_path.exists():
                logger.info(f"Template already exists: {file_path}")
                continue
                
            if content is not None:
                # Create from provided content
                with open(full_path, "w") as f:
                    f.write(content)
                logger.info(f"Created file: {file_path}")
            else:
                # Check if source file exists
                source_path = Path(file_path)
                if source_path.exists():
                    # Copy from source
                    shutil.copy2(source_path, full_path)
                    logger.info(f"Copied file: {file_path}")
                else:
                    # Create placeholder HTML template
                    template_name = os.path.splitext(os.path.basename(file_path))[0]
                    style_name = template_name.split('_')[0].upper()
                    
                    placeholder_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ data.student.name.full_name }}}} - {style_name} School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ text-align: center; margin-bottom: 2rem; }}
        .school-name {{ font-size: 1.8rem; font-weight: bold; color: #003366; }}
        .report-title {{ font-size: 1.4rem; margin-bottom: 1rem; }}
        .student-info {{ margin-bottom: 2rem; }}
        .subject-table th {{ background-color: #e6f2ff; }}
        .comment {{ font-size: 0.9rem; }}
        .general-comment {{ margin: 2rem 0; padding: 1rem; background-color: #f8f9fa; border-radius: 5px; }}
        .signatures {{ margin-top: 3rem; display: flex; justify-content: space-around; }}
        .signature-box {{ text-align: center; width: 40%; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 2rem; padding-top: 0.5rem; }}
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="school-name">{{{{ data.school.name }}}}</div>
            <div class="report-title">Student Progress Report - Semester {{{{ data.semester }}}} {{{{ data.year }}}}</div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{{{ data.student.name.full_name }}}}</p>
                    <p><strong>Grade:</strong> {{{{ data.student.grade }}}}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{{{ data.student.class }}}}</p>
                    <p><strong>Teacher:</strong> {{{{ data.student.teacher.full_name }}}}</p>
                </div>
            </div>
        </div>
        
        <h4>Academic Performance</h4>
        <table class="table table-bordered subject-table">
            <thead>
                <tr>
                    <th>Subject</th>
                    <th>Achievement</th>
                    <th>Effort</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {{% for subject in data.subjects %}}
                <tr>
                    <td>{{{{ subject.subject }}}}</td>
                    <td class="text-center">
                        {{{{ subject.achievement.label }}}}
                    </td>
                    <td class="text-center">
                        {{{{ subject.effort.label }}}}
                    </td>
                    <td class="comment">{{{{ subject.comment }}}}</td>
                </tr>
                {{% endfor %}}
            </tbody>
        </table>
        
        <h4>General Comment</h4>
        <div class="general-comment">
            {{{{ data.general_comment }}}}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{{{ data.student.teacher.full_name }}}}</div>
                <div>Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{{{ data.school.principal }}}}</div>
                <div>Principal</div>
            </div>
        </div>
    </div>
</body>
</html>
'''
                    with open(full_path, "w") as f:
                        f.write(placeholder_template)
                    logger.info(f"Created placeholder template: {file_path}")
        
        # Create configuration files
        for file_path, content in self.config_files.items():
            full_path = self.base_dir / file_path
            
            # Check if file already exists
            if full_path.exists():
                logger.info(f"Config file already exists: {file_path}")
                continue
            
            if content is not None:
                # Create from provided content
                with open(full_path, "w") as f:
                    f.write(content)
                logger.info(f"Created file: {file_path}")
            else:
                # Check if source file exists
                source_path = Path(file_path)
                if source_path.exists():
                    # Copy from source
                    shutil.copy2(source_path, full_path)
                    logger.info(f"Copied file: {file_path}")
                else:
                    # Create placeholder config file
                    file_name = os.path.basename(file_path)
                    
                    if file_name == "requirements.txt":
                        placeholder_content = self._get_requirements_content()
                    elif file_name == "README.md":
                        placeholder_content = '''# Student Report Generation System

An AI-powered system for generating personalized student reports that follow Australian educational standards with support for different state/territory formats.

## Features

- **AI-Generated Content**: Uses Azure OpenAI's GPT-4o to generate realistic, personalized report comments
- **Multiple Report Styles**: Supports different Australian state/territory formats (ACT, NSW, etc.)
- **Customizable Templates**: HTML-based templates for easy customization
- **Batch Processing**: Generate multiple reports at once
- **PDF & HTML Output**: Export reports as PDF or HTML
- **Realistic Student Data**: Generate synthetic student profiles for testing

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env` file:
   ```
   OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
   OPENAI_KEY=your-openai-key
   OPENAI_DEPLOYMENT=gpt-4o
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

See `generate_reports.py` for command-line usage options.
'''
                    else:
                        placeholder_content = f"# Placeholder for {file_name}\n# Replace with actual content\n"
                    
                    with open(full_path, "w") as f:
                        f.write(placeholder_content)
                    logger.info(f"Created placeholder config file: {file_path}")
                    
        # Additional project files
        gitignore_file = self.base_dir / ".gitignore"
        if not gitignore_file.exists():
            with open(gitignore_file, "w") as f:
                f.write('''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
env/
ENV/

# Environment variables
.env

# Generated reports
output/

# Log files
logs/
*.log

# Cache files
.cache/
.pytest_cache/
.coverage
htmlcov/

# IDE files
.idea/
.vscode/
*.swp
*.swo
''')
            logger.info("Created .gitignore file")
            
def _get_requirements_content(self) -> str:
        """Get content for requirements.txt."""
        return '''# Core dependencies
fastapi==0.95.1
uvicorn==0.22.0
python-multipart==0.0.6
openai>=1.0.0
python-dotenv==1.0.0

# Report generation
jinja2==3.1.2
reportlab==3.6.12
pillow==9.5.0
python-docx==0.8.11

# PDF conversion options
xhtml2pdf==0.2.11
weasyprint>=53.0
beautifulsoup4>=4.9.3

# Image processing
requests>=2.28.0

# Data handling
numpy>=1.22.0
pandas>=1.3.0

# Testing and development
pytest>=7.0.0
pytest-cov>=3.0.0
flake8>=4.0.0

# Documentation
sphinx>=4.3.0
sphinx-rtd-theme>=1.0.0
'''
    
    def setup_project(self, clean: bool = False) -> None:
        """
        Set up the project file structure.
        
        Args:
            clean: Whether to clean the project before setting up
        """
        if clean:
            self.clean_project()
        
        self.create_directories()
        self.create_files()
        logger.info("Project setup complete! 🎉")
    
    def update_project(self) -> None:
        """Update the project file structure without cleaning."""
        self.create_directories()
        self.create_files()
        logger.info("Project update complete! 🎉")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Manage Student Report Generation System project")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the project file structure")
    setup_parser.add_argument("--clean", action="store_true", help="Clean the project before setting up")
    setup_parser.add_argument("--dir", default=".", help="Base directory for the project")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update the project file structure")
    update_parser.add_argument("--dir", default=".", help="Base directory for the project")
    
    # Clean command
    script_name = os.path.basename(__file__)
    clean_parser = subparsers.add_parser("clean", help="Clean the project")
    clean_parser.add_argument("--dir", default=".", help="Base directory for the project")
    clean_parser.add_argument("--exclude", nargs="+", 
                             default=[".git", ".github", ".gitignore", ".env", script_name], 
                             help="Files and directories to exclude from cleaning")
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for the project manager."""
    args = parse_args()
    
    if args.command == "setup":
        project_manager = ProjectManager(args.dir)
        project_manager.setup_project(clean=args.clean)
        return 0
    elif args.command == "update":
        project_manager = ProjectManager(args.dir)
        project_manager.update_project()
        return 0
    elif args.command == "clean":
        project_manager = ProjectManager(args.dir)
        project_manager.clean_project(exclude=args.exclude)
        return 0
    else:
        print("Please specify a command. Use --help for more information.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
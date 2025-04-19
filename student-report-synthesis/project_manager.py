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

# Import project components
from content_generators import ContentGenerator
from template_generators import TemplateGenerator

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
        
        # Initialize generators
        self.content_generator = ContentGenerator()
        self.template_generator = TemplateGenerator()
        
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
            "main.py": self.content_generator.get_main_py_content(),
            "generate_reports.py": self.content_generator.get_generate_reports_py_content(),
            "generate_dalle_reports.py": self.content_generator.get_generate_dalle_reports_content(),
            "enhanced_pdf_converter.py": self.content_generator.get_enhanced_pdf_converter_content(),
            
            # src package
            "src/__init__.py": '"""Student Report Generation System package."""\n',
            
            # report_engine package
            "src/report_engine/__init__.py": self.content_generator.get_report_engine_init_content(),
            "src/report_engine/enhanced_report_generator.py": None,  # Large file, load from source
            "src/report_engine/student_data_generator.py": None,  # Large file, load from source
            
            # AI module
            "src/report_engine/ai/__init__.py": self.content_generator.get_ai_init_content(),
            "src/report_engine/ai/ai_content_generator.py": None,  # Large file, load from source
            "src/report_engine/ai/dalle_image_generator.py": self.content_generator.get_dalle_image_generator_content(),
            
            # Styles module
            "src/report_engine/styles/__init__.py": '"""Styles package for report styles."""\n\nfrom src.report_engine.styles.report_styles import ReportStyle, ReportStyleHandler, get_style_handler\n',
            "src/report_engine/styles/report_styles.py": None,  # Large file, load from source
            
            # Templates module
            "src/report_engine/templates/__init__.py": '"""Templates package for report templates."""\n\nfrom src.report_engine.templates.template_handler import TemplateHandler\n',
            "src/report_engine/templates/template_handler.py": None,  # Large file, load from source
            
            # Utils module
            "src/report_engine/utils/__init__.py": '"""Utils package for utility functions."""\n\nfrom src.report_engine.utils.pdf_utils import convert_html_to_pdf\n',
            "src/report_engine/utils/pdf_utils.py": self.content_generator.get_pdf_utils_content(),
        }
        
        # Define templates
        self.templates = {
            "templates/act_template.html": self.template_generator.get_act_template_content(),
            "templates/nsw_template.html": self.template_generator.get_nsw_template_content()
        }
        
        # Define configuration files
        self.config_files = {
            ".env.example": self.content_generator.get_env_example_content(),
            "requirements.txt": self.content_generator.get_requirements_content(),
            "setup.py": None,          # Load from source
            "README.md": None,         # Load from source
            "DALLE_INTEGRATION.md": self.content_generator.get_dalle_integration_readme()
        }

    def create_directories(self):
        """Create all project directories."""
        logger.info("Creating project directories...")
        for path_name, directory in self.directories.items():
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {path_name}")

    def clean_project(self, exclude=None):
        """
        Clean the project by removing files and directories.
        
        Args:
            exclude: List of files and directories to exclude from cleaning
        """
        if exclude is None:
            exclude = [".git", ".github", ".gitignore", ".env", "venv", "env", "__pycache__"]
        
        logger.info("Cleaning project directories...")
        
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            
            if os.path.isdir(item_path) and item not in exclude:
                try:
                    shutil.rmtree(item_path)
                    logger.info(f"Removed directory: {item}")
                except Exception as e:
                    logger.error(f"Failed to remove directory: {item} ({str(e)})")
            elif os.path.isfile(item_path) and item not in exclude:
                try:
                    os.remove(item_path)
                    logger.info(f"Removed file: {item}")
                except Exception as e:
                    logger.error(f"Failed to remove file: {item} ({str(e)})")
    
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
                    
                    placeholder_template = self.template_generator.get_placeholder_template(style_name)
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
                        placeholder_content = self.content_generator.get_requirements_content()
                    elif file_name == "README.md":
                        placeholder_content = self.content_generator.get_readme_content()
                    else:
                        placeholder_content = f"# Placeholder for {file_name}\n# Replace with actual content\n"
                    
                    with open(full_path, "w") as f:
                        f.write(placeholder_content)
                    logger.info(f"Created placeholder config file: {file_path}")
                    
        # Create .gitignore file
        gitignore_file = self.base_dir / ".gitignore"
        if not gitignore_file.exists():
            with open(gitignore_file, "w") as f:
                f.write(self.content_generator.get_gitignore_content())
            logger.info("Created .gitignore file")


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
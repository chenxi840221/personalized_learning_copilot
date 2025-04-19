"""
Template handler module for managing report templates.

This module provides utilities for working with HTML templates
and rendering them with student data to create reports.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# HTML template handling
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    logging.warning("Jinja2 not installed. Template rendering will not be available.")
    Environment = None

# PDF conversion
try:
    import xhtml2pdf.pisa as pisa
except ImportError:
    logging.warning("xhtml2pdf not installed. HTML to PDF conversion will not be available.")
    pisa = None

# Set up logging
logger = logging.getLogger(__name__)


class TemplateHandler:
    """Handler for report templates and rendering."""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize the template handler.
        
        Args:
            templates_dir: Directory containing HTML templates
        """
        self.templates_dir = Path(templates_dir)
        self.env = self._init_jinja_env()
        
    def _init_jinja_env(self) -> Optional[Environment]:
        """Initialize the Jinja2 environment for template rendering."""
        if Environment is None:
            logger.warning("Jinja2 not available. Install it with: pip install jinja2")
            return None
        
        try:
            env = Environment(
                loader=FileSystemLoader(self.templates_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.info(f"Jinja2 environment initialized with templates from: {self.templates_dir}")
            return env
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 environment: {str(e)}")
            return None
    
    def render_template(self, template_name: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Render an HTML template with the provided data.
        
        Args:
            template_name: Name of the template file
            data: Data to render in the template
            
        Returns:
            Rendered HTML content or None if failed
        """
        if self.env is None:
            logger.error("Cannot render template: Jinja2 environment not initialized")
            return None
        
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(data=data)
            return html_content
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            return None
    
    def html_to_pdf(self, html_content: str, output_path: str) -> bool:
        """
        Convert HTML content to PDF.
        
        Args:
            html_content: HTML content to convert
            output_path: Path to save the PDF file
            
        Returns:
            True if conversion was successful, False otherwise
        """
        if pisa is None:
            logger.error("Cannot convert HTML to PDF: xhtml2pdf not installed")
            return False
        
        try:
            with open(output_path, "wb") as pdf_file:
                result = pisa.CreatePDF(
                    src=html_content,
                    dest=pdf_file,
                    encoding="utf-8"
                )
            
            if result.err:
                logger.error(f"Error converting HTML to PDF: {result.err}")
                return False
            
            logger.info(f"HTML successfully converted to PDF: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to convert HTML to PDF: {str(e)}")
            return False
    
    def create_default_template(self, style: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Create a default template for the specified style.
        
        Args:
            style: Report style name
            output_path: Optional path to save the template (default: templates/style_template.html)
            
        Returns:
            Path to the created template or None if failed
        """
        template_name = f"{style.lower()}_template.html"
        
        if output_path is None:
            output_path = self.templates_dir / template_name
        
        # Basic HTML template structure
        html_template = self._get_default_template_content(style)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_template)
            
            logger.info(f"Created default template: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to create default template: {str(e)}")
            return None
    
    def _get_default_template_content(self, style: str) -> str:
        """
        Get the default template content for a style.
        
        Args:
            style: Report style name
            
        Returns:
            Default template HTML content
        """
        # Generic template for any style
        generic_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.student.name.full_name }} - School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .school-name {
            font-size: 1.8rem;
            font-weight: bold;
            color: #003366;
        }
        .report-title {
            font-size: 1.4rem;
            margin-bottom: 1rem;
        }
        .student-info {
            margin-bottom: 2rem;
        }
        .subject-table th {
            background-color: #e6f2ff;
        }
        .comment {
            font-size: 0.9rem;
        }
        .general-comment {
            margin: 2rem 0;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
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
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="school-name">{{ data.school.name }}</div>
            <div class="report-title">Student Progress Report - Semester {{ data.semester }} {{ data.year }}</div>
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
                {% for subject in data.subjects %}
                <tr>
                    <td>{{ subject.subject }}</td>
                    <td class="text-center">
                        {{ subject.achievement.label }}
                        {% if subject.achievement.code %}
                        ({{ subject.achievement.code }})
                        {% endif %}
                    </td>
                    <td class="text-center">
                        {{ subject.effort.label }}
                        {% if subject.effort.code %}
                        ({{ subject.effort.code }})
                        {% endif %}
                    </td>
                    <td class="comment">{{ subject.comment }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <h4>Attendance</h4>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Days Present</th>
                    <th>Days Absent</th>
                    <th>Days Late</th>
                    <th>Attendance Rate</th>
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
        
        <h4>General Comment</h4>
        <div class="general-comment">
            {{ data.general_comment }}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{ data.student.teacher.full_name }}</div>
                <div>Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ data.school.principal }}</div>
                <div>Principal</div>
            </div>
        </div>
        
        <div class="text-center mt-4">
            <small>Report generated on {{ data.report_date }}</small>
        </div>
    </div>
</body>
</html>
"""
        
        # Return style-specific template or generic template
        if style.lower() == "act":
            return self._get_act_template_content()
        elif style.lower() == "nsw":
            return self._get_nsw_template_content()
        else:
            return generic_template
    
    def _get_act_template_content(self) -> str:
        """Get the ACT-specific template content."""
        # ACT template content implementation would go here
        # For brevity, we'll reference an external template
        act_template_path = self.templates_dir / "act_template.html"
        if act_template_path.exists():
            with open(act_template_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning(f"ACT template not found at {act_template_path}, using generic template")
            return self._get_default_template_content("generic")
    
    def _get_nsw_template_content(self) -> str:
        """Get the NSW-specific template content."""
        # NSW template content implementation would go here
        # For brevity, we'll reference an external template
        nsw_template_path = self.templates_dir / "nsw_template.html"
        if nsw_template_path.exists():
            with open(nsw_template_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning(f"NSW template not found at {nsw_template_path}, using generic template")
            return self._get_default_template_content("generic")


# Update the templates package __init__.py to import this module
def update_templates_init():
    """Update the templates package __init__.py to import this module."""
    init_path = Path(__file__).parent / "__init__.py"
    
    if init_path.exists():
        with open(init_path, "r") as f:
            content = f.read()
        
        if "from src.report_engine.templates.template_handler import TemplateHandler" not in content:
            with open(init_path, "a") as f:
                f.write("\nfrom src.report_engine.templates.template_handler import TemplateHandler\n")
    
    logger.info("Updated templates package __init__.py")


# Automatically update the templates package __init__.py when this module is imported
if __name__ != "__main__":
    try:
        update_templates_init()
    except Exception as e:
        logger.error(f"Failed to update templates package __init__.py: {str(e)}")
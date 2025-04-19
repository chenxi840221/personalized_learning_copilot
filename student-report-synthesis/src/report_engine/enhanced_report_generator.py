"""
Enhanced Report Generator module.

This module provides the main class for generating student reports with
AI-generated content using Azure OpenAI.
"""

import os
import logging
import json
import uuid
import tempfile
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import random

# Import from the refactored structure
from src.report_engine.styles.report_styles import ReportStyle, get_style_handler
from src.report_engine.ai.ai_content_generator import AIContentGenerator
from src.report_engine.templates.template_handler import TemplateHandler
from src.report_engine.student_data_generator import StudentProfile, SchoolProfile, StudentDataGenerator

# Try to import utility functions
try:
    from src.report_engine.utils.pdf_utils import convert_html_to_pdf
    has_pdf_utils = True
except ImportError:
    has_pdf_utils = False

# PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import cm, mm
except ImportError:
    logging.warning("ReportLab not installed. PDF generation will be limited.")

# Set up logging
logger = logging.getLogger(__name__)


class EnhancedReportGenerator:
    """Enhanced generator for student reports with GPT-4o generated content."""
    
    def __init__(
        self,
        form_recognizer_endpoint: str,
        form_recognizer_key: str,
        openai_endpoint: str,
        openai_key: str,
        openai_deployment: str,
        templates_dir: str = "templates",
        output_dir: str = "output",
        report_styles_dir: str = "src/report_engine/styles"
    ):
        """Initialize the Enhanced Report Generator."""
        self.form_recognizer_endpoint = form_recognizer_endpoint
        self.form_recognizer_key = form_recognizer_key
        self.openai_endpoint = openai_endpoint
        self.openai_key = openai_key
        self.openai_deployment = openai_deployment
        
        # Directory paths
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.report_styles_dir = Path(report_styles_dir)
        
        # Create necessary directories
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize components
        self.style_handler = get_style_handler()
        self.template_handler = TemplateHandler(templates_dir=templates_dir)
        self.ai_generator = AIContentGenerator(
            openai_endpoint=openai_endpoint,
            openai_key=openai_key,
            openai_deployment=openai_deployment
        )
        
        # Check LibreOffice availability for Word document handling
        self.libreoffice_path = self._find_libreoffice()
        
        logger.info(f"Enhanced Report Generator initialized. OpenAI: {'✅' if self.ai_generator.client else '❌'}")
    
    def _find_libreoffice(self) -> Optional[str]:
        """Find LibreOffice executable for Word document conversion."""
        possible_paths = [
            # Linux
            "/usr/bin/libreoffice",
            "/usr/bin/soffice",
            # macOS
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            # Windows
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found LibreOffice at: {path}")
                return path
        
        logger.warning("LibreOffice not found - Word document conversion may be limited")
        return None
    
    def generate_report(
        self, 
        student_data: Optional[Dict[str, Any]] = None,
        style: str = "generic",
        output_format: str = "pdf",
        comment_length: str = "standard",
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a student report based on provided data or with synthetic data.
        
        Args:
            student_data: Optional student data dictionary
            style: Report style to use (act, nsw, generic, etc.)
            output_format: Output format (pdf or html)
            comment_length: Length of comments (brief, standard, detailed)
            output_path: Optional specific output path
            
        Returns:
            Path to the generated report
        """
        # Create a unique ID for this report if not provided
        report_id = str(uuid.uuid4())[:8]
        
        # Generate synthetic student data if not provided
        if not student_data:
            data_generator = StudentDataGenerator(style=style)
            student_profile = data_generator.generate_student_profile()
            school_profile = data_generator.generate_school_profile(state=style if style in ["act", "nsw", "qld", "vic", "sa", "wa", "tas", "nt"] else "act")
            
            student_data = {
                "student": student_profile.to_dict(),
                "school": school_profile.to_dict(),
                "report_id": report_id,
                "semester": "1" if datetime.now().month < 7 else "2",
                "year": datetime.now().year,
                "report_date": datetime.now().strftime("%d %B %Y")
            }
        
        # Get the style configuration
        style_config = self.style_handler.get_style(style)
        
        # Generate subject assessments with AI-generated comments
        subjects = style_config.get("subjects", ["English", "Mathematics", "Science"])
        achievement_scale = style_config.get("achievement_scale", [])
        effort_scale = style_config.get("effort_scale", [])
        
        subject_assessments = []
        
        for subject in subjects:
            # Determine achievement level - weight toward the middle
            # Create weights list with the same length as achievement_scale
            achievement_weights = []
            if len(achievement_scale) == 5:
                achievement_weights = [0.1, 0.25, 0.4, 0.15, 0.1]  # 5 levels
            elif len(achievement_scale) == 3:
                achievement_weights = [0.25, 0.5, 0.25]  # 3 levels
            else:
                # Ensure weights match the length of the scale
                weight_per_item = 1.0 / len(achievement_scale)
                achievement_weights = [weight_per_item] * len(achievement_scale)
            
            achievement_index = random.choices(
                range(len(achievement_scale)), 
                weights=achievement_weights, 
                k=1
            )[0]
            achievement = achievement_scale[achievement_index]
            
            # Determine effort level - usually correlates somewhat with achievement
            effort_weights = []
            if len(effort_scale) == 4:
                effort_weights = [0.4, 0.3, 0.2, 0.1]  # 4 levels
            elif len(effort_scale) == 3:
                effort_weights = [0.4, 0.4, 0.2]  # 3 levels
            else:
                # Ensure weights match the length of the scale
                weight_per_item = 1.0 / len(effort_scale)
                effort_weights = [weight_per_item] * len(effort_scale)
            
            if random.random() < 0.7:  # 70% chance effort correlates with achievement
                # Adjust effort to be similar to achievement but with some variation
                if achievement_index <= 1:  # High achievement
                    effort_index = 0 if random.random() < 0.7 else 1
                elif achievement_index == 2:  # Middle achievement
                    effort_index = min(random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2], k=1)[0], len(effort_scale) - 1)
                else:  # Lower achievement
                    # Make sure effort_index is within bounds
                    max_index = min(2, len(effort_scale) - 1)
                    effort_index = random.choices(range(1, max_index + 1), k=1)[0]
            else:
                # Sometimes effort doesn't correlate with achievement
                effort_index = random.choices(range(len(effort_scale)), weights=effort_weights, k=1)[0]
            
            effort = effort_scale[effort_index]
            
            # Generate AI comment
            try:
                comment = self.ai_generator.generate_subject_comment(
                    subject=subject,
                    student_profile=student_data["student"],
                    achievement_level=achievement["label"],
                    effort_level=effort["label"],
                    style=style,
                    comment_length=comment_length
                )
            except Exception as e:
                logger.error(f"Error generating AI comment for {subject}: {str(e)}")
                comment = f"The student has shown engagement with the {subject} curriculum this semester."
            
            subject_assessments.append({
                "subject": subject,
                "achievement": achievement,
                "effort": effort,
                "comment": comment
            })
        
        # Add subject assessments to student data
        student_data["subjects"] = subject_assessments
        
        # Generate general comment with AI
        try:
            general_comment = self.ai_generator.generate_general_comment(
                student_profile=student_data["student"],
                subjects_data=subject_assessments,
                school_info=student_data["school"],
                style=style,
                semester=student_data.get("semester", "1"),
                comment_length=comment_length
            )
        except Exception as e:
            logger.error(f"Error generating general comment: {str(e)}")
            general_comment = f"Overall, {student_data['student']['name']['first_name']} has engaged with the learning program this semester, demonstrating strengths and identifying areas for future growth."
        
        student_data["general_comment"] = general_comment
        
        # Generate attendance data if not provided
        if "attendance" not in student_data:
            # Most students have good attendance
            if random.random() < 0.7:  # 70% have good attendance
                absent_days = random.randint(0, 5)
                late_days = random.randint(0, 3)
            elif random.random() < 0.9:  # 20% have moderate attendance issues
                absent_days = random.randint(5, 10)
                late_days = random.randint(2, 6)
            else:  # 10% have significant attendance issues
                absent_days = random.randint(10, 20)
                late_days = random.randint(4, 10)
            
            total_days = random.randint(45, 55)
            present_days = total_days - absent_days
            
            student_data["attendance"] = {
                "total_days": total_days,
                "present_days": present_days,
                "absent_days": absent_days,
                "late_days": late_days,
                "attendance_rate": round(present_days / total_days * 100, 1)
            }
        
        # Determine output path
        if not output_path:
            student_name = student_data["student"]["name"]["full_name"].replace(" ", "_")
            filename = f"{student_name}_{style}_{student_data.get('semester', '1')}_{student_data.get('year', '2024')}"
            
            if output_format.lower() == "html":
                output_path = str(self.output_dir / f"{filename}.html")
            else:
                output_path = str(self.output_dir / f"{filename}.pdf")
        
        # Generate the report in the specified format
        if output_format.lower() == "html":
            return self._generate_html_report(student_data, style, output_path)
        else:
            return self._generate_pdf_report(student_data, style, output_path)
    
    def _generate_html_report(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate an HTML report using templates."""
        try:
            # Get the template name for this style
            style_config = self.style_handler.get_style(style)
            template_name = style_config.get("template_file", f"{style}_template.html")
            
            # Check if template exists, if not, create a default one
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                logger.warning(f"Template {template_name} not found, creating default template")
                self.template_handler.create_default_template(style, str(template_path))
            
            # Render template with data
            html_content = self.template_handler.render_template(template_name, data)
            
            if html_content:
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Write HTML to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                logger.info(f"Generated HTML report: {output_path}")
                return output_path
            else:
                # Fallback to a basic HTML if template rendering fails
                simple_html = self._generate_simple_html_report(data)
                
                # Write the simple HTML to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(simple_html)
                    
                logger.warning(f"Used simple HTML fallback for report: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            return ""
    
    def _generate_simple_html_report(self, data: Dict[str, Any]) -> str:
        """Generate a simple HTML report as fallback."""
        student = data.get("student", {})
        school = data.get("school", {})
        subjects = data.get("subjects", [])
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.get('name', {}).get('full_name', 'Student')} - School Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #003366; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .comment {{ font-size: 0.9em; }}
        .general-comment {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 15px 0; }}
    </style>
</head>
<body>
    <h1>{school.get('name', 'School')} Student Report</h1>
    <h2>Student Information</h2>
    <p><strong>Name:</strong> {student.get('name', {}).get('full_name', '')}</p>
    <p><strong>Grade:</strong> {student.get('grade', '')}</p>
    <p><strong>Class:</strong> {student.get('class', '')}</p>
    <p><strong>Teacher:</strong> {student.get('teacher', {}).get('full_name', '')}</p>
    
    <h2>Academic Performance</h2>
    <table>
        <tr>
            <th>Subject</th>
            <th>Achievement</th>
            <th>Effort</th>
            <th>Comments</th>
        </tr>
"""
        
        # Add subject rows
        for subject in subjects:
            subj_name = subject.get('subject', '')
            achievement = subject.get('achievement', {}).get('label', '')
            achievement_code = subject.get('achievement', {}).get('code', '')
            effort = subject.get('effort', {}).get('label', '')
            effort_code = subject.get('effort', {}).get('code', '')
            comment = subject.get('comment', '')
            
            achievement_display = f"{achievement} ({achievement_code})" if achievement_code else achievement
            effort_display = f"{effort} ({effort_code})" if effort_code else effort
            
            html += f"""
        <tr>
            <td>{subj_name}</td>
            <td>{achievement_display}</td>
            <td>{effort_display}</td>
            <td class="comment">{comment}</td>
        </tr>"""
        
        # Add attendance 
        attendance = data.get("attendance", {})
        html += f"""
    </table>
    
    <h2>Attendance</h2>
    <table>
        <tr>
            <th>Days Present</th>
            <th>Days Absent</th>
            <th>Days Late</th>
            <th>Attendance Rate</th>
        </tr>
        <tr>
            <td>{attendance.get('present_days', 0)}</td>
            <td>{attendance.get('absent_days', 0)}</td>
            <td>{attendance.get('late_days', 0)}</td>
            <td>{attendance.get('attendance_rate', 0)}%</td>
        </tr>
    </table>
    
    <h2>General Comment</h2>
    <div class="general-comment">
        {data.get('general_comment', '')}
    </div>
    
    <h2>Signatures</h2>
    <p><strong>Teacher:</strong> {student.get('teacher', {}).get('full_name', '')}</p>
    <p><strong>Principal:</strong> {school.get('principal', '')}</p>
    
    <p><small>Report generated on {data.get('report_date', '')}</small></p>
</body>
</html>
"""
        return html
    
    def _generate_pdf_report(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate a PDF report."""
        try:
            # First generate an HTML version
            html_path = output_path.replace(".pdf", ".html")
            html_output_path = self._generate_html_report(data, style, html_path)
            
            if html_output_path and os.path.exists(html_output_path):
                # Use PDF utils if available
                if has_pdf_utils:
                    from src.report_engine.utils.pdf_utils import convert_html_to_pdf
                    if convert_html_to_pdf(html_path, output_path):
                        logger.info(f"Generated PDF report using pdf_utils: {output_path}")
                        return output_path
                
                # Try to convert HTML to PDF using WeasyPrint
                try:
                    from weasyprint import HTML, CSS
                    
                    # Custom CSS to enhance PDF rendering
                    css_string = """
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
                    """
                    custom_css = CSS(string=css_string)
                    
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    
                    # Convert HTML to PDF
                    HTML(filename=html_path).write_pdf(
                        output_path,
                        stylesheets=[custom_css]
                    )
                    
                    logger.info(f"Generated PDF report with WeasyPrint: {output_path}")
                    return output_path
                except ImportError:
                    logger.info("WeasyPrint not available, falling back to other methods")
                except Exception as e:
                    logger.error(f"Error with WeasyPrint: {str(e)}")
                
                # Try wkhtmltopdf if available
                try:
                    import subprocess
                    
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
                    
                    if wkhtmltopdf_cmd:
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
                            output_path
                        ]
                        
                        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        if result.returncode == 0:
                            logger.info(f"Generated PDF report with wkhtmltopdf: {output_path}")
                            return output_path
                        else:
                            logger.error(f"Error with wkhtmltopdf: {result.stderr.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    logger.error(f"Error with wkhtmltopdf: {str(e)}")
                
                # Fallback to xhtml2pdf with improved handling
                try:
                    import xhtml2pdf.pisa as pisa
                    from bs4 import BeautifulSoup
                    
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
                    with open(output_path, "wb") as pdf_file:
                        result = pisa.CreatePDF(
                            src=enhanced_html,
                            dest=pdf_file,
                            encoding="utf-8"
                        )
                    
                    if not result.err:
                        logger.info(f"Generated PDF report with enhanced xhtml2pdf: {output_path}")
                        return output_path
                    else:
                        logger.error(f"Error converting HTML to PDF with xhtml2pdf: {result.err}")
                except ImportError:
                    logger.warning("BeautifulSoup not installed. Try: pip install beautifulsoup4")
                except Exception as e:
                    logger.error(f"Error with enhanced xhtml2pdf: {str(e)}")
                
                # Standard xhtml2pdf as final fallback
                try:
                    import xhtml2pdf.pisa as pisa
                    
                    # Read HTML content
                    with open(html_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    
                    # Create PDF
                    with open(output_path, "wb") as pdf_file:
                        result = pisa.CreatePDF(
                            src=html_content,
                            dest=pdf_file,
                            encoding="utf-8"
                        )
                    
                    if not result.err:
                        logger.info(f"Generated PDF report with standard xhtml2pdf: {output_path}")
                        return output_path
                    else:
                        logger.error(f"Error converting HTML to PDF with standard xhtml2pdf: {result.err}")
                except Exception as e:
                    logger.error(f"Error with standard xhtml2pdf: {str(e)}")
            
            # If all HTML to PDF conversions failed or HTML wasn't generated, fallback to ReportLab
            logger.warning("Falling back to ReportLab for PDF generation")
            return self._generate_reportlab_pdf(data, style, output_path)
                
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            return self._generate_reportlab_pdf(data, style, output_path)  # Fallback to ReportLab
    
    def _generate_reportlab_pdf(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate a PDF report using ReportLab."""
        try:
            # Extract data for easier access
            student = data["student"]
            school = data["school"]
            subjects = data["subjects"]
            
            student_name = student["name"]["full_name"]
            grade = student["grade"]
            class_name = student["class"]
            teacher_name = student["teacher"]["full_name"]
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            heading_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # Custom styles
            title_style.alignment = 1  # Center
            
            subject_style = ParagraphStyle(
                'SubjectHeading',
                parent=styles['Heading3'],
                textColor=colors.navy,
                spaceAfter=6
            )
            
            # Create styles for table cells
            header_style = ParagraphStyle(
                'Header',
                parent=normal_style,
                fontSize=10,
                fontName='Helvetica-Bold',
                alignment=1,  # Center
            )
            
            cell_style = ParagraphStyle(
                'Cell',
                parent=normal_style,
                fontSize=9,
                leading=11,
                wordWrap='CJK',
            )
            
            centered_cell_style = ParagraphStyle(
                'CenteredCell',
                parent=cell_style,
                alignment=1,  # Center
            )
            
            comment_style = ParagraphStyle(
                'Comment',
                parent=normal_style,
                fontSize=8,
                leading=10,
                wordWrap='CJK',
            )
            
            # Build content
            content = []
            
            # School header
            content.append(Paragraph(school["name"], title_style))
            content.append(Paragraph("Student Report", heading_style))
            content.append(Spacer(1, 12))
            
            # Student info
            content.append(Paragraph(f"Student: {student_name}", normal_style))
            content.append(Paragraph(f"Grade: {grade}", normal_style))
            content.append(Paragraph(f"Class: {class_name}", normal_style))
            content.append(Paragraph(f"Teacher: {teacher_name}", normal_style))
            content.append(Paragraph(f"Report Period: Semester {data.get('semester', '1')} {data.get('year', '2024')}", normal_style))
            content.append(Spacer(1, 24))
            
            # Academic performance
            content.append(Paragraph("Academic Performance", heading_style))
            content.append(Spacer(1, 6))
            
            # Style-specific label changes
            if style.lower() == "nsw":
                achievement_label = "Achievement"
                effort_label = "Effort"
            elif style.lower() == "act":
                achievement_label = "Achievement"
                effort_label = "Effort"
            else:
                achievement_label = "Achievement"
                effort_label = "Effort"
            
            # Create table for subject assessments
            table_data = [
                [
                    Paragraph("Subject", header_style),
                    Paragraph(achievement_label, header_style),
                    Paragraph(effort_label, header_style),
                    Paragraph("Comments", header_style)
                ]
            ]
            
            for subject_data in subjects:
                subject = subject_data["subject"]
                achievement = subject_data["achievement"]["label"]
                achievement_code = subject_data["achievement"].get("code", "")
                
                effort = subject_data["effort"]["label"]
                effort_code = subject_data["effort"].get("code", "")
                
                comment = subject_data["comment"]
                
                # Add achievement code if available
                achievement_display = f"{achievement} ({achievement_code})" if achievement_code else achievement
                effort_display = f"{effort} ({effort_code})" if effort_code else effort
                
                table_data.append([
                    Paragraph(subject, cell_style),
                    Paragraph(achievement_display, centered_cell_style),
                    Paragraph(effort_display, centered_cell_style),
                    Paragraph(comment, comment_style)
                ])
            
            # Create the table with adjusted column widths
            col_widths = [85, 100, 60, 225]  # Adjusted column widths
            table = Table(table_data, colWidths=col_widths)
            
            # Apply table styling
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align all content to top of cells
                ('LEFTPADDING', (0, 0), (-1, -1), 5),  # Add padding to all cells
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            content.append(table)
            content.append(Spacer(1, 24))
            
            # Attendance
            content.append(Paragraph("Attendance", heading_style))
            content.append(Spacer(1, 6))
            
            attendance = data.get("attendance", {})
            attendance_data = [
                [
                    Paragraph("Days Present", header_style),
                    Paragraph("Days Absent", header_style),
                    Paragraph("Days Late", header_style),
                    Paragraph("Attendance Rate", header_style)
                ],
                [
                    str(attendance.get("present_days", 0)),
                    str(attendance.get("absent_days", 0)),
                    str(attendance.get("late_days", 0)),
                    f"{attendance.get('attendance_rate', 0)}%"
                ]
            ]
            
            attendance_table = Table(attendance_data, colWidths=[120, 120, 120, 120])
            attendance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            content.append(attendance_table)
            content.append(Spacer(1, 24))
            
            # General comment
            content.append(Paragraph("General Comment", heading_style))
            content.append(Spacer(1, 6))
            content.append(Paragraph(data.get("general_comment", ""), normal_style))
            content.append(Spacer(1, 24))
            
            # Signatures
            content.append(Paragraph("Signatures", heading_style))
            content.append(Spacer(1, 6))
            
            signature_data = [
                [
                    Paragraph("Teacher", header_style),
                    Paragraph("Principal", header_style)
                ],
                [
                    teacher_name,
                    school.get("principal", "School Principal")
                ]
            ]
            
            signature_table = Table(signature_data, colWidths=[225, 225])
            signature_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            content.append(signature_table)
            
            # Build the PDF
            doc.build(content)
            logger.info(f"Generated PDF report with ReportLab: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating PDF report with ReportLab: {str(e)}")
            return ""
    
    def generate_batch_reports(
        self, 
        num_reports: int,
        style: str = "generic",
        output_format: str = "pdf",
        comment_length: str = "standard",
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a batch of synthetic student reports.
        
        Args:
            num_reports: Number of reports to generate
            style: Report style to use
            output_format: Output format (pdf or html)
            comment_length: Length of comments (brief, standard, detailed)
            batch_id: Optional batch ID (generated if not provided)
            
        Returns:
            Dictionary with batch information
        """
        # Create or use batch ID
        if not batch_id:
            batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        output_dir = self.output_dir / batch_id
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate reports
        reports = []
        
        for i in range(num_reports):
            try:
                output_path = str(output_dir / f"report_{i+1}.{output_format}")
                
                report_path = self.generate_report(
                    student_data=None,  # Generate synthetic data
                    style=style,
                    output_format=output_format,
                    comment_length=comment_length,
                    output_path=output_path
                )
                
                if report_path:
                    # Extract student name from filename
                    filename = os.path.basename(report_path)
                    student_name = filename.split('_')[0].replace('_', ' ')
                    
                    reports.append({
                        "id": f"report_{i+1}",
                        "student_name": student_name,
                        "path": report_path,
                        "status": "generated"
                    })
                else:
                    reports.append({
                        "id": f"report_{i+1}",
                        "status": "failed"
                    })
            except Exception as e:
                logger.error(f"Error generating report {i+1}: {str(e)}")
                reports.append({
                    "id": f"report_{i+1}",
                    "status": "failed",
                    "error": str(e)
                })
        
        # Create batch information
        batch_result = {
            "batch_id": batch_id,
            "style": style,
            "num_reports": num_reports,
            "format": output_format,
            "reports": reports,
            "status": "completed",
            "completion_time": datetime.now().isoformat()
        }
        
        # Save batch metadata
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(batch_result, f, indent=2)
        
        logger.info(f"Generated {len([r for r in reports if r['status'] == 'generated'])} out of {num_reports} reports for batch {batch_id}")
        return batch_result
    
    def create_zip_archive(self, batch_id: str) -> Optional[str]:
        """
        Create a ZIP archive of all reports in a batch.
        
        Args:
            batch_id: The batch ID
            
        Returns:
            Path to the ZIP archive or None if failed
        """
        import zipfile
        
        batch_dir = self.output_dir / batch_id
        if not batch_dir.exists():
            logger.error(f"Batch directory not found: {batch_dir}")
            return None
        
        zip_path = self.output_dir / f"{batch_id}.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files in the batch directory
                for file_path in batch_dir.glob('*.*'):
                    # Skip the metadata file if desired
                    if file_path.name == "metadata.json":
                        continue
                    
                    # Add file to the archive
                    zipf.write(
                        file_path,
                        arcname=file_path.name
                    )
            
            logger.info(f"Created ZIP archive: {zip_path}")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {str(e)}")
            return None
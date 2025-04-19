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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import random

# Import from the refactored structure
from src.report_engine.styles.report_styles import ReportStyle, get_style_handler
from src.report_engine.ai.ai_content_generator import AIContentGenerator
from src.report_engine.templates.template_handler import TemplateHandler
from src.report_engine.student_data_generator import StudentProfile, SchoolProfile, StudentDataGenerator

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
                # Write HTML to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                logger.info(f"Generated HTML report: {output_path}")
                return output_path
            else:
                logger.error("Failed to render template")
                return ""
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            return ""
    
    def _generate_pdf_report(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate a PDF report."""
        # Try using HTML to PDF conversion first
        html_path = output_path.replace(".pdf", ".html")
        html_output_path = self._generate_html_report(data, style, html_path)
        
        if html_output_path and os.path.exists(html_output_path):
            # Try to convert HTML to PDF
            if hasattr(self.template_handler, 'html_to_pdf') and self.template_handler.html_to_pdf(html_path, output_path):
                # Remove temporary HTML file
                try:
                    os.remove(html_path)
                except:
                    pass
                
                logger.info(f"Generated PDF report: {output_path}")
                return output_path
        
        # Fallback to direct PDF generation using ReportLab
        return self._generate_reportlab_pdf(data, style, output_path)
    
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
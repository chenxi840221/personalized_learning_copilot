import os
import logging
import tempfile
import subprocess
import uuid
import json
import random
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# Azure Form Recognizer/Document Intelligence client
try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        pass

# OpenAI client
try:
    from openai import AzureOpenAI
except ImportError:
    pass

# PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm
except ImportError:
    pass

# Set up logging
logger = logging.getLogger(__name__)

class StudentReportSystem:
    """Student Report System for generating standardized reports based on templates."""
    
    def __init__(
        self,
        form_recognizer_endpoint: str,
        form_recognizer_key: str,
        openai_endpoint: str,
        openai_key: str,
        openai_deployment: str
    ):
        """Initialize the Student Report System with required Azure services."""
        self.form_recognizer_endpoint = form_recognizer_endpoint
        self.form_recognizer_key = form_recognizer_key
        self.openai_endpoint = openai_endpoint
        self.openai_key = openai_key
        self.openai_deployment = openai_deployment
        
        # Initialize Azure clients
        self.document_client = self._init_document_client()
        self.openai_client = self._init_openai_client()
        
        # Check LibreOffice availability for Word document handling
        self.libreoffice_path = self._find_libreoffice()
        
        # Create necessary directories
        os.makedirs("templates", exist_ok=True)
        os.makedirs("output", exist_ok=True)
        os.makedirs("uploads", exist_ok=True)
        
        logger.info(f"Student Report System initialized: Form Recognizer {'✅' if self.document_client else '❌'}, "
                   f"OpenAI {'✅' if self.openai_client else '❌'}, "
                   f"LibreOffice {'✅' if self.libreoffice_path else '❌'}")
    
    def _init_document_client(self):
        """Initialize the Document Intelligence/Form Recognizer client."""
        if not self.form_recognizer_endpoint or not self.form_recognizer_key:
            logger.warning("Form Recognizer credentials not provided")
            return None
        
        try:
            credential = AzureKeyCredential(self.form_recognizer_key)
            
            # Try to use DocumentIntelligence first (newer API)
            try:
                client = DocumentIntelligenceClient(
                    endpoint=self.form_recognizer_endpoint,
                    credential=credential
                )
                logger.info("Using DocumentIntelligence client")
                return client
            except (NameError, ImportError):
                # Fall back to FormRecognizer if DocumentIntelligence is not available
                try:
                    client = DocumentAnalysisClient(
                        endpoint=self.form_recognizer_endpoint,
                        credential=credential
                    )
                    logger.info("Using Form Recognizer client")
                    return client
                except (NameError, ImportError):
                    logger.error("Neither DocumentIntelligence nor FormRecognizer client could be initialized")
                    return None
        except Exception as e:
            logger.error(f"Failed to initialize Document client: {str(e)}")
            return None
    
    def _init_openai_client(self):
        """Initialize the Azure OpenAI client."""
        if not self.openai_endpoint or not self.openai_key or not self.openai_deployment:
            logger.warning("OpenAI credentials not provided")
            return None
        
        try:
            client = AzureOpenAI(
                api_key=self.openai_key,
                api_version="2023-05-15",
                azure_endpoint=self.openai_endpoint
            )
            logger.info(f"OpenAI client initialized with deployment: {self.openai_deployment}")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return None
    
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

    def analyze_template(self, file_path: str) -> Dict[str, Any]:
        """Analyze a template file using Azure Form Recognizer."""
        if not self.document_client:
            logger.error("Document client not initialized")
            return {"status": "error", "message": "Document client not initialized"}
        
        if not os.path.exists(file_path):
            logger.error(f"Template file not found: {file_path}")
            return {"status": "error", "message": f"Template file not found: {file_path}"}
        
        try:
            # Read file content
            with open(file_path, "rb") as f:
                document_content = f.read()
            
            # Use Document Intelligence/Form Recognizer to analyze the document
            result = None
            try:
                # Try DocumentIntelligence API first
                poller = self.document_client.begin_analyze_document(
                    "prebuilt-layout", document_content
                )
                result = poller.result()
            except AttributeError:
                # Fall back to Form Recognizer API
                try:
                    poller = self.document_client.begin_analyze_document(
                        "prebuilt-layout", document_content
                    )
                    result = poller.result()
                except Exception as e:
                    logger.error(f"Form Recognizer analysis failed: {str(e)}")
                    return {"status": "error", "message": f"Form Recognizer analysis failed: {str(e)}"}
            
            # Process the analysis result
            if result:
                # Extract tables, text, and other elements
                tables = []
                text_blocks = []
                
                # Process tables
                for table in result.tables:
                    table_data = []
                    for row_idx in range(table.row_count):
                        row_data = []
                        for col_idx in range(table.column_count):
                            # Find cell at this position
                            cell_text = ""
                            for cell in table.cells:
                                if cell.row_index == row_idx and cell.column_index == col_idx:
                                    cell_text = cell.content
                                    break
                            row_data.append(cell_text)
                        table_data.append(row_data)
                    tables.append(table_data)
                
                # Process text content
                if hasattr(result, 'paragraphs'):
                    for paragraph in result.paragraphs:
                        text_blocks.append({
                            "text": paragraph.content,
                            "bounding_box": paragraph.bounding_regions[0].polygon if paragraph.bounding_regions else None
                        })
                elif hasattr(result, 'content'):
                    text_blocks.append({
                        "text": result.content,
                        "bounding_box": None
                    })
                
                analysis_result = {
                    "status": "success",
                    "tables": tables,
                    "text_blocks": text_blocks,
                    "page_count": result.pages[0].page_number if result.pages else 1,
                    "document_type": "report_template"
                }
                
                return analysis_result
            else:
                logger.error("No result from Form Recognizer analysis")
                return {"status": "error", "message": "No result from Form Recognizer analysis"}
                
        except Exception as e:
            logger.error(f"Template analysis failed: {str(e)}")
            return {"status": "error", "message": f"Template analysis failed: {str(e)}"}

    def convert_word_to_pdf(self, word_path: str) -> Optional[str]:
        """Convert Word document to PDF format."""
        if not os.path.exists(word_path):
            logger.error(f"Word document not found: {word_path}")
            return None
        
        pdf_path = os.path.splitext(word_path)[0] + ".pdf"
        
        if self.libreoffice_path:
            try:
                # Use LibreOffice for conversion
                temp_dir = tempfile.mkdtemp()
                cmd = [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", temp_dir,
                    word_path
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Move converted file to destination
                converted_file = os.path.join(temp_dir, os.path.basename(pdf_path))
                if os.path.exists(converted_file):
                    with open(converted_file, "rb") as src, open(pdf_path, "wb") as dst:
                        dst.write(src.read())
                    logger.info(f"Successfully converted {word_path} to PDF using LibreOffice")
                    return pdf_path
                else:
                    logger.error(f"Conversion failed, output file not found: {converted_file}")
                    return None
            except Exception as e:
                logger.error(f"LibreOffice conversion failed: {str(e)}")
                return None
        else:
            logger.warning("LibreOffice not available for Word conversion")
            # Fallback method using python-docx could be implemented here
            return None
        
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available report templates."""
        templates = []
        templates_dir = Path("templates")
        
        if not templates_dir.exists():
            return templates
        
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir():
                template_id = template_dir.name
                metadata_file = template_dir / "metadata.json"
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                            templates.append(metadata)
                    except Exception as e:
                        logger.error(f"Failed to load template metadata: {str(e)}")
                else:
                    # Basic info without metadata
                    templates.append({
                        "id": template_id,
                        "name": template_id.replace("_", " ").title(),
                        "status": "unknown"
                    })
        
        return templates
    
    def _generate_random_student_data(self) -> Dict[str, Any]:
        """Generate randomized student data for report generation."""
        # Random student names
        first_names = [
            "Emma", "Liam", "Olivia", "Noah", "Charlotte", "Ethan", 
            "Ava", "William", "Sophia", "James", "Amelia", "Benjamin",
            "Isabella", "Lucas", "Mia", "Henry", "Evelyn", "Alexander",
            "Harper", "Mason", "Abigail", "Michael", "Emily", "Elijah",
            "Ella", "Daniel", "Scarlett", "Matthew", "Aria", "Aiden"
        ]
        
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller",
            "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson",
            "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Jackson",
            "Thompson", "White", "Lopez", "Lee", "Gonzalez", "Harris",
            "Clark", "Lewis", "Young", "Walker", "Hall", "Allen"
        ]
        
        # Random teacher names
        teachers = [
            "Ms. Johnson", "Mr. Thompson", "Mrs. Williams", "Mr. Davis",
            "Ms. Martinez", "Mrs. Brown", "Mr. Wilson", "Ms. Anderson",
            "Mr. Thomas", "Mrs. Taylor", "Ms. Lewis", "Mr. Clark"
        ]
        
        # Generate random grade and achievement levels
        grades = ["Prep", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"]
        grade_marks = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
        achievement_levels = ["Above Expected Level", "At Expected Level", "Working Towards Expected Level"]
        
        # Generate random comments
        english_comments = [
            "{name} has shown great improvement in reading comprehension and creative writing. {He_She} contributes well in class discussions and is developing good analytical skills.",
            "{name} reads fluently and with expression, demonstrating excellent comprehension skills. {His_Her} writing is creative with a good grasp of grammar and punctuation.",
            "{name} is working well in English, with consistent effort in both reading and writing tasks. {He_She} should focus on expanding vocabulary and sentence complexity.",
            "{name} shows enthusiasm in English lessons and has made good progress in reading this semester. Writing skills are developing well with good use of descriptive language.",
            "{name} demonstrates strong literacy skills, particularly in comprehension and text analysis. {His_Her} creative writing shows imagination and technical skill."
        ]
        
        math_comments = [
            "{name} demonstrates excellent problem-solving abilities and has a strong grasp of number concepts. {He_She} should continue to challenge {himself_herself} with complex problems.",
            "{name} works methodically in Mathematics, showing good understanding of key concepts. {He_She} has particularly excelled in geometry and measurement this term.",
            "{name} has made solid progress in Mathematics, with strengths in number operations. More practice with word problems would further enhance {his_her} skills.",
            "{name} approaches mathematical challenges with confidence and shows good reasoning skills. {He_She} has developed strong abilities in data interpretation and statistics.",
            "{name} is developing good mathematical thinking and shows persistence when solving problems. {His_Her} understanding of fractions and decimals has improved significantly."
        ]
        
        science_comments = [
            "{name} shows curiosity about scientific concepts and participates actively in experiments. {He_She} is developing good observational skills and scientific reasoning.",
            "{name} demonstrates keen interest in scientific investigations and asks thoughtful questions. {His_Her} experiment reports show detailed observations and logical conclusions.",
            "{name} engages enthusiastically in science activities and is developing good inquiry skills. {He_She} should continue to focus on recording observations systematically.",
            "{name} has a natural curiosity for scientific phenomena and contributes valuable ideas during class discussions. {His_Her} project work shows creativity and understanding.",
            "{name} approaches scientific investigations methodically and shows good understanding of key concepts. {He_She} communicates scientific ideas clearly both verbally and in writing."
        ]
        
        humanities_comments = [
            "{name} has shown a good understanding of historical concepts and geographic principles. {He_She} creates informative projects and contributes thoughtfully to discussions.",
            "{name} demonstrates strong interest in social studies and history topics. {His_Her} research projects are well-organized with attention to detail.",
            "{name} is developing a good knowledge of historical events and cultural perspectives. {He_She} presents information clearly with supporting evidence.",
            "{name} shows curiosity about different cultures and historical periods. {His_Her} map work is detailed and accurate, showing good spatial awareness.",
            "{name} contributes meaningful insights during humanities discussions and makes connections between historical events and modern issues."
        ]
        
        pe_comments = [
            "{name} displays excellent coordination and teamwork skills. {He_She} participates enthusiastically in all activities and demonstrates good sportsmanship.",
            "{name} shows determination and effort in physical activities. {His_Her} ball skills have improved significantly this term.",
            "{name} participates cooperatively in team games and shows growing confidence in movement skills. {He_She} demonstrates good sporting behavior.",
            "{name} approaches physical challenges with enthusiasm and persistence. {He_She} has particularly improved in {his_her} balance and coordination skills.",
            "{name} demonstrates athletic ability and leadership during team activities. {He_She} encourages others and shows excellent sporting values."
        ]
        
        arts_comments = [
            "{name} is developing {his_her} creative skills and shows genuine interest in visual arts. {He_She} works carefully on {his_her} projects and is receptive to feedback.",
            "{name} demonstrates creativity and attention to detail in art projects. {His_Her} understanding of color and composition is developing well.",
            "{name} approaches creative tasks with enthusiasm and originality. {He_She} is developing good technical skills in different artistic media.",
            "{name} shows natural artistic ability and experiments confidently with different techniques. {His_Her} work demonstrates thoughtful planning and execution.",
            "{name} participates enthusiastically in arts activities and is developing a personal style. {He_She} takes pride in {his_her} creative work."
        ]
        
        general_comments = [
            "{name} has had an excellent semester, showing growth academically and socially. {He_She} is a respectful student who contributes positively to the classroom environment. {name} works well independently and collaboratively, taking pride in {his_her} work. We encourage {him_her} to continue challenging {himself_herself} in all areas.",
            "{name} has demonstrated a positive attitude towards learning this semester. {He_She} is a thoughtful class member who treats others with respect and kindness. {name} approaches tasks with enthusiasm and perseverance, showing good organizational skills. We look forward to {his_her} continued progress next semester.",
            "{name} has made good progress across the curriculum this term. {He_She} contributes valuable ideas during class discussions and works cooperatively with peers. {name} is developing effective study habits and shows increasing independence in {his_her} learning. We encourage {him_her} to continue building confidence in sharing {his_her} ideas.",
            "{name} has had a productive semester and should be proud of {his_her} achievements. {He_She} demonstrates curiosity and engagement in learning activities. {name} is a positive influence in the classroom, showing kindness and consideration towards others. We look forward to supporting {his_her} continued growth next term.",
            "{name} has shown commitment to {his_her} learning this semester. {He_She} participates actively in class activities and consistently completes tasks to a high standard. {name} cooperates well with others and demonstrates leadership qualities in group situations. We encourage {him_her} to maintain this positive approach to learning."
        ]
        
        # Generate a random student
        gender = random.choice(["male", "female"])
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        
        # Generate pronouns based on gender
        pronouns = {
            "he_she": "he" if gender == "male" else "she",
            "He_She": "He" if gender == "male" else "She",
            "his_her": "his" if gender == "male" else "her",
            "His_Her": "His" if gender == "male" else "Her",
            "him_her": "him" if gender == "male" else "her",
            "himself_herself": "himself" if gender == "male" else "herself"
        }
        
        # Select random grades and comments
        selected_grade = random.choice(grades)
        
        # Generate random achievement levels and grades for subjects
        subjects = {}
        
        # English
        eng_achievement = random.choices(achievement_levels, weights=[0.4, 0.4, 0.2])[0]
        eng_grade = random.choice(["A+", "A", "A-", "B+", "B"] if eng_achievement == "Above Expected Level" else 
                                 ["B+", "B", "B-", "C+"] if eng_achievement == "At Expected Level" else
                                 ["C+", "C", "C-"])
        eng_comment = random.choice(english_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        subjects["English"] = {
            "grade": eng_grade,
            "comment": eng_comment,
            "achievement": eng_achievement
        }
        
        # Mathematics
        math_achievement = random.choices(achievement_levels, weights=[0.4, 0.4, 0.2])[0]
        math_grade = random.choice(["A+", "A", "A-", "B+", "B"] if math_achievement == "Above Expected Level" else 
                                  ["B+", "B", "B-", "C+"] if math_achievement == "At Expected Level" else
                                  ["C+", "C", "C-"])
        math_comment = random.choice(math_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        subjects["Mathematics"] = {
            "grade": math_grade,
            "comment": math_comment,
            "achievement": math_achievement
        }
        
        # Science
        sci_achievement = random.choices(achievement_levels, weights=[0.3, 0.5, 0.2])[0]
        sci_grade = random.choice(["A+", "A", "A-", "B+", "B"] if sci_achievement == "Above Expected Level" else 
                                 ["B+", "B", "B-", "C+"] if sci_achievement == "At Expected Level" else
                                 ["C+", "C", "C-"])
        sci_comment = random.choice(science_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        subjects["Science"] = {
            "grade": sci_grade,
            "comment": sci_comment,
            "achievement": sci_achievement
        }
        
        # Humanities
        hum_achievement = random.choices(achievement_levels, weights=[0.3, 0.5, 0.2])[0]
        hum_grade = random.choice(["A+", "A", "A-", "B+", "B"] if hum_achievement == "Above Expected Level" else 
                                 ["B+", "B", "B-", "C+"] if hum_achievement == "At Expected Level" else
                                 ["C+", "C", "C-"])
        hum_comment = random.choice(humanities_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        subjects["Humanities"] = {
            "grade": hum_grade,
            "comment": hum_comment,
            "achievement": hum_achievement
        }
        
        # Physical Education
        pe_achievement = random.choices(achievement_levels, weights=[0.4, 0.4, 0.2])[0]
        pe_grade = random.choice(["A+", "A", "A-", "B+", "B"] if pe_achievement == "Above Expected Level" else 
                                ["B+", "B", "B-", "C+"] if pe_achievement == "At Expected Level" else
                                ["C+", "C", "C-"])
        pe_comment = random.choice(pe_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        subjects["Physical Education"] = {
            "grade": pe_grade,
            "comment": pe_comment,
            "achievement": pe_achievement
        }
        
        # Arts
        arts_achievement = random.choices(achievement_levels, weights=[0.3, 0.5, 0.2])[0]
        arts_grade = random.choice(["A+", "A", "A-", "B+", "B"] if arts_achievement == "Above Expected Level" else 
                                  ["B+", "B", "B-", "C+"] if arts_achievement == "At Expected Level" else
                                  ["C+", "C", "C-"])
        arts_comment = random.choice(arts_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        subjects["Arts"] = {
            "grade": arts_grade,
            "comment": arts_comment,
            "achievement": arts_achievement
        }
        
        # Attendance - generate realistic numbers
        total_days = random.randint(45, 52)
        absent_days = random.randint(0, 5)
        late_days = random.randint(0, 3)
        present_days = total_days - absent_days
        
        # General comment
        general_comment = random.choice(general_comments).format(name=first_name, **{k: v for k, v in pronouns.items()})
        
        # Principal and teacher signatures
        principals = ["Dr. A. Williams", "Mrs. E. Bennett", "Mr. J. Robertson", "Dr. S. Thompson", "Ms. L. Chen"]
        selected_teacher = random.choice(teachers)
        
        return {
            "name": full_name,
            "grade": selected_grade,
            "teacher": selected_teacher,
            "period": f"Semester {random.randint(1, 2)}, 2025",
            "subjects": subjects,
            "attendance": {
                "days_present": present_days,
                "days_absent": absent_days,
                "days_late": late_days
            },
            "general_comment": general_comment,
            "principal_signature": random.choice(principals),
            "teacher_signature": selected_teacher
        }

    def generate_report_pdf(self, student_data: Dict[str, Any], template_analysis: Dict[str, Any], output_path: str) -> bool:
        """Generate a PDF report for a student based on template analysis."""
        try:
            # Create a PDF document
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
            subject_style = ParagraphStyle(
                'SubjectHeading',
                parent=styles['Heading3'],
                textColor=colors.navy,
                spaceAfter=6
            )
            
            # Create styles for all table cells to ensure proper text wrapping
            header_style = ParagraphStyle(
                'Header',
                parent=normal_style,
                fontSize=10,
                fontName='Helvetica-Bold',
                alignment=1,  # Center
            )
            
            subject_cell_style = ParagraphStyle(
                'Subject',
                parent=normal_style,
                fontSize=9,
                leading=11,
                wordWrap='CJK',
            )
            
            achievement_cell_style = ParagraphStyle(
                'Achievement',
                parent=normal_style,
                fontSize=9,
                leading=11,
                wordWrap='CJK',
                alignment=1,  # Center
            )
            
            grade_cell_style = ParagraphStyle(
                'Grade',
                parent=normal_style,
                fontSize=9,
                leading=11,
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
            content.append(Paragraph("Australian Primary School", title_style))
            content.append(Paragraph("Student Progress Report", heading_style))
            content.append(Spacer(1, 12))
            
            # Student info
            content.append(Paragraph(f"Student: {student_data['name']}", normal_style))
            content.append(Paragraph(f"Grade: {student_data['grade']}", normal_style))
            content.append(Paragraph(f"Teacher: {student_data['teacher']}", normal_style))
            content.append(Paragraph(f"Reporting Period: {student_data['period']}", normal_style))
            content.append(Spacer(1, 24))
            
            # Academic performance
            content.append(Paragraph("Academic Performance", heading_style))
            content.append(Spacer(1, 6))
            
            # Create table for subject assessments with styled paragraphs for all cells
            table_data = [
                [
                    Paragraph("Subject", header_style),
                    Paragraph("Achievement", header_style),
                    Paragraph("Grade", header_style),
                    Paragraph("Comments", header_style)
                ]
            ]
            
            for subject, details in student_data['subjects'].items():
                # Wrap all text in appropriate Paragraph objects
                table_data.append([
                    Paragraph(subject, subject_cell_style),
                    Paragraph(details['achievement'], achievement_cell_style),
                    Paragraph(details['grade'], grade_cell_style),
                    Paragraph(details['comment'], comment_style)
                ])
            
            # Create the table with adjusted column widths
            col_widths = [85, 100, 40, 225]  # Adjusted column widths
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
            
            # Use Paragraph objects for attendance table headers too
            attendance_data = [
                [
                    Paragraph("Days Present", header_style),
                    Paragraph("Days Absent", header_style),
                    Paragraph("Days Late", header_style)
                ],
                [
                    str(student_data['attendance']['days_present']),
                    str(student_data['attendance']['days_absent']),
                    str(student_data['attendance']['days_late'])
                ]
            ]
            
            attendance_table = Table(attendance_data, colWidths=[150, 150, 150])
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
            content.append(Paragraph(student_data['general_comment'], normal_style))
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
                    student_data['teacher_signature'],
                    student_data['principal_signature']
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
            logger.info(f"Generated report PDF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {str(e)}")
            return False

    def generate_reports(self, template_id: str, num_reports: int = 5, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate synthetic student reports based on the template."""
        logger.info(f"Generating {num_reports} reports using template: {template_id}")
        
        # Get template information
        template_dir = Path("templates") / template_id
        metadata_file = template_dir / "metadata.json"
        
        if not metadata_file.exists():
            error_msg = f"Template metadata not found: {template_id}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        try:
            # Load template metadata
            with open(metadata_file, "r") as f:
                template_metadata = json.load(f)
            
            # Analyze template if not already analyzed
            template_analysis = None
            analysis_file = template_dir / "analysis.json"
            
            if analysis_file.exists():
                with open(analysis_file, "r") as f:
                    template_analysis = json.load(f)
            else:
                # Perform analysis on the template
                template_path = template_metadata.get("file_path")
                if template_path and os.path.exists(template_path):
                    template_analysis = self.analyze_template(template_path)
                    # Save analysis for future use
                    with open(analysis_file, "w") as f:
                        json.dump(template_analysis, f, indent=2)
                else:
                    error_msg = f"Template file not found: {template_path}"
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}
            
            # Create or use batch ID
            if not batch_id:
                batch_id = f"batch_{uuid.uuid4().hex[:8]}"
            
            output_dir = Path("output") / batch_id
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate reports
            reports = []
            for i in range(num_reports):
                # Generate unique student data for each report
                student_data = self._generate_random_student_data()
                
                # Create report ID
                report_id = f"report_{i+1}"
                report_path = output_dir / f"{report_id}.pdf"
                
                # Generate PDF report
                success = self.generate_report_pdf(
                    student_data=student_data,
                    template_analysis=template_analysis,
                    output_path=str(report_path)
                )
                
                if success:
                    reports.append({
                        "id": report_id,
                        "student_name": student_data["name"],
                        "path": str(report_path),
                        "status": "generated"
                    })
                else:
                    reports.append({
                        "id": report_id,
                        "student_name": student_data["name"],
                        "status": "failed"
                    })
            
            # Update batch metadata
            batch_result = {
                "batch_id": batch_id,
                "template_id": template_id,
                "template_name": template_metadata.get("name", "Unknown"),
                "num_reports": num_reports,
                "reports": reports,
                "status": "completed",
                "completion_time": datetime.now().isoformat()
            }
            
            # Save batch metadata
            with open(output_dir / "metadata.json", "w") as f:
                json.dump(batch_result, f, indent=2)
            
            logger.info(f"Successfully generated {len(reports)} reports for batch: {batch_id}")
            return batch_result
            
        except Exception as e:
            error_msg = f"Failed to generate reports: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
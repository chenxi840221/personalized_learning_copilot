# Student Report Generation System

An AI-powered system for generating personalized student reports that follow Australian educational standards with support for different state/territory formats (ACT, NSW, etc.).

## Overview

This system automates the creation of student academic reports by leveraging Azure OpenAI's GPT-4o to generate realistic, personalized report comments. It supports multiple Australian educational standards and formats, allowing schools to produce professional and consistent reports across different states and territories.

## Features

### Core Functionality
- **AI-Generated Content**: Uses Azure OpenAI's GPT-4o to generate realistic, personalized report comments based on student achievement and effort levels
- **Multiple Report Styles**: Supports different Australian state/territory formats (ACT, NSW, QLD, VIC, etc.)
- **Personalized Assessment**: Generates comments tailored to specific subjects and student profiles
- **Batch Processing**: Generate multiple reports at once with unique synthetic student profiles
- **Multiple Output Formats**: Export reports as PDF or HTML with professionally formatted layouts

### Technical Features
- **Customizable Templates**: HTML-based templates for easy customization
- **Robust PDF Generation**: Multiple PDF conversion methods for maximum reliability
- **Realistic Student Data**: Generate synthetic student profiles for testing with diverse demographics
- **Style Management**: Easily configure different grading scales, subjects, and terminology
- **Command-Line Interface**: Simple CLI for generating reports individually or in batches

## System Architecture

### Core Components
- **AI Content Generator**: Interfaces with Azure OpenAI to generate personalized report comments
- **Report Style Handling**: Manages different grading scales and formats by state/territory
- **Template System**: HTML-based template rendering for consistent report formatting
- **PDF Generation**: Multiple fallback methods to ensure reliable PDF production
- **Student Data Generator**: Creates realistic synthetic student profiles for testing

### Directory Structure
```
student-report-synthesis/
├── src/
│   └── report_engine/
│       ├── ai/                 # AI content generation using Azure OpenAI
│       ├── styles/             # Report style handling for different standards
│       ├── templates/          # HTML template handling and rendering
│       ├── utils/              # Utility functions (PDF conversion, etc.)
│       ├── student_data_generator.py  # Synthetic student profile generation
│       └── enhanced_report_generator.py  # Main report generation logic
├── report_styles/              # JSON configurations for different report formats
├── templates/                  # HTML templates for report rendering
├── output/                     # Generated reports are saved here
├── main.py                     # Main entry point to run a single report
├── generate_reports.py         # CLI for generating individual or batch reports
├── enhanced_pdf_converter.py   # Standalone tool for HTML to PDF conversion
└── manage_project.py           # Project management utilities
```

## Setup

### Prerequisites
- Python 3.8 or higher
- Azure OpenAI API access
- Required Python packages (see requirements.txt)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/student-report-synthesis.git
   cd student-report-synthesis
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env` file:
   ```
   OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
   OPENAI_KEY=your-openai-key
   OPENAI_DEPLOYMENT=gpt-4o
   ```

### Optional Dependencies
For PDF generation:
- WeasyPrint (recommended for best quality)
- xhtml2pdf (fallback)
- wkhtmltopdf (command-line tool, recommended for enhanced PDF handling)

## Usage

### Basic Usage
Generate a sample report with default settings:
```bash
python main.py
```

### Command-line Interface
The system provides a comprehensive command-line interface for report generation:

#### Generate a single report:
```bash
python generate_reports.py single --style act --format pdf --comment-length standard
```

#### Generate multiple reports in batch:
```bash
python generate_reports.py batch --num 10 --style nsw --format pdf
```

#### List available report styles:
```bash
python generate_reports.py styles
```

#### Validate your setup:
```bash
python generate_reports.py validate
```

### Command Options
- `--style`: Report style (generic, act, nsw, qld, vic, etc.)
- `--format`: Output format (pdf, html)
- `--comment-length`: Length of generated comments (brief, standard, detailed)
- `--output`: Custom output file path (for single reports)
- `--num`: Number of reports to generate (for batch mode)
- `--batch-id`: Custom batch ID (for batch mode)

## Report Styles

The system supports multiple Australian educational jurisdiction styles:

| Style | Description |
|-------|-------------|
| generic | Standard report format with basic subjects |
| act | Australian Capital Territory format |
| nsw | New South Wales format |
| qld | Queensland format |
| vic | Victoria format |

Additional styles can be added by creating new JSON configuration files in the `report_styles` directory.

## Customization

### Templates
Report templates are HTML files located in the `templates` directory. They can be customized to match your school's branding and layout preferences.

### Report Styles
Each report style is defined in a JSON file in the `report_styles` directory. You can customize:
- Subject names
- Achievement scales
- Effort scales
- Additional assessment criteria

### AI Prompts
The AI prompts used to generate report comments can be found in `src/report_engine/ai/ai_content_generator.py` and can be adjusted to match your school's tone and content requirements.

## Development

### Project Structure
The codebase follows a modular structure with clear separation of concerns:
- **AI Generation**: Handled by the `AIContentGenerator` class
- **Report Styles**: Managed by the `ReportStyleHandler` class
- **Templates**: Managed by the `TemplateHandler` class
- **Student Data**: Generated by the `StudentDataGenerator` class
- **Report Generation**: Orchestrated by the `EnhancedReportGenerator` class

### Adding a New Report Style
1. Create a new JSON file in `report_styles/` (e.g., `sa.json` for South Australia)
2. Define the style properties (subjects, achievement scale, effort scale, etc.)
3. Optionally create a corresponding HTML template in `templates/` (e.g., `sa_template.html`)

### Creating Custom Templates
Templates use Jinja2 syntax and have access to the following data:
- `data.student`: Student information (name, grade, class, teacher, etc.)
- `data.school`: School information (name, principal, etc.)
- `data.subjects`: Subject assessments (subject, achievement, effort, comment)
- `data.general_comment`: Overall student comment
- `data.attendance`: Attendance information

## License

[Specify your license here]

## Acknowledgements

- This project uses Azure OpenAI services for AI-generated content
- PDF conversion uses multiple libraries including WeasyPrint and xhtml2pdf
- Template rendering uses Jinja2
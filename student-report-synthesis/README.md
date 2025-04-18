# Student Report Synthesis System

A proof-of-concept project for generating standardized primary student reports following Australian education guidelines. This system uses Azure's AI services to extract information from report templates and produce high-quality, standards-compliant student reports.

## Overview

This system automates the process of creating student reports by:

1. Extracting formatting and content from existing report templates using Azure Form Recognizer
2. Analyzing report structures with Azure OpenAI (GPT-4o)
3. Generating consistent reports according to Australian curriculum guidelines
4. Producing professional PDF reports for training machine learning models

## Features

- **Template Analysis**: Upload and analyze different school report templates
- **Format Standardization**: Extract common elements and create unified report structures
- **Report Generation**: Create synthetic student reports with realistic academic data
- **PDF Output**: Generate professionally formatted PDFs matching education standards
- **Compliance Verification**: Ensure reports meet Australian education guidelines

## System Architecture

The system consists of several components:

- **Data Ingestion**: Processing report templates with Azure Form Recognizer
- **Content Analysis**: Using Azure OpenAI to extract structure and formatting rules
- **Report Generation**: Creating student reports with appropriate content 
- **Quality Assurance**: Verifying compliance with educational standards

## Setup Requirements

### Prerequisites

- Azure Form Recognizer / Document Intelligence account
- Azure OpenAI Service with GPT-4o access
- Docker and Docker Compose
- Python 3.9+

### Environment Variables

Create a `.env` file with the following variables:

```
FORM_RECOGNIZER_ENDPOINT=https://your-form-recognizer.cognitiveservices.azure.com/
FORM_RECOGNIZER_KEY=your-form-recognizer-key
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_KEY=your-openai-key
OPENAI_DEPLOYMENT=gpt-4o
```

## Installation

### Using Docker (Recommended)

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/student-report-synthesis.git
   cd student-report-synthesis
   ```

2. Build and run using Docker:
   ```bash
   chmod +x deployment.sh
   ./deployment.sh
   ```

3. Access the web interface at `http://localhost:8000`

### Manual Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export FORM_RECOGNIZER_ENDPOINT="your-endpoint"
   export FORM_RECOGNIZER_KEY="your-key"
   export OPENAI_ENDPOINT="your-endpoint"
   export OPENAI_KEY="your-key"
   export OPENAI_DEPLOYMENT="gpt-4o"
   ```

3. Run the application:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Usage

### Web Interface

The system includes a web interface where you can:

1. Upload report templates in PDF format
2. View and select from available templates
3. Generate synthetic student reports
4. Download individual reports or all reports as a ZIP file

### API Reference

The system exposes the following API endpoints:

- `POST /templates/upload/`: Upload a new report template
- `GET /templates/`: List all available templates
- `GET /templates/{template_id}/`: Get details of a specific template
- `POST /reports/generate/`: Generate student reports
- `GET /reports/status/{batch_id}/`: Check generation status
- `GET /reports/{batch_id}/{report_id}/download/`: Download a specific report
- `GET /reports/{batch_id}/download-all/`: Download all reports in a batch

## Educational Guidelines Compliance

The system enforces compliance with:

- NSW Department of Education report guidelines
- Victorian Curriculum and Assessment Authority (VCAA) standards
- Australian Curriculum, Assessment and Reporting Authority (ACARA) requirements

## Machine Learning Training

The generated reports can be used to train ML models for:

- Automated assessment text generation
- Student progress analytics
- Report format standardization

## Project Structure

```
student-report-synthesis/
├── main.py                      # FastAPI application entry point
├── student_report_system.py     # Core system implementation
├── Dockerfile                   # Docker configuration
├── requirements.txt             # Python dependencies
├── deployment.sh                # Deployment script
├── templates/                   # Directory for report templates
├── output/                      # Directory for generated reports
├── static/                      # Static web files
│   └── index.html               # Web interface
└── README.md                    # This file
```

## Future Enhancements

- Integration with school management systems
- Additional language support
- Custom template creation tools
- AI-assisted teacher comments
- More detailed curriculum alignment
- Mobile-friendly interfaces

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- NSW Department of Education for report guidelines
- Victorian Curriculum and Assessment Authority (VCAA)
- Australian Curriculum, Assessment and Reporting Authority (ACARA)
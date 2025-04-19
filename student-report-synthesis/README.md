# Student Report Generation System

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

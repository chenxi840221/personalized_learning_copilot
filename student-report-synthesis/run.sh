#!/bin/bash
# run.sh - Direct startup script without Docker

# Set environment variables (replace with your actual Azure service credentials)
export FORM_RECOGNIZER_ENDPOINT=https://australiaeast.api.cognitive.microsoft.com/
export FORM_RECOGNIZER_KEY=416d8e218d834fd6a2c72e4919247b2d
export OPENAI_ENDPOINT=https://australiaeast.api.cognitive.microsoft.com/
export OPENAI_KEY=2ece0e0981a949eba7ff8159f16e96de
export OPENAI_DEPLOYMENT=gpt-4o

#!/bin/bash
# run.sh - Direct startup script without Docker

# Set environment variables (replace with your actual Azure service credentials)
#export FORM_RECOGNIZER_ENDPOINT="https://your-form-recognizer.cognitiveservices.azure.com/"
#export FORM_RECOGNIZER_KEY="your-form-recognizer-key"
#export OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
#export OPENAI_KEY="your-openai-key"
#export OPENAI_DEPLOYMENT="gpt-4o"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Python is not installed. Please install Python 3 and try again."
        exit 1
    fi
else
    PYTHON_CMD="python3"
fi

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ pip is not installed. Please install pip and try again."
    exit 1
fi

# Determine pip command
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
else
    PIP_CMD="pip"
fi

# Check if LibreOffice is installed for Word document support
if command -v libreoffice &> /dev/null || command -v soffice &> /dev/null; then
    echo "✅ LibreOffice found for Word document conversion"
    LIBREOFFICE_INSTALLED=true
else
    echo "⚠️ LibreOffice not found. Word document conversion will use fallback method."
    echo "📌 For better Word document support, consider installing LibreOffice:"
    echo "   - Ubuntu/Debian: sudo apt-get install libreoffice"
    echo "   - CentOS/RHEL: sudo yum install libreoffice"
    echo "   - macOS: brew install --cask libreoffice"
    echo "   - Windows: Download from https://www.libreoffice.org/download/download/"
    LIBREOFFICE_INSTALLED=false
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔨 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ Could not find activation script for virtual environment."
    exit 1
fi

# Install dependencies with specific NumPy and Pandas versions
echo "📦 Installing NumPy and Pandas with specific versions..."
$PIP_CMD install numpy==1.23.5
$PIP_CMD install pandas==2.0.0

# Install other dependencies
echo "📦 Installing other dependencies..."
$PIP_CMD install -r requirements.txt

# Create necessary directories
mkdir -p templates
mkdir -p output
mkdir -p uploads
mkdir -p static
mkdir -p logs

# Check if index.html exists in static directory
if [ ! -f "static/index.html" ]; then
    echo "Creating index.html in static directory..."
    mkdir -p static
    
    # Write a basic index.html file
    cat > static/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Report Synthesis System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.10.5/cdn.min.js" defer></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold text-center text-blue-800">Student Report Synthesis System</h1>
        <p class="text-center text-gray-600">Generate standardized student reports following Australian education guidelines</p>
        
        <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mt-8">
            <p>System is running in direct Python mode.</p>
            <p>The system now supports both PDF and Word (.docx, .doc) templates! All reports will be generated in PDF format.</p>
        </div>
    </div>
</body>
</html>
EOF
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found. Please make sure all application files are in the current directory."
    exit 1
fi

# Run the application
echo "🚀 Starting application..."
echo "✅ The system now supports both PDF and Word (.docx, .doc) templates!"
echo "✅ All reports will be generated in PDF format."
$PYTHON_CMD -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# This will run until you press Ctrl+C

# Deactivate virtual environment (this line won't run until the app stops)
deactivate
#!/bin/bash

# Set environment variables (replace with your actual Azure service credentials)
export FORM_RECOGNIZER_ENDPOINT="https://your-form-recognizer.cognitiveservices.azure.com/"
export FORM_RECOGNIZER_KEY="your-form-recognizer-key"
export OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
export OPENAI_KEY="your-openai-key"
export OPENAI_DEPLOYMENT="gpt-4o"

# Container name
CONTAINER_NAME="student-report-system"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if container already exists
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    echo "Container '$CONTAINER_NAME' already exists. Stopping and removing..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    echo "Container removed."
fi

# Create necessary directories
mkdir -p templates
mkdir -p output
mkdir -p static

# Copy static files if not already present
if [ ! -f "static/index.html" ]; then
    echo "Creating index.html in static directory..."
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
        
        <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded relative mt-8">
            <p>If you're seeing this page, the server is running but the main application hasn't been properly installed.</p>
            <p>Please check that all files are in the correct location and restart the application.</p>
        </div>
    </div>
</body>
</html>
EOF
fi

# Build Docker image with additional LibreOffice for Word document support
echo "Building Docker image..."

# Create a custom Dockerfile with LibreOffice
cat > Dockerfile.custom << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including LibreOffice
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with specific NumPy and Pandas versions for compatibility
RUN pip install numpy==1.23.5
RUN pip install pandas==2.0.0
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p templates output uploads static logs

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Use the custom Dockerfile
docker build -t student-report-system -f Dockerfile.custom .

# Run Docker container with proper volume mounts
echo "Starting container..."
docker run -d \
  --name $CONTAINER_NAME \
  -p 8000:8000 \
  -e FORM_RECOGNIZER_ENDPOINT=${FORM_RECOGNIZER_ENDPOINT} \
  -e FORM_RECOGNIZER_KEY=${FORM_RECOGNIZER_KEY} \
  -e OPENAI_ENDPOINT=${OPENAI_ENDPOINT} \
  -e OPENAI_KEY=${OPENAI_KEY} \
  -e OPENAI_DEPLOYMENT=${OPENAI_DEPLOYMENT} \
  -v $(pwd)/templates:/app/templates \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/static:/app/static \
  student-report-system

# Check if container started successfully
if [ $? -eq 0 ]; then
    echo "✅ Student Report Synthesis System is now running at http://localhost:8000"
    echo "Access the web interface by opening this URL in your browser"
    
    # Wait a moment and check if the application is responding
    echo "⏳ Checking application status..."
    sleep 5
    
    if curl -s http://localhost:8000/health >/dev/null; then
        echo "✅ Application is responding correctly!"
        echo "✅ The system now supports both PDF and Word (.docx, .doc) templates!"
        echo "✅ All reports will be generated in PDF format."
    else
        echo "⚠️ Application may not be running correctly. Check the logs with:"
        echo "docker logs $CONTAINER_NAME"
    fi
else
    echo "❌ Failed to start container. Check Docker logs for more information."
    exit 1
fi

# Display logs for debugging
echo ""
echo "🔍 Container logs (last 10 lines):"
docker logs $CONTAINER_NAME --tail 10
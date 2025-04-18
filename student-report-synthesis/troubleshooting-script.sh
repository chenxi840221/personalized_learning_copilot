#!/bin/bash

# Set environment variables (replace with your actual Azure service credentials)
export FORM_RECOGNIZER_ENDPOINT="https://australiaeast.api.cognitive.microsoft.com/"
export FORM_RECOGNIZER_KEY="2ece0e0981a949eba7ff8159f16e96de"
export OPENAI_ENDPOINT="https://australiaeast.api.cognitive.microsoft.com/"
export OPENAI_KEY="2ece0e0981a949eba7ff8159f16e96de"
export OPENAI_DEPLOYMENT="gpt-4o"

# Container name
CONTAINER_NAME="student-report-system"

# Function to check container status
check_container_status() {
    # Check if container is running
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo "✅ Container is running."
        
        # Get container logs
        echo "🔍 Container logs:"
        docker logs $CONTAINER_NAME --tail 20
        
        # Get container port mappings
        echo "🔌 Port mappings:"
        docker port $CONTAINER_NAME
        
        # Check if application is listening on port 8000 inside container
        echo "🔄 Checking if application is listening on port 8000 inside container..."
        docker exec $CONTAINER_NAME netstat -tuln 2>/dev/null | grep 8000 || echo "⚠️ No process is listening on port 8000 inside the container."
    else
        echo "❌ Container is not running! Checking for errors..."
        if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
            echo "🔍 Container exit logs:"
            docker logs $CONTAINER_NAME --tail 50
        else
            echo "❓ Container doesn't exist."
        fi
    fi
}

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

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t student-report-system .

# Run Docker container
echo "🚀 Starting container..."
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
  student-report-system

# Sleep for a moment to allow container to start up
echo "⏳ Waiting for container to start up..."
sleep 5

# Check container status
check_container_status

# Provide debugging guidance
echo ""
echo "🔧 Troubleshooting steps if you can't access the application at http://localhost:8000:"
echo "1. Make sure no other application is using port 8000"
echo "   Check with: netstat -tuln | grep 8000"
echo ""
echo "2. Try accessing with curl to verify the API is responding:"
echo "   curl http://localhost:8000"
echo ""
echo "3. Check if your firewall is blocking the connection"
echo ""
echo "4. If the container is running but the app is not responding, you can:"
echo "   - View detailed logs: docker logs $CONTAINER_NAME"
echo "   - Access the container shell: docker exec -it $CONTAINER_NAME bash"
echo ""
echo "5. To restart the container:"
echo "   docker restart $CONTAINER_NAME"
echo ""
echo "6. For more information on container status:"
echo "   docker inspect $CONTAINER_NAME"
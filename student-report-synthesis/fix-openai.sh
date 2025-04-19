#!/bin/bash
# fix-openai.sh - Install compatible OpenAI library version

echo "Installing OpenAI version 0.28.1..."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Determine pip command
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
else
    PIP_CMD="pip"
fi

# Uninstall current OpenAI
echo "Removing current OpenAI installation..."
$PIP_CMD uninstall -y openai

# Install compatible OpenAI version
echo "Installing OpenAI version 0.28.1..."
$PIP_CMD install openai==0.28.1

echo "OpenAI fix completed! Run your application again."
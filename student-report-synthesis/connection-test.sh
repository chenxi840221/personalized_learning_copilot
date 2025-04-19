#!/bin/bash
# connection-test.sh - Test Azure service connections

echo "===== Testing Azure Service Connections ====="

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Check environment variables
echo "Checking environment variables..."
if [ -z "$FORM_RECOGNIZER_ENDPOINT" ]; then
    echo "❌ FORM_RECOGNIZER_ENDPOINT is not set"
else
    echo "✓ FORM_RECOGNIZER_ENDPOINT is set to: $FORM_RECOGNIZER_ENDPOINT"
fi

if [ -z "$FORM_RECOGNIZER_KEY" ]; then
    echo "❌ FORM_RECOGNIZER_KEY is not set"
else
    echo "✓ FORM_RECOGNIZER_KEY is set (value hidden)"
fi

if [ -z "$OPENAI_ENDPOINT" ]; then
    echo "❌ OPENAI_ENDPOINT is not set"
else
    echo "✓ OPENAI_ENDPOINT is set to: $OPENAI_ENDPOINT"
fi

if [ -z "$OPENAI_KEY" ]; then
    echo "❌ OPENAI_KEY is not set"
else
    echo "✓ OPENAI_KEY is set (value hidden)"
fi

if [ -z "$OPENAI_DEPLOYMENT" ]; then
    echo "❌ OPENAI_DEPLOYMENT is not set"
else
    echo "✓ OPENAI_DEPLOYMENT is set to: $OPENAI_DEPLOYMENT"
fi

# Create test Python script
echo "Creating test script..."
cat > test_azure_connections.py << 'EOF'
import os
import sys
import openai
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

def test_document_intelligence():
    print("\n=== Testing Document Intelligence Connection ===")
    endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT")
    key = os.environ.get("FORM_RECOGNIZER_KEY")
    
    if not endpoint or not key:
        print("❌ Missing Document Intelligence credentials")
        return False
    
    try:
        client = DocumentIntelligenceClient(
            endpoint=endpoint, 
            credential=AzureKeyCredential(key)
        )
        print("✓ Successfully created Document Intelligence client")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Document Intelligence: {str(e)}")
        return False

def test_openai():
    print("\n=== Testing OpenAI Connection ===")
    endpoint = os.environ.get("OPENAI_ENDPOINT")
    key = os.environ.get("OPENAI_KEY")
    deployment = os.environ.get("OPENAI_DEPLOYMENT")
    
    if not endpoint or not key or not deployment:
        print("❌ Missing OpenAI credentials")
        return False
    
    try:
        # Configure OpenAI
        openai.api_type = "azure"
        openai.api_base = endpoint
        openai.api_version = "2023-05-15"
        openai.api_key = key
        
        # Test with a simple request
        response = openai.ChatCompletion.create(
            deployment_id=deployment,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            print("✓ Successfully connected to OpenAI")
            print(f"✓ Response: {response.choices[0].message.content}")
            return True
        else:
            print("❌ OpenAI connection test failed: unexpected response format")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to OpenAI: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Testing Azure service connections...")
    doc_success = test_document_intelligence()
    openai_success = test_openai()
    
    print("\n=== Summary ===")
    print(f"Document Intelligence: {'✓ Connected' if doc_success else '❌ Failed'}")
    print(f"OpenAI: {'✓ Connected' if openai_success else '❌ Failed'}")
    
    if not doc_success or not openai_success:
        print("\n=== Suggestions ===")
        if not doc_success:
            print("- Check FORM_RECOGNIZER_ENDPOINT and FORM_RECOGNIZER_KEY")
            print("- Verify your Azure subscription is active")
            print("- Confirm the Document Intelligence service is provisioned")
        
        if not openai_success:
            print("- Check OPENAI_ENDPOINT, OPENAI_KEY, and OPENAI_DEPLOYMENT")
            print("- Verify your Azure OpenAI service is provisioned")
            print("- Confirm the specified deployment exists")
            print("- Make sure you're using openai==0.28.1 library version")
EOF

# Run the test script
echo -e "\nRunning connection tests..."
python test_azure_connections.py
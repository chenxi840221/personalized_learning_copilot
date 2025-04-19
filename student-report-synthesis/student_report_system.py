#!/bin/bash
# test-azure-openai.sh - Script to test Azure OpenAI available deployments

echo "===== Testing Azure OpenAI Deployments ====="

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
    echo "Environment variables loaded."
fi

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Create test Python script
cat > test_azure_openai_deployments.py << 'EOF'
import os
import sys
from openai import AzureOpenAI

def test_azure_openai_deployments():
    print("\n=== Testing Azure OpenAI Deployments ===")
    endpoint = os.environ.get("OPENAI_ENDPOINT")
    key = os.environ.get("OPENAI_KEY")
    
    if not endpoint or not key:
        print("❌ Missing Azure OpenAI credentials")
        print(f"  OPENAI_ENDPOINT: {'Set' if endpoint else 'Not set'}")
        print(f"  OPENAI_KEY: {'Set' if key else 'Not set'}")
        return False
    
    try:
        client = AzureOpenAI(
            api_key=key,
            api_version="2023-05-15",
            azure_endpoint=endpoint
        )
        
        print(f"✓ Successfully created Azure OpenAI client")
        print(f"✓ Endpoint: {endpoint}")
        
        # List available deployments
        try:
            deployments = client.models.list()
            
            print("\n=== Available Azure OpenAI Deployments ===")
            if len(deployments.data) == 0:
                print("No deployments found")
            else:
                for deployment in deployments.data:
                    print(f"- {deployment.id}")
                
                print("\nℹ️ Use one of these deployment names for your OPENAI_DEPLOYMENT environment variable.")
                print("   For example: export OPENAI_DEPLOYMENT=\"gpt-35-turbo\"")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to list deployments: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect to Azure OpenAI: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Testing Azure OpenAI deployments...")
    success = test_azure_openai_deployments()
    
    print("\n=== Summary ===")
    print(f"Azure OpenAI: {'✓ Connected' if success else '❌ Failed'}")
    
    if not success:
        print("\n=== Suggestions ===")
        print("- Check OPENAI_ENDPOINT and OPENAI_KEY environment variables")
        print("- Make sure your Azure OpenAI service is properly provisioned")
        print("- Verify that you have at least one deployment created")
EOF

# Run the test script
echo -e "\nRunning Azure OpenAI deployments test..."
python test_azure_openai_deployments.py

# Clean up
echo -e "\nCleaning up..."
rm test_azure_openai_deployments.py

echo -e "\nTest complete."
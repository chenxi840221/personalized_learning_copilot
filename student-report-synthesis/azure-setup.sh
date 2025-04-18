#!/bin/bash
# azure-setup.sh - Script to set up Azure resources for Student Report Synthesis System

# Exit on error
set -e

# Default parameters (override with environment variables or command line arguments)
RESOURCE_GROUP="${RESOURCE_GROUP:-student-report-rg}"
LOCATION="${LOCATION:-australiaeast}"
FORM_RECOGNIZER_NAME="${FORM_RECOGNIZER_NAME:-student-report-fr}"
OPENAI_NAME="${OPENAI_NAME:-student-report-openai}"
OPENAI_DEPLOYMENT="${OPENAI_DEPLOYMENT:-gpt-4o}"
EMBED_DEPLOYMENT="text-embedding-ada-002"

# Parse command line arguments
while [ $# -gt 0 ]; do
  case "$1" in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    --form-recognizer-name)
      FORM_RECOGNIZER_NAME="$2"
      shift 2
      ;;
    --openai-name)
      OPENAI_NAME="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --resource-group NAME     Resource group name (default: student-report-rg)"
      echo "  --location LOCATION       Azure region (default: australiaeast)"
      echo "  --form-recognizer-name NAME  Form Recognizer resource name (default: student-report-fr)"
      echo "  --openai-name NAME        OpenAI resource name (default: student-report-openai)"
      echo "  --help                    Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Setting up Azure resources with the following parameters:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Form Recognizer Name: $FORM_RECOGNIZER_NAME"
echo "  OpenAI Name: $OPENAI_NAME"
echo "  OpenAI Deployment: $OPENAI_DEPLOYMENT"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
  echo "Azure CLI not found. Please install it first."
  echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
  exit 1
fi

# Check if user is logged in to Azure
echo "Checking Azure login status..."
if ! az account show &> /dev/null; then
  echo "You are not logged in to Azure. Please run 'az login' first."
  exit 1
fi

# Create resource group
echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Create Form Recognizer / Document Intelligence resource
echo "Creating Form Recognizer / Document Intelligence resource..."
az cognitiveservices account create \
  --name "$FORM_RECOGNIZER_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --kind "FormRecognizer" \
  --sku "S0" \
  --yes

# Get Form Recognizer keys and endpoint
echo "Retrieving Form Recognizer keys..."
FORM_RECOGNIZER_KEY=$(az cognitiveservices account keys list \
  --name "$FORM_RECOGNIZER_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "key1" \
  --output tsv)

FORM_RECOGNIZER_ENDPOINT=$(az cognitiveservices account show \
  --name "$FORM_RECOGNIZER_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.endpoint" \
  --output tsv)

# Create OpenAI resource
echo "Creating Azure OpenAI resource..."
az cognitiveservices account create \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --kind "OpenAI" \
  --sku "S0" \
  --yes

# Get OpenAI keys and endpoint
echo "Retrieving OpenAI keys..."
OPENAI_KEY=$(az cognitiveservices account keys list \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "key1" \
  --output tsv)

OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.endpoint" \
  --output tsv)

# Deploy OpenAI model (note: this may require additional permissions or manual setup)
echo "NOTE: You may need to deploy the $OPENAI_DEPLOYMENT model manually in Azure Portal"
echo "Visit the Azure OpenAI Studio to deploy GPT-4o and text-embedding-ada-002 models"

# Create .env file with the credentials
echo "Creating .env file with credentials..."
cat > .env << EOF
FORM_RECOGNIZER_ENDPOINT=$FORM_RECOGNIZER_ENDPOINT
FORM_RECOGNIZER_KEY=$FORM_RECOGNIZER_KEY
OPENAI_ENDPOINT=$OPENAI_ENDPOINT
OPENAI_KEY=$OPENAI_KEY
OPENAI_DEPLOYMENT=$OPENAI_DEPLOYMENT
EOF

# Display credentials to screen
echo ""
echo "🔑 Azure Credentials (for immediate use):"
echo "--------------------------------------------------"
echo "FORM_RECOGNIZER_ENDPOINT=$FORM_RECOGNIZER_ENDPOINT"
echo "FORM_RECOGNIZER_KEY=$FORM_RECOGNIZER_KEY"
echo "OPENAI_ENDPOINT=$OPENAI_ENDPOINT"
echo "OPENAI_KEY=$OPENAI_KEY"
echo "OPENAI_DEPLOYMENT=$OPENAI_DEPLOYMENT"
echo "--------------------------------------------------"

# Final guidance
echo ""
echo "✅ Setup complete! Azure resources have been created."
echo "✅ Credentials have been saved to .env file."
echo ""
echo "Next steps:"
echo "1. Deploy the OpenAI models in Azure OpenAI Studio if needed"
echo "2. Run './deployment.sh' to deploy the Student Report Synthesis System"

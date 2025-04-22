import logging
from typing import List, Dict, Any, Optional
import openai
import os
import json
from config.settings import Settings
# Initialize settings
settings = Settings()
# Initialize logger
logger = logging.getLogger(__name__)
class OpenAIAdapter:
    """
    Adapter class for Azure OpenAI API using the standard OpenAI package.
    This provides compatibility with systems that don't support the azure-ai-openai package.
    """
    def __init__(self):
        """Initialize the OpenAI client with Azure configuration."""
        # Configure OpenAI with Azure details
        openai.api_type = settings.OPENAI_API_TYPE
        openai.api_version = settings.OPENAI_API_VERSION
        openai.api_base = settings.OPENAI_API_BASE
        openai.api_key = settings.OPENAI_API_KEY
    async def create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a chat completion using Azure OpenAI.
        Args:
            model: The deployment name in Azure OpenAI
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum number of tokens to generate
            response_format: Optional format specification (e.g., {"type": "json_object"})
        Returns:
            Dictionary containing the completion response
        """
        try:
            # Set up the parameters
            params = {
                "engine": model,  # Use the deployment name
                "messages": messages,
                "temperature": temperature
            }
            # Add max_tokens if specified
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            # Add response_format if specified and API version supports it
            if response_format is not None and "2023-09-01" <= settings.OPENAI_API_VERSION:
                params["response_format"] = response_format
            # Make the API call
            response = await openai.ChatCompletion.acreate(**params)
            return response
        except Exception as e:
            logger.error(f"Error creating chat completion: {e}")
            raise
    async def create_embedding(
        self,
        model: str,
        text: str
    ) -> List[float]:
        """
        Create an embedding using Azure OpenAI.
        Args:
            model: The deployment name in Azure OpenAI
            text: Text to embed
        Returns:
            List of embedding values
        """
        try:
            # Make the API call
            response = await openai.Embedding.acreate(
                engine=model,  # Use the deployment name 
                input=text
            )
            # Extract the embedding
            embedding = response["data"][0]["embedding"]
            return embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise
# Singleton instance
openai_adapter = None
async def get_openai_adapter():
    """Get or create the OpenAI adapter singleton."""
    global openai_adapter
    if openai_adapter is None:
        openai_adapter = OpenAIAdapter()
    return openai_adapter
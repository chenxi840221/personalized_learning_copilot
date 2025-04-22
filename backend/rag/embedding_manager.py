# Embedding Manager (embedding_manager.py)
# ./personalized_learning_copilot/backend/rag/embedding_manager.py
import logging
from typing import List, Dict, Any, Optional
import asyncio
import numpy as np
import os
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from config.settings import Settings
# Initialize settings
settings = Settings()
# Initialize logger
logger = logging.getLogger(__name__)
class EmbeddingManager:
    """
    Manages the generation and storage of embeddings for content.
    """
    def __init__(self):
        """Initialize the embedding manager with configured embedding model."""
        self.model_name = "text-embedding-ada-002"
        # Initialize embeddings client
        self.embeddings = OpenAIEmbeddings(
            model=self.model_name,
            azure_deployment=settings.EMBEDDING_DEPLOYMENT_NAME,
            openai_api_type=settings.OPENAI_API_TYPE,
            openai_api_version=settings.OPENAI_API_VERSION,
            openai_api_base=settings.OPENAI_API_BASE,
            openai_api_key=settings.OPENAI_API_KEY
        )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for a text string.
        Args:
            text: Text to embed
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Generate embedding
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        Args:
            texts: List of texts to embed
        Returns:
            List of embedding vectors
        """
        try:
            # Generate embeddings
            embeddings = await self.embeddings.aembed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents.
        Args:
            documents: List of documents to embed
        Returns:
            Documents with embeddings added to metadata
        """
        try:
            # Extract text from documents
            texts = [doc.page_content for doc in documents]
            # Generate embeddings
            embeddings = await self.generate_embeddings_batch(texts)
            # Add embeddings to document metadata
            for i, doc in enumerate(documents):
                doc.metadata["embedding"] = embeddings[i]
            return documents
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        Returns:
            Cosine similarity score (0-1)
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
# Singleton instance
embedding_manager = None
async def get_embedding_manager():
    """Get or create the embedding manager singleton."""
    global embedding_manager
    if embedding_manager is None:
        embedding_manager = EmbeddingManager()
    return embedding_manager

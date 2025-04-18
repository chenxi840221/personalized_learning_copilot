# Document Processor (document_processor.py)
# ./personalized_learning_copilot/backend/rag/document_processor.py

import logging
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from bson import ObjectId

from models.content import Content, ContentWithEmbedding
from utils.db_manager import get_db
from rag.embedding_manager import EmbeddingManager
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Process documents for RAG pipeline, including content extraction,
    text splitting, and preparation for embedding.
    """
    
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""]
        )
    
    async def process_content(self, content: Content) -> ContentWithEmbedding:
        """
        Process a content item for the RAG pipeline.
        
        Args:
            content: Content item to process
            
        Returns:
            Content item with embedding
        """
        try:
            # Prepare text for embedding
            text = self._prepare_text_for_embedding(content)
            
            # Generate embedding
            embedding = await self.embedding_manager.generate_embedding(text)
            
            # Create content with embedding
            content_with_embedding = ContentWithEmbedding(
                **content.dict(),
                embedding=embedding,
                embedding_model=self.embedding_manager.model_name
            )
            
            return content_with_embedding
        
        except Exception as e:
            logger.error(f"Error processing content {content.id}: {e}")
            raise
    
    def _prepare_text_for_embedding(self, content: Content) -> str:
        """
        Prepare content text for embedding by combining relevant fields.
        
        Args:
            content: Content item
            
        Returns:
            Processed text ready for embedding
        """
        # Combine relevant fields
        text_parts = [
            f"Title: {content.title}",
            f"Subject: {content.subject}",
            f"Topics: {', '.join(content.topics)}",
            f"Description: {content.description}",
            f"Content Type: {content.content_type}",
            f"Difficulty Level: {content.difficulty_level}",
            f"Grade Level: {'-'.join(map(str, content.grade_level))}"
        ]
        
        # Add keywords if available
        if content.keywords:
            text_parts.append(f"Keywords: {', '.join(content.keywords)}")
        
        return "\n".join(text_parts)
    
    async def process_html_content(self, html_content: str, url: str, metadata: Dict[str, Any]) -> List[Document]:
        """
        Process HTML content into documents for the RAG pipeline.
        
        Args:
            html_content: HTML content to process
            url: Source URL
            metadata: Additional metadata
            
        Returns:
            List of processed documents
        """
        # Extract text from HTML
        text = self._extract_text_from_html(html_content)
        
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Create documents
        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": url,
                    "chunk_id": i,
                    **metadata
                }
            )
            documents.append(doc)
        
        return documents
    
    def _extract_text_from_html(self, html: str) -> str:
        """
        Extract clean text from HTML content.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        return text

# Singleton instance
document_processor = None

async def get_document_processor():
    """Get or create the document processor singleton."""
    global document_processor
    if document_processor is None:
        document_processor = DocumentProcessor()
    return document_processor

async def process_all_content():
    """Process all content items in the database that don't have embeddings."""
    processor = await get_document_processor()
    db = await get_db()
    
    # Get all content without embeddings
    contents = await db.contents.find({}).to_list(length=1000)
    
    processed_count = 0
    error_count = 0
    
    for content_dict in contents:
        try:
            # Convert to Content model
            content = Content(**content_dict)
            
            # Check if embedding already exists
            existing = await db.contents_with_embeddings.find_one({"_id": content.id})
            if existing:
                continue
                
            # Process content
            content_with_embedding = await processor.process_content(content)
            
            # Save to database
            await db.contents_with_embeddings.insert_one(content_with_embedding.dict())
            
            processed_count += 1
            logger.info(f"Processed content: {content.title}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing content: {e}")
    
    logger.info(f"Completed processing. Processed: {processed_count}, Errors: {error_count}")
    return processed_count, error_count
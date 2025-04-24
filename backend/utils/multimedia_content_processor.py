import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import os
import uuid
from datetime import datetime
from urllib.parse import urlparse

# Azure imports
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

# For vector store
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import Vector

from models.content import Content, ContentType
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class MultimediaContentProcessor:
    """
    Process various types of educational content (text, audio, video) 
    for indexing, embedding, and retrieval.
    """
    def __init__(self):
        """Initialize the multimedia content processor."""
        # Will be initialized as needed
        self.openai_client = None
        self.speech_config = None
        self.document_client = None
        self.vision_client = None
        self.search_client = None
    
    async def initialize(self):
        """Initialize all required clients for content processing."""
        # Import here to avoid circular imports
        from rag.openai_adapter import get_openai_adapter
        
        # Initialize OpenAI client for embeddings
        self.openai_client = await get_openai_adapter()
        
        # Initialize Azure Form Recognizer client for document processing
        if settings.FORM_RECOGNIZER_ENDPOINT and settings.FORM_RECOGNIZER_KEY:
            self.document_client = DocumentAnalysisClient(
                endpoint=settings.FORM_RECOGNIZER_ENDPOINT,
                credential=AzureKeyCredential(settings.FORM_RECOGNIZER_KEY)
            )
        
        # Initialize Speech Services for audio processing
        if hasattr(settings, 'SPEECH_KEY') and hasattr(settings, 'SPEECH_REGION'):
            self.speech_config = SpeechConfig(
                subscription=settings.SPEECH_KEY,
                region=settings.SPEECH_REGION
            )
        
        # Initialize Computer Vision for video processing
        if hasattr(settings, 'COMPUTER_VISION_ENDPOINT') and hasattr(settings, 'COMPUTER_VISION_KEY'):
            self.vision_client = ComputerVisionClient(
                endpoint=settings.COMPUTER_VISION_ENDPOINT,
                credentials=CognitiveServicesCredentials(settings.COMPUTER_VISION_KEY)
            )
        
        # Initialize Azure AI Search client
        if settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY:
            self.search_client = SearchClient(
                endpoint=settings.AZURE_SEARCH_ENDPOINT,
                index_name=settings.AZURE_SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
            )
    
    async def close(self):
        """Close all clients."""
        if self.search_client:
            await self.search_client.close()
    
    async def process_content(self, content_url: str, content_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process content based on its type (text, audio, video) and prepare it for indexing.
        
        Args:
            content_url: URL of the content
            content_info: Basic metadata about the content
            
        Returns:
            Processed content information with extracted text and embedding
        """
        if not self.openai_client:
            await self.initialize()
        
        content_type = content_info.get('content_type', '')
        
        # Initialize the content item with basic info
        content_item = {
            "id": str(uuid.uuid4()),
            "title": content_info.get('title', 'Untitled Content'),
            "description": content_info.get('description', ''),
            "content_type": content_type,
            "subject": content_info.get('subject', ''),
            "topics": content_info.get('topics', []),
            "url": content_url,
            "source": content_info.get('source', 'ABC Education'),
            "difficulty_level": content_info.get('difficulty_level', 'intermediate'),
            "grade_level": content_info.get('grade_level', []),
            "duration_minutes": content_info.get('duration_minutes', 0),
            "keywords": content_info.get('keywords', []),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        
        # Extract content based on type
        extracted_text = ""
        
        if 'text' in content_type or 'article' in content_type:
            # Process text content
            extracted_text = await self._process_text_content(content_url, content_info)
            content_item["metadata"]["content_text"] = extracted_text
            
        elif 'audio' in content_type or 'podcast' in content_type:
            # Process audio content
            audio_text, duration = await self._process_audio_content(content_url)
            content_item["metadata"]["transcription"] = audio_text
            extracted_text = audio_text
            
            # Update duration if available
            if duration and duration > 0:
                content_item["duration_minutes"] = duration
                
        elif 'video' in content_type:
            # Process video content
            video_text, duration, thumbnail_url = await self._process_video_content(content_url)
            content_item["metadata"]["transcription"] = video_text
            content_item["metadata"]["thumbnail_url"] = thumbnail_url
            extracted_text = video_text
            
            # Update duration if available
            if duration and duration > 0:
                content_item["duration_minutes"] = duration
        
        # Generate embedding for search
        if extracted_text:
            text_for_embedding = self._prepare_text_for_embedding(content_item, extracted_text)
            embedding = await self._generate_embedding(text_for_embedding)
            content_item["embedding"] = embedding
        
        return content_item
    
    async def _process_text_content(self, content_url: str, content_info: Dict[str, Any]) -> str:
        """
        Process text content from a URL.
        
        Args:
            content_url: URL of the text content
            content_info: Basic metadata about the content
            
        Returns:
            Extracted text content
        """
        # If HTML content is already provided, use it
        if 'content_html' in content_info:
            from bs4 import BeautifulSoup
            
            # Extract text from HTML
            soup = BeautifulSoup(content_info['content_html'], 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            return text
        
        # Otherwise, try to extract text using Form Recognizer for structured documents
        if self.document_client and (content_url.endswith('.pdf') or 
                                    content_url.endswith('.docx') or 
                                    content_url.endswith('.pptx')):
            try:
                # Use Form Recognizer to extract text
                poller = await self.document_client.begin_analyze_document_from_url(
                    "prebuilt-document", content_url
                )
                result = await poller.result()
                
                # Extract text content
                return result.content
            except Exception as e:
                logger.error(f"Error extracting text with Form Recognizer: {e}")
        
        # For web pages, we need to fetch and parse them
        if content_url.startswith(('http://', 'https://')):
            try:
                import aiohttp
                from bs4 import BeautifulSoup
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(content_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Parse HTML
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.extract()
                                
                            # Get text
                            text = soup.get_text(separator='\n', strip=True)
                            return text
            except Exception as e:
                logger.error(f"Error fetching and parsing web content: {e}")
        
        # Return empty string if nothing could be extracted
        return ""
    
    async def _process_audio_content(self, audio_url: str) -> Tuple[str, Optional[int]]:
        """
        Process audio content using Azure Speech Services.
        
        Args:
            audio_url: URL of the audio content
            
        Returns:
            Tuple of (transcription, duration_minutes)
        """
        if not self.speech_config:
            logger.warning("Speech Services not configured. Cannot process audio content.")
            return "", None
        
        try:
            # Download the audio file
            import aiohttp
            import tempfile
            
            audio_file = None
            duration_minutes = None
            
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status == 200:
                        # Create a temporary file
                        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(audio_url))
                        audio_file_path = audio_file.name
                        audio_file.close()
                        
                        # Save the audio content
                        with open(audio_file_path, 'wb') as f:
                            f.write(await response.read())
                        
                        # Get audio duration using a helper library
                        try:
                            from pydub import AudioSegment
                            audio = AudioSegment.from_file(audio_file_path)
                            duration_seconds = len(audio) / 1000
                            duration_minutes = int(duration_seconds / 60) + (1 if duration_seconds % 60 >= 30 else 0)
                        except ImportError:
                            logger.warning("Pydub not available. Cannot determine audio duration.")
                        
                        # Configure speech recognition
                        audio_config = AudioConfig(filename=audio_file_path)
                        speech_recognizer = SpeechRecognizer(
                            speech_config=self.speech_config, 
                            audio_config=audio_config
                        )
                        
                        # Start continuous recognition
                        transcription = []
                        
                        # This is a simplified approach - in a real system you'd want to use the continuous 
                        # recognition API with proper event handling
                        done = False
                        
                        def stop_cb(evt):
                            nonlocal done
                            done = True
                        
                        def recognized_cb(evt):
                            if evt.result.reason == ResultReason.RecognizedSpeech:
                                transcription.append(evt.result.text)
                        
                        # Connect callbacks
                        speech_recognizer.recognized.connect(recognized_cb)
                        speech_recognizer.session_stopped.connect(stop_cb)
                        speech_recognizer.canceled.connect(stop_cb)
                        
                        # Start continuous speech recognition
                        speech_recognizer.start_continuous_recognition()
                        
                        # Wait for completion (would be event-based in a real system)
                        while not done:
                            await asyncio.sleep(0.5)
                        
                        speech_recognizer.stop_continuous_recognition()
                        
                        # Clean up the temporary file
                        os.unlink(audio_file_path)
                        
                        return " ".join(transcription), duration_minutes
            
            return "", None
                    
        except Exception as e:
            logger.error(f"Error processing audio content: {e}")
            return "", None
    
    async def _process_video_content(self, video_url: str) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Process video content using Azure Video Indexer or Computer Vision.
        
        Args:
            video_url: URL of the video content
            
        Returns:
            Tuple of (transcription, duration_minutes, thumbnail_url)
        """
        if not self.vision_client:
            logger.warning("Computer Vision not configured. Cannot process video content.")
            return "", None, None
        
        try:
            # For video analysis, we would typically use Azure Video Indexer
            # However, that requires a separate service setup
            # For this example, we'll use Computer Vision to analyze frames
            # and simulated transcription
            
            # In a real implementation, you would:
            # 1. Upload the video to Azure Video Indexer
            # 2. Wait for indexing to complete
            # 3. Retrieve insights (transcription, topics, etc.)
            
            # Simulated response for now
            return (
                "This is a simulated transcription for the video content. "
                "In a real implementation, Azure Video Indexer would provide "
                "full transcription, speaker identification, and visual content analysis.",
                10,  # Simulated 10-minute duration
                None  # No thumbnail URL
            )
                    
        except Exception as e:
            logger.error(f"Error processing video content: {e}")
            return "", None, None
    
    def _prepare_text_for_embedding(self, content_item: Dict[str, Any], extracted_text: str) -> str:
        """
        Prepare text for embedding by combining metadata with extracted content.
        
        Args:
            content_item: Content item with metadata
            extracted_text: Extracted text from the content
            
        Returns:
            Text prepared for embedding
        """
        # Combine relevant fields
        text_parts = [
            f"Title: {content_item['title']}",
            f"Subject: {content_item['subject']}",
        ]
        
        # Add description if available
        if content_item['description']:
            text_parts.append(f"Description: {content_item['description']}")
            
        # Add topics if available
        if content_item['topics']:
            text_parts.append(f"Topics: {', '.join(content_item['topics'])}")
            
        # Add keywords if available
        if content_item['keywords']:
            text_parts.append(f"Keywords: {', '.join(content_item['keywords'])}")
            
        # Add extracted text (truncated if too long)
        if extracted_text:
            # Limit to around 2000 characters for embedding
            if len(extracted_text) > 2000:
                text_parts.append(f"Content: {extracted_text[:2000]}...")
            else:
                text_parts.append(f"Content: {extracted_text}")
        
        return "\n".join(text_parts)
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Azure OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        try:
            embedding = await self.openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fall back to empty embedding vector with appropriate dimensions
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    async def save_to_search(self, content_items: List[Dict[str, Any]]) -> bool:
        """
        Save processed content items to Azure AI Search.
        
        Args:
            content_items: List of processed content items
            
        Returns:
            Success status
        """
        if not self.search_client:
            logger.error("Search client not initialized")
            return False
            
        if not content_items:
            logger.warning("No content items to save")
            return False
        
        try:
            # Process in batches to avoid overwhelming the service
            batch_size = 20
            success_count = 0
            error_count = 0
            
            for i in range(0, len(content_items), batch_size):
                batch = content_items[i:i+batch_size]
                
                try:
                    # Upload batch to Azure Search
                    result = await self.search_client.upload_documents(documents=batch)
                    
                    # Count successes and failures
                    for idx, item in enumerate(result):
                        if item.succeeded:
                            success_count += 1
                        else:
                            error_count += 1
                            logger.error(f"Failed to upload document: {item.key}, {item.error_message}")
                    
                    # Wait a bit between batches
                    await asyncio.sleep(1)
                    
                except Exception as batch_error:
                    logger.error(f"Error uploading batch: {batch_error}")
                    error_count += len(batch)
            
            logger.info(f"Upload complete: {success_count} succeeded, {error_count} failed")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error saving to search: {e}")
            return False
    
    def _get_file_extension(self, url: str) -> str:
        """Get file extension from URL."""
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Get file extension
        extension = os.path.splitext(path)[1].lower()
        
        # Default to .mp3 for audio if no extension
        if not extension:
            return '.mp3'
            
        return extension

# Singleton instance
content_processor = None

async def get_content_processor():
    """Get or create content processor singleton."""
    global content_processor
    if content_processor is None:
        content_processor = MultimediaContentProcessor()
        await content_processor.initialize()
    return content_processor

async def process_and_index_content(content_url: str, content_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process content and index it in the search service.
    
    Args:
        content_url: URL of the content
        content_info: Basic metadata about the content
        
    Returns:
        Processed content item
    """
    processor = await get_content_processor()
    
    # Process the content
    content_item = await processor.process_content(content_url, content_info)
    
    # Save to search index
    if content_item:
        # Create a batch of one item
        success = await processor.save_to_search([content_item])
        if success:
            logger.info(f"Successfully indexed content: {content_item['title']}")
        else:
            logger.warning(f"Failed to index content: {content_item['title']}")
    
    return content_item
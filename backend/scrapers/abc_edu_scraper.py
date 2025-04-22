import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urljoin
from datetime import datetime
import json
import uuid
import openai

# Azure imports
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ABCEducationScraper:
    def __init__(self):
        self.base_url = "https://www.abc.net.au/education/subjects-and-topics"
        self.subjects = ["english", "mathematics", "science", "history", "geography", "arts", 
                         "health-and-physical-education", "languages", "economics", 
                         "civics-and-citizenship", "media-literacy"]
        self.session = None
        
        # Azure AI Search client
        self.search_client = None
        
        # Configure OpenAI with Azure settings
        openai.api_type = "azure"
        openai.api_version = settings.AZURE_OPENAI_API_VERSION
        openai.api_base = settings.get_openai_endpoint()
        openai.api_key = settings.get_openai_key()
        
        # Azure Computer Vision client using Cognitive Services
        self.computer_vision_client = ComputerVisionClient(
            endpoint=settings.COMPUTER_VISION_ENDPOINT,
            credentials=CognitiveServicesCredentials(settings.COMPUTER_VISION_KEY)
        )
        
        # Azure Form Recognizer client using Cognitive Services
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=settings.FORM_RECOGNIZER_ENDPOINT,
            credential=AzureKeyCredential(settings.FORM_RECOGNIZER_KEY)
        )
        
        # Azure Text Analytics client using Cognitive Services
        self.text_analytics_client = TextAnalyticsClient(
            endpoint=settings.TEXT_ANALYTICS_ENDPOINT, 
            credential=AzureKeyCredential(settings.TEXT_ANALYTICS_KEY)
        )
    
    async def initialize(self):
        """Initialize the HTTP session and search client."""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        
        # Initialize Azure AI Search client
        self.search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.CONTENT_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
    
    async def close(self):
        """Close the HTTP session and search client."""
        if self.session:
            await self.session.close()
        
        if self.search_client:
            await self.search_client.close()
    
    async def scrape_all_subjects(self):
        """Scrape all subjects."""
        if not self.session:
            await self.initialize()
        
        all_content = []
        for subject in self.subjects:
            subject_content = await self.scrape_subject(subject)
            all_content.extend(subject_content)
            logger.info(f"Scraped {len(subject_content)} items from {subject}")
        
        return all_content
    
    async def scrape_subject(self, subject: str) -> List[Dict[str, Any]]:
        """Scrape content for a specific subject."""
        subject_url = f"{self.base_url}/{subject}"
        
        try:
            # Fetch the subject page
            async with self.session.get(subject_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch {subject_url}: {response.status}")
                    return []
                
            # Upload batch to Azure Search
            try:
                upload_result = await self.search_client.upload_documents(documents=processed_batch)
                success_count = sum(1 for result in upload_result if result.succeeded)
                logger.info(f"Uploaded batch: {success_count}/{len(processed_batch)} succeeded")
            except Exception as e:
                logger.error(f"Error uploading batch to Azure Search: {e}")
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Find all content items
                content_items = []
                
                # Find topic sections
                topic_sections = soup.find_all("div", class_=re.compile("topic-section"))
                
                for topic_section in topic_sections:
                    topic_title = topic_section.find("h2")
                    topic = topic_title.text.strip() if topic_title else "General"
                    
                    # Find content cards
                    content_cards = topic_section.find_all("div", class_=re.compile("card"))
                    
                    for card in content_cards:
                        try:
                            # Extract content information
                            title_elem = card.find("h3") or card.find("h2")
                            title = title_elem.text.strip() if title_elem else "Untitled"
                            
                            link_elem = card.find("a")
                            if not link_elem or not link_elem.get("href"):
                                continue
                                
                            content_url = urljoin(self.base_url, link_elem["href"])
                            
                            description_elem = card.find("p")
                            description = description_elem.text.strip() if description_elem else ""
                            
                            # Determine content type
                            content_type = self._determine_content_type(card, content_url)
                            
                            # Determine difficulty level and grade level
                            difficulty, grade_levels = self._determine_difficulty_and_grade(title, description, subject)
                            
                            # Generate unique ID for the content
                            content_id = str(uuid.uuid4())
                            
                            # Create content item
                            content_item = {
                                "id": content_id,
                                "title": title,
                                "description": description,
                                "content_type": content_type.value,
                                "subject": subject.capitalize(),
                                "topics": [topic],
                                "url": content_url,
                                "source": "ABC Education",
                                "difficulty_level": difficulty.value,
                                "grade_level": grade_levels,
                                "duration_minutes": self._estimate_duration(content_type),
                                "keywords": self._extract_keywords(title, description),
                                "created_at": datetime.utcnow().isoformat(),
                                "updated_at": datetime.utcnow().isoformat()
                            }
                            
                            content_items.append(content_item)
                        except Exception as e:
                            logger.error(f"Error processing content card: {e}")
                
                return content_items
                
        except Exception as e:
            logger.error(f"Error scraping {subject}: {e}")
            return []
    
    def _determine_content_type(self, card, url: str) -> ContentType:
        """Determine the content type based on the card and URL."""
        # Check for specific indicators in the card or URL
        card_text = card.text.lower()
        url_lower = url.lower()
        
        if "video" in card_text or "video" in url_lower:
            return ContentType.VIDEO
        elif "quiz" in card_text or "quiz" in url_lower:
            return ContentType.QUIZ
        elif "worksheet" in card_text or "worksheet" in url_lower:
            return ContentType.WORKSHEET
        elif "interactive" in card_text or "interactive" in url_lower:
            return ContentType.INTERACTIVE
        elif "lesson" in card_text or "lesson" in url_lower:
            return ContentType.LESSON
        elif "activity" in card_text or "activity" in url_lower:
            return ContentType.ACTIVITY
        else:
            return ContentType.ARTICLE
    
    def _determine_difficulty_and_grade(self, title: str, description: str, subject: str):
        """Determine the difficulty level and grade levels based on content."""
        text = f"{title} {description}".lower()
        
        # Extract grade/year level patterns
        grade_patterns = [
            r"year (\d+)",
            r"grade (\d+)",
            r"years? (\d+)-(\d+)",
            r"grades? (\d+)-(\d+)"
        ]
        
        extracted_grades = []
        
        # Check for specific grade mentions
        for pattern in grade_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):  # Range of years
                    start, end = int(match[0]), int(match[1])
                    extracted_grades.extend(range(start, end + 1))
                elif isinstance(match, str) and match.isdigit():
                    extracted_grades.append(int(match))
        
        # Check for Foundation/Prep/Kindergarten
        if any(term in text for term in ["foundation", "prep", "kindergarten"]):
            extracted_grades.append(0)  # Representing Foundation level
            
        # Remove duplicates and sort
        extracted_grades = sorted(list(set(extracted_grades)))
        
        # Check for explicit difficulty indicators
        if any(word in text for word in ["basic", "beginner", "easy", "introduction", "start"]):
            difficulty = DifficultyLevel.BEGINNER
            grade_levels = extracted_grades or [3, 4, 5]
        elif any(word in text for word in ["advanced", "complex", "difficult", "challenging"]):
            difficulty = DifficultyLevel.ADVANCED
            grade_levels = extracted_grades or [8, 9, 10]
        else:
            difficulty = DifficultyLevel.INTERMEDIATE
            grade_levels = extracted_grades or [6, 7, 8]
        
        # Adjust based on subject
        if subject == "mathematics":
            # Math often has specific grade indicators
            if "algebra" in text or "equation" in text:
                difficulty = DifficultyLevel.INTERMEDIATE
                grade_levels = extracted_grades or [7, 8, 9]
            elif "calculus" in text or "trigonometry" in text:
                difficulty = DifficultyLevel.ADVANCED
                grade_levels = extracted_grades or [9, 10, 11]
        
        return difficulty, grade_levels
    
    def _estimate_duration(self, content_type: ContentType) -> int:
        """Estimate the duration in minutes based on content type."""
        if content_type == ContentType.VIDEO:
            return 20
        elif content_type == ContentType.INTERACTIVE:
            return 30
        elif content_type == ContentType.QUIZ:
            return 15
        elif content_type == ContentType.WORKSHEET:
            return 45
        elif content_type == ContentType.LESSON:
            return 60
        elif content_type == ContentType.ACTIVITY:
            return 40
        else:  # Article
            return 25
    
    def _extract_keywords(self, title: str, description: str) -> List[str]:
        """Extract keywords from title and description."""
        text = f"{title} {description}".lower()
        
        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "about", "as"}
        
        # Extract words and filter out short words and stop words
        words = re.findall(r'\b\w+\b', text)
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Remove duplicates and return top keywords
        unique_keywords = list(set(keywords))
        return unique_keywords[:10]  # Return up to 10 keywords
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI."""
        try:
            # Call OpenAI API
            response = await openai.Embedding.acreate(
                engine=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                input=text
            )
            
            return response["data"][0]["embedding"]
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fall back to empty vector
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    async def extract_video_content(self, url: str) -> Dict[str, Any]:
        """
        Extract video content using Azure Computer Vision.
        For video content, extracts frames, captions, and transcripts.
        """
        try:
            # For this example, we'll use a placeholder video analysis approach
            # In a real implementation, you would:
            # 1. Download the video or get a streamable URL
            # 2. Submit the video for analysis with Azure Video Indexer or Computer Vision
            # 3. Extract frames, transcript, and other metadata
            
            # Simulated video analysis result
            video_analysis = {
                "transcript": "",
                "keyframes": [],
                "topics": [],
                "entities": []
            }
            
            # Try to extract video ID or direct video URL
            video_id_match = re.search(r'(watch\?v=|/videos/)([^&]+)', url)
            if video_id_match:
                video_id = video_id_match.group(2)
                
                # In a real implementation, submit the video for analysis to Azure Video Indexer
                # and get a detailed transcript, extracted frames, etc.
                
                # For now, we'll use Computer Vision to analyze a thumbnail image
                # This is a simplified approach - real video analysis is more complex
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                
                # Analyze the thumbnail image
                image_analysis = self.computer_vision_client.analyze_image(
                    thumbnail_url,
                    visual_features=[
                        VisualFeatureTypes.tags,
                        VisualFeatureTypes.categories,
                        VisualFeatureTypes.description,
                        VisualFeatureTypes.objects
                    ]
                )
                
                # Extract tags and descriptions
                if hasattr(image_analysis, 'tags'):
                    video_analysis["topics"] = [tag.name for tag in image_analysis.tags]
                
                if hasattr(image_analysis, 'description') and hasattr(image_analysis.description, 'captions'):
                    captions = [caption.text for caption in image_analysis.description.captions]
                    video_analysis["transcript"] = " ".join(captions)
            
            return video_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing video content: {e}")
            return {
                "transcript": "",
                "keyframes": [],
                "topics": [],
                "entities": []
            }
    
    async def extract_document_content(self, url: str) -> Dict[str, Any]:
        """
        Extract document content using Azure Form Recognizer.
        For document content (like worksheets), extracts text and structure.
        """
        try:
            # In a real implementation, download the document and analyze it
            # For this example, we'll use text analytics on the page content instead
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {"text": "", "topics": [], "entities": []}
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Extract main content
                main_content = soup.find("main") or soup.find("article") or soup
                if not main_content:
                    return {"text": "", "topics": [], "entities": []}
                
                # Get text content
                paragraphs = main_content.find_all("p")
                text_content = " ".join([p.text.strip() for p in paragraphs])
                
                # Use Text Analytics to extract key phrases and entities
                if text_content:
                    try:
                        # Get key phrases
                        key_phrase_response = self.text_analytics_client.extract_key_phrases([text_content])
                        key_phrases = []
                        if not key_phrase_response[0].is_error:
                            key_phrases = key_phrase_response[0].key_phrases
                        
                        # Get entities
                        entity_response = self.text_analytics_client.recognize_entities([text_content])
                        entities = []
                        if not entity_response[0].is_error:
                            entities = [entity.text for entity in entity_response[0].entities]
                        
                        return {
                            "text": text_content,
                            "topics": key_phrases,
                            "entities": entities
                        }
                    except Exception as e:
                        logger.error(f"Error in text analytics: {e}")
                
                return {"text": text_content, "topics": [], "entities": []}
                
        except Exception as e:
            logger.error(f"Error extracting document content: {e}")
            return {"text": "", "topics": [], "entities": []}
    
    async def process_content_details(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process content details based on content type."""
        content_type = content_item["content_type"]
        url = content_item["url"]
        
        # Additional content details
        additional_content = {}
        
        # Process based on content type
        if content_type == ContentType.VIDEO.value:
            video_content = await self.extract_video_content(url)
            additional_content["transcript"] = video_content["transcript"]
            additional_content["additional_topics"] = video_content["topics"]
            
            # Add transcript to the description for better embedding context
            if video_content["transcript"]:
                content_item["full_description"] = f"{content_item['description']} {video_content['transcript']}"
            
        elif content_type in [ContentType.ARTICLE.value, ContentType.LESSON.value]:
            document_content = await self.extract_document_content(url)
            additional_content["full_text"] = document_content["text"]
            additional_content["additional_topics"] = document_content["topics"]
            additional_content["entities"] = document_content["entities"]
            
            # Add full text to the description for better embedding context
            if document_content["text"]:
                content_item["full_description"] = document_content["text"]
        
        # Add any additional topics as keywords
        if "additional_topics" in additional_content and additional_content["additional_topics"]:
            content_item["keywords"].extend(additional_content["additional_topics"])
            content_item["keywords"] = list(set(content_item["keywords"]))[:20]  # Limit to 20 unique keywords
        
        # Add the additional content
        content_item["additional_content"] = additional_content
        
        return content_item
    
    async def save_to_azure_search(self, content_items: List[Dict[str, Any]]):
        """Save content items to Azure AI Search."""
        if not self.search_client:
            await self.initialize()
        
        logger.info(f"Uploading {len(content_items)} items to Azure AI Search...")
        
        # Process in batches to avoid overwhelming the service
        batch_size = 50
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i:i+batch_size]
            
            # Process each item to generate embeddings and additional details
            processed_batch = []
            for item in batch:
                try:
                    # Process content details
                    processed_item = await self.process_content_details(item)
                    
                    # Create text for embedding
                    text_for_embedding = f"{processed_item['title']} {processed_item['description']} "
                    if "full_description" in processed_item:
                        text_for_embedding += processed_item["full_description"]
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(text_for_embedding)
                    processed_item["embedding"] = embedding
                    
                    processed_batch.append(processed_item)
                except Exception as e:
                    logger.error(f"Error processing item {item['title']}: {e}")
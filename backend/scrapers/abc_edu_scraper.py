import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json
import uuid
import random
import sys
import os

# Add the parent directory to the path so we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Azure imports
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
# Import the compatible Vector class
from utils.vector_compat import Vector

from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ABCEducationScraper:
    def __init__(self):
        self.base_url = "https://www.abc.net.au/education"
        self.subjects_url = "https://www.abc.net.au/education/subjects-and-topics"
        # Mapping of subject slugs to their proper names
        self.subject_mapping = {
            "english": "English",
            "mathematics": "Mathematics",
            "science": "Science",
            "history": "History",
            "geography": "Geography",
            "arts": "Arts",
            "health-and-physical-education": "Health and Physical Education",
            "languages": "Languages",
            "economics": "Economics",
            "civics-and-citizenship": "Civics and Citizenship",
            "media-literacy": "Media Literacy"
        }
        self.session = None
        self.search_client = None
        
        # Common stop words for keyword extraction
        self.stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
                          "with", "by", "about", "as", "of", "from", "this", "that", "these", 
                          "those", "is", "are", "was", "were", "be", "been", "being", "have", 
                          "has", "had", "do", "does", "did", "will", "would", "should", "can", 
                          "could", "may", "might", "must", "shall"}
    
    async def initialize(self):
        """Initialize the HTTP session and search client."""
        # Use a more browser-like user agent to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        self.session = aiohttp.ClientSession(headers=headers)
        
        # Initialize Azure AI Search client if credentials are available
        if settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY:
            try:
                self.search_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                )
                logger.info(f"Initialized Azure AI Search client with index: {settings.AZURE_SEARCH_INDEX_NAME}")
            except Exception as e:
                logger.error(f"Failed to initialize Azure AI Search client: {e}")
    
    async def close(self):
        """Close the HTTP session and search client."""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.search_client:
            await self.search_client.close()
            self.search_client = None
    
    async def discover_subjects(self) -> List[Dict[str, str]]:
        """Dynamically discover available subjects from the subjects page."""
        if not self.session:
            await self.initialize()
            
        try:
            logger.info(f"Fetching subjects from {self.subjects_url}")
            async with self.session.get(self.subjects_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch subjects page: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for subject links - this pattern might need adjustment
                # based on the actual page structure
                subject_links = []
                
                # Method 1: Try to find links in a navigation menu
                nav_elements = soup.select("nav ul li a, .navigation a, .menu a, .subjects a")
                for link in nav_elements:
                    href = link.get("href", "")
                    if "/education/subjects-and-topics/" in href or "/education/subject/" in href:
                        subject_slug = href.split("/")[-1]
                        subject_name = link.text.strip()
                        if subject_slug and subject_name:
                            subject_links.append({"slug": subject_slug, "name": subject_name})
                
                # Method 2: Look for subject cards or tiles
                subject_cards = soup.select(".subject-card, .card, .tile, .subject-tile")
                for card in subject_cards:
                    link = card.find("a")
                    if link and link.get("href"):
                        href = link.get("href")
                        if "/education/subjects-and-topics/" in href or "/education/subject/" in href:
                            subject_slug = href.split("/")[-1]
                            title_elem = card.find("h2") or card.find("h3") or card.find("h4")
                            subject_name = title_elem.text.strip() if title_elem else link.text.strip()
                            if subject_slug and subject_name:
                                subject_links.append({"slug": subject_slug, "name": subject_name})
                
                # If we didn't find any subjects with the above methods,
                # fall back to the predefined mapping
                if not subject_links:
                    logger.warning("No subjects found on page, using predefined list")
                    for slug, name in self.subject_mapping.items():
                        subject_links.append({"slug": slug, "name": name})
                
                logger.info(f"Discovered {len(subject_links)} subjects")
                return subject_links
                
        except Exception as e:
            logger.error(f"Error discovering subjects: {e}")
            # Fall back to using our predefined mapping
            fallback_subjects = [
                {"slug": slug, "name": name} 
                for slug, name in self.subject_mapping.items()
            ]
            logger.info(f"Using {len(fallback_subjects)} subjects from predefined mapping")
            return fallback_subjects
    
    async def scrape_all_subjects(self, limit=None):
        """Scrape all subjects, optionally limiting to a specific number."""
        if not self.session:
            await self.initialize()
        
        # Discover available subjects
        subjects = await self.discover_subjects()
        
        # Limit the number of subjects if requested
        if limit:
            subjects = subjects[:limit]
        
        all_content = []
        for subject_info in subjects:
            subject_slug = subject_info["slug"]
            subject_name = subject_info["name"]
            try:
                logger.info(f"Scraping subject: {subject_name} ({subject_slug})")
                subject_content = await self.scrape_subject(subject_slug, subject_name)
                all_content.extend(subject_content)
                logger.info(f"Scraped {len(subject_content)} items from {subject_name}")
                
                # Add a delay between subjects to avoid overloading the server
                await asyncio.sleep(random.uniform(1.5, 3.0))
            except Exception as e:
                logger.error(f"Error scraping subject {subject_name} ({subject_slug}): {e}")
        
        return all_content
    
    async def scrape_subject(self, subject_slug: str, subject_name: str) -> List[Dict[str, Any]]:
        """Scrape content for a specific subject."""
        subject_url = f"{self.subjects_url}/{subject_slug}"
        logger.info(f"Accessing subject URL: {subject_url}")
        
        try:
            # Fetch the subject page
            async with self.session.get(subject_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch {subject_url}: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for API endpoints in the page that might load content dynamically
                # This is a common pattern for websites that load content via JavaScript
                api_endpoints = self._extract_api_endpoints(html)
                
                # If we found API endpoints, try to use them to get content
                if api_endpoints:
                    return await self._fetch_from_api(api_endpoints, subject_name)
                
                # Otherwise, fall back to scraping the HTML directly
                return await self._parse_subject_page(soup, subject_url, subject_name)
                
        except Exception as e:
            logger.error(f"Error scraping {subject_name} ({subject_slug}): {e}")
            return []
    
    def _extract_api_endpoints(self, html: str) -> List[str]:
        """Extract potential API endpoints from the page HTML."""
        # Look for API endpoints in script tags or network requests
        api_endpoints = []
        
        # Look for API URLs in script tags
        api_patterns = [
            r'"apiUrl"\s*:\s*"([^"]+)"',
            r'"endpoint"\s*:\s*"([^"]+)"',
            r'"dataSource"\s*:\s*"([^"]+)"',
            r'fetch\([\'"]([^\'"]+)[\'"]',
            r'axios\.get\([\'"]([^\'"]+)[\'"]',
            r'"/api/([^"]+)"',
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                # Only consider URLs that might be API endpoints
                if ("api" in match.lower() or "data" in match.lower() or 
                    "content" in match.lower() or "json" in match.lower()):
                    # Ensure it's a full URL
                    if not match.startswith(('http://', 'https://')):
                        if match.startswith('/'):
                            # Convert relative URL to absolute
                            domain = urlparse(self.base_url).netloc
                            scheme = urlparse(self.base_url).scheme
                            match = f"{scheme}://{domain}{match}"
                        else:
                            # Skip if we can't form a proper URL
                            continue
                    
                    api_endpoints.append(match)
        
        # Remove duplicates and return
        return list(set(api_endpoints))
    
    async def _fetch_from_api(self, api_endpoints: List[str], subject_name: str) -> List[Dict[str, Any]]:
        """Fetch content items from API endpoints."""
        all_content = []
        
        for endpoint in api_endpoints:
            logger.info(f"Fetching from API endpoint: {endpoint}")
            try:
                # Add a slight delay to avoid rate limiting
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                async with self.session.get(endpoint) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch from API {endpoint}: {response.status}")
                        continue
                    
                    # Try to parse as JSON
                    try:
                        data = await response.json()
                        
                        # Extract content items from the JSON response
                        # This will need to be adapted based on the actual API response structure
                        content_items = self._parse_api_response(data, subject_name)
                        all_content.extend(content_items)
                        logger.info(f"Extracted {len(content_items)} items from API")
                    except Exception as e:
                        logger.warning(f"Failed to parse API response as JSON: {e}")
                        
                        # If not JSON, try to parse as HTML
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        content_items = await self._parse_subject_page(soup, endpoint, subject_name)
                        all_content.extend(content_items)
                        
            except Exception as e:
                logger.error(f"Error fetching from API {endpoint}: {e}")
        
        return all_content
    
    def _parse_api_response(self, data: Any, subject_name: str) -> List[Dict[str, Any]]:
        """Parse content items from an API response."""
        content_items = []
        
        # Determine if the response is a list or an object with a list property
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Look for likely container properties
            for key in ['items', 'results', 'content', 'data', 'resources', 'articles']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                # If we couldn't find a list, check if the object itself represents a content item
                if self._looks_like_content_item(data):
                    items = [data]
                else:
                    # Otherwise just return empty list
                    return []
        else:
            return []
        
        # Process each item in the list
        for item in items:
            try:
                if not isinstance(item, dict):
                    continue
                
                # Extract required properties with reasonable defaults
                content_id = str(item.get('id', uuid.uuid4()))
                title = self._extract_text_property(item, ['title', 'name', 'heading'])
                
                # Skip items without a title
                if not title:
                    continue
                
                # Extract other properties
                description = self._extract_text_property(
                    item, ['description', 'summary', 'excerpt', 'abstract', 'content']
                )
                
                # Get URL - might be directly in the item or in a links object
                url = self._extract_url_property(item)
                if not url:
                    # Skip items without a URL
                    continue
                
                # Normalize URL to absolute
                if not url.startswith(('http://', 'https://')):
                    url = urljoin(self.base_url, url)
                
                # Content type - try to determine from properties or fall back to generic
                content_type = self._determine_content_type_from_api(item, url)
                
                # Extract or infer topics
                topics = self._extract_topics_from_api(item)
                
                # Determine difficulty level and grade levels
                difficulty, grade_levels = self._determine_difficulty_and_grade(title, description, subject_name)
                
                # Create content item
                content_item = {
                    "id": content_id,
                    "title": title,
                    "description": description or f"A {content_type.value} resource for {subject_name}",
                    "content_type": content_type.value,
                    "subject": subject_name,
                    "topics": topics,
                    "url": url,
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
                logger.error(f"Error processing API item: {e}")
        
        return content_items
    
    def _extract_text_property(self, item: Dict, possible_keys: List[str]) -> str:
        """Extract text from various possible keys in an item."""
        for key in possible_keys:
            if key in item and item[key]:
                value = item[key]
                if isinstance(value, str):
                    return value.strip()
                elif isinstance(value, dict) and 'text' in value:
                    return value['text'].strip()
        return ""
    
    def _extract_url_property(self, item: Dict) -> str:
        """Extract URL from various possible locations in an item."""
        # Direct URL field
        for key in ['url', 'link', 'href', 'path']:
            if key in item and item[key]:
                return item[key]
        
        # URL in links object
        if 'links' in item and isinstance(item['links'], dict):
            for key in ['self', 'item', 'resource', 'page', 'content']:
                if key in item['links']:
                    link_obj = item['links'][key]
                    if isinstance(link_obj, str):
                        return link_obj
                    elif isinstance(link_obj, dict) and 'href' in link_obj:
                        return link_obj['href']
        
        # URL in fields object
        if 'fields' in item and isinstance(item['fields'], dict):
            for key in ['url', 'link', 'href', 'path']:
                if key in item['fields'] and item['fields'][key]:
                    return item['fields'][key]
        
        return ""
    
    def _looks_like_content_item(self, item: Any) -> bool:
        """Check if an object likely represents a content item."""
        if not isinstance(item, dict):
            return False
        
        # Check for common content item properties
        required_properties = ['title', 'url', 'id']
        return any(prop in item for prop in required_properties)
    
    def _determine_content_type_from_api(self, item: Dict, url: str) -> ContentType:
        """Determine content type from API item properties."""
        # Try to get type directly from the item
        item_type = ""
        for key in ['type', 'content_type', 'resource_type', 'format']:
            if key in item and item[key]:
                item_type = str(item[key]).lower()
                break
        
        # Map item type to ContentType enum
        if item_type:
            if any(video_term in item_type for video_term in ['video', 'mov', 'mp4']):
                return ContentType.VIDEO
            elif any(quiz_term in item_type for quiz_term in ['quiz', 'test', 'assessment']):
                return ContentType.QUIZ
            elif any(worksheet_term in item_type for worksheet_term in ['worksheet', 'exercise', 'sheet']):
                return ContentType.WORKSHEET
            elif any(interactive_term in item_type for interactive_term in ['interactive', 'game', 'simulation']):
                return ContentType.INTERACTIVE
            elif any(lesson_term in item_type for lesson_term in ['lesson', 'class', 'course']):
                return ContentType.LESSON
            elif any(activity_term in item_type for activity_term in ['activity', 'project', 'lab']):
                return ContentType.ACTIVITY
        
        # Fall back to URL-based detection if type not found in item
        url_lower = url.lower()
        if any(video_term in url_lower for video_term in ['/video/', 'watch', '.mp4']):
            return ContentType.VIDEO
        elif any(quiz_term in url_lower for quiz_term in ['/quiz/', 'test', 'assessment']):
            return ContentType.QUIZ
        elif any(worksheet_term in url_lower for worksheet_term in ['/worksheet/', 'exercise']):
            return ContentType.WORKSHEET
        elif any(interactive_term in url_lower for interactive_term in ['/interactive/', 'game', 'simulation']):
            return ContentType.INTERACTIVE
        elif any(lesson_term in url_lower for lesson_term in ['/lesson/', 'class', 'course']):
            return ContentType.LESSON
        elif any(activity_term in url_lower for activity_term in ['/activity/', 'project', 'lab']):
            return ContentType.ACTIVITY
        
        # Default to article if we can't determine the type
        return ContentType.ARTICLE
    
    def _extract_topics_from_api(self, item: Dict) -> List[str]:
        """Extract topics from API item."""
        topics = []
        
        # Look for topics in various properties
        topic_keys = ['topics', 'categories', 'tags', 'subjects', 'themes']
        for key in topic_keys:
            if key in item and item[key]:
                value = item[key]
                if isinstance(value, list):
                    # If it's a list of strings
                    if all(isinstance(v, str) for v in value):
                        topics.extend(value)
                    # If it's a list of objects with name/title properties
                    elif all(isinstance(v, dict) for v in value):
                        for v in value:
                            for name_key in ['name', 'title', 'value', 'label']:
                                if name_key in v and v[name_key]:
                                    topics.append(v[name_key])
                                    break
                elif isinstance(value, str):
                    # Split comma-separated string
                    topics.extend([t.strip() for t in value.split(',')])
        
        # Ensure topics are unique and non-empty
        return [t for t in list(set(topics)) if t]
    
    async def _parse_subject_page(self, soup: BeautifulSoup, url: str, subject_name: str) -> List[Dict[str, Any]]:
        """Parse content items from a subject page."""
        content_items = []
        
        # Try multiple selectors to find content cards
        selectors = [
            ".card", ".content-card", ".resource-card", ".item", ".tile", 
            "article", ".article", ".resource", ".content-item", 
            "[data-testid='card']", "[data-testid='contentCard']"
        ]
        
        found_cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                logger.info(f"Found {len(cards)} content cards with selector: {selector}")
                found_cards.extend(cards)
        
        # Deduplicate cards (in case our selectors overlapped)
        seen_cards = set()
        unique_cards = []
        for card in found_cards:
            # Create a simple hash of the card's text and structure
            card_text = card.get_text().strip()
            card_hash = hash(card_text)
            if card_hash not in seen_cards:
                seen_cards.add(card_hash)
                unique_cards.append(card)
        
        logger.info(f"Processing {len(unique_cards)} unique content cards")
        
        # Process each content card
        for card in unique_cards:
            try:
                # Extract title
                title_elem = card.select_one("h1, h2, h3, h4, .title, .heading")
                if not title_elem:
                    continue
                title = title_elem.get_text().strip()
                
                # Extract link
                link_elem = card.select_one("a")
                if not link_elem or not link_elem.get("href"):
                    continue
                
                content_url = link_elem["href"]
                # Convert relative URL to absolute
                if not content_url.startswith(('http://', 'https://')):
                    content_url = urljoin(url, content_url)
                
                # Extract description
                description_elem = card.select_one("p, .description, .summary, .excerpt")
                description = description_elem.get_text().strip() if description_elem else ""
                
                # Extract content type
                content_type = self._determine_content_type(card, content_url)
                
                # Extract topics
                topic_elems = card.select(".topic, .category, .tag, .subject")
                topics = [elem.get_text().strip() for elem in topic_elems if elem.get_text().strip()]
                
                # If no topics found, try to extract from the URL or card classes
                if not topics:
                    # Extract from URL path
                    url_path = urlparse(content_url).path
                    path_parts = [p for p in url_path.split('/') if p]
                    
                    # Check if any path part looks like a topic
                    for part in path_parts:
                        # Skip very short parts or parts that are likely not topics
                        if len(part) < 3 or part in ['www', 'edu', 'com', 'au', 'org']:
                            continue
                        # Convert hyphens to spaces and capitalize
                        topic = part.replace('-', ' ').capitalize()
                        topics.append(topic)
                
                # If still no topics, use the subject name
                if not topics:
                    topics = [subject_name]
                
                # Determine difficulty and grade levels
                difficulty, grade_levels = self._determine_difficulty_and_grade(title, description, subject_name)
                
                # Generate a unique ID
                content_id = str(uuid.uuid4())
                
                # Create content item
                content_item = {
                    "id": content_id,
                    "title": title,
                    "description": description or f"A {content_type.value} resource for {subject_name}",
                    "content_type": content_type.value,
                    "subject": subject_name,
                    "topics": topics,
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
    
    def _determine_content_type(self, card, url: str) -> ContentType:
        """Determine the content type based on the card and URL."""
        # Check for type indicators in the card's classes
        card_classes = card.get('class', [])
        card_classes = ' '.join(card_classes).lower() if isinstance(card_classes, list) else card_classes.lower()
        
        # Check for specific class indicators
        if any(video_class in card_classes for video_class in ['video', 'media-video']):
            return ContentType.VIDEO
        elif any(quiz_class in card_classes for quiz_class in ['quiz', 'assessment']):
            return ContentType.QUIZ
        elif any(worksheet_class in card_classes for worksheet_class in ['worksheet', 'exercise']):
            return ContentType.WORKSHEET
        elif any(interactive_class in card_classes for interactive_class in ['interactive', 'game']):
            return ContentType.INTERACTIVE
        elif any(lesson_class in card_classes for lesson_class in ['lesson', 'class']):
            return ContentType.LESSON
        elif any(activity_class in card_classes for activity_class in ['activity', 'project']):
            return ContentType.ACTIVITY
        
        # Check for indicators in the card's text
        card_text = card.get_text().lower()
        if any(video_text in card_text for video_text in ['watch video', 'video:', 'view video']):
            return ContentType.VIDEO
        elif any(quiz_text in card_text for quiz_text in ['take quiz', 'quiz:', 'test yourself']):
            return ContentType.QUIZ
        elif any(worksheet_text in card_text for worksheet_text in ['worksheet:', 'download worksheet']):
            return ContentType.WORKSHEET
        elif any(interactive_text in card_text for interactive_text in ['interactive:', 'play', 'explore']):
            return ContentType.INTERACTIVE
        elif any(lesson_text in card_text for lesson_text in ['lesson:', 'class:', 'teacher notes']):
            return ContentType.LESSON
        elif any(activity_text in card_text for activity_text in ['activity:', 'project:', 'try this']):
            return ContentType.ACTIVITY
        
        # Check for type indicators in the URL
        url_lower = url.lower()
        if any(video_term in url_lower for video_term in ['/video/', '/watch/', '.mp4']):
            return ContentType.VIDEO
        elif any(quiz_term in url_lower for quiz_term in ['/quiz/', '/test/', '/assessment/']):
            return ContentType.QUIZ
        elif any(worksheet_term in url_lower for worksheet_term in ['/worksheet/', '/exercise/']):
            return ContentType.WORKSHEET
        elif any(interactive_term in url_lower for interactive_term in ['/interactive/', '/game/', '/simulation/']):
            return ContentType.INTERACTIVE
        elif any(lesson_term in url_lower for lesson_term in ['/lesson/', '/class/', '/course/']):
            return ContentType.LESSON
        elif any(activity_term in url_lower for activity_term in ['/activity/', '/project/', '/lab/']):
            return ContentType.ACTIVITY
        
        # Default to article if we can't determine type
        return ContentType.ARTICLE
    
    def _determine_difficulty_and_grade(self, title: str, description: str, subject: str):
        """Determine the difficulty level and grade levels based on content."""
        text = f"{title} {description}".lower()
        
        # Extract grade/year level patterns
        grade_patterns = [
            r'year (\d+)',
            r'grade (\d+)',
            r'years? (\d+)[- ](\d+)',
            r'grades? (\d+)[- ](\d+)',
            r'years? (\d+),? (\d+)(?:,? and (\d+))?',
            r'grades? (\d+),? (\d+)(?:,? and (\d+))?'
        ]
        
        extracted_grades = []
        
        # Check for specific grade mentions
        for pattern in grade_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    # Process each number in the tuple
                    for grade_str in match:
                        if grade_str and grade_str.strip() and grade_str.isdigit():
                            grade = int(grade_str)
                            if 1 <= grade <= 12:  # Valid grade range
                                extracted_grades.append(grade)
                    
                    # If it's a range (just two numbers), fill in the range
                    if len(match) == 2 and all(m.isdigit() for m in match):
                        start, end = int(match[0]), int(match[1])
                        if 1 <= start <= end <= 12 and end - start <= 6:  # Reasonable range
                            extracted_grades.extend(range(start, end + 1))
                elif isinstance(match, str) and match.isdigit():
                    grade = int(match)
                    if 1 <= grade <= 12:
                        extracted_grades.append(grade)
        
        # Check for Australian year levels like "Foundation" or "Prep"
        foundation_terms = ['foundation', 'prep', 'kindergarten', 'reception', 'kinder', 'kindy']
        if any(term in text for term in foundation_terms):
            extracted_grades.append(0)  # Represent Foundation/Prep as grade 0
            
        # Remove duplicates and sort
        extracted_grades = sorted(list(set(extracted_grades)))
        
        # Check for explicit difficulty indicators
        if any(word in text for word in ['basic', 'beginner', 'easy', 'introduction', 'start', 'simple']):
            difficulty = DifficultyLevel.BEGINNER
            default_grades = [3, 4, 5]
        elif any(word in text for word in ['advanced', 'complex', 'difficult', 'challenging', 'hard']):
            difficulty = DifficultyLevel.ADVANCED
            default_grades = [9, 10, 11, 12]
        else:
            difficulty = DifficultyLevel.INTERMEDIATE
            default_grades = [6, 7, 8]
        
        # Subject-specific adjustments
        subject_lower = subject.lower()
        if 'math' in subject_lower:
            # Math-specific topic indicators
            if any(term in text for term in ['calculus', 'trigonometry', 'quadratic', 'polynomial']):
                difficulty = DifficultyLevel.ADVANCED
                if not extracted_grades:
                    extracted_grades = [10, 11, 12]
            elif any(term in text for term in ['algebra', 'geometry', 'equation', 'function']):
                difficulty = DifficultyLevel.INTERMEDIATE
                if not extracted_grades:
                    extracted_grades = [7, 8, 9]
            elif any(term in text for term in ['fraction', 'decimal', 'arithmetic', 'counting']):
                difficulty = DifficultyLevel.BEGINNER
                if not extracted_grades:
                    extracted_grades = [3, 4, 5, 6]
        elif 'science' in subject_lower:
            # Science-specific topic indicators
            if any(term in text for term in ['quantum', 'nuclear', 'advanced chemistry', 'complex system']):
                difficulty = DifficultyLevel.ADVANCED
                if not extracted_grades:
                    extracted_grades = [10, 11, 12]
        
        # If we found specific grades, use those
        # Otherwise fall back to default grades for the difficulty level
        grade_levels = extracted_grades or default_grades
        
        return difficulty, grade_levels
    
    def _estimate_duration(self, content_type: ContentType) -> int:
        """Estimate the duration in minutes based on content type."""
        if content_type == ContentType.VIDEO:
            return random.randint(15, 25)  # Videos are typically 15-25 minutes
        elif content_type == ContentType.INTERACTIVE:
            return random.randint(25, 35)  # Interactives typically take 25-35 minutes
        elif content_type == ContentType.QUIZ:
            return random.randint(10, 20)  # Quizzes typically take 10-20 minutes
        elif content_type == ContentType.WORKSHEET:
            return random.randint(30, 50)  # Worksheets typically take 30-50 minutes
        elif content_type == ContentType.LESSON:
            return random.randint(45, 65)  # Lessons typically take 45-65 minutes
        elif content_type == ContentType.ACTIVITY:
            return random.randint(30, 55)  # Activities typically take 30-55 minutes
        else:  # Article
            return random.randint(20, 30)  # Articles typically take 20-30 minutes to read
    
    def _extract_keywords(self, title: str, description: str) -> List[str]:
        """Extract keywords from title and description."""
        if not title and not description:
            return []
            
        text = f"{title} {description}".lower()
        
        # Extract words and filter out short words and stop words
        words = re.findall(r'\b\w+\b', text)
        keywords = [word for word in words if len(word) > 3 and word not in self.stop_words]
        
        # Remove duplicates and return top keywords (up to 15)
        unique_keywords = sorted(list(set(keywords)), key=lambda x: text.count(x), reverse=True)
        return unique_keywords[:15]
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI."""
        try:
            import openai
            # Configure OpenAI with Azure settings
            openai.api_type = "azure"
            openai.api_version = settings.AZURE_OPENAI_API_VERSION
            openai.api_base = settings.get_openai_endpoint()
            openai.api_key = settings.get_openai_key()
            
            # Call OpenAI API to get embedding
            response = await openai.Embedding.acreate(
                engine=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                input=text
            )
            
            return response["data"][0]["embedding"]
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fall back to empty vector with appropriate dimensions
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    async def process_content_details(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process content details to prepare for saving to search index."""
        try:
            # Create text for embedding that combines all relevant fields
            text_for_embedding = f"{content_item['title']} {content_item['subject']} "
            
            if content_item['description']:
                text_for_embedding += f"{content_item['description']} "
            
            if content_item.get('topics'):
                text_for_embedding += f"Topics: {', '.join(content_item['topics'])} "
            
            if content_item.get('keywords'):
                text_for_embedding += f"Keywords: {', '.join(content_item['keywords'])} "
            
            # Generate embedding
            embedding = await self.generate_embedding(text_for_embedding)
            content_item["embedding"] = embedding
            
            return content_item
        except Exception as e:
            logger.error(f"Error processing content details: {e}")
            return content_item
    
    async def save_to_azure_search(self, content_items: List[Dict[str, Any]]):
        """Save content items to Azure AI Search."""
        if not self.search_client:
            await self.initialize()
            
        # Check again in case initialization failed
        if not self.search_client:
            logger.error("Cannot save to Azure AI Search: Search client not initialized")
            return
        
        # Skip if no items to save
        if not content_items:
            logger.warning("No content items to save to Azure AI Search")
            return
        
        logger.info(f"Preparing to upload {len(content_items)} items to Azure AI Search...")
        
        # Process content items to generate embeddings
        processed_items = []
        for item in content_items:
            try:
                processed_item = await self.process_content_details(item)
                processed_items.append(processed_item)
                # Add a slight delay to avoid overwhelming the embedding API
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Error processing item '{item.get('title', 'Unknown')}': {e}")
        
        # Skip if no processed items
        if not processed_items:
            logger.warning("No processed items to save to Azure AI Search")
            return
        
        logger.info(f"Uploading {len(processed_items)} processed items to Azure AI Search...")
        
        # Process in batches to avoid overwhelming the service
        batch_size = 20  # Smaller batch size to avoid timeouts
        success_count = 0
        error_count = 0
        
        for i in range(0, len(processed_items), batch_size):
            batch = processed_items[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(processed_items) + batch_size - 1) // batch_size
            
            logger.info(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            try:
                # Upload batch to Azure Search
                upload_result = await self.search_client.upload_documents(documents=batch)
                batch_success = sum(1 for result in upload_result if result.succeeded)
                batch_error = len(batch) - batch_success
                
                success_count += batch_success
                error_count += batch_error
                
                logger.info(f"Batch {batch_num} results: {batch_success} succeeded, {batch_error} failed")
                
                # Add a delay between batches to avoid rate limits
                await asyncio.sleep(1.5)
                
            except Exception as e:
                logger.error(f"Error uploading batch {batch_num} to Azure Search: {e}")
                error_count += len(batch)
        
        logger.info(f"Upload complete: {success_count} succeeded, {error_count} failed")

# Main function to run the scraper
async def run_scraper(subject_limit=None):
    """Run the scraper to collect content and save to Azure AI Search."""
    logger.info("Starting ABC Education scraper")
    scraper = ABCEducationScraper()
    
    try:
        await scraper.initialize()
        contents = await scraper.scrape_all_subjects(limit=subject_limit)
        logger.info(f"Scraped {len(contents)} content items")
        
        await scraper.save_to_azure_search(contents)
        logger.info("Content saved to Azure AI Search")
        
        return contents  # Return the scraped contents for testing purposes
    except Exception as e:
        logger.error(f"Error in main scraper routine: {e}")
        return []
    finally:
        await scraper.close()
        logger.info("Scraper resources closed")

# Entry point for running the script directly
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('abc_scraper.log')
        ]
    )
    
    # Set a specific subject limit for testing, use None for all subjects
    SUBJECT_LIMIT = 2  # Limit to first 2 subjects, set to None for all subjects
    
    # Run the scraper
    asyncio.run(run_scraper(subject_limit=SUBJECT_LIMIT))
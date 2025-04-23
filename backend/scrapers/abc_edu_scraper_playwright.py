import asyncio
import logging
import re
import json
import uuid
import random
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
from pathlib import Path

# Playwright imports
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Azure imports
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.aio import SearchClient
    # Import the compatible Vector class
    from utils.vector_compat import Vector
except ImportError:
    # Define fallback Vector class if not available
    class Vector:
        def __init__(self, value, k=None, fields=None, exhaustive=None):
            self.value = value
            self.k = k
            self.fields = fields
            self.exhaustive = exhaustive

# Try to import models, but provide fallbacks if not available
try:
    from models.content import Content, ContentType, DifficultyLevel
    from config.settings import Settings
    settings = Settings()
except ImportError:
    # Create fallback classes and settings
    class ContentType:
        ARTICLE = "article"
        VIDEO = "video"
        INTERACTIVE = "interactive"
        WORKSHEET = "worksheet"
        QUIZ = "quiz"
        LESSON = "lesson"
        ACTIVITY = "activity"
        
    class DifficultyLevel:
        BEGINNER = "beginner"
        INTERMEDIATE = "intermediate"
        ADVANCED = "advanced"
    
    class Settings:
        AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
        AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")
        AZURE_SEARCH_INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "educational-content")
        AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
        AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        
        def get_openai_endpoint(self):
            return os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            
        def get_openai_key(self):
            return os.environ.get("AZURE_OPENAI_KEY", "")
    
    settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('abc_scraper.log')
    ]
)

logger = logging.getLogger(__name__)

# List of target subjects to focus on
TARGET_SUBJECTS = [
    "Arts",
    "English",
    "Geography", 
    "History",
    "Maths",
    "Science",
    "Technologies"
]

class DeepContentScraper:
    def __init__(self):
        """Initialize the deep content scraper for ABC Education."""
        self.base_url = "https://www.abc.net.au/education"
        self.subjects_url = "https://www.abc.net.au/education/subjects-and-topics"
        
        # Will be initialized in setup()
        self.browser = None
        self.context = None
        self.page = None
        self.search_client = None
        
        # Debug directory for screenshots and HTML dumps
        self.debug_dir = Path("debug_output")
        self.debug_dir.mkdir(exist_ok=True)
        
        # Common stop words for keyword extraction
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "with", "by", "about", "as", "of", "from", "this", "that", "these", 
            "those", "is", "are", "was", "were", "be", "been", "being", "have", 
            "has", "had", "do", "does", "did", "will", "would", "should", "can", 
            "could", "may", "might", "must", "shall"
        }
    
    async def setup(self, headless=False):
        """Initialize Playwright browser and search client."""
        logger.info(f"Setting up Playwright browser (headless={headless}) and search client...")
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless, 
            slow_mo=50  # Add slight delay between actions for stability
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        # Enable debug features
        await self.context.tracing.start(screenshots=True, snapshots=True)
        
        self.page = await self.context.new_page()
        
        # Set default timeout (120 seconds)
        self.page.set_default_timeout(120000)
        
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
    
    async def teardown(self):
        """Close browser and other resources."""
        logger.info("Tearing down browser and search client...")
        
        if self.context:
            trace_path = self.debug_dir / "playwright_trace.zip"
            await self.context.tracing.stop(path=trace_path)
            logger.info(f"Saved Playwright trace to {trace_path}")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.search_client:
            await self.search_client.close()
    
    async def take_screenshot(self, name):
        """Take a screenshot for debugging purposes."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.debug_dir / f"{name}_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
    
    async def save_html(self, name):
        """Save the current page HTML for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = self.debug_dir / f"{name}_{timestamp}.html"
            html_content = await self.page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML saved to {html_path}")
    
    async def get_targeted_subjects(self) -> List[Dict[str, str]]:
        """
        Get the list of targeted subjects with their URLs.
        Returns:
            List of dictionaries with name and url for each target subject
        """
        logger.info(f"Navigating to subjects page: {self.subjects_url}")
        
        # Navigate to the subjects page
        await self.page.goto(self.subjects_url, wait_until="networkidle")
        
        # Wait for subjects to load
        await self.page.wait_for_selector("h1", state="visible", timeout=30000)
        
        # Take screenshot and save HTML for debugging
        await self.take_screenshot("subjects_page")
        await self.save_html("subjects_page")
        
        # Find all subject links
        subject_links = []
        
        # Updated to use more specific selectors
        subject_selectors = [
            "a[href*='/subjects-and-topics/']",  # General links
            ".banner__header a",  # Header links
            ".content-block-tiles__tile a",  # Tile links
            "a.content-block-list__item-link",  # List item links
            ".content-block-topic-cards a"  # Topic card links
        ]
        
        all_subjects = []
        for selector in subject_selectors:
            links = await self.page.query_selector_all(selector)
            logger.info(f"Found {len(links)} potential subject links with selector: {selector}")
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    
                    # Skip if not a valid subject link
                    if not href or not ('/subjects-and-topics/' in href):
                        continue
                    
                    # Skip duplicate links to the subjects page itself
                    if href.rstrip('/') == self.subjects_url.rstrip('/'):
                        continue
                    
                    # Get text from the link or its parent
                    text = await link.text_content()
                    text = text.strip()
                    
                    # If text is empty, try to get it from a heading inside the link
                    if not text:
                        heading = await link.query_selector("h2, h3, h4")
                        if heading:
                            text = await heading.text_content()
                            text = text.strip()
                    
                    # Skip if no text found
                    if not text:
                        continue
                    
                    # Ensure href is an absolute URL
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(self.subjects_url, href)
                    
                    # Add to all subjects list
                    subject_data = {"name": text, "url": href}
                    if subject_data not in all_subjects:
                        all_subjects.append(subject_data)
                        logger.info(f"Found subject: {text} at {href}")
                
                except Exception as e:
                    logger.error(f"Error extracting subject: {e}")
        
        # Filter to only include target subjects
        target_subjects = []
        for subject in all_subjects:
            # Check if this subject is in our target list (case-insensitive partial match)
            for target in TARGET_SUBJECTS:
                if target.lower() in subject["name"].lower():
                    target_subjects.append(subject)
                    logger.info(f"Selected target subject: {subject['name']} at {subject['url']}")
                    break
        
        # Log summary
        logger.info(f"Found {len(all_subjects)} total subjects, selected {len(target_subjects)} target subjects")
        
        return target_subjects
    
    async def extract_content_cards(self, page_url: str, subject_name: str):
        """
        Extract content cards from a subject page with deep content extraction.
        For each card:
        1. Extract basic metadata from the card
        2. Visit the content URL to extract detailed information
        3. Return to the subject page to continue

        Args:
            page_url: URL of the subject page
            subject_name: Name of the subject for categorization
        Returns:
            List of processed content items
        """
        logger.info(f"Extracting content from: {page_url}")
        
        # Navigate to the page
        await self.page.goto(page_url, wait_until="networkidle")
        
        # Wait for content to load
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot and save HTML
        await self.take_screenshot("subject_page_initial")
        await self.save_html("subject_page_initial")
        
        # All processed content items
        all_content_items = []
        
        # Main scraping loop - continue until no more "Load more" button
        page_counter = 1
        processed_urls = set()  # Keep track of already processed URLs
        
        while True:
            logger.info(f"Processing content page {page_counter}")
            
            # Wait for network to be idle to ensure all content is loaded
            await self.page.wait_for_load_state("networkidle")
            
            # Extract content cards/tiles on the current page
            content_cards = await self._find_content_cards()
            
            if not content_cards:
                logger.info("No content cards found on the current page")
                break
                
            logger.info(f"Found {len(content_cards)} content cards on page {page_counter}")
            
            # Process each content card
            for i, card in enumerate(content_cards):
                try:
                    # Extract basic info from the card
                    card_info = await self._extract_card_info(card, subject_name)
                    
                    if not card_info or not card_info.get("url"):
                        logger.warning(f"Skipping card {i+1} - could not extract URL")
                        continue
                    
                    content_url = card_info["url"]
                    
                    # Skip if we've already processed this URL
                    if content_url in processed_urls:
                        logger.info(f"Skipping already processed URL: {content_url}")
                        continue
                        
                    logger.info(f"Processing content card {i+1}/{len(content_cards)}: {card_info.get('title', 'Unknown')}")
                    
                    # Visit the content page to extract detailed information
                    content_item = await self._visit_and_extract_content(content_url, card_info, subject_name)
                    
                    if content_item:
                        all_content_items.append(content_item)
                        processed_urls.add(content_url)
                        logger.info(f"Successfully processed: {content_item['title']}")
                    
                    # Return to the subject page
                    await self.page.goto(page_url, wait_until="networkidle")
                    await self.page.wait_for_load_state("domcontentloaded")
                    
                    # Add a short delay to ensure the page is fully loaded
                    await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"Error processing content card: {e}")
                    
                    # Try to return to the subject page if something went wrong
                    try:
                        await self.page.goto(page_url, wait_until="networkidle")
                    except Exception as nav_error:
                        logger.error(f"Error returning to subject page: {nav_error}")
            
            # Save the current batch of content
            await self._save_current_batch(all_content_items, subject_name, page_counter)
            
            # Try to click "Load more" button to get more content
            load_more_clicked = await self._click_load_more()
            
            if not load_more_clicked:
                logger.info("No more content to load, finishing extraction")
                break
                
            page_counter += 1
            
            # Wait for new content to load
            await asyncio.sleep(2)
            
            # Safety measure: limit to 20 pages maximum to avoid infinite loops
            if page_counter > 20:
                logger.warning("Reached maximum page limit (20), stopping pagination")
                break
        
        logger.info(f"Completed extracting content from {page_url}. Total items: {len(all_content_items)}")
        return all_content_items
    
    async def _find_content_cards(self):
        """Find all content cards/tiles on the current page."""
        # Try multiple selectors to find content cards
        selectors = [
            ".content-block-tiles__tile",  # Main tile selector for ABC Education
            "article",  # Article elements
            ".resource-card",  # Resource card class
            ".card",  # Generic card class
            ".content-card",  # Content card class
            ".tile",  # Generic tile class
            ".list-view-item",  # List view items
            "[data-testid='card']",  # Cards with test ID
            "a.content-block-tiles__item-link"  # Direct content links
        ]
        
        found_cards = []
        
        for selector in selectors:
            cards = await self.page.query_selector_all(selector)
            if cards:
                logger.info(f"Found {len(cards)} content cards with selector: {selector}")
                found_cards.extend(cards)
                break  # Use the first successful selector
        
        return found_cards
    
    async def _extract_card_info(self, card, subject_name: str):
        """Extract basic information from a content card."""
        try:
            # Get inner HTML for debugging
            card_html = await card.inner_html()
            
            # Extract title
            title_selectors = [
                "h2, h3, h4",  # Heading elements
                ".title, .heading",  # Class-based title elements
                "a > strong",  # Strong text in links
                ".content-block-tiles__title",  # Specific title class
                ".tile__title"  # Tile title class
            ]
            
            title_elem = None
            for selector in title_selectors:
                elem = await card.query_selector(selector)
                if elem:
                    title_elem = elem
                    break
            
            if not title_elem:
                return None
            
            title = await title_elem.text_content()
            title = title.strip()
            
            if not title:
                return None
            
            # Extract link
            link_elem = await card.query_selector("a")
            if not link_elem:
                # The card itself might be a link
                if await card.get_attribute("href"):
                    link_elem = card
            
            if not link_elem:
                return None
            
            content_url = await link_elem.get_attribute("href")
            if not content_url:
                return None
            
            # Ensure URL is absolute
            if not content_url.startswith(('http://', 'https://')):
                content_url = urljoin(self.base_url, content_url)
            
            # Extract description
            description_selectors = [
                "p:not(h2 ~ p, h3 ~ p)",  # Paragraphs not following headings
                ".description, .summary",  # Generic description classes
                ".content-block-tiles__description",  # Specific description class
                ".tile__description"  # Tile description class
            ]
            
            description_elem = None
            for selector in description_selectors:
                elem = await card.query_selector(selector)
                if elem:
                    description_elem = elem
                    break
            
            description = ""
            if description_elem:
                description = await description_elem.text_content()
                description = description.strip()
            
            # Extract topics
            topics = await self._extract_topics_from_card(card, subject_name)
            
            # Return the basic card information
            return {
                "title": title,
                "description": description,
                "url": content_url,
                "topics": topics,
                "subject": subject_name,
                "content_type": self._determine_content_type(card_html, content_url).value
            }
        
        except Exception as e:
            logger.error(f"Error extracting card info: {e}")
            return None
    
    async def _visit_and_extract_content(self, content_url: str, card_info: Dict[str, Any], subject_name: str):
        """Visit a content page and extract detailed information."""
        logger.info(f"Visiting content URL: {content_url}")
        
        try:
            # Navigate to the content page
            response = await self.page.goto(content_url, wait_until="networkidle")
            
            # Check if navigation was successful
            if not response or response.status >= 400:
                logger.error(f"Failed to navigate to {content_url}: {response.status if response else 'No response'}")
                return None
                
            # Wait for the page to load
            await self.page.wait_for_selector("body", state="visible")
            
            # Take screenshot and save HTML
            path_safe_title = card_info["title"].replace(" ", "_").replace("/", "_")[:30]
            await self.take_screenshot(f"content_{path_safe_title}")
            await self.save_html(f"content_{path_safe_title}")
            
            # Extract detailed content information
            detailed_info = await self._extract_detailed_content(card_info, subject_name)
            
            if not detailed_info:
                logger.warning(f"Could not extract detailed info from {content_url}")
                return None
                
            # Generate a unique ID
            content_id = str(uuid.uuid4())
            
            # Create content item
            content_item = {
                "id": content_id,
                "title": detailed_info.get("title", card_info["title"]),
                "description": detailed_info.get("description", card_info["description"]),
                "content_type": detailed_info.get("content_type", card_info["content_type"]),
                "subject": subject_name,
                "topics": detailed_info.get("topics", card_info["topics"]),
                "url": content_url,
                "source": "ABC Education",
                "difficulty_level": detailed_info.get("difficulty_level", DifficultyLevel.INTERMEDIATE.value),
                "grade_level": detailed_info.get("grade_level", [6, 7, 8]),
                "duration_minutes": detailed_info.get("duration_minutes", self._estimate_duration(ContentType(card_info["content_type"]))),
                "keywords": detailed_info.get("keywords", self._extract_keywords(card_info["title"], card_info["description"])),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "content_html": detailed_info.get("content_html", ""),
                "author": detailed_info.get("author", "ABC Education")
            }
            
            return content_item
            
        except Exception as e:
            logger.error(f"Error visiting and extracting content from {content_url}: {e}")
            return None
    
    async def _extract_detailed_content(self, card_info: Dict[str, Any], subject_name: str):
        """Extract detailed information from a content page."""
        try:
            # Get the page title
            title = await self.page.title()
            title = title.strip()
            
            # If the page title looks good, use it; otherwise keep the card title
            if title and "ABC Education" in title and len(title) > 5:
                title = title.replace(" - ABC Education", "").strip()
            else:
                title = card_info["title"]
            
            # Extract the main content
            content_selectors = [
                "article",
                "main",
                ".content-block-article__content",
                ".article__body",
                ".content-main",
                "#content-main",
                ".main-content"
            ]
            
            content_elem = None
            for selector in content_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    content_elem = elem
                    break
            
            content_html = ""
            if content_elem:
                content_html = await content_elem.inner_html()
            
            # Extract description/summary
            description_selectors = [
                "meta[name='description']",
                ".article__summary",
                ".content-block-article__summary",
                ".summary"
            ]
            
            description = card_info["description"]  # Default to card description
            
            for selector in description_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    if selector.startswith("meta"):
                        desc = await elem.get_attribute("content")
                    else:
                        desc = await elem.text_content()
                    
                    if desc and len(desc) > len(description):
                        description = desc.strip()
                        break
            
            # Extract author
            author_selectors = [
                ".byline",
                ".author",
                ".content-block-article__byline"
            ]
            
            author = "ABC Education"  # Default author
            
            for selector in author_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    author_text = await elem.text_content()
                    if author_text:
                        author = author_text.replace("By ", "").strip()
                        break
            
            # Extract topics/tags
            topics_selectors = [
                ".tags",
                ".topics",
                ".categories",
                ".content-block-article__tags"
            ]
            
            topics = card_info["topics"]  # Default to card topics
            
            for selector in topics_selectors:
                elems = await self.page.query_selector_all(f"{selector} a, {selector} span")
                if elems:
                    new_topics = []
                    for elem in elems:
                        topic_text = await elem.text_content()
                        if topic_text and topic_text.strip():
                            new_topics.append(topic_text.strip())
                    
                    if new_topics:
                        topics = new_topics
                        break
            
            # Extract duration
            duration_selectors = [
                ".duration",
                ".video-duration",
                "[data-testid='duration']"
            ]
            
            duration_minutes = None
            
            for selector in duration_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    duration_text = await elem.text_content()
                    if duration_text:
                        # Try to parse duration
                        minutes = self._parse_duration(duration_text)
                        if minutes:
                            duration_minutes = minutes
                            break
            
            # If no specific duration found, estimate based on content type
            if not duration_minutes:
                duration_minutes = self._estimate_duration(ContentType(card_info["content_type"]))
            
            # Determine content type more accurately from the detailed page
            content_type = self._determine_detailed_content_type(card_info["content_type"])
            
            # Determine difficulty level and grade levels
            difficulty, grade_levels = self._determine_difficulty_and_grade(title, description, subject_name)
            
            # Extract keywords
            keywords = self._extract_keywords(title, description)
            
            return {
                "title": title,
                "description": description,
                "content_type": content_type.value,
                "topics": topics,
                "difficulty_level": difficulty.value,
                "grade_level": grade_levels,
                "duration_minutes": duration_minutes,
                "keywords": keywords,
                "content_html": content_html,
                "author": author
            }
            
        except Exception as e:
            logger.error(f"Error extracting detailed content: {e}")
            return None
    
    def _determine_detailed_content_type(self, initial_type: str) -> ContentType:
        """Determine content type more accurately from the detailed page."""
        page_url = self.page.url
        
        # Try to determine from the URL first
        if '/video/' in page_url or '/watch/' in page_url or '/iview/' in page_url:
            return ContentType.VIDEO
        elif '/quiz/' in page_url or '/test/' in page_url:
            return ContentType.QUIZ
        elif '/worksheet/' in page_url or '/exercise/' in page_url:
            return ContentType.WORKSHEET
        elif '/interactive/' in page_url or '/game/' in page_url:
            return ContentType.INTERACTIVE
        elif '/lesson/' in page_url or '/class/' in page_url:
            return ContentType.LESSON
        elif '/activity/' in page_url or '/project/' in page_url:
            return ContentType.ACTIVITY
        
        # Check page content for video player elements
        video_selectors = [
            "video",
            ".video-player",
            ".media-player",
            "iframe[src*='youtube']",
            "iframe[src*='vimeo']"
        ]
        
        for selector in video_selectors:
            try:
                elem = self.page.query_selector(selector)
                if elem:
                    return ContentType.VIDEO
            except:
                pass
        
        # Check for interactive elements
        interactive_selectors = [
            ".interactive",
            ".game",
            "iframe[src*='interactive']",
            "canvas"
        ]
        
        for selector in interactive_selectors:
            try:
                elem = self.page.query_selector(selector)
                if elem:
                    return ContentType.INTERACTIVE
            except:
                pass
        
        # Check for quiz elements
        quiz_selectors = [
            ".quiz",
            ".question",
            "form[data-quiz]",
            "input[type='radio']"
        ]
        
        for selector in quiz_selectors:
            try:
                elem = self.page.query_selector(selector)
                if elem:
                    return ContentType.QUIZ
            except:
                pass
        
        # Fall back to the initial content type
        return ContentType(initial_type)
    
    def _parse_duration(self, duration_text: str) -> Optional[int]:
        """Parse duration text (e.g., "5:30", "5m 30s", "5 min") to minutes."""
        try:
            # Clean the text
            duration_text = duration_text.lower().strip()
            
            # Check for "X:XX" format
            if ":" in duration_text:
                parts = duration_text.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes + (1 if seconds >= 30 else 0)  # Round up for 30+ seconds
                elif len(parts) == 3:  # Hours:Minutes:Seconds
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    return hours * 60 + minutes + (1 if seconds >= 30 else 0)
            
            # Check for "X min Y sec" format
            minutes_match = re.search(r'(\d+)\s*(?:min|m)', duration_text)
            seconds_match = re.search(r'(\d+)\s*(?:sec|s)', duration_text)
            
            if minutes_match:
                minutes = int(minutes_match.group(1))
                if seconds_match:
                    seconds = int(seconds_match.group(1))
                    return minutes + (1 if seconds >= 30 else 0)
                return minutes
            
            # Check for just seconds
            if seconds_match:
                seconds = int(seconds_match.group(1))
                return 1 if seconds > 0 else 0  # At least 1 minute for any duration
            
            # Check for just a number (assume minutes)
            number_match = re.search(r'^(\d+)$', duration_text)
            if number_match:
                return int(number_match.group(1))
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing duration '{duration_text}': {e}")
            return None
    
    async def _click_load_more(self) -> bool:
        """Try to click the 'Load more' button if it exists."""
        load_more_selectors = [
            "button:has-text('Load more')",
            "button:text-is('Load more')",
            "button.content-block-tiles__load-more",
            "[data-testid='load-more-button']"
        ]
        
        for selector in load_more_selectors:
            try:
                # Check if button is visible
                button = await self.page.query_selector(selector)
                if button and await button.is_visible():
                    logger.info(f"Clicking 'Load more' button with selector: {selector}")
                    await button.click()
                    return True
            except Exception as e:
                logger.debug(f"Could not click 'Load more' button with selector '{selector}': {e}")
        
        # Try to find any button that looks like "Load more"
        try:
            all_buttons = await self.page.query_selector_all("button")
            for button in all_buttons:
                text = await button.text_content()
                if text and text.lower().strip() == "load more" and await button.is_visible():
                    logger.info("Clicking 'Load more' button found by text")
                    await button.click()
                    return True
        except Exception as e:
            logger.debug(f"Could not find 'Load more' button by text: {e}")
        
        logger.info("No 'Load more' button found")
        return False
    
    async def _save_current_batch(self, content_items: List[Dict[str, Any]], subject_name: str, page_number: int):
        """Save the current batch of content items to a JSON file."""
        if not content_items:
            logger.warning("No content items to save for current batch")
            return
            
        try:
            safe_subject_name = subject_name.replace(" ", "_").replace("/", "_")
            batch_file = self.debug_dir / f"{safe_subject_name}_batch_{page_number}.json"
            
            # Create a copy without embeddings
            content_copy = []
            for item in content_items:
                item_copy = item.copy()
                if 'embedding' in item_copy:
                    del item_copy['embedding']
                content_copy.append(item_copy)
            
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(content_copy, f, indent=2)
                
            logger.info(f"Saved batch {page_number} with {len(content_items)} items to {batch_file}")
            
        except Exception as e:
            logger.error(f"Error saving current batch: {e}")
    
    async def _extract_topics_from_card(self, card, subject_name: str) -> List[str]:
        """Extract topics from a content card."""
        topics = []
        
        # Try to find topic tags
        topic_selectors = [
            ".tag", 
            ".topic", 
            ".category", 
            ".subjects",
            ".tile__subject",
            ".content-block-tiles__subject",
            "[data-testid='tag']", 
            "[data-testid='topic']"
        ]
        
        for selector in topic_selectors:
            topic_elems = await card.query_selector_all(selector)
            for elem in topic_elems:
                topic_text = await elem.text_content()
                topic_text = topic_text.strip()
                if topic_text and topic_text not in topics:
                    topics.append(topic_text)
        
        # If no topics found, use the subject name
        if not topics:
            topics = [subject_name]
        
        return topics
    
    def _determine_content_type(self, card_html: str, url: str) -> ContentType:
        """Determine the content type based on the card HTML and URL."""
        # Convert to lowercase for case-insensitive matching
        card_html_lower = card_html.lower()
        url_lower = url.lower()
        
        # Check for video indicators
        if any(video_term in card_html_lower for video_term in ['video', 'watch', 'play button', 'duration']) or \
           any(video_term in url_lower for video_term in ['/video/', '/watch/', '.mp4', '/tv/', '/iview/']):
            return ContentType.VIDEO
        
        # Check for quiz indicators
        elif any(quiz_term in card_html_lower for quiz_term in ['quiz', 'test yourself', 'assessment']) or \
             any(quiz_term in url_lower for quiz_term in ['/quiz/', '/test/', '/assessment/']):
            return ContentType.QUIZ
        
        # Check for worksheet indicators
        elif any(worksheet_term in card_html_lower for worksheet_term in ['worksheet', 'printable', 'exercise']) or \
             any(worksheet_term in url_lower for worksheet_term in ['/worksheet/', '/exercise/', '/printable/']):
            return ContentType.WORKSHEET
        
        # Check for interactive indicators
        elif any(interactive_term in card_html_lower for interactive_term in ['interactive', 'game', 'simulation', 'play']) or \
             any(interactive_term in url_lower for interactive_term in ['/interactive/', '/game/', '/simulation/', '/play/']):
            return ContentType.INTERACTIVE
        
        # Check for lesson indicators
        elif any(lesson_term in card_html_lower for lesson_term in ['lesson', 'class', 'course', 'teacher notes']) or \
             any(lesson_term in url_lower for lesson_term in ['/lesson/', '/class/', '/course/']):
            return ContentType.LESSON
        
        # Check for activity indicators
        elif any(activity_term in card_html_lower for activity_term in ['activity', 'project', 'try this', 'experiment']) or \
             any(activity_term in url_lower for activity_term in ['/activity/', '/project/', '/lab/', '/experiment/']):
            return ContentType.ACTIVITY
        
        # Default to article
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
            r'grades? (\d+),? (\d+)(?:,? and (\d+))?',
            r'foundation',  # For Australian foundation year
            r'prep',  # Alternative name for foundation
            r'reception', # Alternative name for foundation
            r'kindergarten'  # Alternative name for foundation
        ]
        
        extracted_grades = []
        
        # Check for specific grade mentions
        for pattern in grade_patterns:
            if pattern in ['foundation', 'prep', 'reception', 'kindergarten']:
                if re.search(pattern, text):
                    extracted_grades.append(0)  # Use 0 to represent foundation/prep
                    continue
                    
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
    
    def _estimate_duration(self, content_type: ContentType):
        """Estimate the duration in minutes based on content type."""
        if content_type == ContentType.VIDEO:
            return random.randint(3, 25)  # Videos are typically 3-25 minutes
        elif content_type == ContentType.INTERACTIVE:
            return random.randint(15, 35)  # Interactives typically take 15-35 minutes
        elif content_type == ContentType.QUIZ:
            return random.randint(10, 20)  # Quizzes typically take 10-20 minutes
        elif content_type == ContentType.WORKSHEET:
            return random.randint(20, 50)  # Worksheets typically take 20-50 minutes
        elif content_type == ContentType.LESSON:
            return random.randint(30, 60)  # Lessons typically take 30-60 minutes
        elif content_type == ContentType.ACTIVITY:
            return random.randint(20, 50)  # Activities typically take 20-50 minutes
        else:  # Article
            return random.randint(10, 30)  # Articles typically take 10-30 minutes to read
    
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
    
    async def process_content_for_search(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process content for search indexing by adding embedding."""
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
            logger.error(f"Error processing content for search: {e}")
            return content_item
    
    async def save_to_azure_search(self, content_items: List[Dict[str, Any]]):
        """Save content items to Azure AI Search."""
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
                processed_item = await self.process_content_for_search(item)
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
    
    async def save_to_json(self, content_items: List[Dict[str, Any]], filepath: str):
        """Save content items to a JSON file."""
        if not content_items:
            logger.warning("No content items to save to JSON")
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            # Remove embeddings and content HTML before saving to file to reduce size
            content_for_save = []
            for item in content_items:
                item_copy = item.copy()
                if 'embedding' in item_copy:
                    del item_copy['embedding']
                # Optionally keep only a summary of the content HTML
                if 'content_html' in item_copy and len(item_copy['content_html']) > 500:
                    item_copy['content_html'] = item_copy['content_html'][:500] + "... [truncated]"
                content_for_save.append(item_copy)
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content_for_save, f, indent=2)
                
            logger.info(f"Saved {len(content_items)} content items to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving content to JSON: {e}")
    
    async def scrape_all_target_subjects(self):
        """Scrape all targeted subjects."""
        try:
            # Get the list of targeted subjects
            target_subjects = await self.get_targeted_subjects()
            
            if not target_subjects:
                logger.error("No target subjects found!")
                return []
            
            logger.info(f"Starting to scrape {len(target_subjects)} targeted subjects")
            
            all_content_items = []
            
            # Process each subject
            for subject_info in target_subjects:
                subject_name = subject_info["name"]
                subject_url = subject_info["url"]
                
                logger.info(f"Processing subject: {subject_name} at {subject_url}")
                
                try:
                    # Use deep content extraction for this subject
                    content_items = await self.extract_content_cards(subject_url, subject_name)
                    all_content_items.extend(content_items)
                    
                    # Save results to JSON file
                    await self.save_to_json(content_items, os.path.join(
                        self.debug_dir, 
                        f"content_{subject_name.replace(' ', '_')}_all.json"
                    ))
                    
                    # Add a delay between subjects to avoid overloading the server
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing subject {subject_name}: {e}")
            
            # Save all results to a combined JSON file
            await self.save_to_json(all_content_items, os.path.join(self.debug_dir, "all_content.json"))
            
            logger.info(f"Completed scraping all target subjects. Total content items: {len(all_content_items)}")
            return all_content_items
            
        except Exception as e:
            logger.error(f"Error in scrape_all_target_subjects: {e}")
            return []

async def run_deep_scraper(headless=False, output_path=None):
    """Run the deep content scraper for ABC Education."""
    scraper = DeepContentScraper()
    
    try:
        # Setup browser and search client
        await scraper.setup(headless=headless)
        
        # Scrape content
        content_items = await scraper.scrape_all_target_subjects()
        logger.info(f"Scraped {len(content_items)} content items")
        
        # Save to output path if provided
        if output_path and content_items:
            await scraper.save_to_json(content_items, output_path)
            logger.info(f"Content saved to {output_path}")
        
        # Save to Azure Search (only if we have valid credentials)
        if settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY and content_items:
            await scraper.save_to_azure_search(content_items)
            logger.info("Content saved to Azure AI Search")
        
        return content_items
    except Exception as e:
        logger.error(f"Error running deep scraper: {e}")
        return []
    finally:
        # Close browser and other resources
        await scraper.teardown()

if __name__ == "__main__":
    # Run the scraper in visible mode
    asyncio.run(run_deep_scraper(
        headless=False,
        output_path="debug_output/abc_education_content.json"
    ))
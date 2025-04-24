import asyncio
import logging
from typing import List, Dict, Any, Optional
import re
import uuid
import random
import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Setup path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Playwright imports for browser automation
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Import our new multimedia content processor
from utils.multimedia_content_processor import get_content_processor, process_and_index_content

# Import models and settings
from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('abc_scraper.log')
    ]
)

logger = logging.getLogger(__name__)

# Target subjects to focus on
TARGET_SUBJECTS = [
    "Arts",
    "English",
    "Geography", 
    "History",
    "Mathematics",
    "Science",
    "Technologies"
]

class EnhancedEducationScraper:
    """Enhanced scraper for educational content with multimedia processing."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.base_url = "https://www.abc.net.au/education"
        self.subjects_url = "https://www.abc.net.au/education/subjects-and-topics"
        
        # Will be initialized later
        self.browser = None
        self.context = None
        self.page = None
        self.content_processor = None
        
        # Common stop words for keyword extraction
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "with", "by", "about", "as", "of", "from", "this", "that", "these", 
            "those", "is", "are", "was", "were", "be", "been", "being", "have", 
            "has", "had", "do", "does", "did", "will", "would", "should", "can", 
            "could", "may", "might", "must", "shall"
        }
    
    async def setup(self, headless=True):
        """Initialize Playwright browser and content processor."""
        logger.info(f"Setting up Playwright browser (headless={headless}) and content processor...")
        
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
        
        self.page = await self.context.new_page()
        
        # Set default timeout (120 seconds)
        self.page.set_default_timeout(120000)
        
        # Initialize content processor
        self.content_processor = await get_content_processor()
    
    async def teardown(self):
        """Close browser and other resources."""
        logger.info("Tearing down browser and content processor...")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
    
    async def get_subjects(self) -> List[Dict[str, str]]:
        """Get available subjects from the website."""
        logger.info(f"Navigating to subjects page: {self.subjects_url}")
        
        # Navigate to the subjects page
        await self.page.goto(self.subjects_url, wait_until="networkidle")
        
        # Wait for subjects to load
        await self.page.wait_for_selector("h1", state="visible", timeout=30000)
        
        # Find all subject links
        subject_links = []
        
        # Try multiple selectors to find subject links
        subject_selectors = [
            "a[href*='/subjects-and-topics/']",
            ".banner__header a",
            ".content-block-tiles__tile a",
            "a.content-block-list__item-link",
            ".content-block-topic-cards a"
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
        
        return target_subjects
    
    async def extract_content_cards(self, page_url: str, subject_name: str) -> List[Dict[str, Any]]:
        """
        Extract content cards from a subject page.
        
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
        
        # All processed content items
        all_content_items = []
        processed_urls = set()  # Track processed URLs to avoid duplicates
        
        # Main scraping loop - continue until no more "Load more" button
        page_counter = 1
        
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
                    
                    # Process the content using our multimedia content processor
                    processed_content = await process_and_index_content(content_url, card_info)
                    
                    if processed_content:
                        all_content_items.append(processed_content)
                        processed_urls.add(content_url)
                        logger.info(f"Successfully processed: {processed_content['title']}")
                    
                except Exception as e:
                    logger.error(f"Error processing content card: {e}")
            
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
    
    async def _extract_card_info(self, card, subject_name: str) -> Dict[str, Any]:
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
            
            # Determine content type
            content_type_value = self._determine_content_type(card_html, content_url).value
            
            # Extract keywords
            keywords = self._extract_keywords(title, description)
            
            # Determine difficulty level and grade levels
            difficulty, grade_levels = self._determine_difficulty_and_grade(title, description, subject_name)
            
            # Return the basic card information
            return {
                "title": title,
                "description": description,
                "url": content_url,
                "topics": topics,
                "subject": subject_name,
                "content_type": content_type_value,
                "difficulty_level": difficulty.value,
                "grade_level": grade_levels,
                "keywords": keywords,
                "source": "ABC Education"
            }
        
        except Exception as e:
            logger.error(f"Error extracting card info: {e}")
            return None
    
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
    
    def _determine_content_type(self, card_html: str, url: str) -> ContentType:
        """Determine the content type based on card HTML and URL."""
        # Convert to lowercase for case-insensitive matching
        card_html_lower = card_html.lower()
        url_lower = url.lower()
        
        # Check for video indicators
        if any(video_term in card_html_lower for video_term in ['video', 'watch', 'play button', 'duration']) or \
           any(video_term in url_lower for video_term in ['/video/', '/watch/', '.mp4', '/tv/', '/iview/']):
            return ContentType.VIDEO
        
        # Check for audio indicators
        elif any(audio_term in card_html_lower for audio_term in ['audio', 'listen', 'podcast', 'sound']) or \
             any(audio_term in url_lower for audio_term in ['/audio/', '/podcast/', '.mp3', '.wav', '/radio/']):
            return ContentType.AUDIO
        
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
        
        # If we found specific grades, use those
        # Otherwise fall back to default grades for the difficulty level
        grade_levels = extracted_grades or default_grades
        
        return difficulty, grade_levels
    
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
    
    async def scrape_all_subjects(self, subject_limit=None):
        """
        Scrape all targeted subjects, optionally limiting to a specific number.
        
        Args:
            subject_limit: Maximum number of subjects to scrape (None for all)
            
        Returns:
            All scraped content items
        """
        try:
            # Get the list of targeted subjects
            subjects = await self.get_subjects()
            
            if not subjects:
                logger.error("No subjects found!")
                return []
            
            # Apply subject limit if specified
            if subject_limit and isinstance(subject_limit, int) and subject_limit > 0:
                subjects = subjects[:subject_limit]
                
            logger.info(f"Starting to scrape {len(subjects)} subjects")
            
            all_content_items = []
            
            # Process each subject
            for subject_info in subjects:
                subject_name = subject_info["name"]
                subject_url = subject_info["url"]
                
                logger.info(f"Processing subject: {subject_name} at {subject_url}")
                
                try:
                    # Extract content for this subject
                    content_items = await self.extract_content_cards(subject_url, subject_name)
                    all_content_items.extend(content_items)
                    
                    # Add a delay between subjects to avoid overloading the server
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing subject {subject_name}: {e}")
            
            logger.info(f"Completed scraping all subjects. Total content items: {len(all_content_items)}")
            return all_content_items
            
        except Exception as e:
            logger.error(f"Error in scrape_all_subjects: {e}")
            return []

async def run_scraper(subject_limit=None, save_to_search=True, headless=True):
    """
    Run the ABC Education scraper with multimedia support.
    
    Args:
        subject_limit: Maximum number of subjects to scrape (None for all)
        save_to_search: Whether to save content to Azure AI Search
        headless: Whether to run browser in headless mode
        
    Returns:
        All scraped content items
    """
    scraper = EnhancedEducationScraper()
    
    try:
        # Setup browser and content processor
        await scraper.setup(headless=headless)
        
        # Scrape all subjects (or limited number)
        logger.info(f"Starting scraper with subject_limit={subject_limit}")
        content_items = await scraper.scrape_all_subjects(subject_limit=subject_limit)
        
        logger.info(f"Scraping completed. Found {len(content_items)} content items")
        return content_items
        
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        return []
        
    finally:
        # Clean up resources
        await scraper.teardown()

if __name__ == "__main__":
    # Run the scraper directly
    asyncio.run(run_scraper(
        subject_limit=2,  # Limit to 2 subjects for testing
        save_to_search=True,
        headless=False  # Run with visible browser for debugging
    ))
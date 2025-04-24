import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import uuid
import json
import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Playwright imports for browser automation
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Setup path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import necessary components, with fallbacks for testing
try:
    # Import the multimedia content processor
    from utils.multimedia_content_processor import get_content_processor, process_and_index_content
    
    # Import models and settings
    from models.content import Content, ContentType, DifficultyLevel
    from config.settings import Settings
    
    # Initialize settings
    settings = Settings()
except ImportError:
    # Fallback ContentType enum for testing
    class ContentType:
        ARTICLE = "article"
        VIDEO = "video"
        AUDIO = "audio"
        INTERACTIVE = "interactive"
        WORKSHEET = "worksheet"
        QUIZ = "quiz"
        LESSON = "lesson"
        ACTIVITY = "activity"
    
    # Fallback DifficultyLevel enum for testing
    class DifficultyLevel:
        BEGINNER = "beginner"
        INTERMEDIATE = "intermediate"
        ADVANCED = "advanced"
    
    # Mock process_and_index_content function
    async def process_and_index_content(url, content_info):
        return content_info

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('edu_scraper.log')
    ]
)

logger = logging.getLogger(__name__)

# Predefined list of subjects with their URLs
SUBJECT_LINKS = [
    {"name": "Arts", "url": "https://www.abc.net.au/education/subjects-and-topics/arts"},
    {"name": "English", "url": "https://www.abc.net.au/education/subjects-and-topics/english"},
    {"name": "Geography", "url": "https://www.abc.net.au/education/subjects-and-topics/geography"},
    {"name": "Maths", "url": "https://www.abc.net.au/education/subjects-and-topics/maths"},
    {"name": "Science", "url": "https://www.abc.net.au/education/subjects-and-topics/science"},
    {"name": "Technologies", "url": "https://www.abc.net.au/education/subjects-and-topics/technologies"},
    {"name": "Languages", "url": "https://www.abc.net.au/education/subjects-and-topics/languages"}
]

class SimplifiedEducationScraper:
    """Simplified scraper for educational content focusing on direct subject URLs."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.base_url = "https://www.abc.net.au/education"
        
        # Will be initialized later
        self.browser = None
        self.context = None
        self.page = None
        self.content_processor = None
        
        # Create debug output directory
        self.debug_dir = os.path.join(os.getcwd(), "debug_output")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # Directory for saving resources
        self.resources_dir = os.path.join(os.getcwd(), "education_resources")
        os.makedirs(self.resources_dir, exist_ok=True)
        
        # Common stop words for keyword extraction
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "with", "by", "about", "as", "of", "from", "this", "that", "these", 
            "those", "is", "are", "was", "were", "be", "been", "being", "have", 
            "has", "had", "do", "does", "did", "will", "would", "should", "can", 
            "could", "may", "might", "must", "shall"
        }
    
    async def setup(self, headless=True):
        """Initialize Playwright browser."""
        logger.info(f"Setting up Playwright browser (headless={headless})...")
        
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
        
        # Try to initialize content processor if available
        try:
            self.content_processor = await get_content_processor()
            logger.info("Content processor initialized")
        except:
            logger.warning("Content processor not available. Running in data collection mode only.")
    
    async def teardown(self):
        """Close browser and other resources."""
        logger.info("Tearing down browser...")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
    
    async def save_screenshot(self, name):
        """Save a screenshot for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.debug_dir, f"{name}_{timestamp}.png")
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
    
    async def save_html(self, name):
        """Save the current page HTML for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(self.debug_dir, f"{name}_{timestamp}.html")
            html_content = await self.page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML saved to {html_path}")
    
    async def find_education_resources(self, subject_link: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Find all education resource links on a subject page.
        
        Args:
            subject_link: Dictionary with subject name and URL
            
        Returns:
            List of dictionaries with resource title and URL
        """
        subject_name = subject_link["name"]
        subject_url = subject_link["url"]
        
        logger.info(f"Finding education resources for {subject_name} at {subject_url}")
        
        # Navigate to the subject page
        await self.page.goto(subject_url, wait_until="networkidle")
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot and save HTML for debugging
        await self.save_screenshot(f"subject_{subject_name}")
        await self.save_html(f"subject_{subject_name}")
        
        # Get the main content area, excluding header and navigation
        main_content_selectors = [
            "main",
            "#main",
            ".main-content",
            "article",
            ".content-main",
            ".content-wrapper",
            "body"  # Fallback to body if no other containers found
        ]
        
        main_content = None
        for selector in main_content_selectors:
            content = await self.page.query_selector(selector)
            if content:
                main_content = content
                logger.info(f"Found main content with selector: {selector}")
                break
        
        if not main_content:
            logger.warning(f"Could not find main content area for {subject_name}")
            return []
        
        # Find all links in the main content
        links = await main_content.query_selector_all("a")
        logger.info(f"Found {len(links)} links in the main content for {subject_name}")
        
        # Filter links to identify education resources
        resource_links = []
        
        for link in links:
            try:
                # Get href and text
                href = await link.get_attribute("href")
                if not href:
                    continue
                
                # Make absolute URL if needed
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                
                # Skip non-ABC links or navigation links
                if not ('abc.net.au' in href and '/education/' in href):
                    continue
                
                # Skip if it's the current subject page
                if href == subject_url:
                    continue
                
                # Get text content
                text = await link.text_content()
                text = text.strip()
                
                # Skip if no text or very short text (likely UI elements)
                if not text or len(text) < 5:
                    continue
                
                # Check if it's not in a typical navigation element
                parent_element = await link.evaluate("""el => {
                    let parent = el.parentElement;
                    for (let i = 0; i < 5 && parent; i++) {
                        if (parent.tagName && ['NAV', 'HEADER', 'FOOTER'].includes(parent.tagName)) {
                            return false;
                        }
                        if (parent.className && ['nav', 'header', 'footer', 'menu', 'navigation'].some(c => parent.className.includes(c))) {
                            return false;
                        }
                        parent = parent.parentElement;
                    }
                    return true;
                }""")
                
                if not parent_element:
                    continue
                
                # Looks like an education resource - add to list
                resource_links.append({
                    "title": text,
                    "url": href,
                    "subject": subject_name
                })
                logger.info(f"Found resource: {text[:40]}{'...' if len(text) > 40 else ''}")
                
            except Exception as e:
                logger.error(f"Error processing link: {e}")
        
        logger.info(f"Identified {len(resource_links)} education resources for {subject_name}")
        
        # Save the resource links to a JSON file
        self.save_resource_links_to_json(resource_links, subject_name)
        
        return resource_links
    
    def save_resource_links_to_json(self, resource_links: List[Dict[str, str]], subject_name: str):
        """Save resource links to a JSON file."""
        if not resource_links:
            return
            
        # Create a safe filename
        safe_subject = subject_name.replace(" ", "_").replace("/", "_")
        filename = os.path.join(self.resources_dir, f"{safe_subject}_resources.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(resource_links, f, indent=2)
                
            logger.info(f"Saved {len(resource_links)} resource links to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving resource links to JSON: {e}")
    
    async def extract_content_details(self, resource_link: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract detailed content from a resource page.
        
        Args:
            resource_link: Dictionary with resource title, URL, and subject
            
        Returns:
            Dictionary with extracted content details
        """
        resource_url = resource_link["url"]
        resource_title = resource_link["title"]
        subject_name = resource_link["subject"]
        
        logger.info(f"Extracting content details from: {resource_title[:30]}{'...' if len(resource_title) > 30 else ''}")
        
        # Navigate to the resource page
        await self.page.goto(resource_url, wait_until="networkidle")
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot and save HTML for debugging
        safe_title = resource_title.replace(" ", "_").replace("/", "_")[:30]
        await self.save_screenshot(f"resource_{safe_title}")
        await self.save_html(f"resource_{safe_title}")
        
        # Extract basic metadata
        metadata = {
            "title": resource_title,
            "url": resource_url,
            "subject": subject_name,
            "source": "ABC Education",
            "id": str(uuid.uuid4())
        }
        
        # Extract description
        description = await self._extract_description()
        if description:
            metadata["description"] = description
        else:
            # If no description found, use a generic one
            metadata["description"] = f"Educational resource about {subject_name}"
        
        # Determine content type
        content_type = await self._determine_content_type()
        metadata["content_type"] = content_type.value
        
        # Extract topics
        topics = await self._extract_topics(subject_name)
        metadata["topics"] = topics
        
        # Determine difficulty level and grade levels
        difficulty, grade_levels = self._determine_difficulty_and_grade(
            resource_title, 
            metadata.get("description", ""), 
            subject_name
        )
        metadata["difficulty_level"] = difficulty.value
        metadata["grade_level"] = grade_levels
        
        # Extract duration
        duration = await self._extract_duration()
        if duration:
            metadata["duration_minutes"] = duration
        else:
            # Estimate based on content type
            metadata["duration_minutes"] = self._estimate_duration(content_type)
        
        # Extract keywords
        keywords = self._extract_keywords(
            resource_title, 
            metadata.get("description", "")
        )
        metadata["keywords"] = keywords
        
        # Extract content based on content type
        if content_type == ContentType.VIDEO:
            video_info = await self._extract_video_content()
            metadata.update(video_info)
            
        elif content_type == ContentType.AUDIO:
            audio_info = await self._extract_audio_content()
            metadata.update(audio_info)
            
        elif content_type in [ContentType.ARTICLE, ContentType.WORKSHEET]:
            article_text = await self._extract_article_text()
            metadata["article_text"] = article_text
            
        elif content_type in [ContentType.INTERACTIVE, ContentType.ACTIVITY]:
            interactive_info = await self._extract_interactive_content()
            metadata.update(interactive_info)
            
        elif content_type == ContentType.QUIZ:
            quiz_info = await self._extract_quiz_content()
            metadata.update(quiz_info)
        
        # Extract author if available
        author = await self._extract_author()
        if author:
            metadata["author"] = author
        
        # Get current page content for processing
        html_content = await self.page.content()
        metadata["content_html"] = html_content
        
        logger.info(f"Extracted content details for: {resource_title[:30]}{'...' if len(resource_title) > 30 else ''}")
        return metadata
    
    async def _extract_description(self) -> Optional[str]:
        """Extract description from the current page."""
        description_selectors = [
            "meta[name='description']",
            ".description",
            ".summary",
            ".content-block-article__summary",
            "p.intro",
            ".intro p",
            "article p:first-of-type"
        ]
        
        for selector in description_selectors:
            if selector.startswith("meta"):
                # Handle meta tags
                meta = await self.page.query_selector(selector)
                if meta:
                    content = await meta.get_attribute("content")
                    if content and content.strip():
                        return content.strip()
            else:
                # Handle regular elements
                elem = await self.page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    if text and text.strip():
                        return text.strip()
        
        return None
    
    async def _determine_content_type(self) -> ContentType:
        """Determine the content type of the current page."""
        url = self.page.url
        html = await self.page.content()
        
        # Check URL and page content for indicators
        if any(video_term in url for video_term in ['/video/', '/watch/', '.mp4', '/iview/']):
            return ContentType.VIDEO
        elif any(audio_term in url for audio_term in ['/audio/', '/podcast/', '.mp3', '/radio/']):
            return ContentType.AUDIO
        elif any(quiz_term in url for quiz_term in ['/quiz/', '/test/', '/assessment/']):
            return ContentType.QUIZ
        elif any(worksheet_term in url for worksheet_term in ['/worksheet/', '/exercise/', '/printable/']):
            return ContentType.WORKSHEET
        elif any(interactive_term in url for interactive_term in ['/interactive/', '/game/', '/simulation/']):
            return ContentType.INTERACTIVE
        elif any(lesson_term in url for lesson_term in ['/lesson/', '/class/', '/course/']):
            return ContentType.LESSON
        elif any(activity_term in url for activity_term in ['/activity/', '/project/', '/lab/']):
            return ContentType.ACTIVITY
        
        # Check for specific elements in the page
        has_video = await self.page.query_selector("video, .video-player, iframe[src*='youtube'], iframe[src*='vimeo']")
        if has_video:
            return ContentType.VIDEO
            
        has_audio = await self.page.query_selector("audio, .audio-player")
        if has_audio:
            return ContentType.AUDIO
            
        has_quiz = await self.page.query_selector(".quiz, .assessment, form[data-quiz]")
        if has_quiz:
            return ContentType.QUIZ
            
        has_interactive = await self.page.query_selector("iframe[src*='interactive'], canvas, .interactive, [data-component-name='Interactive']")
        if has_interactive:
            return ContentType.INTERACTIVE
            
        # Default to article if no specific indicators found
        return ContentType.ARTICLE
    
    async def _extract_topics(self, subject_name: str) -> List[str]:
        """Extract topics from the current page."""
        topics = []
        
        # Look for topic tags
        topic_selectors = [
            ".tag",
            ".topic",
            ".category",
            ".subject",
            "[data-testid='tag']",
            "[data-testid='topic']",
            "meta[name='keywords']"
        ]
        
        for selector in topic_selectors:
            if selector.startswith("meta"):
                # Handle meta tags
                meta = await self.page.query_selector(selector)
                if meta:
                    content = await meta.get_attribute("content")
                    if content:
                        # Split by commas
                        keywords = [k.strip() for k in content.split(",")]
                        topics.extend([k for k in keywords if k])
            else:
                # Handle regular elements
                elems = await self.page.query_selector_all(selector)
                for elem in elems:
                    text = await elem.text_content()
                    if text and text.strip():
                        topics.append(text.strip())
        
        # Clean up and remove duplicates
        unique_topics = list(set(topics))
        
        # Always include the main subject as a topic
        if subject_name not in unique_topics:
            unique_topics.append(subject_name)
        
        return unique_topics
    
    def _determine_difficulty_and_grade(self, title: str, description: str, subject: str) -> Tuple[DifficultyLevel, List[int]]:
        """Determine difficulty level and grade levels from text."""
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
    
    async def _extract_duration(self) -> Optional[int]:
        """Extract duration from the current page."""
        duration_selectors = [
            ".duration",
            ".video-duration",
            ".audio-duration",
            "[data-testid='duration']"
        ]
        
        for selector in duration_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                duration_text = await elem.text_content()
                if duration_text and duration_text.strip():
                    # Try to parse duration
                    return self._parse_duration_text(duration_text.strip())
        
        return None
    
    def _parse_duration_text(self, duration_text: str) -> Optional[int]:
        """Parse duration text to extract minutes."""
        try:
            # Clean up the text
            duration_text = duration_text.strip().lower()
            
            # Check for MM:SS format
            if ":" in duration_text:
                parts = duration_text.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes + (1 if seconds >= 30 else 0)  # Round up for 30+ seconds
                elif len(parts) == 3:  # HH:MM:SS format
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
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing duration text '{duration_text}': {e}")
            return None
    
    def _estimate_duration(self, content_type: ContentType) -> int:
        """Estimate duration based on content type."""
        if content_type == ContentType.VIDEO:
            return 10  # 10 minutes for video
        elif content_type == ContentType.AUDIO:
            return 15  # 15 minutes for audio
        elif content_type == ContentType.INTERACTIVE:
            return 20  # 20 minutes for interactive content
        elif content_type == ContentType.QUIZ:
            return 10  # 10 minutes for quiz
        elif content_type == ContentType.WORKSHEET:
            return 30  # 30 minutes for worksheet
        elif content_type == ContentType.LESSON:
            return 45  # 45 minutes for lesson
        elif content_type == ContentType.ACTIVITY:
            return 30  # 30 minutes for activity
        else:  # Article
            return 15  # 15 minutes for article
    
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
    
    async def _extract_video_content(self) -> Dict[str, Any]:
        """Extract video content from the current page."""
        video_info = {}
        
        # Look for video elements
        video_selectors = [
            "video",
            ".video-player",
            ".media-player",
            "iframe[src*='youtube']",
            "iframe[src*='vimeo']",
            "iframe[src*='iview']",
            "[data-component-name='VideoPlayer']"
        ]
        
        for selector in video_selectors:
            video_elem = await self.page.query_selector(selector)
            if video_elem:
                # For video element
                if selector == "video":
                    src = await video_elem.get_attribute("src")
                    if src:
                        video_info["video_url"] = src
                    
                    poster = await video_elem.get_attribute("poster")
                    if poster:
                        video_info["thumbnail_url"] = poster
                
                # For iframe (YouTube, Vimeo, etc.)
                if selector.startswith("iframe"):
                    src = await video_elem.get_attribute("src")
                    if src:
                        video_info["video_url"] = src
                
                break
        
        # Look for transcript
        transcript_selectors = [
            ".transcript",
            ".video-transcript",
            "[data-testid='transcript']",
            ".closed-captions"
        ]
        
        for selector in transcript_selectors:
            transcript_elem = await self.page.query_selector(selector)
            if transcript_elem:
                transcript = await transcript_elem.text_content()
                if transcript and transcript.strip():
                    video_info["transcription"] = transcript.strip()
                break
        
        return video_info
    
    async def _extract_audio_content(self) -> Dict[str, Any]:
        """Extract audio content from the current page."""
        audio_info = {}
        
        # Look for audio elements
        audio_selectors = [
            "audio",
            ".audio-player",
            "[data-component-name='AudioPlayer']",
            ".podcast-player"
        ]
        
        for selector in audio_selectors:
            audio_elem = await self.page.query_selector(selector)
            if audio_elem:
                # For audio element
                if selector == "audio":
                    src = await audio_elem.get_attribute("src")
                    if src:
                        audio_info["audio_url"] = src
                
                break
        
        # Look for transcript
        transcript_selectors = [
            ".transcript",
            ".audio-transcript",
            "[data-testid='transcript']"
        ]
        
        for selector in transcript_selectors:
            transcript_elem = await self.page.query_selector(selector)
            if transcript_elem:
                transcript = await transcript_elem.text_content()
                if transcript and transcript.strip():
                    audio_info["transcription"] = transcript.strip()
                break
        
        return audio_info
    
    async def _extract_article_text(self) -> str:
        """Extract article text from the current page."""
        # Look for article content
        content_selectors = [
            "article",
            "main",
            ".content-block-article__content",
            ".article__body",
            ".content-main",
            "#content-main",
            ".main-content"
        ]
        
        for selector in content_selectors:
            content_elem = await self.page.query_selector(selector)
            if content_elem:
                # Get all paragraphs
                paragraphs = await content_elem.query_selector_all("p")
                if paragraphs:
                    text_parts = []
                    for p in paragraphs:
                        text = await p.text_content()
                        if text and text.strip():
                            text_parts.append(text.strip())
                    
                    if text_parts:
                        return "\n\n".join(text_parts)
                
                # If no paragraphs found, get all text content
                text = await content_elem.text_content()
                if text and text.strip():
                    return text.strip()
        
        return ""
    
    async def _extract_interactive_content(self) -> Dict[str, Any]:
        """Extract interactive content from the current page."""
        interactive_info = {}
        
        # Check for interactive elements
        interactive_selectors = [
            "iframe",
            ".interactive",
            ".game",
            "canvas",
            "[data-component-name='Interactive']"
        ]
        
        for selector in interactive_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                if selector == "iframe":
                    src = await elem.get_attribute("src")
                    if src:
                        interactive_info["iframe_src"] = src
                
                interactive_info["has_interactive"] = True
                break
        
        # Extract instructions
        instruction_selectors = [
            ".instructions",
            ".description",
            ".how-to-play",
            ".guidelines"
        ]
        
        for selector in instruction_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                instructions = await elem.text_content()
                if instructions and instructions.strip():
                    interactive_info["instructions"] = instructions.strip()
                    break
        
        return interactive_info
    
    async def _extract_quiz_content(self) -> Dict[str, Any]:
        """Extract quiz content from the current page."""
        quiz_info = {}
        
        # Look for quiz elements
        quiz_selectors = [
            ".quiz",
            ".assessment",
            ".questions",
            "form[data-quiz]",
            "[data-component-name='Quiz']"
        ]
        
        for selector in quiz_selectors:
            quiz_elem = await self.page.query_selector(selector)
            if quiz_elem:
                quiz_info["has_quiz"] = True
                
                # Try to extract number of questions
                questions = await quiz_elem.query_selector_all(".question, .quiz-question")
                if questions:
                    quiz_info["question_count"] = len(questions)
                
                break
        
        # Extract instructions
        instruction_selectors = [
            ".quiz-instructions",
            ".quiz-intro",
            ".instructions",
            ".description"
        ]
        
        for selector in instruction_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                instructions = await elem.text_content()
                if instructions and instructions.strip():
                    quiz_info["instructions"] = instructions.strip()
                    break
        
        return quiz_info
    
    async def _extract_author(self) -> Optional[str]:
        """Extract author from the current page."""
        author_selectors = [
            ".author",
            ".byline",
            ".content-block-article__byline",
            "[data-testid='author']",
            "meta[name='author']"
        ]
        
        for selector in author_selectors:
            if selector.startswith("meta"):
                elem = await self.page.query_selector(selector)
                if elem:
                    author = await elem.get_attribute("content")
                    if author and author.strip():
                        return author.strip()
            else:
                elem = await self.page.query_selector(selector)
                if elem:
                    author = await elem.text_content()
                    if author and author.strip():
                        # Remove "By" prefix if present
                        author = author.strip()
                        if author.lower().startswith("by "):
                            author = author[3:].strip()
                        return author
        
        return None
    
    async def process_subject(self, subject_link: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Process a subject: find resources and extract content.
        
        Args:
            subject_link: Dictionary with subject name and URL
            
        Returns:
            List of processed content items
        """
        subject_name = subject_link["name"]
        logger.info(f"Processing subject: {subject_name}")
        
        # Find education resources for this subject
        resources = await self.find_education_resources(subject_link)
        
        if not resources:
            logger.warning(f"No education resources found for {subject_name}")
            return []
        
        # Process each resource
        processed_items = []
        
        for i, resource in enumerate(resources):
            try:
                logger.info(f"Processing resource {i+1}/{len(resources)}: {resource['title'][:30]}{'...' if len(resource['title']) > 30 else ''}")
                
                # Extract content details
                content_details = await self.extract_content_details(resource)
                
                # Process and index content if possible
                if self.content_processor:
                    try:
                        processed_content = await process_and_index_content(resource["url"], content_details)
                        if processed_content:
                            processed_items.append(processed_content)
                            logger.info(f"Successfully processed: {resource['title'][:30]}{'...' if len(resource['title']) > 30 else ''}")
                    except Exception as e:
                        logger.error(f"Error processing content: {e}")
                        # Still save the extracted details even if processing fails
                        processed_items.append(content_details)
                else:
                    # Just save the extracted details
                    processed_items.append(content_details)
                    logger.info(f"Extracted details for: {resource['title'][:30]}{'...' if len(resource['title']) > 30 else ''}")
                
            except Exception as e:
                logger.error(f"Error processing resource: {e}")
        
        # Save all processed items for this subject
        self.save_processed_items_to_json(processed_items, subject_name)
        
        logger.info(f"Processed {len(processed_items)} resources for {subject_name}")
        return processed_items
    
    def save_processed_items_to_json(self, processed_items: List[Dict[str, Any]], subject_name: str):
        """Save processed items to a JSON file."""
        if not processed_items:
            return
            
        # Create a safe filename
        safe_subject = subject_name.replace(" ", "_").replace("/", "_")
        filename = os.path.join(self.resources_dir, f"{safe_subject}_processed.json")
        
        try:
            # Remove embeddings and large HTML content to save space
            items_for_saving = []
            for item in processed_items:
                item_copy = item.copy()
                if 'embedding' in item_copy:
                    del item_copy['embedding']
                if 'content_html' in item_copy and len(item_copy['content_html']) > 500:
                    item_copy['content_html'] = item_copy['content_html'][:500] + "... [truncated]"
                items_for_saving.append(item_copy)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(items_for_saving, f, indent=2)
                
            logger.info(f"Saved {len(processed_items)} processed items to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving processed items to JSON: {e}")
    
    async def create_resource_index(self) -> Dict[str, Any]:
        """
        Create an index of all educational resources by subject.
        
        Returns:
            Dictionary with subjects as keys and resource lists as values
        """
        # Path to the directory containing resource files
        resources_dir = self.resources_dir
        
        # Dictionary to hold the index
        index = {
            "total_resources": 0,
            "subjects": {}
        }
        
        # Look for processed resource files
        processed_files = [f for f in os.listdir(resources_dir) if f.endswith('_processed.json')]
        
        for file in processed_files:
            try:
                # Extract subject name from filename
                subject_name = file.replace('_processed.json', '').replace('_', ' ')
                
                # Read the file
                with open(os.path.join(resources_dir, file), 'r', encoding='utf-8') as f:
                    resources = json.load(f)
                
                # Add to index
                if subject_name not in index["subjects"]:
                    index["subjects"][subject_name] = {
                        "count": 0,
                        "resources": []
                    }
                
                # Add summary of each resource
                for resource in resources:
                    resource_summary = {
                        "id": resource.get("id", ""),
                        "title": resource.get("title", ""),
                        "description": resource.get("description", ""),
                        "url": resource.get("url", ""),
                        "content_type": resource.get("content_type", ""),
                        "difficulty_level": resource.get("difficulty_level", ""),
                        "topics": resource.get("topics", [])
                    }
                    index["subjects"][subject_name]["resources"].append(resource_summary)
                
                # Update counts
                index["subjects"][subject_name]["count"] = len(resources)
                index["total_resources"] += len(resources)
                
            except Exception as e:
                logger.error(f"Error processing file {file}: {e}")
        
        # Save the index to a JSON file
        index_path = os.path.join(resources_dir, "resource_index.json")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
            logger.info(f"Saved resource index to {index_path}")
        except Exception as e:
            logger.error(f"Error saving resource index: {e}")
        
        return index

async def run_scraper(subject_limit=None, headless=True):
    """
    Run the simplified education scraper.
    
    Args:
        subject_limit: Maximum number of subjects to process (None for all)
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary with resource index
    """
    scraper = SimplifiedEducationScraper()
    
    try:
        # Setup browser
        await scraper.setup(headless=headless)
        
        # Get subjects to process
        subjects = SUBJECT_LINKS
        if subject_limit and isinstance(subject_limit, int) and subject_limit > 0:
            subjects = subjects[:subject_limit]
        
        logger.info(f"Starting scraper with {len(subjects)} subjects")
        
        # Process each subject
        all_processed_items = []
        for subject in subjects:
            try:
                processed_items = await scraper.process_subject(subject)
                all_processed_items.extend(processed_items)
                # Add a small delay between subjects
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error processing subject {subject['name']}: {e}")
        
        # Create resource index
        resource_index = await scraper.create_resource_index()
        
        logger.info(f"Scraping completed. Processed {len(all_processed_items)} resources across {len(subjects)} subjects")
        return resource_index
        
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        return {}
        
    finally:
        # Clean up resources
        await scraper.teardown()

if __name__ == "__main__":
    # Run the scraper with a limit of 2 subjects for testing
    asyncio.run(run_scraper(
        subject_limit=2,  # Limit to 2 subjects for testing
        headless=False  # Run with visible browser for debugging
    ))
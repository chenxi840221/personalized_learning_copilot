import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urljoin
from langchain.embeddings import OpenAIEmbeddings

from models.content import Content, ContentType, DifficultyLevel, ContentWithEmbedding
from utils.db_manager import get_db
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ABCEducationScraper:
    def __init__(self):
        self.base_url = "https://www.abc.net.au/education/subjects-and-topics"
        self.subjects = ["english", "mathematics", "science"]
        self.session = None
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            azure_deployment="text-embedding-ada-002",
            openai_api_type="azure",
            openai_api_version=settings.OPENAI_API_VERSION,
            openai_api_base=settings.OPENAI_API_BASE,
            openai_api_key=settings.OPENAI_API_KEY
        )
    
    async def initialize(self):
        """Initialize the HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
    
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
                            
                            # Create content item
                            content_item = {
                                "title": title,
                                "description": description,
                                "content_type": content_type,
                                "subject": subject.capitalize(),
                                "topics": [topic],
                                "url": content_url,
                                "source": "ABC Education",
                                "difficulty_level": difficulty,
                                "grade_level": grade_levels,
                                "duration_minutes": self._estimate_duration(content_type),
                                "keywords": self._extract_keywords(title, description)
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
        
        # Check for explicit difficulty indicators
        if any(word in text for word in ["basic", "beginner", "easy", "introduction", "start"]):
            difficulty = DifficultyLevel.BEGINNER
            grade_levels = [3, 4, 5]
        elif any(word in text for word in ["advanced", "complex", "difficult", "challenging"]):
            difficulty = DifficultyLevel.ADVANCED
            grade_levels = [8, 9, 10]
        else:
            difficulty = DifficultyLevel.INTERMEDIATE
            grade_levels = [6, 7, 8]
        
        # Adjust based on subject
        if subject == "mathematics":
            # Math often has specific grade indicators
            if "algebra" in text or "equation" in text:
                difficulty = DifficultyLevel.INTERMEDIATE
                grade_levels = [7, 8, 9]
            elif "calculus" in text or "trigonometry" in text:
                difficulty = DifficultyLevel.ADVANCED
                grade_levels = [9, 10, 11]
        
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
    
    async def generate_embedding(self, content: Dict[str, Any]) -> List[float]:
        """Generate embedding for content."""
        text = f"{content['title']} {content['description']}"
        embeddings = await self.embeddings.aembed_query(text)
        return embeddings
    
    async def save_to_database(self, contents: List[Dict[str, Any]]):
        """Save scraped content to the database with embeddings."""
        db = await get_db()
        
        for content in contents:
            try:
                # Check if content already exists
                existing_content = await db.contents.find_one({"url": content["url"]})
                if existing_content:
                    logger.info(f"Content already exists: {content['title']}")
                    continue
                
                # Generate embedding
                embedding = await self.generate_embedding(content)
                
                # Create content with embedding
                content_with_embedding = {
                    **content,
                    "embedding": embedding,
                    "embedding_model": "text-embedding-ada-002"
                }
                
                # Save to database
                await db.contents_with_embeddings.insert_one(content_with_embedding)
                
                # Also save without embedding to the regular collection
                await db.contents.insert_one(content)
                
                logger.info(f"Saved content: {content['title']}")
            except Exception as e:
                logger.error(f"Error saving content {content['title']}: {e}")

async def run_scraper():
    """Run the scraper to collect content."""
    scraper = ABCEducationScraper()
    
    try:
        await scraper.initialize()
        contents = await scraper.scrape_all_subjects()
        logger.info(f"Scraped {len(contents)} content items")
        
        await scraper.save_to_database(contents)
        logger.info("Content saved to database")
    finally:
        await scraper.close()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the scraper
    asyncio.run(run_scraper())
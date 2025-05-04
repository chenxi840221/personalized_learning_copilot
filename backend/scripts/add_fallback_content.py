#!/usr/bin/env python3
"""
Script to add fallback content to the database.
This ensures that even if the search service fails, we have some content to show.
"""

import asyncio
import sys
import os
import logging
from pprint import pprint

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define fallback content for each subject
FALLBACK_CONTENT = {
    "Mathematics": [
        {
            "id": "fb-math-001",
            "title": "Introduction to Algebra Concepts",
            "description": "This resource introduces foundational algebra concepts with visual explanations and interactive examples.",
            "content_type": "lesson",
            "difficulty_level": "intermediate",
            "url": "https://www.khanacademy.org/math/algebra",
            "grade_level": [6, 7, 8, 9, 10],
            "keywords": ["algebra", "equations", "variables", "expressions"]
        },
        {
            "id": "fb-math-002",
            "title": "Visual Geometry Learning",
            "description": "An interactive geometry resource with visual demonstrations of shapes, angles, and transformations.",
            "content_type": "interactive",
            "difficulty_level": "beginner",
            "url": "https://www.geogebra.org/geometry",
            "grade_level": [4, 5, 6, 7, 8],
            "keywords": ["geometry", "shapes", "angles", "transformations"]
        }
    ],
    "Science": [
        {
            "id": "fb-science-001",
            "title": "Introduction to Scientific Method",
            "description": "Learn the scientific method through interactive experiments and real-world examples.",
            "content_type": "lesson",
            "difficulty_level": "beginner",
            "url": "https://www.khanacademy.org/science/high-school-biology/hs-biology-foundations/hs-biology-and-the-scientific-method/a/the-science-of-biology",
            "grade_level": [5, 6, 7, 8, 9],
            "keywords": ["scientific method", "experiments", "hypothesis", "research"]
        },
        {
            "id": "fb-science-002",
            "title": "Earth's Systems and Cycles",
            "description": "Explore Earth's major systems and cycles including the water cycle, carbon cycle, and weather patterns.",
            "content_type": "video",
            "difficulty_level": "intermediate",
            "url": "https://www.nationalgeographic.org/encyclopedia/earths-systems/",
            "grade_level": [6, 7, 8, 9, 10],
            "keywords": ["earth science", "water cycle", "weather", "climate"]
        }
    ],
    "English": [
        {
            "id": "fb-english-001",
            "title": "Reading Comprehension Strategies",
            "description": "Learn effective reading comprehension strategies to better understand and analyze texts.",
            "content_type": "lesson",
            "difficulty_level": "intermediate",
            "url": "https://www.readingstrategies.org/comprehension",
            "grade_level": [6, 7, 8, 9, 10],
            "keywords": ["reading", "comprehension", "analysis", "literacy"]
        },
        {
            "id": "fb-english-002",
            "title": "Essay Writing Fundamentals",
            "description": "A comprehensive guide to writing effective essays with structure and clarity.",
            "content_type": "article",
            "difficulty_level": "intermediate",
            "url": "https://owl.purdue.edu/owl/general_writing/academic_writing/essay_writing/index.html",
            "grade_level": [7, 8, 9, 10, 11],
            "keywords": ["writing", "essays", "structure", "composition"]
        }
    ],
    "History": [
        {
            "id": "fb-history-001",
            "title": "Timeline of World History",
            "description": "Interactive timeline of major events in world history with multimedia resources.",
            "content_type": "interactive",
            "difficulty_level": "intermediate",
            "url": "https://www.bbc.co.uk/history/interactive/timelines/",
            "grade_level": [6, 7, 8, 9, 10],
            "keywords": ["world history", "timeline", "civilization", "events"]
        },
        {
            "id": "fb-history-002",
            "title": "Primary Source Analysis",
            "description": "Learn techniques for analyzing and interpreting primary historical sources.",
            "content_type": "lesson",
            "difficulty_level": "advanced",
            "url": "https://www.loc.gov/programs/teachers/primary-source-analysis-tool/",
            "grade_level": [8, 9, 10, 11, 12],
            "keywords": ["primary sources", "historical analysis", "documents", "research"]
        }
    ]
}

def get_fallback_content(subject):
    """Get fallback content for a specific subject or a default if not found."""
    if subject in FALLBACK_CONTENT:
        content_list = FALLBACK_CONTENT[subject]
    else:
        # Use Mathematics as default fallback
        content_list = FALLBACK_CONTENT["Mathematics"]
    
    # Convert dictionaries to Content objects
    contents = []
    for content_dict in content_list:
        content = Content(
            id=content_dict["id"],
            title=content_dict["title"],
            description=content_dict["description"],
            content_type=ContentType(content_dict["content_type"]),
            subject=subject,  # Use the requested subject
            difficulty_level=DifficultyLevel(content_dict["difficulty_level"]),
            url=content_dict["url"],
            grade_level=content_dict["grade_level"],
            keywords=content_dict["keywords"],
            source="Fallback Content"
        )
        contents.append(content)
    
    return contents

# Example of usage
if __name__ == "__main__":
    # Print out some example fallback content
    for subject in FALLBACK_CONTENT:
        contents = get_fallback_content(subject)
        print(f"\n{subject} Fallback Content:")
        for content in contents:
            print(f"  - {content.title} ({content.content_type.value})")
            print(f"    URL: {content.url}")
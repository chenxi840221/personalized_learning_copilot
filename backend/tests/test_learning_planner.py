import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.learning_planner import LearningPlanner, get_learning_planner
from models.user import User, LearningStyle
from models.content import Content, ContentType, DifficultyLevel
from models.learning_plan import ActivityStatus
from tests.run_tests import AsyncioTestCase
from config.settings import Settings

# Initialize settings
settings = Settings()


class TestLearningPlanner(AsyncioTestCase):
    """Test the Learning Planner with mocked OpenAI API."""

    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Create a sample user
        self.user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            grade_level=8,
            subjects_of_interest=["Mathematics", "Science"],
            learning_style=LearningStyle.VISUAL
        )
        
        # Create sample content
        self.content = [
            Content(
                id="content-1",
                title="Introduction to Algebra",
                description="Learn the basics of algebraic expressions",
                content_type=ContentType.VIDEO,
                subject="Mathematics",
                topics=["Algebra"],
                url="https://example.com/algebra",
                source="Test Source",
                difficulty_level=DifficultyLevel.BEGINNER,
                grade_level=[7, 8],
                duration_minutes=20
            ),
            Content(
                id="content-2",
                title="Solving Equations",
                description="How to solve linear equations",
                content_type=ContentType.LESSON,
                subject="Mathematics",
                topics=["Algebra", "Equations"],
                url="https://example.com/equations",
                source="Test Source",
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                grade_level=[8, 9],
                duration_minutes=30
            )
        ]
        
        # Create the planner
        self.planner = LearningPlanner()
        
        # Reset the singleton
        import rag.learning_planner
        rag.learning_planner.learning_planner = None
        
        # Sample learning plan response
        self.sample_plan_json = """{
            "title": "Algebra Fundamentals",
            "description": "A personalized learning plan for algebra fundamentals",
            "subject": "Mathematics",
            "topics": ["Algebra", "Equations"],
            "activities": [
                {
                    "title": "Introduction to Algebra",
                    "description": "Watch the introductory video on algebra",
                    "content_id": "content-1",
                    "duration_minutes": 20,
                    "order": 1
                },
                {
                    "title": "Solving Equations",
                    "description": "Complete the lesson on solving equations",
                    "content_id": "content-2",
                    "duration_minutes": 30,
                    "order": 2
                },
                {
                    "title": "Practice Problems",
                    "description": "Solve the practice problems",
                    "content_id": null,
                    "duration_minutes": 25,
                    "order": 3
                }
            ]
        }"""
    
    @patch('rag.openai_adapter.get_openai_adapter')
    def test_create_learning_plan(self, mock_get_adapter):
        """Test creating a learning plan."""
        # Configure mock
        mock_adapter = AsyncMock()
        mock_chat_response = {
            "choices": [
                {
                    "message": {
                        "content": self.sample_plan_json
                    }
                }
            ]
        }
        mock_adapter.create_chat_completion.return_value = mock_chat_response
        mock_get_adapter.return_value = mock_adapter
        
        # Create a learning plan
        plan = self.run_async(self.planner.create_learning_plan(
            student=self.user,
            subject="Mathematics",
            relevant_content=self.content,
            duration_days=14
        ))
        
        # Assertions
        mock_adapter.create_chat_completion.assert_called_once_with(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an educational AI that creates personalized learning plans."},
                {"role": "user", "content": mock_adapter.create_chat_completion.call_args[1]["messages"][1]["content"]}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        self.assertEqual(plan.title, "Algebra Fundamentals")
        self.assertEqual(plan.subject, "Mathematics")
        self.assertEqual(len(plan.activities), 3)
        self.assertEqual(plan.activities[0].content_id, "content-1")
        self.assertEqual(plan.activities[0].status, ActivityStatus.NOT_STARTED)
        self.assertEqual(plan.status, ActivityStatus.NOT_STARTED)
        self.assertEqual(plan.progress_percentage, 0.0)
    
    @patch('rag.openai_adapter.get_openai_adapter')
    def test_create_learning_plan_with_error(self, mock_get_adapter):
        """Test creating a learning plan with API error."""
        # Configure mock to raise an exception
        mock_adapter = AsyncMock()
        mock_adapter.create_chat_completion.side_effect = Exception("API Error")
        mock_get_adapter.return_value = mock_adapter
        
        # Create a learning plan (should get a fallback plan)
        plan = self.run_async(self.planner.create_learning_plan(
            student=self.user,
            subject="Mathematics",
            relevant_content=self.content,
            duration_days=14
        ))
        
        # Assertions
        mock_adapter.create_chat_completion.assert_called_once_with(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an educational AI that creates personalized learning plans."},
                {"role": "user", "content": mock_adapter.create_chat_completion.call_args[1]["messages"][1]["content"]}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        self.assertEqual(plan.subject, "Mathematics")
        self.assertEqual(len(plan.activities), 0)  # Fallback plan has no activities
    
    @patch('rag.openai_adapter.get_openai_adapter')
    def test_create_advanced_learning_path(self, mock_get_adapter):
        """Test creating an advanced learning path."""
        # Sample learning path response
        sample_path_json = """{
            "title": "Advanced Algebra Path",
            "description": "A comprehensive learning path for mastering algebra",
            "overall_goal": "Develop strong algebraic skills and problem-solving abilities",
            "weeks": [
                {
                    "week_number": 1,
                    "theme": "Foundations of Algebra",
                    "goal": "Understand algebraic expressions and variables",
                    "days": [
                        {
                            "day_number": 1,
                            "activities": [
                                {
                                    "title": "Introduction to Variables",
                                    "description": "Learn about variables and their importance",
                                    "content_id": "content-1",
                                    "type": "video",
                                    "duration_minutes": 20
                                }
                            ]
                        }
                    ],
                    "skills": ["Understanding variables"],
                    "assessment": "Quiz on variables"
                }
            ]
        }"""
        
        # Configure mock
        mock_adapter = AsyncMock()
        mock_chat_response = {
            "choices": [
                {
                    "message": {
                        "content": sample_path_json
                    }
                }
            ]
        }
        mock_adapter.create_chat_completion.return_value = mock_chat_response
        mock_get_adapter.return_value = mock_adapter
        
        # Create a learning path
        path = self.run_async(self.planner.create_advanced_learning_path(
            student=self.user,
            subject="Mathematics",
            relevant_content=self.content,
            duration_weeks=4
        ))
        
        # Assertions
        mock_adapter.create_chat_completion.assert_called_once_with(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an educational AI that creates comprehensive learning paths."},
                {"role": "user", "content": mock_adapter.create_chat_completion.call_args[1]["messages"][1]["content"]}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        self.assertEqual(path["title"], "Advanced Algebra Path")
        self.assertEqual(path["subject"], "Mathematics")
        self.assertEqual(path["overall_goal"], "Develop strong algebraic skills and problem-solving abilities")
        self.assertEqual(len(path["weeks"]), 1)
        self.assertEqual(path["weeks"][0]["theme"], "Foundations of Algebra")
        self.assertIn("student_id", path)
        self.assertIn("created_at", path)
    
    async def test_adapt_plan_for_performance(self):
        """Test adapting a plan based on performance metrics."""
        # This is a more complex test that would require mocking the database
        # For now, we'll implement a simplified version
        pass
    
    @patch('rag.learning_planner.LearningPlanner')
    def test_get_learning_planner(self, mock_planner_class):
        """Test getting the learning planner singleton."""
        # Configure mock
        mock_instance = MagicMock()
        mock_planner_class.return_value = mock_instance
        
        # Call function twice to verify singleton behavior
        planner1 = self.run_async(get_learning_planner())
        planner2 = self.run_async(get_learning_planner())
        
        # Assertions
        mock_planner_class.assert_called_once()  # Constructor should be called only once
        self.assertEqual(planner1, planner2)  # Should return the same instance


if __name__ == "__main__":
    unittest.main()
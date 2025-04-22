import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cognitive_services import (
    format_cognitive_endpoint,
    validate_cognitive_key,
    get_service_specific_endpoint
)


class TestCognitiveServices(unittest.TestCase):
    """Test the Cognitive Services utility functions."""

    def test_format_cognitive_endpoint(self):
        """Test formatting cognitive service endpoints."""
        # Test with trailing slash in base endpoint
        self.assertEqual(
            format_cognitive_endpoint("https://example.com/", "path"),
            "https://example.com/path"
        )
        
        # Test without trailing slash in base endpoint
        self.assertEqual(
            format_cognitive_endpoint("https://example.com", "path"),
            "https://example.com/path"
        )
        
        # Test with leading slash in service path
        self.assertEqual(
            format_cognitive_endpoint("https://example.com", "/path"),
            "https://example.com/path"
        )
        
        # Test with both trailing and leading slashes
        self.assertEqual(
            format_cognitive_endpoint("https://example.com/", "/path"),
            "https://example.com/path"
        )
        
        # Test with empty service path
        self.assertEqual(
            format_cognitive_endpoint("https://example.com/", ""),
            "https://example.com/"
        )
    
    def test_validate_cognitive_key(self):
        """Test validation of cognitive service keys."""
        # Test valid hexadecimal key (32 characters)
        self.assertTrue(validate_cognitive_key("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"))
        
        # Test valid JWT-like key
        self.assertTrue(validate_cognitive_key("abcdef1234567890.abcdefghijklmnopqrstuvwxyz.1234567890"))
        
        # Test invalid key (too short)
        self.assertFalse(validate_cognitive_key("a1b2c3"))
        
        # Test invalid key (not a string)
        with self.assertRaises(AttributeError):
            validate_cognitive_key(123456)
    
    def test_get_service_specific_endpoint(self):
        """Test getting service-specific endpoints."""
        base_endpoint = "https://example.cognitiveservices.azure.com"
        
        # Test OpenAI endpoint
        self.assertEqual(
            get_service_specific_endpoint(base_endpoint, "openai"),
            "https://example.cognitiveservices.azure.com/openai"
        )
        
        # Test Form Recognizer endpoint
        self.assertEqual(
            get_service_specific_endpoint(base_endpoint, "formrecognizer"),
            "https://example.cognitiveservices.azure.com/formrecognizer/documentAnalysis"
        )
        
        # Test Text Analytics endpoint
        self.assertEqual(
            get_service_specific_endpoint(base_endpoint, "textanalytics"),
            "https://example.cognitiveservices.azure.com/text/analytics/v3.1"
        )
        
        # Test Computer Vision endpoint
        self.assertEqual(
            get_service_specific_endpoint(base_endpoint, "computervision"),
            "https://example.cognitiveservices.azure.com/vision/v3.2"
        )
        
        # Test unknown service (should use as-is)
        self.assertEqual(
            get_service_specific_endpoint(base_endpoint, "unknown-service"),
            "https://example.cognitiveservices.azure.com/unknown-service"
        )
        
        # Test with API version
        self.assertEqual(
            get_service_specific_endpoint(base_endpoint, "openai", "2023-05-15"),
            "https://example.cognitiveservices.azure.com/openai?api-version=2023-05-15"
        )


if __name__ == "__main__":
    unittest.main()
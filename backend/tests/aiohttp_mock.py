
class MockResponse:
    """Mock aiohttp ClientResponse object with proper async methods."""
    
    def __init__(self, text="", status=200, json_data=None, content=None):
        self.text_content = text
        self.status = status
        self._json = json_data
        self._content = content if content is not None else text.encode('utf-8')

    async def text(self):
        """Return text content asynchronously."""
        return self.text_content
        
    async def json(self):
        """Return JSON data asynchronously."""
        return self._json
        
    async def read(self):
        """Return raw content asynchronously."""
        return self._content
        
    async def __aenter__(self):
        """Support async context manager protocol."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager protocol."""
        pass
        
    def raise_for_status(self):
        """Mock raise_for_status method."""
        if self.status >= 400:
            raise Exception(f"HTTP Error {self.status}")

class MockClientSession:
    """Mock aiohttp ClientSession with proper async context manager support."""
    
    def __init__(self, responses=None):
        """Initialize with optional predefined responses."""
        self.responses = responses or {}
        self.calls = []
        self.closed = False
        
    async def __aenter__(self):
        """Support async context manager protocol."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager protocol."""
        self.closed = True
    
    async def get(self, url, **kwargs):
        """Mock get method that returns predefined responses or default response."""
        self.calls.append(('get', url, kwargs))
        
        # Return predefined response if available
        if url in self.responses:
            if callable(self.responses[url]):
                return self.responses[url]()
            return self.responses[url]
            
        # Default response
        if "default" in self.responses:
            return self.responses["default"]
            
        # Fall back to generic response
        return MockResponse(text="<html><body>Default mock response</body></html>")
    
    async def post(self, url, **kwargs):
        """Mock post method."""
        self.calls.append(('post', url, kwargs))
        
        # Return predefined response if available
        if url in self.responses:
            if callable(self.responses[url]):
                return self.responses[url]()
            return self.responses[url]
            
        # Default response
        if "default" in self.responses:
            return self.responses["default"]
            
        # Fall back to generic response
        return MockResponse(json_data={"status": "success"})
    
    async def close(self):
        """Mock close method."""
        self.closed = True

def patch_aiohttp_session(responses=None):
    """
    Create a patch for aiohttp.ClientSession.
    
    Args:
        responses: Dictionary mapping URLs to MockResponse objects or callables returning MockResponse
        
    Returns:
        Patch object that can be used as decorator or context manager
    """
    from unittest.mock import patch
    session = MockClientSession(responses)
    
    # Return a patch that replaces aiohttp.ClientSession with our mock
    return patch('aiohttp.ClientSession', return_value=session)

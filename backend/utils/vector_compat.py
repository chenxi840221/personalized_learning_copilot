# utils/vector_compat.py
"""
Compatibility module for Azure Search Vector class.
This module provides the Vector class for different versions of the Azure Search SDK.
"""

try:
    # Try to import Vector from azure.search.documents.models
    from azure.search.documents.models import Vector
    USING_SDK_VERSION = "Standard"
except ImportError:
    try:
        # Try to import from beta package
        from azure.search.documents.aio._search_client import Vector
        USING_SDK_VERSION = "Beta-aio"
    except ImportError:
        try:
            # Try another possible location
            from azure.search.documents._search_client import Vector
            USING_SDK_VERSION = "Beta-sync"
        except ImportError:
            # Define our own Vector class if none is available
            class Vector:
                """
                Vector class for Azure Search vector search.
                This is a compatibility implementation for when the SDK doesn't provide it.
                """
                def __init__(self, value, k=None, fields=None, exhaustive=None):
                    self.value = value
                    self.k = k
                    self.fields = fields
                    self.exhaustive = exhaustive
                
                def __repr__(self):
                    return (f"Vector(value=[...], k={self.k}, "
                            f"fields={self.fields}, exhaustive={self.exhaustive})")
            
            USING_SDK_VERSION = "Compatibility"

print(f"Using Azure Search Vector class from: {USING_SDK_VERSION}")
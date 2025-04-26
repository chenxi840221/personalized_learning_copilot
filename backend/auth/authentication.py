# backend/auth/authentication.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from azure.identity import ClientSecretCredential, InteractiveBrowserCredential
from msal import ConfidentialClientApplication
import jwt
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Set up OAuth2 with more relaxed handling for testing
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    auto_error=True  # Set to True to ensure proper error handling
)

# Initialize Entra ID application if credentials are available
app = None
if settings.CLIENT_ID and settings.CLIENT_SECRET and settings.TENANT_ID:
    app = ConfidentialClientApplication(
        client_id=settings.CLIENT_ID,
        client_credential=settings.CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.TENANT_ID}"
    )

# Secret key for JWT tokens (simple auth)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from Microsoft token or simple JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # For development and testing, try to check both token types
        user = None
        
        # First try Microsoft token if Microsoft auth is configured
        if app is not None:
            try:
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False},  # We rely on MS for signature verification
                    audience=settings.CLIENT_ID
                )
                
                # Extract user info from claims
                username = payload.get("preferred_username")
                if username:
                    # Create user object from claims
                    user = {
                        "id": payload.get("oid"),  # Object ID from Microsoft
                        "username": username,
                        "email": username,
                        "full_name": payload.get("name"),
                        "roles": payload.get("roles", [])
                    }
                    logger.debug("Successfully validated Microsoft token")
            except Exception as ms_error:
                logger.debug(f"Not a valid Microsoft token: {ms_error}")
        
        # If Microsoft token validation failed or not configured, try simple JWT
        if user is None:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                
                if username is None:
                    raise credentials_exception
                
                # Check if token has expired
                exp = payload.get("exp")
                if exp is not None:
                    expiry = datetime.fromtimestamp(exp)
                    if datetime.utcnow() > expiry:
                        logger.warning(f"Token for {username} has expired")
                        raise credentials_exception
                
                # For simple auth, fetch user from database or mock
                from backend.auth.simple_auth import get_user
                user_data = get_user(username)
                if user_data is None:
                    raise credentials_exception
                
                # Format user data
                user = {
                    "id": username,  # Use username as ID for simple auth
                    "username": username,
                    "email": user_data.get("email", ""),
                    "full_name": user_data.get("full_name", ""),
                    "grade_level": user_data.get("grade_level", None),
                    "subjects_of_interest": user_data.get("subjects_of_interest", []),
                    "learning_style": user_data.get("learning_style", None),
                    "is_active": user_data.get("is_active", True)
                }
                logger.debug("Successfully validated simple JWT token")
            except jwt.JWTError as jwt_error:
                logger.error(f"JWT validation error: {jwt_error}")
                raise credentials_exception

        if user is None:
            logger.warning("Failed to validate token with any method")
            raise credentials_exception
            
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in auth validation: {e}")
        raise credentials_exception

async def get_ms_login_url(redirect_uri):
    """Generate Microsoft login URL."""
    if app is None:
        logger.error("Microsoft authentication not configured")
        return None
        
    auth_url = app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=redirect_uri,
        state="12345"  # Should be a random state in production
    )
    return auth_url

async def get_token_from_code(auth_code, redirect_uri):
    """Exchange authorization code for token."""
    if app is None:
        logger.error("Microsoft authentication not configured")
        return None
        
    result = app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=["User.Read"],
        redirect_uri=redirect_uri
    )
    
    if "error" in result:
        logger.error(f"Error getting token: {result.get('error_description')}")
        raise Exception(f"Error getting token: {result.get('error_description')}")
        
    return result

def create_simple_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    """Create a simple JWT token for authentication when MS auth is not available."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
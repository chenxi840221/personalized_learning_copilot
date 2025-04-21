from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import httpx
import json
from urllib.parse import urlencode

from models.user import User, UserInDB, TokenData
from utils.db_manager import get_db
from config.settings import Settings

# Initialize settings
settings = Settings()

# Configure password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure OAuth2 with authorization code flow
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://login.microsoftonline.com/{settings.TENANT_ID}/oauth2/v2.0/authorize",
    tokenUrl=f"https://login.microsoftonline.com/{settings.TENANT_ID}/oauth2/v2.0/token",
    scopes={
        f"api://{settings.CLIENT_ID}/access_as_user": "Access as a user",
        "openid": "OpenID Connect",
        "profile": "Profile information",
        "email": "Email address"
    },
    auto_error=True
)

# Configure logger
logger = logging.getLogger(__name__)

def verify_password(plain_password, hashed_password):
    """Verify password against hashed version."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password."""
    return pwd_context.hash(password)

async def get_user(username: str):
    """Get user from database."""
    db = await get_db()
    user_dict = await db.users.find_one({"username": username})
    if user_dict:
        return UserInDB(**user_dict)
    return None

async def get_user_by_email(email: str):
    """Get user by email from database."""
    db = await get_db()
    user_dict = await db.users.find_one({"email": email})
    if user_dict:
        return UserInDB(**user_dict)
    return None

async def authenticate_user_password(username: str, password: str):
    """Authenticate user by username and password (legacy method)."""
    user = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_microsoft_token(code: str, redirect_uri: str) -> Dict[str, Any]:
    """Exchange authorization code for Microsoft token."""
    token_url = f"https://login.microsoftonline.com/{settings.TENANT_ID}/oauth2/v2.0/token"
    
    # Prepare request data
    data = {
        "client_id": settings.CLIENT_ID,
        "client_secret": settings.CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": "openid profile email api://YOUR_API_CLIENT_ID/access_as_user"
    }
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        
        if response.status_code != 200:
            logger.error(f"Error getting token: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate Microsoft credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return response.json()

async def get_microsoft_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Microsoft Graph API."""
    graph_url = "https://graph.microsoft.com/v1.0/me"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            graph_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            logger.error(f"Error getting user info: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not retrieve user information",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return response.json()

async def verify_microsoft_token(token: str) -> Dict[str, Any]:
    """Verify Microsoft JWT token and return claims."""
    try:
        # Get Microsoft OpenID Connect configuration
        async with httpx.AsyncClient() as client:
            oidc_config_response = await client.get(
                f"https://login.microsoftonline.com/{settings.TENANT_ID}/v2.0/.well-known/openid-configuration"
            )
            oidc_config = oidc_config_response.json()
        
        # Get JWKS (JSON Web Key Set)
        async with httpx.AsyncClient() as client:
            jwks_response = await client.get(oidc_config["jwks_uri"])
            jwks = jwks_response.json()
        
        # Decode and verify token
        header = jwt.get_unverified_header(token)
        
        # Find the key used to sign the token
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not find appropriate key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.CLIENT_ID,
            issuer=f"https://login.microsoftonline.com/{settings.TENANT_ID}/v2.0"
        )
        
        return payload
        
    except JWTError as e:
        logger.error(f"Error verifying Microsoft token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Microsoft token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def create_user_from_microsoft(user_info: Dict[str, Any]) -> User:
    """Create or update user based on Microsoft user info."""
    db = await get_db()
    
    # Try to find user by email
    email = user_info.get("mail") or user_info.get("userPrincipalName")
    existing_user = await get_user_by_email(email)
    
    if existing_user:
        # Update user info if needed
        update_data = {}
        if user_info.get("displayName") and user_info["displayName"] != existing_user.full_name:
            update_data["full_name"] = user_info["displayName"]
        
        if update_data:
            await db.users.update_one(
                {"_id": existing_user.id},
                {"$set": update_data, "$currentDate": {"updated_at": True}}
            )
            # Refresh user data
            user_dict = await db.users.find_one({"_id": existing_user.id})
            return User(**user_dict)
        
        return existing_user
    
    # Create new user
    new_user = {
        "username": email.split("@")[0],  # Use part before @ as username
        "email": email,
        "full_name": user_info.get("displayName", ""),
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert new user
    result = await db.users.insert_one(new_user)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    return User(**created_user)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token."""
    try:
        # Verify the token with Microsoft
        payload = await verify_microsoft_token(token)
        
        # Extract user information
        username: str = payload.get("preferred_username", "").split("@")[0]
        email: str = payload.get("preferred_username") or payload.get("email")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials - email missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(username=username)
    except JWTError:
        logger.error("JWT error when decoding token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database or create if not exists
    user = await get_user_by_email(email)
    
    if user is None:
        # Fetch more user info from Microsoft Graph
        try:
            async with httpx.AsyncClient() as client:
                graph_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                user_info = graph_response.json()
                
                # Create user based on Microsoft info
                user = await create_user_from_microsoft(user_info)
        except Exception as e:
            logger.error(f"Error creating user from Microsoft info: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to create user profile",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user
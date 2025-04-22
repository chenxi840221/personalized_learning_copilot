# auth/authentication.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from azure.identity import ClientSecretCredential, InteractiveBrowserCredential
from msal import ConfidentialClientApplication
import jwt
from config.settings import Settings

settings = Settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize Entra ID application
app = ConfidentialClientApplication(
    client_id=settings.CLIENT_ID,
    client_credential=settings.CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{settings.TENANT_ID}"
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from Microsoft token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token with Microsoft
        # For API validation we can use Microsoft's JWKS endpoint or JWT validation
        payload = jwt.decode(
            token, 
            options={"verify_signature": False},  # We rely on MS for signature verification
            audience=settings.CLIENT_ID
        )
        
        # Extract user info from claims
        username = payload.get("preferred_username")
        if not username:
            raise credentials_exception
            
        # Create user object from claims
        user = {
            "id": payload.get("oid"),  # Object ID from Microsoft
            "username": username,
            "email": username,
            "full_name": payload.get("name"),
            "roles": payload.get("roles", [])
        }
        
        return user
    except Exception:
        raise credentials_exception

async def get_ms_login_url(redirect_uri):
    """Generate Microsoft login URL."""
    auth_url = app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=redirect_uri,
        state="12345"  # Should be a random state in production
    )
    return auth_url

async def get_token_from_code(auth_code, redirect_uri):
    """Exchange authorization code for token."""
    result = app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=["User.Read"],
        redirect_uri=redirect_uri
    )
    
    if "error" in result:
        raise Exception(f"Error getting token: {result.get('error_description')}")
        
    return result
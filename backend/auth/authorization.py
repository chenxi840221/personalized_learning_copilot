# Authorization Module (authorization.py)
# ./personalized_learning_copilot/backend/auth/authorization.py

from fastapi import Depends, HTTPException, status
from typing import List, Optional, Dict, Any, Callable
from enum import Enum

from models.user import User
from auth.authentication import get_current_user

class Role(str, Enum):
    """User roles for authorization purposes."""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class Permission(str, Enum):
    """Permissions for resource access control."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

# Role-based permissions mapping
ROLE_PERMISSIONS = {
    Role.STUDENT: [Permission.READ],
    Role.TEACHER: [Permission.READ, Permission.WRITE],
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
}

async def check_permission(
    user: User, 
    required_permission: Permission
) -> bool:
    """
    Check if a user has the required permission.
    
    Args:
        user: The user to check permissions for
        required_permission: The permission required
        
    Returns:
        True if user has permission, False otherwise
    """
    # Default role for MVP: all users are students
    # In a full implementation, the user object would have a role field
    user_role = getattr(user, "role", Role.STUDENT)
    
    # Get permissions for the user's role
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])
    
    # Admin role has all permissions
    if user_role == Role.ADMIN:
        return True
    
    # Check if the user has the required permission
    return required_permission in user_permissions

def require_permission(required_permission: Permission):
    """
    Dependency for requiring a specific permission.
    
    Args:
        required_permission: The permission required to access the endpoint
        
    Returns:
        Dependency function that checks user permissions
    """
    async def permission_dependency(current_user: User = Depends(get_current_user)):
        has_permission = await check_permission(current_user, required_permission)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to perform this action",
            )
        
        return current_user
    
    return permission_dependency

# Convenience dependencies for common permission checks
require_read = require_permission(Permission.READ)
require_write = require_permission(Permission.WRITE)
require_delete = require_permission(Permission.DELETE)
require_admin = require_permission(Permission.ADMIN)

# Resource owner check
async def check_resource_owner(
    resource_owner_id: Any,
    current_user: User,
    admin_override: bool = True
) -> bool:
    """
    Check if the current user is the owner of a resource.
    
    Args:
        resource_owner_id: ID of the resource owner
        current_user: The current authenticated user
        admin_override: Whether admin users can access regardless of ownership
        
    Returns:
        True if user is the owner or admin with override, False otherwise
    """
    # Convert IDs to strings for comparison
    owner_id = str(resource_owner_id)
    user_id = str(current_user.id)
    
    # Check if user is the owner
    is_owner = owner_id == user_id
    
    # Admin override if enabled
    if admin_override and hasattr(current_user, "role") and current_user.role == Role.ADMIN:
        return True
    
    return is_owner

def require_resource_owner(get_owner_id: Callable, admin_override: bool = True):
    """
    Dependency for requiring resource ownership.
    
    Args:
        get_owner_id: Function that extracts the owner ID from the request
        admin_override: Whether admin users can access regardless of ownership
        
    Returns:
        Dependency function that checks resource ownership
    """
    async def ownership_dependency(current_user: User = Depends(get_current_user)):
        owner_id = await get_owner_id()
        is_owner = await check_resource_owner(owner_id, current_user, admin_override)
        
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource",
            )
        
        return current_user
    
    return ownership_dependency
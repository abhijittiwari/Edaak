"""
Admin routes for user and system management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List

from app.auth.jwt import JWTService
from app.services.admin_service import AdminService
from app.models.user import User

# Create router
admin_router = APIRouter()

# Security
security = HTTPBearer()


# Pydantic models
class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False
    quota_mb: Optional[int] = None


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_admin: bool
    status: str
    auth_provider: str
    last_login: Optional[str]
    created_at: str


class SystemStatsResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_mailboxes: int
    total_emails: int
    total_storage_mb: int
    timestamp: str


# Dependency to get current admin user
async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated admin user"""
    try:
        payload = JWTService.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = int(payload.get("sub"))
        user = AdminService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Admin routes
@admin_router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(get_current_admin)
):
    """Get all users with pagination"""
    users = AdminService.get_all_users(skip=skip, limit=limit)
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_admin=user.is_admin,
            status=user.status,
            auth_provider=user.auth_provider,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@admin_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin)
):
    """Get a specific user"""
    user = AdminService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_admin=user.is_admin,
        status=user.status,
        auth_provider=user.auth_provider,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat()
    )


@admin_router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_admin: User = Depends(get_current_admin)
):
    """Create a new user"""
    user = AdminService.create_user(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name,
        is_admin=request.is_admin,
        quota_mb=request.quota_mb
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_admin=user.is_admin,
        status=user.status,
        auth_provider=user.auth_provider,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat()
    )


@admin_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_admin: User = Depends(get_current_admin)
):
    """Update a user"""
    success = AdminService.update_user(
        user_id=user_id,
        email=request.email,
        username=request.username,
        full_name=request.full_name,
        is_admin=request.is_admin,
        status=request.status
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or update failed"
        )
    
    user = AdminService.get_user_by_id(user_id)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_admin=user.is_admin,
        status=user.status,
        auth_provider=user.auth_provider,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat()
    )


@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin)
):
    """Delete a user"""
    success = AdminService.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete user"
        )
    
    return {"message": "User deleted successfully"}


@admin_router.post("/users/{user_id}/quota")
async def set_user_quota(
    user_id: int,
    quota_mb: int,
    current_admin: User = Depends(get_current_admin)
):
    """Set mailbox quota for a user"""
    success = AdminService.set_user_quota(user_id, quota_mb)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to set user quota"
        )
    
    return {"message": f"Quota set to {quota_mb}MB"}


@admin_router.get("/users/{user_id}/quota")
async def get_user_quota(
    user_id: int,
    current_admin: User = Depends(get_current_admin)
):
    """Get mailbox quota for a user"""
    quota = AdminService.get_user_quota(user_id)
    
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"quota_mb": quota}


@admin_router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(current_admin: User = Depends(get_current_admin)):
    """Get system statistics"""
    stats = AdminService.get_system_stats()
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system statistics"
        )
    
    return SystemStatsResponse(**stats)


@admin_router.get("/users/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    current_admin: User = Depends(get_current_admin)
):
    """Get statistics for a specific user"""
    stats = AdminService.get_user_stats(user_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return stats


@admin_router.get("/users/search/{query}")
async def search_users(
    query: str,
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin)
):
    """Search users"""
    users = AdminService.search_users(query, skip=skip, limit=limit)
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_admin=user.is_admin,
            status=user.status,
            auth_provider=user.auth_provider,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@admin_router.post("/users/{user_id}/lock")
async def lock_user(
    user_id: int,
    lock_duration_minutes: int = 30,
    current_admin: User = Depends(get_current_admin)
):
    """Lock a user account"""
    success = AdminService.lock_user(user_id, lock_duration_minutes)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to lock user account"
        )
    
    return {"message": f"User account locked for {lock_duration_minutes} minutes"}


@admin_router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin)
):
    """Unlock a user account"""
    success = AdminService.unlock_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to unlock user account"
        )
    
    return {"message": "User account unlocked"} 
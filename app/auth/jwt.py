"""
JWT token management for authentication
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class JWTService:
    """JWT service for token management"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
    
    @staticmethod
    def create_user_token(user: User) -> str:
        """Create JWT token for user"""
        data = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "is_admin": user.is_admin,
            "is_superuser": user.is_superuser,
            "auth_provider": user.auth_provider
        }
        return JWTService.create_access_token(data)
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """Get user from JWT token"""
        payload = JWTService.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Here you would typically query the database to get the user
        # For now, we'll return a mock user object
        # In a real implementation, you'd use: db.query(User).filter(User.id == user_id).first()
        return None 
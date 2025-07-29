"""
Authentication service for local user management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserStatus
from app.auth.jwt import JWTService

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    async def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate a user with username/email and password"""
        db = SessionLocal()
        try:
            # Try to find user by username or email
            user = db.query(User).filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if not user:
                return None
            
            # Check if user is active
            if user.status != UserStatus.ACTIVE:
                logger.warning(f"Login attempt for inactive user: {username}")
                return None
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                logger.warning(f"Login attempt for locked account: {username}")
                return None
            
            # Verify password
            if not AuthService.verify_password(password, user.password_hash):
                # Increment failed login attempts
                user.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                    logger.warning(f"Account locked due to failed login attempts: {username}")
                
                db.commit()
                return None
            
            # Reset failed login attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Access all user attributes while session is active to avoid DetachedInstanceError
            user_data = {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'is_admin': user.is_admin,
                'is_superuser': user.is_superuser,
                'auth_provider': user.auth_provider,
                'status': user.status,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
                'last_login': user.last_login
            }
            
            # Create a new User object with the data (not attached to session)
            detached_user = User(
                id=user_data['id'],
                email=user_data['email'],
                username=user_data['username'],
                is_admin=user_data['is_admin'],
                is_superuser=user_data['is_superuser'],
                auth_provider=user_data['auth_provider'],
                status=user_data['status'],
                created_at=user_data['created_at'],
                updated_at=user_data['updated_at'],
                last_login=user_data['last_login']
            )
            
            return detached_user
            
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def create_user(
        email: str,
        username: str,
        password: str,
        full_name: str = None,
        is_admin: bool = False
    ) -> Optional[User]:
        """Create a new user"""
        db = SessionLocal()
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.email == email) | (User.username == username)
            ).first()
            
            if existing_user:
                logger.warning(f"User already exists: {email} or {username}")
                return None
            
            # Hash password
            hashed_password = AuthService.get_password_hash(password)
            
            # Create user
            user = User(
                email=email,
                username=username,
                password_hash=hashed_password,
                full_name=full_name,
                is_admin=is_admin,
                status=UserStatus.ACTIVE,
                auth_provider="local"
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Created new user: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    @staticmethod
    def update_user_password(user_id: int, new_password: str) -> bool:
        """Update user password"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.password_hash = AuthService.get_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Updated password for user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def can_send_from(user_id: int, email_address: str) -> bool:
        """Check if user can send from the given email address"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # User can only send from their own email address
            return user.email.lower() == email_address.lower()
            
        except Exception as e:
            logger.error(f"Error checking send permission: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def is_local_address(email_address: str) -> bool:
        """Check if email address belongs to a local user"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email_address).first()
            return user is not None
            
        except Exception as e:
            logger.error(f"Error checking local address: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email address"""
        db = SessionLocal()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID"""
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    
    @staticmethod
    def create_access_token(user: User) -> str:
        """Create JWT access token for user"""
        return JWTService.create_user_token(user)
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        from app.core.config import settings
        
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"
        
        if settings.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if settings.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        if settings.REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong" 
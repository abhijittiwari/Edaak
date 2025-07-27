"""
Admin service for user and system management
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserStatus
from app.models.mailbox import Mailbox
from app.services.auth_service import AuthService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AdminService:
    """Admin service for system management"""
    
    @staticmethod
    async def create_default_admin():
        """Create default admin user if it doesn't exist"""
        db = SessionLocal()
        try:
            # Check if admin already exists
            admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
            if admin:
                logger.info("Default admin user already exists")
                return admin
            
            # Create default admin
            admin = AuthService.create_user(
                email=settings.ADMIN_EMAIL,
                username="admin",
                password=settings.ADMIN_PASSWORD,
                full_name="System Administrator",
                is_admin=True
            )
            
            if admin:
                logger.info("Default admin user created successfully")
                return admin
            else:
                logger.error("Failed to create default admin user")
                return None
                
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def get_all_users(skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        db = SessionLocal()
        try:
            return db.query(User).offset(skip).limit(limit).all()
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
    def create_user(
        email: str,
        username: str,
        password: str,
        full_name: str = None,
        is_admin: bool = False,
        quota_mb: int = None
    ) -> Optional[User]:
        """Create a new user"""
        try:
            # Create user
            user = AuthService.create_user(
                email=email,
                username=username,
                password=password,
                full_name=full_name,
                is_admin=is_admin
            )
            
            if user and quota_mb:
                # Set custom quota
                AdminService.set_user_quota(user.id, quota_mb)
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            return None
    
    @staticmethod
    def update_user(
        user_id: int,
        email: str = None,
        username: str = None,
        full_name: str = None,
        is_admin: bool = None,
        status: str = None
    ) -> bool:
        """Update user information"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if email is not None:
                user.email = email
            if username is not None:
                user.username = username
            if full_name is not None:
                user.full_name = full_name
            if is_admin is not None:
                user.is_admin = is_admin
            if status is not None:
                user.status = status
            
            user.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Updated user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete a user"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Don't allow deletion of the last admin
            if user.is_admin:
                admin_count = db.query(User).filter(User.is_admin == True).count()
                if admin_count <= 1:
                    logger.warning("Cannot delete the last admin user")
                    return False
            
            db.delete(user)
            db.commit()
            
            logger.info(f"Deleted user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def set_user_quota(user_id: int, quota_mb: int) -> bool:
        """Set mailbox quota for a user"""
        db = SessionLocal()
        try:
            mailboxes = db.query(Mailbox).filter(Mailbox.user_id == user_id).all()
            
            for mailbox in mailboxes:
                mailbox.quota_mb = quota_mb
            
            db.commit()
            
            logger.info(f"Set quota {quota_mb}MB for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting quota for user {user_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_user_quota(user_id: int) -> Optional[int]:
        """Get mailbox quota for a user"""
        db = SessionLocal()
        try:
            mailbox = db.query(Mailbox).filter(Mailbox.user_id == user_id).first()
            return mailbox.quota_mb if mailbox else None
        finally:
            db.close()
    
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Get system statistics"""
        db = SessionLocal()
        try:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
            admin_users = db.query(User).filter(User.is_admin == True).count()
            
            total_mailboxes = db.query(Mailbox).count()
            total_emails = db.query(User).count()  # This should be Email model count
            
            # Calculate total storage used
            total_storage_mb = db.query(Mailbox.used_storage_mb).scalar() or 0
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "admin_users": admin_users,
                "total_mailboxes": total_mailboxes,
                "total_emails": total_emails,
                "total_storage_mb": total_storage_mb,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            mailboxes = db.query(Mailbox).filter(Mailbox.user_id == user_id).all()
            total_mailboxes = len(mailboxes)
            total_storage_mb = sum(mb.used_storage_mb for mb in mailboxes)
            total_quota_mb = sum(mb.quota_mb for mb in mailboxes)
            
            return {
                "user_id": user_id,
                "email": user.email,
                "username": user.username,
                "status": user.status,
                "is_admin": user.is_admin,
                "total_mailboxes": total_mailboxes,
                "total_storage_mb": total_storage_mb,
                "total_quota_mb": total_quota_mb,
                "storage_usage_percent": (total_storage_mb / total_quota_mb * 100) if total_quota_mb > 0 else 0,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def search_users(query: str, skip: int = 0, limit: int = 50) -> List[User]:
        """Search users by email, username, or full name"""
        db = SessionLocal()
        try:
            return db.query(User).filter(
                (User.email.ilike(f"%{query}%")) |
                (User.username.ilike(f"%{query}%")) |
                (User.full_name.ilike(f"%{query}%"))
            ).offset(skip).limit(limit).all()
        finally:
            db.close()
    
    @staticmethod
    def lock_user(user_id: int, lock_duration_minutes: int = 30) -> bool:
        """Lock a user account"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.locked_until = datetime.utcnow() + timedelta(minutes=lock_duration_minutes)
            db.commit()
            
            logger.info(f"Locked user account: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error locking user {user_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def unlock_user(user_id: int) -> bool:
        """Unlock a user account"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()
            
            logger.info(f"Unlocked user account: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error unlocking user {user_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close() 
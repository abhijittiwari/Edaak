"""
Mailbox model for email storage and management
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MailboxType(str, Enum):
    """Mailbox type enumeration"""
    INBOX = "INBOX"
    SENT = "Sent"
    DRAFTS = "Drafts"
    TRASH = "Trash"
    SPAM = "Spam"
    ARCHIVE = "Archive"
    CUSTOM = "Custom"


class Mailbox(Base):
    """Mailbox model"""
    __tablename__ = "mailboxes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    mailbox_type = Column(String(50), default=MailboxType.CUSTOM)
    
    # Quota and storage
    quota_mb = Column(BigInteger, default=1000)  # Quota in MB
    used_storage_mb = Column(BigInteger, default=0)  # Used storage in MB
    
    # IMAP flags
    is_subscribed = Column(Boolean, default=True)
    is_selectable = Column(Boolean, default=True)
    is_read_only = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="mailboxes")
    emails = relationship("Email", back_populates="mailbox", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_mailbox_user_name', 'user_id', 'name'),
    )
    
    def __repr__(self):
        return f"<Mailbox(id={self.id}, user_id={self.user_id}, name='{self.name}')>"
    
    @property
    def is_full(self):
        """Check if mailbox is full"""
        return self.used_storage_mb >= self.quota_mb
    
    @property
    def usage_percentage(self):
        """Get storage usage percentage"""
        if self.quota_mb == 0:
            return 0
        return (self.used_storage_mb / self.quota_mb) * 100 
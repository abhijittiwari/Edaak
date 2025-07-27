"""
Email model for storing email messages
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EmailFlag(str, Enum):
    """Email flag enumeration"""
    SEEN = "\\Seen"
    ANSWERED = "\\Answered"
    FLAGGED = "\\Flagged"
    DELETED = "\\Deleted"
    DRAFT = "\\Draft"
    RECENT = "\\Recent"


class Email(Base):
    """Email model"""
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    mailbox_id = Column(Integer, ForeignKey("mailboxes.id"), nullable=False)
    
    # Message ID and threading
    message_id = Column(String(255), nullable=True, index=True)
    in_reply_to = Column(String(255), nullable=True)
    references = Column(Text, nullable=True)
    
    # Headers
    subject = Column(String(500), nullable=True)
    from_address = Column(String(255), nullable=False)
    to_addresses = Column(Text, nullable=False)  # JSON array of addresses
    cc_addresses = Column(Text, nullable=True)   # JSON array of addresses
    bcc_addresses = Column(Text, nullable=True)  # JSON array of addresses
    
    # Content
    text_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    raw_message = Column(Text, nullable=False)  # Full RFC822 message
    
    # Metadata
    size_bytes = Column(BigInteger, default=0)
    flags = Column(Text, nullable=True)  # JSON array of flags
    internal_date = Column(DateTime, nullable=False)
    received_date = Column(DateTime, default=func.now())
    
    # IMAP specific
    uid = Column(BigInteger, nullable=False)  # IMAP UID
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    mailbox = relationship("Mailbox", back_populates="emails")
    attachments = relationship("EmailAttachment", back_populates="email", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_email_mailbox_uid', 'mailbox_id', 'uid'),
        Index('idx_email_message_id', 'message_id'),
        Index('idx_email_from', 'from_address'),
        Index('idx_email_subject', 'subject'),
        Index('idx_email_date', 'internal_date'),
    )
    
    def __repr__(self):
        return f"<Email(id={self.id}, mailbox_id={self.mailbox_id}, subject='{self.subject}')>"


class EmailAttachment(Base):
    """Email attachment model"""
    __tablename__ = "email_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    
    # Attachment metadata
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    content_disposition = Column(String(50), default="attachment")
    size_bytes = Column(BigInteger, default=0)
    
    # Content
    content_id = Column(String(255), nullable=True)  # For inline attachments
    file_path = Column(String(500), nullable=True)   # Path to stored file
    content = Column(Text, nullable=True)            # Base64 encoded content
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    email = relationship("Email", back_populates="attachments")
    
    def __repr__(self):
        return f"<EmailAttachment(id={self.id}, email_id={self.email_id}, filename='{self.filename}')>" 
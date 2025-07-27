"""
Contact model for address book functionality
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ContactSource(str, Enum):
    """Contact source enumeration"""
    MANUAL = "manual"
    AZURE_AD = "azure_ad"
    LDAP = "ldap"
    IMPORT = "import"


class Contact(Base):
    """Contact model for address book"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(255), nullable=True)
    nickname = Column(String(100), nullable=True)
    
    # Email addresses
    primary_email = Column(String(255), nullable=True)
    secondary_email = Column(String(255), nullable=True)
    work_email = Column(String(255), nullable=True)
    
    # Phone numbers
    primary_phone = Column(String(50), nullable=True)
    mobile_phone = Column(String(50), nullable=True)
    work_phone = Column(String(50), nullable=True)
    home_phone = Column(String(50), nullable=True)
    
    # Address
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    
    # Physical address
    street_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Additional information
    website = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    birthday = Column(DateTime, nullable=True)
    
    # Source and sync
    source = Column(String(50), default=ContactSource.MANUAL)
    external_id = Column(String(255), nullable=True)  # ID from external system
    is_synced = Column(Boolean, default=False)
    last_sync = Column(DateTime, nullable=True)
    
    # Organization
    is_favorite = Column(Boolean, default=False)
    tags = Column(Text, nullable=True)  # JSON array of tags
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="contacts")
    
    # Indexes
    __table_args__ = (
        Index('idx_contact_user', 'user_id'),
        Index('idx_contact_email', 'primary_email'),
        Index('idx_contact_name', 'first_name', 'last_name'),
        Index('idx_contact_external', 'external_id'),
    )
    
    def __repr__(self):
        return f"<Contact(id={self.id}, user_id={self.user_id}, name='{self.display_name}')>"
    
    @property
    def full_name(self):
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.display_name:
            return self.display_name
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.primary_email or "Unknown"
    
    @property
    def primary_contact_method(self):
        """Get primary contact method"""
        return self.primary_email or self.primary_phone or self.mobile_phone 
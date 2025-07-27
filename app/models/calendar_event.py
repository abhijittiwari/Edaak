"""
Calendar event model for calendar functionality
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EventStatus(str, Enum):
    """Event status enumeration"""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class EventVisibility(str, Enum):
    """Event visibility enumeration"""
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class CalendarEvent(Base):
    """Calendar event model"""
    __tablename__ = "calendar_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Event details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    
    # Time and date
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    all_day = Column(Boolean, default=False)
    timezone = Column(String(100), nullable=True)
    
    # Event properties
    status = Column(String(20), default=EventStatus.CONFIRMED)
    visibility = Column(String(20), default=EventVisibility.PUBLIC)
    priority = Column(Integer, default=0)  # 0-9, higher is more important
    
    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(Text, nullable=True)  # RRULE string
    recurrence_exceptions = Column(Text, nullable=True)  # JSON array of exception dates
    
    # Attendees and reminders
    attendees = Column(Text, nullable=True)  # JSON array of attendee objects
    reminders = Column(Text, nullable=True)  # JSON array of reminder objects
    
    # External integration
    external_id = Column(String(255), nullable=True)  # ID from external calendar
    external_source = Column(String(100), nullable=True)  # Source system
    ical_uid = Column(String(255), nullable=True)  # iCal UID
    
    # Categories and tags
    categories = Column(Text, nullable=True)  # JSON array of categories
    tags = Column(Text, nullable=True)  # JSON array of tags
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="calendar_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_event_user', 'user_id'),
        Index('idx_event_time', 'start_time', 'end_time'),
        Index('idx_event_external', 'external_id'),
        Index('idx_event_ical', 'ical_uid'),
    )
    
    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, user_id={self.user_id}, title='{self.title}')>"
    
    @property
    def duration_minutes(self):
        """Get event duration in minutes"""
        if self.all_day:
            return 24 * 60  # 24 hours
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    @property
    def is_past(self):
        """Check if event is in the past"""
        return self.end_time < datetime.utcnow()
    
    @property
    def is_current(self):
        """Check if event is currently happening"""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time
    
    @property
    def is_future(self):
        """Check if event is in the future"""
        return self.start_time > datetime.utcnow() 
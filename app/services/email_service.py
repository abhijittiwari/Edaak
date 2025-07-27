"""
Email service for processing and managing emails
"""

import logging
import json
import email
from datetime import datetime
from typing import List, Optional, Dict, Any
from email.message import EmailMessage
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.mailbox import Mailbox, MailboxType
from app.models.email import Email, EmailAttachment
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for processing and managing emails"""
    
    @staticmethod
    async def process_incoming_email(
        from_address: str,
        to_addresses: List[str],
        message: EmailMessage,
        raw_content: bytes
    ):
        """Process incoming email and store it in appropriate mailboxes"""
        try:
            # Parse email content
            subject = message.get('Subject', '')
            message_id = message.get('Message-ID', '')
            in_reply_to = message.get('In-Reply-To', '')
            references = message.get('References', '')
            
            # Extract text and HTML content
            text_content = None
            html_content = None
            
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if part.get_content_maintype() == 'text':
                        if part.get_content_subtype() == 'plain':
                            text_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        elif part.get_content_subtype() == 'html':
                            html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                if message.get_content_subtype() == 'plain':
                    text_content = message.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif message.get_content_subtype() == 'html':
                    html_content = message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Process each recipient
            for to_address in to_addresses:
                await EmailService._deliver_to_recipient(
                    from_address=from_address,
                    to_address=to_address,
                    subject=subject,
                    message_id=message_id,
                    in_reply_to=in_reply_to,
                    references=references,
                    text_content=text_content,
                    html_content=html_content,
                    message=message,
                    raw_content=raw_content
                )
                
        except Exception as e:
            logger.error(f"Error processing incoming email: {e}")
    
    @staticmethod
    async def _deliver_to_recipient(
        from_address: str,
        to_address: str,
        subject: str,
        message_id: str,
        in_reply_to: str,
        references: str,
        text_content: str,
        html_content: str,
        message: EmailMessage,
        raw_content: bytes
    ):
        """Deliver email to a specific recipient"""
        try:
            # Get user by email address
            user = AuthService.get_user_by_email(to_address)
            if not user:
                logger.warning(f"No user found for email address: {to_address}")
                return
            
            # Get or create user's inbox
            inbox = await EmailService.get_or_create_user_mailbox(user.id, 'INBOX')
            if not inbox:
                logger.error(f"Could not get or create inbox for user: {user.id}")
                return
            
            # Check mailbox quota
            if inbox.is_full:
                logger.warning(f"Mailbox full for user: {user.id}")
                return
            
            # Create email record
            email_record = Email(
                mailbox_id=inbox.id,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references,
                subject=subject,
                from_address=from_address,
                to_addresses=json.dumps([to_address]),
                cc_addresses=json.dumps(message.get_all('cc', [])),
                bcc_addresses=json.dumps(message.get_all('bcc', [])),
                text_content=text_content,
                html_content=html_content,
                raw_message=raw_content.decode('utf-8', errors='ignore'),
                size_bytes=len(raw_content),
                internal_date=datetime.utcnow(),
                uid=await EmailService._get_next_uid(inbox.id)
            )
            
            # Save email to database
            db = SessionLocal()
            try:
                db.add(email_record)
                db.commit()
                db.refresh(email_record)
                
                # Process attachments
                await EmailService._process_attachments(email_record, message)
                
                # Update mailbox storage usage
                inbox.used_storage_mb += len(raw_content) // (1024 * 1024)  # Convert to MB
                db.commit()
                
                logger.info(f"Email delivered to {to_address}: {subject}")
                
            except Exception as e:
                logger.error(f"Error saving email to database: {e}")
                db.rollback()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error delivering email to {to_address}: {e}")
    
    @staticmethod
    async def _process_attachments(email_record: Email, message: EmailMessage):
        """Process email attachments"""
        try:
            if not message.is_multipart():
                return
            
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                
                if part.get_filename():
                    # This is an attachment
                    filename = part.get_filename()
                    content_type = part.get_content_type()
                    content_disposition = part.get('Content-Disposition', 'attachment')
                    content_id = part.get('Content-ID', '')
                    
                    # Get attachment content
                    content = part.get_payload(decode=True)
                    size_bytes = len(content) if content else 0
                    
                    # Create attachment record
                    attachment = EmailAttachment(
                        email_id=email_record.id,
                        filename=filename,
                        content_type=content_type,
                        content_disposition=content_disposition,
                        content_id=content_id,
                        size_bytes=size_bytes,
                        content=content.decode('utf-8', errors='ignore') if content else None
                    )
                    
                    # Save attachment
                    db = SessionLocal()
                    try:
                        db.add(attachment)
                        db.commit()
                    except Exception as e:
                        logger.error(f"Error saving attachment: {e}")
                        db.rollback()
                    finally:
                        db.close()
                        
        except Exception as e:
            logger.error(f"Error processing attachments: {e}")
    
    @staticmethod
    async def get_or_create_user_mailbox(user_id: int, mailbox_name: str) -> Optional[Mailbox]:
        """Get or create a mailbox for a user"""
        db = SessionLocal()
        try:
            # Try to get existing mailbox
            mailbox = db.query(Mailbox).filter(
                Mailbox.user_id == user_id,
                Mailbox.name == mailbox_name
            ).first()
            
            if mailbox:
                return mailbox
            
            # Create new mailbox
            mailbox_type = MailboxType.INBOX if mailbox_name == 'INBOX' else MailboxType.CUSTOM
            
            mailbox = Mailbox(
                user_id=user_id,
                name=mailbox_name,
                mailbox_type=mailbox_type,
                quota_mb=1000  # Default quota
            )
            
            db.add(mailbox)
            db.commit()
            db.refresh(mailbox)
            
            return mailbox
            
        except Exception as e:
            logger.error(f"Error getting/creating mailbox: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    @staticmethod
    async def get_user_mailboxes(user_id: int) -> List[Mailbox]:
        """Get all mailboxes for a user"""
        db = SessionLocal()
        try:
            return db.query(Mailbox).filter(Mailbox.user_id == user_id).all()
        finally:
            db.close()
    
    @staticmethod
    async def get_user_mailbox(user_id: int, mailbox_name: str) -> Optional[Mailbox]:
        """Get a specific mailbox for a user"""
        db = SessionLocal()
        try:
            return db.query(Mailbox).filter(
                Mailbox.user_id == user_id,
                Mailbox.name == mailbox_name
            ).first()
        finally:
            db.close()
    
    @staticmethod
    async def get_mailbox_emails(mailbox_id: int) -> List[Email]:
        """Get all emails in a mailbox"""
        db = SessionLocal()
        try:
            return db.query(Email).filter(
                Email.mailbox_id == mailbox_id,
                Email.is_deleted == False
            ).order_by(Email.internal_date.desc()).all()
        finally:
            db.close()
    
    @staticmethod
    async def get_email_by_uid(mailbox_id: int, uid: int) -> Optional[Email]:
        """Get email by UID"""
        db = SessionLocal()
        try:
            return db.query(Email).filter(
                Email.mailbox_id == mailbox_id,
                Email.uid == uid,
                Email.is_deleted == False
            ).first()
        finally:
            db.close()
    
    @staticmethod
    async def _get_next_uid(mailbox_id: int) -> int:
        """Get next available UID for a mailbox"""
        db = SessionLocal()
        try:
            max_uid = db.query(Email.uid).filter(
                Email.mailbox_id == mailbox_id
            ).order_by(Email.uid.desc()).first()
            
            return (max_uid[0] if max_uid else 0) + 1
        finally:
            db.close()
    
    @staticmethod
    async def send_email(
        from_user_id: int,
        to_addresses: List[str],
        subject: str,
        text_content: str = None,
        html_content: str = None,
        cc_addresses: List[str] = None,
        bcc_addresses: List[str] = None
    ) -> bool:
        """Send an email (simplified - just store in Sent folder)"""
        try:
            # Get sender
            sender = AuthService.get_user_by_id(from_user_id)
            if not sender:
                return False
            
            # Get or create Sent mailbox
            sent_mailbox = await EmailService.get_or_create_user_mailbox(from_user_id, 'Sent')
            if not sent_mailbox:
                return False
            
            # Create email message
            email_record = Email(
                mailbox_id=sent_mailbox.id,
                subject=subject,
                from_address=sender.email,
                to_addresses=json.dumps(to_addresses),
                cc_addresses=json.dumps(cc_addresses or []),
                bcc_addresses=json.dumps(bcc_addresses or []),
                text_content=text_content,
                html_content=html_content,
                raw_message=f"From: {sender.email}\nTo: {', '.join(to_addresses)}\nSubject: {subject}\n\n{text_content or ''}",
                size_bytes=len(f"From: {sender.email}\nTo: {', '.join(to_addresses)}\nSubject: {subject}\n\n{text_content or ''}"),
                internal_date=datetime.utcnow(),
                uid=await EmailService._get_next_uid(sent_mailbox.id)
            )
            
            # Save email
            db = SessionLocal()
            try:
                db.add(email_record)
                db.commit()
                
                logger.info(f"Email sent from {sender.email} to {to_addresses}")
                return True
                
            except Exception as e:
                logger.error(f"Error sending email: {e}")
                db.rollback()
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in send_email: {e}")
            return False 
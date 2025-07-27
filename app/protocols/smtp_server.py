"""
SMTP server implementation
"""

import asyncio
import logging
import email
from email import policy
from email.message import EmailMessage
from typing import Optional, Tuple
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer
from aiosmtpd.smtp import AuthResult, LoginPassword

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class EdaakSMTPHandler:
    """SMTP handler for Edaak mail server"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.auth_service = AuthService()
    
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Handle RCPT command"""
        if not address:
            return '550 not relaying to that domain'
        
        # Extract domain from address
        domain = address.split('@')[-1]
        
        # Check if domain is allowed
        if domain not in settings.MAIL_DOMAINS:
            return '550 not relaying to that domain'
        
        envelope.rcpt_tos.append(address)
        return '250 OK'
    
    async def handle_DATA(self, server, session, envelope):
        """Handle DATA command"""
        try:
            # Parse the email message
            message = email.message_from_bytes(envelope.content, policy=policy.default)
            
            # Extract message details
            from_address = envelope.mail_from
            to_addresses = envelope.rcpt_tos
            
            # Validate sender authentication if required
            if session.authenticated:
                # Check if authenticated user can send from this address
                if not self.auth_service.can_send_from(session.user_id, from_address):
                    return '550 Authentication required'
            else:
                # For unauthenticated sessions, check if it's a local user
                if not self.auth_service.is_local_address(from_address):
                    return '550 Authentication required'
            
            # Process the email
            await self.email_service.process_incoming_email(
                from_address=from_address,
                to_addresses=to_addresses,
                message=message,
                raw_content=envelope.content
            )
            
            logger.info(f"Email processed: {from_address} -> {to_addresses}")
            return '250 Message accepted for delivery'
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return '550 Error processing message'
    
    async def handle_AUTH(self, server, session, envelope, mechanism, auth_data):
        """Handle AUTH command"""
        try:
            if mechanism not in ['PLAIN', 'LOGIN']:
                return AuthResult(success=False, handled=False)
            
            # Parse authentication data
            if mechanism == 'PLAIN':
                # PLAIN auth: \0username\0password
                auth_string = auth_data.decode('utf-8')
                parts = auth_string.split('\0')
                if len(parts) >= 3:
                    username = parts[1]
                    password = parts[2]
                else:
                    return AuthResult(success=False, handled=True)
            else:  # LOGIN
                # LOGIN auth: username and password in separate steps
                if not hasattr(session, 'auth_username'):
                    session.auth_username = auth_data.decode('utf-8')
                    return AuthResult(success=False, handled=True, auth_required=True)
                else:
                    username = session.auth_username
                    password = auth_data.decode('utf-8')
            
            # Authenticate user
            user = await self.auth_service.authenticate_user(username, password)
            if user:
                session.authenticated = True
                session.user_id = user.id
                session.username = user.username
                logger.info(f"SMTP authentication successful: {username}")
                return AuthResult(success=True, handled=True)
            else:
                logger.warning(f"SMTP authentication failed: {username}")
                return AuthResult(success=False, handled=True)
                
        except Exception as e:
            logger.error(f"SMTP authentication error: {e}")
            return AuthResult(success=False, handled=True)
    
    async def handle_EHLO(self, server, session, envelope, hostname, responses):
        """Handle EHLO command"""
        responses.append('250-AUTH PLAIN LOGIN')
        responses.append('250-SIZE 52428800')  # 50MB max message size
        responses.append('250-8BITMIME')
        responses.append('250-STARTTLS')
        return '250 OK'


async def start_smtp_server():
    """Start the SMTP server"""
    try:
        handler = EdaakSMTPHandler()
        
        # Create controller
        controller = Controller(
            handler,
            hostname=settings.HOST,
            port=settings.SMTP_PORT,
            enable_SMTPUTF8=True,
            auth_require_tls=False,  # Allow auth without TLS for testing
            auth_exclude_mechanism=['CRAM-MD5', 'DIGEST-MD5']
        )
        
        # Start server
        controller.start()
        logger.info(f"SMTP server started on {settings.HOST}:{settings.SMTP_PORT}")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("SMTP server shutdown requested")
        finally:
            controller.stop()
            logger.info("SMTP server stopped")
            
    except Exception as e:
        logger.error(f"Error starting SMTP server: {e}")
        raise 
"""
IMAP server implementation
"""

import asyncio
import logging
import email
import imaplib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class EdaakIMAPServer:
    """IMAP server for Edaak mail server"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.auth_service = AuthService()
        self.sessions: Dict[str, Dict] = {}
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle IMAP connection"""
        session_id = f"{id(writer)}"
        session = {
            'id': session_id,
            'authenticated': False,
            'user_id': None,
            'username': None,
            'selected_mailbox': None,
            'reader': reader,
            'writer': writer
        }
        self.sessions[session_id] = session
        
        try:
            # Send greeting
            await self._send_response(writer, f"* OK Edaak IMAP server ready {datetime.utcnow().strftime('%d-%b-%Y %H:%M:%S')}")
            
            # Handle commands
            while True:
                line = await reader.readline()
                if not line:
                    break
                
                command = line.decode('utf-8').strip()
                if not command:
                    continue
                
                await self._handle_command(session, command)
                
        except Exception as e:
            logger.error(f"IMAP connection error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            del self.sessions[session_id]
    
    async def _handle_command(self, session: Dict, command: str):
        """Handle IMAP command"""
        try:
            parts = command.split(' ', 1)
            tag = parts[0]
            cmd_parts = parts[1].split(' ') if len(parts) > 1 else []
            cmd = cmd_parts[0].upper() if cmd_parts else ''
            args = cmd_parts[1:] if len(cmd_parts) > 1 else []
            
            if cmd == 'CAPABILITY':
                await self._handle_capability(session, tag)
            elif cmd == 'AUTHENTICATE':
                await self._handle_authenticate(session, tag, args)
            elif cmd == 'LOGIN':
                await self._handle_login(session, tag, args)
            elif cmd == 'LOGOUT':
                await self._handle_logout(session, tag)
            elif cmd == 'LIST':
                await self._handle_list(session, tag, args)
            elif cmd == 'SELECT':
                await self._handle_select(session, tag, args)
            elif cmd == 'FETCH':
                await self._handle_fetch(session, tag, args)
            elif cmd == 'SEARCH':
                await self._handle_search(session, tag, args)
            elif cmd == 'STORE':
                await self._handle_store(session, tag, args)
            elif cmd == 'EXPUNGE':
                await self._handle_expunge(session, tag)
            elif cmd == 'CLOSE':
                await self._handle_close(session, tag)
            else:
                await self._send_response(session['writer'], f"{tag} BAD Unknown command")
                
        except Exception as e:
            logger.error(f"Error handling IMAP command: {e}")
            await self._send_response(session['writer'], f"{tag} BAD Internal error")
    
    async def _handle_capability(self, session: Dict, tag: str):
        """Handle CAPABILITY command"""
        capabilities = [
            "IMAP4rev1",
            "AUTH=PLAIN",
            "AUTH=LOGIN",
            "STARTTLS",
            "IDLE",
            "NAMESPACE",
            "QUOTA",
            "ID",
            "ENABLE",
            "CONDSTORE",
            "QRESYNC"
        ]
        await self._send_response(session['writer'], f"* CAPABILITY {' '.join(capabilities)}")
        await self._send_response(session['writer'], f"{tag} OK CAPABILITY completed")
    
    async def _handle_authenticate(self, session: Dict, tag: str, args: List[str]):
        """Handle AUTHENTICATE command"""
        if not args:
            await self._send_response(session['writer'], f"{tag} BAD Missing mechanism")
            return
        
        mechanism = args[0].upper()
        if mechanism not in ['PLAIN', 'LOGIN']:
            await self._send_response(session['writer'], f"{tag} BAD Unsupported mechanism")
            return
        
        # For now, we'll require LOGIN instead of AUTHENTICATE
        await self._send_response(session['writer'], f"{tag} BAD Use LOGIN command")
    
    async def _handle_login(self, session: Dict, tag: str, args: List[str]):
        """Handle LOGIN command"""
        if len(args) < 2:
            await self._send_response(session['writer'], f"{tag} BAD Missing username or password")
            return
        
        username = args[0]
        password = args[1]
        
        # Authenticate user
        user = await self.auth_service.authenticate_user(username, password)
        if user:
            session['authenticated'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            await self._send_response(session['writer'], f"{tag} OK LOGIN completed")
        else:
            await self._send_response(session['writer'], f"{tag} NO Login failed")
    
    async def _handle_logout(self, session: Dict, tag: str):
        """Handle LOGOUT command"""
        await self._send_response(session['writer'], "* BYE Edaak IMAP server signing off")
        await self._send_response(session['writer'], f"{tag} OK LOGOUT completed")
    
    async def _handle_list(self, session: Dict, tag: str, args: List[str]):
        """Handle LIST command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated")
            return
        
        if len(args) < 2:
            await self._send_response(session['writer'], f"{tag} BAD Missing arguments")
            return
        
        reference = args[0]
        mailbox_pattern = args[1]
        
        # Get user's mailboxes
        mailboxes = await self.email_service.get_user_mailboxes(session['user_id'])
        
        for mailbox in mailboxes:
            # Check if mailbox matches pattern
            if self._mailbox_matches_pattern(mailbox.name, mailbox_pattern):
                flags = self._get_mailbox_flags(mailbox)
                await self._send_response(
                    session['writer'],
                    f'* LIST ({flags}) "/" "{mailbox.name}"'
                )
        
        await self._send_response(session['writer'], f"{tag} OK LIST completed")
    
    async def _handle_select(self, session: Dict, tag: str, args: List[str]):
        """Handle SELECT command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated")
            return
        
        if not args:
            await self._send_response(session['writer'], f"{tag} BAD Missing mailbox name")
            return
        
        mailbox_name = args[0]
        
        # Get mailbox
        mailbox = await self.email_service.get_user_mailbox(session['user_id'], mailbox_name)
        if not mailbox:
            await self._send_response(session['writer'], f"{tag} NO Mailbox does not exist")
            return
        
        session['selected_mailbox'] = mailbox
        
        # Send mailbox information
        flags = self._get_mailbox_flags(mailbox)
        await self._send_response(session['writer'], f'* FLAGS ({flags})')
        await self._send_response(session['writer'], f'* {mailbox.emails.count()} EXISTS')
        await self._send_response(session['writer'], f'* 0 RECENT')
        await self._send_response(session['writer'], f'* OK [UIDVALIDITY 1] UIDs valid')
        await self._send_response(session['writer'], f'* OK [UIDNEXT {mailbox.emails.count() + 1}] Predicted next UID')
        await self._send_response(session['writer'], f'* OK [PERMANENTFLAGS ({flags})] Permanent flags')
        await self._send_response(session['writer'], f'* OK [UNSEEN 1] First unseen message')
        await self._send_response(session['writer'], f"{tag} OK [READ-WRITE] SELECT completed")
    
    async def _handle_fetch(self, session: Dict, tag: str, args: List[str]):
        """Handle FETCH command"""
        if not session['authenticated'] or not session['selected_mailbox']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated or no mailbox selected")
            return
        
        if len(args) < 2:
            await self._send_response(session['writer'], f"{tag} BAD Missing arguments")
            return
        
        message_set = args[0]
        data_items = args[1]
        
        # Parse message set (simplified - only supports single UID for now)
        try:
            uid = int(message_set)
        except ValueError:
            await self._send_response(session['writer'], f"{tag} BAD Invalid message set")
            return
        
        # Get email
        email_msg = await self.email_service.get_email_by_uid(session['selected_mailbox'].id, uid)
        if not email_msg:
            await self._send_response(session['writer'], f"{tag} NO Message not found")
            return
        
        # Send email data
        await self._send_email_data(session['writer'], uid, email_msg, data_items)
        await self._send_response(session['writer'], f"{tag} OK FETCH completed")
    
    async def _handle_search(self, session: Dict, tag: str, args: List[str]):
        """Handle SEARCH command"""
        if not session['authenticated'] or not session['selected_mailbox']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated or no mailbox selected")
            return
        
        # Simplified search - return all messages
        emails = await self.email_service.get_mailbox_emails(session['selected_mailbox'].id)
        uids = [email.uid for email in emails]
        
        await self._send_response(session['writer'], f"* SEARCH {' '.join(map(str, uids))}")
        await self._send_response(session['writer'], f"{tag} OK SEARCH completed")
    
    async def _handle_store(self, session: Dict, tag: str, args: List[str]):
        """Handle STORE command"""
        if not session['authenticated'] or not session['selected_mailbox']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated or no mailbox selected")
            return
        
        # Simplified - just acknowledge
        await self._send_response(session['writer'], f"{tag} OK STORE completed")
    
    async def _handle_expunge(self, session: Dict, tag: str):
        """Handle EXPUNGE command"""
        if not session['authenticated'] or not session['selected_mailbox']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated or no mailbox selected")
            return
        
        await self._send_response(session['writer'], f"{tag} OK EXPUNGE completed")
    
    async def _handle_close(self, session: Dict, tag: str):
        """Handle CLOSE command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], f"{tag} NO Not authenticated")
            return
        
        session['selected_mailbox'] = None
        await self._send_response(session['writer'], f"{tag} OK CLOSE completed")
    
    async def _send_response(self, writer: asyncio.StreamWriter, response: str):
        """Send response to client"""
        writer.write(f"{response}\r\n".encode('utf-8'))
        await writer.drain()
    
    def _mailbox_matches_pattern(self, mailbox_name: str, pattern: str) -> bool:
        """Check if mailbox matches pattern"""
        # Simplified pattern matching
        if pattern == '*' or pattern == '%':
            return True
        return mailbox_name.lower() == pattern.lower()
    
    def _get_mailbox_flags(self, mailbox) -> str:
        """Get mailbox flags"""
        flags = []
        if mailbox.is_subscribed:
            flags.append("\\Subscribed")
        if mailbox.is_selectable:
            flags.append("\\Selectable")
        if mailbox.is_read_only:
            flags.append("\\ReadOnly")
        return " ".join(flags) if flags else "\\Noinferiors"
    
    async def _send_email_data(self, writer: asyncio.StreamWriter, uid: int, email_msg, data_items: str):
        """Send email data for FETCH command"""
        # Simplified - just send basic info
        response = f"* {uid} FETCH ("
        
        if "FLAGS" in data_items:
            flags = "\\Seen"  # Simplified
            response += f"FLAGS ({flags}) "
        
        if "UID" in data_items:
            response += f"UID {uid} "
        
        if "RFC822.SIZE" in data_items:
            response += f"RFC822.SIZE {len(email_msg.raw_message)} "
        
        if "RFC822.HEADER" in data_items or "BODY[HEADER]" in data_items:
            # Extract headers from raw message
            headers = email_msg.raw_message.split('\n\n')[0]
            response += f"RFC822.HEADER {{{len(headers)}}}\r\n{headers} "
        
        response = response.rstrip() + ")"
        await self._send_response(writer, response)


async def start_imap_server():
    """Start the IMAP server"""
    try:
        server = EdaakIMAPServer()
        
        # Create server
        imap_server = await asyncio.start_server(
            server.handle_connection,
            settings.HOST,
            settings.IMAP_PORT
        )
        
        logger.info(f"IMAP server started on {settings.HOST}:{settings.IMAP_PORT}")
        
        # Keep server running
        try:
            async with imap_server:
                await imap_server.serve_forever()
        except asyncio.CancelledError:
            logger.info("IMAP server shutdown requested")
        finally:
            imap_server.close()
            await imap_server.wait_closed()
            logger.info("IMAP server stopped")
            
    except Exception as e:
        logger.error(f"Error starting IMAP server: {e}")
        raise 
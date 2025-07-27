"""
POP3 server implementation
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import email

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class EdaakPOP3Server:
    """POP3 server for Edaak mail server"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.auth_service = AuthService()
        self.sessions: Dict[str, Dict] = {}
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle POP3 connection"""
        session_id = f"{id(writer)}"
        session = {
            'id': session_id,
            'authenticated': False,
            'user_id': None,
            'username': None,
            'reader': reader,
            'writer': writer
        }
        self.sessions[session_id] = session
        
        try:
            # Send greeting
            await self._send_response(writer, f"+OK Edaak POP3 server ready {datetime.utcnow().strftime('%d-%b-%Y %H:%M:%S')}")
            
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
            logger.error(f"POP3 connection error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            del self.sessions[session_id]
    
    async def _handle_command(self, session: Dict, command: str):
        """Handle POP3 command"""
        try:
            parts = command.split(' ', 1)
            cmd = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ''
            
            if cmd == 'USER':
                await self._handle_user(session, args)
            elif cmd == 'PASS':
                await self._handle_pass(session, args)
            elif cmd == 'QUIT':
                await self._handle_quit(session)
            elif cmd == 'STAT':
                await self._handle_stat(session)
            elif cmd == 'LIST':
                await self._handle_list(session, args)
            elif cmd == 'RETR':
                await self._handle_retr(session, args)
            elif cmd == 'DELE':
                await self._handle_dele(session, args)
            elif cmd == 'NOOP':
                await self._handle_noop(session)
            elif cmd == 'RSET':
                await self._handle_rset(session)
            elif cmd == 'UIDL':
                await self._handle_uidl(session, args)
            elif cmd == 'TOP':
                await self._handle_top(session, args)
            else:
                await self._send_response(session['writer'], "-ERR Unknown command")
                
        except Exception as e:
            logger.error(f"Error handling POP3 command: {e}")
            await self._send_response(session['writer'], "-ERR Internal error")
    
    async def _handle_user(self, session: Dict, username: str):
        """Handle USER command"""
        if not username:
            await self._send_response(session['writer'], "-ERR Missing username")
            return
        
        session['username'] = username
        await self._send_response(session['writer'], "+OK Username accepted")
    
    async def _handle_pass(self, session: Dict, password: str):
        """Handle PASS command"""
        if not session.get('username'):
            await self._send_response(session['writer'], "-ERR USER command required first")
            return
        
        if not password:
            await self._send_response(session['writer'], "-ERR Missing password")
            return
        
        # Authenticate user
        user = await self.auth_service.authenticate_user(session['username'], password)
        if user:
            session['authenticated'] = True
            session['user_id'] = user.id
            await self._send_response(session['writer'], "+OK Authentication successful")
        else:
            await self._send_response(session['writer'], "-ERR Authentication failed")
    
    async def _handle_quit(self, session: Dict):
        """Handle QUIT command"""
        await self._send_response(session['writer'], "+OK Edaak POP3 server signing off")
    
    async def _handle_stat(self, session: Dict):
        """Handle STAT command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], "-ERR Not authenticated")
            return
        
        # Get user's inbox
        inbox = await self.email_service.get_user_mailbox(session['user_id'], 'INBOX')
        if not inbox:
            await self._send_response(session['writer'], "+OK 0 0")
            return
        
        # Count messages and total size
        emails = await self.email_service.get_mailbox_emails(inbox.id)
        message_count = len(emails)
        total_size = sum(email.size_bytes for email in emails)
        
        await self._send_response(session['writer'], f"+OK {message_count} {total_size}")
    
    async def _handle_list(self, session: Dict, args: str):
        """Handle LIST command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], "-ERR Not authenticated")
            return
        
        # Get user's inbox
        inbox = await self.email_service.get_user_mailbox(session['user_id'], 'INBOX')
        if not inbox:
            await self._send_response(session['writer'], "+OK 0 messages")
            return
        
        emails = await self.email_service.get_mailbox_emails(inbox.id)
        
        if args:
            # List specific message
            try:
                msg_num = int(args)
                if 1 <= msg_num <= len(emails):
                    email_msg = emails[msg_num - 1]
                    await self._send_response(session['writer'], f"+OK {msg_num} {email_msg.size_bytes}")
                else:
                    await self._send_response(session['writer'], "-ERR Message not found")
            except ValueError:
                await self._send_response(session['writer'], "-ERR Invalid message number")
        else:
            # List all messages
            await self._send_response(session['writer'], f"+OK {len(emails)} messages")
            for i, email_msg in enumerate(emails, 1):
                await self._send_response(session['writer'], f"{i} {email_msg.size_bytes}")
            await self._send_response(session['writer'], ".")
    
    async def _handle_retr(self, session: Dict, args: str):
        """Handle RETR command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], "-ERR Not authenticated")
            return
        
        if not args:
            await self._send_response(session['writer'], "-ERR Missing message number")
            return
        
        try:
            msg_num = int(args)
        except ValueError:
            await self._send_response(session['writer'], "-ERR Invalid message number")
            return
        
        # Get user's inbox
        inbox = await self.email_service.get_user_mailbox(session['user_id'], 'INBOX')
        if not inbox:
            await self._send_response(session['writer'], "-ERR No messages")
            return
        
        emails = await self.email_service.get_mailbox_emails(inbox.id)
        
        if 1 <= msg_num <= len(emails):
            email_msg = emails[msg_num - 1]
            await self._send_response(session['writer'], f"+OK {email_msg.size_bytes} octets")
            await self._send_response(session['writer'], email_msg.raw_message)
            await self._send_response(session['writer'], ".")
        else:
            await self._send_response(session['writer'], "-ERR Message not found")
    
    async def _handle_dele(self, session: Dict, args: str):
        """Handle DELE command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], "-ERR Not authenticated")
            return
        
        if not args:
            await self._send_response(session['writer'], "-ERR Missing message number")
            return
        
        try:
            msg_num = int(args)
        except ValueError:
            await self._send_response(session['writer'], "-ERR Invalid message number")
            return
        
        # For now, just acknowledge the delete command
        # In a real implementation, you would mark the message for deletion
        await self._send_response(session['writer'], f"+OK Message {msg_num} marked for deletion")
    
    async def _handle_noop(self, session: Dict):
        """Handle NOOP command"""
        await self._send_response(session['writer'], "+OK")
    
    async def _handle_rset(self, session: Dict):
        """Handle RSET command"""
        # Reset any pending deletions
        await self._send_response(session['writer'], "+OK Reset completed")
    
    async def _handle_uidl(self, session: Dict, args: str):
        """Handle UIDL command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], "-ERR Not authenticated")
            return
        
        # Get user's inbox
        inbox = await self.email_service.get_user_mailbox(session['user_id'], 'INBOX')
        if not inbox:
            await self._send_response(session['writer'], "+OK 0 messages")
            return
        
        emails = await self.email_service.get_mailbox_emails(inbox.id)
        
        if args:
            # Get UIDL for specific message
            try:
                msg_num = int(args)
                if 1 <= msg_num <= len(emails):
                    email_msg = emails[msg_num - 1]
                    await self._send_response(session['writer'], f"+OK {msg_num} {email_msg.uid}")
                else:
                    await self._send_response(session['writer'], "-ERR Message not found")
            except ValueError:
                await self._send_response(session['writer'], "-ERR Invalid message number")
        else:
            # Get UIDL for all messages
            await self._send_response(session['writer'], f"+OK {len(emails)} messages")
            for i, email_msg in enumerate(emails, 1):
                await self._send_response(session['writer'], f"{i} {email_msg.uid}")
            await self._send_response(session['writer'], ".")
    
    async def _handle_top(self, session: Dict, args: str):
        """Handle TOP command"""
        if not session['authenticated']:
            await self._send_response(session['writer'], "-ERR Not authenticated")
            return
        
        if not args:
            await self._send_response(session['writer'], "-ERR Missing arguments")
            return
        
        try:
            parts = args.split(' ')
            msg_num = int(parts[0])
            lines = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            await self._send_response(session['writer'], "-ERR Invalid arguments")
            return
        
        # Get user's inbox
        inbox = await self.email_service.get_user_mailbox(session['user_id'], 'INBOX')
        if not inbox:
            await self._send_response(session['writer'], "-ERR No messages")
            return
        
        emails = await self.email_service.get_mailbox_emails(inbox.id)
        
        if 1 <= msg_num <= len(emails):
            email_msg = emails[msg_num - 1]
            
            # Parse email to get headers and body
            try:
                parsed_email = email.message_from_string(email_msg.raw_message)
                headers = str(parsed_email)
                
                # Get body lines
                body_lines = []
                if parsed_email.is_multipart():
                    for part in parsed_email.walk():
                        if part.get_content_maintype() == 'text':
                            body_lines.extend(part.get_payload(decode=True).decode('utf-8', errors='ignore').split('\n'))
                            break
                else:
                    body_lines = parsed_email.get_payload(decode=True).decode('utf-8', errors='ignore').split('\n')
                
                # Send headers and specified number of body lines
                response = headers + '\n'
                response += '\n'.join(body_lines[:lines])
                
                await self._send_response(session['writer'], f"+OK {len(response)} octets")
                await self._send_response(session['writer'], response)
                await self._send_response(session['writer'], ".")
                
            except Exception as e:
                logger.error(f"Error parsing email for TOP: {e}")
                await self._send_response(session['writer'], "-ERR Error parsing message")
        else:
            await self._send_response(session['writer'], "-ERR Message not found")
    
    async def _send_response(self, writer: asyncio.StreamWriter, response: str):
        """Send response to client"""
        writer.write(f"{response}\r\n".encode('utf-8'))
        await writer.drain()


async def start_pop3_server():
    """Start the POP3 server"""
    try:
        server = EdaakPOP3Server()
        
        # Create server
        pop3_server = await asyncio.start_server(
            server.handle_connection,
            settings.HOST,
            settings.POP3_PORT
        )
        
        logger.info(f"POP3 server started on {settings.HOST}:{settings.POP3_PORT}")
        
        # Keep server running
        try:
            async with pop3_server:
                await pop3_server.serve_forever()
        except asyncio.CancelledError:
            logger.info("POP3 server shutdown requested")
        finally:
            pop3_server.close()
            await pop3_server.wait_closed()
            logger.info("POP3 server stopped")
            
    except Exception as e:
        logger.error(f"Error starting POP3 server: {e}")
        raise 
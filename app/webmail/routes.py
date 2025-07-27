"""
Webmail routes for web-based email interface
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List

from app.auth.jwt import JWTService
from app.services.email_service import EmailService
from app.models.user import User

# Create router
webmail_router = APIRouter()

# Security
security = HTTPBearer()

# Templates
templates = Jinja2Templates(directory="templates")


# Pydantic models
class ComposeEmailRequest(BaseModel):
    to_addresses: List[str]
    subject: str
    text_content: Optional[str] = None
    html_content: Optional[str] = None
    cc_addresses: Optional[List[str]] = None
    bcc_addresses: Optional[List[str]] = None


# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    try:
        payload = JWTService.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = int(payload.get("sub"))
        user = AuthService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Webmail interface routes
@webmail_router.get("/", response_class=HTMLResponse)
async def webmail_home(request: Request):
    """Webmail home page"""
    return templates.TemplateResponse("webmail/index.html", {"request": request})


@webmail_router.get("/login", response_class=HTMLResponse)
async def webmail_login(request: Request):
    """Webmail login page"""
    return templates.TemplateResponse("webmail/login.html", {"request": request})


@webmail_router.get("/inbox", response_class=HTMLResponse)
async def webmail_inbox(request: Request):
    """Webmail inbox page"""
    return templates.TemplateResponse("webmail/inbox.html", {"request": request})


@webmail_router.get("/compose", response_class=HTMLResponse)
async def webmail_compose(request: Request):
    """Webmail compose page"""
    return templates.TemplateResponse("webmail/compose.html", {"request": request})


@webmail_router.get("/settings", response_class=HTMLResponse)
async def webmail_settings(request: Request):
    """Webmail settings page"""
    return templates.TemplateResponse("webmail/settings.html", {"request": request})


# API routes for webmail
@webmail_router.get("/api/mailboxes")
async def get_mailboxes(current_user: User = Depends(get_current_user)):
    """Get user's mailboxes for webmail"""
    mailboxes = await EmailService.get_user_mailboxes(current_user.id)
    
    return [
        {
            "id": mailbox.id,
            "name": mailbox.name,
            "type": mailbox.mailbox_type,
            "quota_mb": mailbox.quota_mb,
            "used_storage_mb": mailbox.used_storage_mb,
            "usage_percentage": mailbox.usage_percentage,
            "is_subscribed": mailbox.is_subscribed,
            "is_selectable": mailbox.is_selectable,
            "is_read_only": mailbox.is_read_only
        }
        for mailbox in mailboxes
    ]


@webmail_router.get("/api/mailboxes/{mailbox_name}/emails")
async def get_mailbox_emails(
    mailbox_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get emails in a mailbox for webmail"""
    mailbox = await EmailService.get_user_mailbox(current_user.id, mailbox_name)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mailbox not found"
        )
    
    emails = await EmailService.get_mailbox_emails(mailbox.id)
    
    return [
        {
            "uid": email.uid,
            "subject": email.subject,
            "from_address": email.from_address,
            "to_addresses": email.to_addresses,
            "internal_date": email.internal_date.isoformat(),
            "size_bytes": email.size_bytes,
            "flags": email.flags,
            "is_deleted": email.is_deleted,
            "has_attachments": len(email.attachments) > 0
        }
        for email in emails
    ]


@webmail_router.get("/api/mailboxes/{mailbox_name}/emails/{uid}")
async def get_email(
    mailbox_name: str,
    uid: int,
    current_user: User = Depends(get_current_user)
):
    """Get a specific email for webmail"""
    mailbox = await EmailService.get_user_mailbox(current_user.id, mailbox_name)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mailbox not found"
        )
    
    email = await EmailService.get_email_by_uid(mailbox.id, uid)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    return {
        "uid": email.uid,
        "subject": email.subject,
        "from_address": email.from_address,
        "to_addresses": email.to_addresses,
        "cc_addresses": email.cc_addresses,
        "bcc_addresses": email.bcc_addresses,
        "text_content": email.text_content,
        "html_content": email.html_content,
        "internal_date": email.internal_date.isoformat(),
        "size_bytes": email.size_bytes,
        "flags": email.flags,
        "attachments": [
            {
                "id": attachment.id,
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "size_bytes": attachment.size_bytes
            }
            for attachment in email.attachments
        ]
    }


@webmail_router.post("/api/emails/send")
async def send_email(
    request: ComposeEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send an email from webmail"""
    success = await EmailService.send_email(
        from_user_id=current_user.id,
        to_addresses=request.to_addresses,
        subject=request.subject,
        text_content=request.text_content,
        html_content=request.html_content,
        cc_addresses=request.cc_addresses,
        bcc_addresses=request.bcc_addresses
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )
    
    return {"message": "Email sent successfully"}


@webmail_router.get("/api/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile for webmail"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "status": current_user.status,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    } 
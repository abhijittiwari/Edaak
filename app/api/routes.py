"""
Main API routes for Edaak Mail Server
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List

from app.auth.jwt import JWTService
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.models.user import User

# Create router
api_router = APIRouter()

# Security
security = HTTPBearer()


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_admin: bool
    status: str


class SendEmailRequest(BaseModel):
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


# Authentication routes
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login with username/email and password"""
    user = await AuthService.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = AuthService.create_access_token(user)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "status": user.status
        }
    )


@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_admin=current_user.is_admin,
        status=current_user.status
    )


# Email routes
@api_router.post("/emails/send")
async def send_email(
    request: SendEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send an email"""
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


@api_router.get("/mailboxes")
async def get_mailboxes(current_user: User = Depends(get_current_user)):
    """Get user's mailboxes"""
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


@api_router.get("/mailboxes/{mailbox_name}/emails")
async def get_mailbox_emails(
    mailbox_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get emails in a mailbox"""
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
            "is_deleted": email.is_deleted
        }
        for email in emails
    ]


@api_router.get("/mailboxes/{mailbox_name}/emails/{uid}")
async def get_email(
    mailbox_name: str,
    uid: int,
    current_user: User = Depends(get_current_user)
):
    """Get a specific email"""
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


# Health check
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Edaak Mail Server"} 
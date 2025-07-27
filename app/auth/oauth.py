"""
OAuth implementation for external identity providers
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from app.core.config import settings
from app.models.user import User, OAuthToken, AuthProvider
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# OAuth configuration
config = Config('.env')
oauth = OAuth(config)

# Register OAuth providers
if settings.AZURE_AD_CLIENT_ID:
    oauth.register(
        name='azure_ad',
        client_id=settings.AZURE_AD_CLIENT_ID,
        client_secret=settings.AZURE_AD_CLIENT_SECRET,
        server_metadata_url=f'https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0/.well-known/openid_configuration',
        client_kwargs={
            'scope': 'openid email profile User.Read'
        }
    )

if settings.CLERK_CLIENT_ID:
    oauth.register(
        name='clerk',
        client_id=settings.CLERK_CLIENT_ID,
        client_secret=settings.CLERK_CLIENT_SECRET,
        authorize_url='https://clerk.your-domain.com/oauth/authorize',
        token_url='https://clerk.your-domain.com/oauth/token',
        userinfo_url='https://clerk.your-domain.com/oauth/userinfo',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

if settings.KEYCLOAK_CLIENT_ID:
    oauth.register(
        name='keycloak',
        client_id=settings.KEYCLOAK_CLIENT_ID,
        client_secret=settings.KEYCLOAK_CLIENT_SECRET,
        server_metadata_url=f'{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/.well-known/openid_configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )


class OAuthService:
    """OAuth service for handling external authentication"""
    
    @staticmethod
    async def get_user_info(provider: str, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user information from OAuth provider"""
        try:
            if provider == 'azure_ad':
                return await OAuthService._get_azure_user_info(token)
            elif provider == 'clerk':
                return await OAuthService._get_clerk_user_info(token)
            elif provider == 'keycloak':
                return await OAuthService._get_keycloak_user_info(token)
            else:
                logger.error(f"Unsupported OAuth provider: {provider}")
                return None
        except Exception as e:
            logger.error(f"Error getting user info from {provider}: {e}")
            return None
    
    @staticmethod
    async def _get_azure_user_info(token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user information from Azure AD"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {'Authorization': f"Bearer {token['access_token']}"}
                response = await client.get(
                    'https://graph.microsoft.com/v1.0/me',
                    headers=headers
                )
                response.raise_for_status()
                user_data = response.json()
                
                return {
                    'id': user_data.get('id'),
                    'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                    'name': user_data.get('displayName'),
                    'first_name': user_data.get('givenName'),
                    'last_name': user_data.get('surname'),
                    'job_title': user_data.get('jobTitle'),
                    'department': user_data.get('department'),
                    'company': user_data.get('companyName')
                }
        except Exception as e:
            logger.error(f"Error getting Azure AD user info: {e}")
            return None
    
    @staticmethod
    async def _get_clerk_user_info(token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user information from Clerk"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {'Authorization': f"Bearer {token['access_token']}"}
                response = await client.get(
                    'https://clerk.your-domain.com/oauth/userinfo',
                    headers=headers
                )
                response.raise_for_status()
                user_data = response.json()
                
                return {
                    'id': user_data.get('sub'),
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'first_name': user_data.get('given_name'),
                    'last_name': user_data.get('family_name')
                }
        except Exception as e:
            logger.error(f"Error getting Clerk user info: {e}")
            return None
    
    @staticmethod
    async def _get_keycloak_user_info(token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user information from Keycloak"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {'Authorization': f"Bearer {token['access_token']}"}
                response = await client.get(
                    f'{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo',
                    headers=headers
                )
                response.raise_for_status()
                user_data = response.json()
                
                return {
                    'id': user_data.get('sub'),
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'first_name': user_data.get('given_name'),
                    'last_name': user_data.get('family_name')
                }
        except Exception as e:
            logger.error(f"Error getting Keycloak user info: {e}")
            return None
    
    @staticmethod
    def get_or_create_user(user_info: Dict[str, Any], provider: str) -> Optional[User]:
        """Get existing user or create new one from OAuth info"""
        db = SessionLocal()
        try:
            # Check if user exists by external ID
            user = db.query(User).filter(
                User.external_id == user_info['id'],
                User.auth_provider == provider
            ).first()
            
            if user:
                # Update user info
                user.email = user_info.get('email', user.email)
                user.full_name = user_info.get('name', user.full_name)
                user.last_login = datetime.utcnow()
                db.commit()
                return user
            
            # Check if user exists by email
            if user_info.get('email'):
                user = db.query(User).filter(User.email == user_info['email']).first()
                if user:
                    # Link existing user to OAuth
                    user.external_id = user_info['id']
                    user.auth_provider = provider
                    user.last_login = datetime.utcnow()
                    db.commit()
                    return user
            
            # Create new user
            user = User(
                email=user_info.get('email'),
                username=user_info.get('email', '').split('@')[0],
                full_name=user_info.get('name'),
                external_id=user_info['id'],
                auth_provider=provider,
                status='active',
                last_login=datetime.utcnow()
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating/getting user: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    @staticmethod
    def save_oauth_token(user_id: int, provider: str, token: Dict[str, Any]):
        """Save OAuth token to database"""
        db = SessionLocal()
        try:
            # Check if token exists
            existing_token = db.query(OAuthToken).filter(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == provider
            ).first()
            
            expires_at = None
            if token.get('expires_in'):
                expires_at = datetime.utcnow() + timedelta(seconds=token['expires_in'])
            
            if existing_token:
                # Update existing token
                existing_token.access_token = token['access_token']
                existing_token.refresh_token = token.get('refresh_token')
                existing_token.token_type = token.get('token_type')
                existing_token.expires_at = expires_at
                existing_token.scope = token.get('scope')
                existing_token.updated_at = datetime.utcnow()
            else:
                # Create new token
                oauth_token = OAuthToken(
                    user_id=user_id,
                    provider=provider,
                    access_token=token['access_token'],
                    refresh_token=token.get('refresh_token'),
                    token_type=token.get('token_type'),
                    expires_at=expires_at,
                    scope=token.get('scope')
                )
                db.add(oauth_token)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving OAuth token: {e}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def get_oauth_token(user_id: int, provider: str) -> Optional[OAuthToken]:
        """Get OAuth token from database"""
        db = SessionLocal()
        try:
            token = db.query(OAuthToken).filter(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == provider
            ).first()
            return token
        finally:
            db.close()
    
    @staticmethod
    async def refresh_token(user_id: int, provider: str) -> Optional[Dict[str, Any]]:
        """Refresh OAuth token"""
        db = SessionLocal()
        try:
            token = db.query(OAuthToken).filter(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == provider
            ).first()
            
            if not token or not token.refresh_token:
                return None
            
            # Refresh token logic would go here
            # This is provider-specific and would need to be implemented
            # based on the OAuth provider's refresh token endpoint
            
            return None
            
        finally:
            db.close() 
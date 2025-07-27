"""
Configuration settings for the Edaak Mail Server
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/edaak_mail"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Application Settings
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SMTP_PORT: int = 25
    IMAP_PORT: int = 143
    POP3_PORT: int = 110
    SMTPS_PORT: int = 587
    IMAPS_PORT: int = 993
    POP3S_PORT: int = 995
    
    # Email Configuration
    MAIL_DOMAINS: str = "example.com,test.com"
    DEFAULT_QUOTA_MB: int = 1000
    MAX_ATTACHMENT_SIZE_MB: int = 25
    ALLOWED_ATTACHMENT_TYPES: str = ".pdf,.doc,.docx,.txt,.jpg,.png,.gif"
    
    # OAuth Configuration
    OAUTH_ENABLED: bool = True
    OAUTH_PROVIDERS: str = "azure_ad,clerk,keycloak"
    
    # Azure AD OAuth
    AZURE_AD_CLIENT_ID: Optional[str] = None
    AZURE_AD_CLIENT_SECRET: Optional[str] = None
    AZURE_AD_TENANT_ID: Optional[str] = None
    AZURE_AD_REDIRECT_URI: str = "http://localhost:8000/auth/azure/callback"
    
    # Clerk OAuth
    CLERK_CLIENT_ID: Optional[str] = None
    CLERK_CLIENT_SECRET: Optional[str] = None
    CLERK_REDIRECT_URI: str = "http://localhost:8000/auth/clerk/callback"
    
    # Keycloak OAuth
    KEYCLOAK_CLIENT_ID: Optional[str] = None
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080/auth"
    KEYCLOAK_REALM: str = "your-realm"
    KEYCLOAK_REDIRECT_URI: str = "http://localhost:8000/auth/keycloak/callback"
    
    # Security Settings
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    PASSWORD_MIN_LENGTH: int = 8
    REQUIRE_SPECIAL_CHARS: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_UPPERCASE: bool = True
    
    # TLS/SSL Configuration
    SSL_CERT_FILE: Optional[str] = None
    SSL_KEY_FILE: Optional[str] = None
    SSL_ENABLED: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/edaak.log"
    
    # Redis (Optional - for caching)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False
    
    # Email Authentication
    SPF_ENABLED: bool = True
    DKIM_ENABLED: bool = True
    DMARC_ENABLED: bool = True
    DKIM_PRIVATE_KEY: Optional[str] = None
    DKIM_SELECTOR: str = "default"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # Admin Settings
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"
    FIRST_RUN: bool = True
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    @validator("MAIL_DOMAINS", pre=True)
    def parse_mail_domains(cls, v):
        """Parse mail domains string into list"""
        if isinstance(v, str):
            return [domain.strip() for domain in v.split(",")]
        return v
    
    @validator("ALLOWED_ATTACHMENT_TYPES", pre=True)
    def parse_attachment_types(cls, v):
        """Parse attachment types string into list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("OAUTH_PROVIDERS", pre=True)
    def parse_oauth_providers(cls, v):
        """Parse OAuth providers string into list"""
        if isinstance(v, str):
            return [provider.strip() for provider in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings() 
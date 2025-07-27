# Edaak Mail Server

A comprehensive, modern mail server built with Python that supports IMAP/POP3/SMTP protocols with OAuth/OpenID Connect integration, webmail interface, and admin center.

## Features

### Core Email Functionality
- **SMTP Server**: Send emails with authentication and relay support
- **IMAP Server**: Full IMAP4rev1 support for email retrieval
- **POP3 Server**: POP3 support for legacy clients
- **Webmail Interface**: Modern web-based email client
- **Email Storage**: PostgreSQL-based email storage with efficient indexing

### Authentication & Identity
- **OAuth 2.0 / OpenID Connect**: Integration with Azure AD, Clerk, Keycloak, and other identity providers
- **Local Identity Store**: Built-in user management for organizations not using external identity providers
- **Multi-factor Authentication**: Support for TOTP and other MFA methods
- **Single Sign-On (SSO)**: Seamless integration with enterprise identity systems

### Address Book & Calendar
- **Address Book**: Contact management with LDAP/Active Directory sync
- **Calendar Support**: iCal format support with event management
- **Azure AD Integration**: Automatic contact population from Azure AD
- **Contact Sync**: Real-time synchronization with external directories

### Administration
- **Admin Center**: Web-based administration interface
- **User Management**: Create, modify, and delete user accounts
- **Mailbox Quotas**: Configurable storage limits per user
- **Domain Management**: Multi-domain support
- **System Monitoring**: Real-time server statistics and logs

### Security & Compliance
- **TLS/SSL Support**: Encrypted communication for all protocols
- **SPF/DKIM/DMARC**: Email authentication and anti-spam measures
- **Audit Logging**: Comprehensive activity logging
- **Data Encryption**: At-rest and in-transit encryption

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Webmail UI    │    │   Admin Center  │    │   OAuth/SSO     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   FastAPI Core  │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SMTP Server   │    │   IMAP Server   │    │   POP3 Server   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   Database      │
                    └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Edaak
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

### Configuration

The application uses environment variables for configuration. Key settings include:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Application secret key
- `OAUTH_PROVIDERS`: OAuth provider configurations
- `MAIL_DOMAINS`: Allowed email domains
- `SMTP_PORT`, `IMAP_PORT`, `POP3_PORT`: Protocol ports

## API Documentation

Once running, visit:
- Webmail: http://localhost:8000
- Admin Center: http://localhost:8000/admin
- API Documentation: http://localhost:8000/docs

## Development

### Project Structure
```
Edaak/
├── app/
│   ├── core/           # Core configuration and utilities
│   ├── models/         # Database models
│   ├── api/            # API routes
│   ├── services/       # Business logic
│   ├── protocols/      # SMTP/IMAP/POP3 servers
│   ├── auth/           # Authentication and OAuth
│   ├── admin/          # Admin center
│   └── webmail/        # Webmail interface
├── migrations/         # Database migrations
├── static/            # Static files
├── templates/         # HTML templates
└── tests/             # Test suite
```

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Join our community discussions 
# Edaak Mail Server - Quick Start Guide

## 🚀 Quick Setup

### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Edaak
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Webmail: http://localhost:8000
   - Admin Center: http://localhost:8000/admin
   - API Documentation: http://localhost:8000/docs

### Option 2: Local Development

1. **Prerequisites**
   - Python 3.9+
   - PostgreSQL 12+
   - Redis (optional)

2. **Setup**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd Edaak
   
   # Run setup script
   python setup.py
   
   # Or manually:
   pip install -r requirements.txt
   cp env.example .env
   # Edit .env with your settings
   alembic upgrade head
   ```

3. **Start the server**
   ```bash
   python main.py
   ```

## 🔐 Default Credentials

- **Admin Email**: admin@example.com
- **Admin Password**: admin123

**⚠️ Important**: Change the default password immediately after first login!

## 📧 Email Client Configuration

### SMTP Settings (Outgoing)
- **Server**: localhost
- **Port**: 587 (or 25)
- **Security**: STARTTLS
- **Authentication**: Username/Password

### IMAP Settings (Incoming)
- **Server**: localhost
- **Port**: 143 (or 993 for SSL)
- **Security**: STARTTLS (or SSL)
- **Authentication**: Username/Password

### POP3 Settings (Incoming)
- **Server**: localhost
- **Port**: 110 (or 995 for SSL)
- **Security**: STARTTLS (or SSL)
- **Authentication**: Username/Password

## 🔧 Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/edaak_mail

# OAuth Providers
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
AZURE_AD_TENANT_ID=your-azure-tenant-id

# Mail Domains
MAIL_DOMAINS=example.com,yourdomain.com

# Security
SECRET_KEY=your-super-secret-key
```

### OAuth Setup

1. **Azure AD**
   - Register app in Azure AD
   - Set redirect URI: `http://localhost:8000/auth/azure/callback`
   - Add client ID and secret to `.env`

2. **Clerk**
   - Create Clerk application
   - Set redirect URI: `http://localhost:8000/auth/clerk/callback`
   - Add client ID and secret to `.env`

3. **Keycloak**
   - Create realm and client in Keycloak
   - Set redirect URI: `http://localhost:8000/auth/keycloak/callback`
   - Add client ID and secret to `.env`

## 📁 Project Structure

```
Edaak/
├── app/
│   ├── core/           # Configuration and database
│   ├── models/         # Database models
│   ├── api/            # REST API endpoints
│   ├── admin/          # Admin center
│   ├── webmail/        # Webmail interface
│   ├── auth/           # Authentication & OAuth
│   ├── protocols/      # SMTP/IMAP/POP3 servers
│   └── services/       # Business logic
├── templates/          # HTML templates
├── static/            # Static files
├── migrations/        # Database migrations
├── logs/              # Application logs
├── main.py            # Application entry point
├── requirements.txt   # Python dependencies
├── Dockerfile         # Docker configuration
└── docker-compose.yml # Docker services
```

## 🛠️ Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **OAuth 2.0/OpenID Connect**: Integration with external identity providers
- **Password Hashing**: bcrypt password hashing
- **Rate Limiting**: Configurable rate limiting
- **TLS/SSL Support**: Encrypted communication
- **SPF/DKIM/DMARC**: Email authentication

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Logs
```bash
# Docker
docker-compose logs -f edaak

# Local
tail -f logs/edaak.log
```

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify DATABASE_URL in .env
   - Ensure database exists

2. **Port Already in Use**
   - Check if ports 25, 143, 110, 587, 993, 995 are available
   - Stop other mail servers (Postfix, Dovecot, etc.)

3. **OAuth Not Working**
   - Verify OAuth provider configuration
   - Check redirect URIs match exactly
   - Ensure client IDs and secrets are correct

4. **Emails Not Sending**
   - Check SMTP server is running
   - Verify domain configuration
   - Check firewall settings

### Getting Help

- Check the logs in `logs/edaak.log`
- Review the API documentation at `/docs`
- Check the README.md for detailed information

## 🔄 Updates

```bash
# Docker
docker-compose pull
docker-compose up -d

# Local
git pull
pip install -r requirements.txt
alembic upgrade head
```

## 📝 License

This project is licensed under the MIT License. 
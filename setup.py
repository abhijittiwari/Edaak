#!/usr/bin/env python3
"""
Setup script for Edaak Mail Server
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"  Error: {e.stderr}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "static",
        "templates",
        "migrations/versions"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def setup_environment():
    """Setup environment file"""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from template...")
        with open(env_example, 'r') as f:
            content = f.read()
        
        # Update with actual values
        content = content.replace(
            "postgresql://username:password@localhost:5432/edaak_mail",
            "postgresql://postgres:password@localhost:5432/edaak_mail"
        )
        
        with open(env_file, 'w') as f:
            f.write(content)
        print("✓ Created .env file")
    else:
        print("✓ .env file already exists")

def install_dependencies():
    """Install Python dependencies"""
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    return True

def setup_database():
    """Setup database"""
    print("Setting up database...")
    
    # Check if PostgreSQL is running
    if not run_command("pg_isready -h localhost", "Checking PostgreSQL connection"):
        print("⚠ PostgreSQL is not running. Please start PostgreSQL and try again.")
        return False
    
    # Create database if it doesn't exist
    if not run_command("createdb -h localhost -U postgres edaak_mail", "Creating database"):
        print("⚠ Database creation failed. It might already exist.")
    
    # Run migrations
    if not run_command("alembic upgrade head", "Running database migrations"):
        print("⚠ Database migration failed.")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Edaak Mail Server...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("✗ Python 3.9 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create directories
    create_directories()
    
    # Setup environment
    setup_environment()
    
    # Install dependencies
    if not install_dependencies():
        print("✗ Failed to install dependencies")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        print("⚠ Database setup had issues. You may need to configure it manually.")
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Start the server: python main.py")
    print("3. Access webmail at: http://localhost:8000")
    print("4. Access admin at: http://localhost:8000/admin")
    print("\nDefault admin credentials:")
    print("  Email: admin@example.com")
    print("  Password: admin123")
    print("\nRemember to change the default password!")

if __name__ == "__main__":
    main() 
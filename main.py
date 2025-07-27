#!/usr/bin/env python3
"""
Edaak Mail Server - Main Application Entry Point
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api.routes import api_router
from app.admin.routes import admin_router
from app.webmail.routes import webmail_router
from app.protocols.smtp_server import start_smtp_server
from app.protocols.imap_server import start_imap_server
from app.protocols.pop3_server import start_pop3_server
from app.services.admin_service import create_default_admin

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global variables to store server tasks
smtp_server_task = None
imap_server_task = None
pop3_server_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Edaak Mail Server...")
    
    # Initialize database
    await init_db()
    
    # Create default admin if first run
    if settings.FIRST_RUN:
        await create_default_admin()
        logger.info("Default admin account created")
    
    # Start protocol servers
    global smtp_server_task, imap_server_task, pop3_server_task
    
    smtp_server_task = asyncio.create_task(start_smtp_server())
    imap_server_task = asyncio.create_task(start_imap_server())
    pop3_server_task = asyncio.create_task(start_pop3_server())
    
    logger.info("All servers started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Edaak Mail Server...")
    
    # Cancel protocol server tasks
    if smtp_server_task:
        smtp_server_task.cancel()
    if imap_server_task:
        imap_server_task.cancel()
    if pop3_server_task:
        pop3_server_task.cancel()
    
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    # Create static and templates directories if they don't exist
    Path("static").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    app = FastAPI(
        title="Edaak Mail Server",
        description="A comprehensive mail server with OAuth support and webmail interface",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/admin")
    app.include_router(webmail_router, prefix="/webmail")
    
    # Root redirect to webmail
    @app.get("/")
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/webmail")
    
    return app


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main application entry point"""
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create application
    app = create_app()
    
    # Run the application
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
        ssl_keyfile=settings.SSL_KEY_FILE if settings.SSL_ENABLED else None,
        ssl_certfile=settings.SSL_CERT_FILE if settings.SSL_ENABLED else None,
    )


if __name__ == "__main__":
    main() 
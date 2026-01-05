"""
Configuration management for the Alert Bot.
Centralizes all environment variables and settings.
"""

import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration from environment variables."""
    
    # Slack credentials
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
    SLACK_ALERT_CHANNEL = os.environ.get("SLACK_ALERT_CHANNEL", "alerts")
    
    # Server settings
    WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", 3000))
    WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
    
    # Feature flags
    SLACK_STUB = os.environ.get("SLACK_STUB", "0") == "1"
    
    # Alert settings
    MAX_ALERTS = int(os.environ.get("MAX_ALERTS", 100))
    APP_HOME_LIMIT = int(os.environ.get("APP_HOME_LIMIT", 50))
    
    @classmethod
    def validate(cls, require_slack_tokens=True):
        """
        Validate required configuration.
        
        Args:
            require_slack_tokens: If False, skip Slack token validation (for stub mode)
        """
        errors = []
        
        if require_slack_tokens and not cls.SLACK_STUB:
            if not cls.SLACK_BOT_TOKEN:
                errors.append("SLACK_BOT_TOKEN is not set")
            if not cls.SLACK_APP_TOKEN:
                errors.append("SLACK_APP_TOKEN is not set")
            if not cls.SLACK_SIGNING_SECRET:
                errors.append("SLACK_SIGNING_SECRET is not set")
        
        if errors:
            for error in errors:
                logger.error(f"❌ {error}")
            raise ValueError("Missing required configuration. Check environment variables.")
        
        logger.info("✅ Configuration validated")
    
    @classmethod
    def print_config(cls):
        """Print non-sensitive configuration."""
        logger.info("=" * 60)
        logger.info("ALERT BOT CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"  Webhook Port: {cls.WEBHOOK_PORT}")
        logger.info(f"  Webhook Host: {cls.WEBHOOK_HOST}")
        logger.info(f"  Alert Channel: #{cls.SLACK_ALERT_CHANNEL}")
        logger.info(f"  Stub Mode: {cls.SLACK_STUB}")
        logger.info(f"  Max Alerts: {cls.MAX_ALERTS}")
        logger.info(f"  App Home Limit: {cls.APP_HOME_LIMIT}")
        logger.info("=" * 60)
    
    @classmethod
    def get_stub_tokens(cls):
        """Get stub tokens for testing."""
        return {
            "bot_token": cls.SLACK_BOT_TOKEN or "xoxb-stub",
            "app_token": cls.SLACK_APP_TOKEN or "xapp-stub",
            "signing_secret": cls.SLACK_SIGNING_SECRET or "stub-secret"
        }


"""
Alert Bot - Main Entry Point
A Slack-first alerting bot with webhook ingestion, slash commands, and App Home.

This is the refactored version with proper separation of concerns.
"""

import logging
import threading
from alert_store import AlertStore
from src.config import Config
from src.alert_service import AlertService
from slack_bot import create_slack_app, start_slack_bot
import webhook_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    try:
        # Print banner
        logger.info("=" * 60)
        logger.info("ALERT BOT - Phase 1 (Refactored)")
        logger.info("=" * 60)
        
        # Validate and print configuration
        Config.validate(require_slack_tokens=not Config.SLACK_STUB)
        Config.print_config()
        
        # Initialize core components
        alert_store = AlertStore()
        logger.info("✅ Alert store initialized")
        
        # Create Slack app and get client
        slack_app = create_slack_app(None)  # Temp, will set service after
        slack_client = slack_app.client
        
        # Create alert service
        alert_service = AlertService(slack_client, alert_store)
        logger.info("✅ Alert service initialized")
        
        # Re-create Slack app with alert service
        slack_app = create_slack_app(alert_service)
        
        # Initialize webhook server
        webhook_server.init_webhook_server(alert_service)
        logger.info("✅ Webhook server initialized")
        
        if Config.SLACK_STUB:
            logger.info("")
            logger.info("🧪 RUNNING IN STUB MODE")
            logger.info("   - No real Slack API calls will be made")
            logger.info("   - Webhook server: http://localhost:{Config.WEBHOOK_PORT}")
            logger.info("   - Test with: ./scripts/send_alert.sh")
            logger.info("")
            
            # In stub mode, just run webhook server (no Socket Mode)
            webhook_server.run_server()
            
        else:
            logger.info("")
            logger.info("🚀 STARTING PRODUCTION MODE")
            logger.info(f"   - Webhook: http://localhost:{Config.WEBHOOK_PORT}/webhook/alert")
            logger.info(f"   - Alert Channel: #{Config.SLACK_ALERT_CHANNEL}")
            logger.info("")
            
            # Start Flask webhook server in background thread
            flask_thread = threading.Thread(
                target=webhook_server.run_server,
                daemon=True,
                name="WebhookServer"
            )
            flask_thread.start()
            logger.info(f"✅ Webhook server started on port {Config.WEBHOOK_PORT}")
            
            # Start Slack Socket Mode handler (blocks until interrupted)
            start_slack_bot(slack_app, alert_service)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")
    except Exception as error:
        logger.error(f"❌ Failed to start application: {error}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()


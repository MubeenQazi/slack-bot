"""
Slack bot initialization and Socket Mode handler.
Registers all command and event handlers.
"""

import ssl
import logging
import certifi
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web import WebClient

from src.config import Config
from src.alert_service import AlertService
from src.handlers.commands import register_commands
from src.handlers.events import register_events

logger = logging.getLogger(__name__)


class StubSlackClient:
    """Stub Slack client that logs instead of making API calls."""
    
    def chat_postMessage(self, **kwargs):
        logger.info(f"[STUB] chat.postMessage: channel={kwargs.get('channel')}, text={kwargs.get('text')}")
        return {'ok': True, 'ts': '1234567890.123456'}
    
    def views_publish(self, **kwargs):
        logger.info(f"[STUB] views.publish: user_id={kwargs.get('user_id')}")
        return {'ok': True}
    
    def users_info(self, **kwargs):
        logger.info(f"[STUB] users.info: user={kwargs.get('user')}")
        return {
            'ok': True,
            'user': {
                'id': kwargs.get('user'),
                'name': 'stub_user',
                'real_name': 'Stub User',
                'profile': {'display_name': 'Stub User'}
            }
        }


class StubApp:
    """Stub Slack app for testing without real Slack."""
    
    def __init__(self):
        self.client = StubSlackClient()
        self._command_handlers = {}
        self._event_handlers = {}
    
    def command(self, command_name):
        def decorator(func):
            self._command_handlers[command_name] = func
            logger.info(f"[STUB] Registered command: {command_name}")
            return func
        return decorator
    
    def event(self, event_type):
        def decorator(func):
            self._event_handlers[event_type] = func
            logger.info(f"[STUB] Registered event: {event_type}")
            return func
        return decorator


def create_slack_app(alert_service: AlertService):
    """
    Create and configure Slack app with all handlers.
    
    Args:
        alert_service: AlertService instance
        
    Returns:
        Configured Slack app instance
    """
    if Config.SLACK_STUB:
        logger.info("Creating Slack app in STUB mode")
        app = StubApp()
    else:
        # Fix SSL certificate verification on macOS
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Create WebClient with SSL context
        web_client = WebClient(
            token=Config.SLACK_BOT_TOKEN,
            ssl=ssl_context
        )
        
        # Create Slack app
        app = App(
            client=web_client,
            signing_secret=Config.SLACK_SIGNING_SECRET
        )
        
        logger.info("Created Slack app with real API client")
    
    # Register all handlers
    register_commands(app, alert_service)
    register_events(app, alert_service)
    
    logger.info("✅ All Slack handlers registered")
    
    return app


def start_slack_bot(app, alert_service: AlertService):
    """
    Start Slack bot with Socket Mode.
    
    Args:
        app: Slack Bolt app instance
        alert_service: AlertService instance
    """
    if Config.SLACK_STUB:
        logger.info("Slack bot in STUB mode - Socket Mode not started")
        logger.info("Commands and events will be logged but not executed")
        return
    
    try:
        handler = SocketModeHandler(app, Config.SLACK_APP_TOKEN)
        logger.info("✅ Starting Slack Socket Mode...")
        handler.start()  # Blocks until interrupted
        
    except KeyboardInterrupt:
        logger.info("\n👋 Slack bot shutting down...")
    except Exception as error:
        logger.error(f"Failed to start Slack bot: {error}")
        raise


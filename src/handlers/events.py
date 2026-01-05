"""
Slack event handlers.
"""

import logging
from src.config import Config
from src.alert_service import AlertService

logger = logging.getLogger(__name__)


def register_events(app, alert_service: AlertService):
    """
    Register all event handlers.
    
    Args:
        app: Slack Bolt app instance
        alert_service: AlertService instance
    """
    
    @app.event("app_home_opened")
    def handle_app_home_opened(event, client):
        """
        Handle App Home opened event.
        Updates the home tab with current active alerts.
        """
        try:
            user_id = event['user']
            
            # Track viewer for future auto-refreshes
            alert_service.track_app_home_viewer(user_id)
            logger.info(f"Recorded App Home viewer: {user_id}")
            
            # Update App Home for this user
            alert_service.update_app_home_for_user(user_id)
            
        except Exception as error:
            logger.error(f"Error updating App Home: {error}")


"""
Alert service - Business logic layer.
Handles alert creation, Slack notifications, and App Home updates.
"""

import logging
from typing import Dict, Set
from src.config import Config
from alert_store import AlertStore
from slack_formatter import format_alert_message, format_app_home_view

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service layer for alert management.
    Coordinates between alert storage, Slack notifications, and App Home updates.
    """
    
    def __init__(self, slack_client, alert_store: AlertStore):
        """
        Initialize alert service.
        
        Args:
            slack_client: Slack WebClient instance
            alert_store: AlertStore instance
        """
        self.slack_client = slack_client
        self.alert_store = alert_store
        self.app_home_viewers: Set[str] = set()
    
    def create_alert(self, service: str, severity: str, message: str) -> Dict:
        """
        Create an alert and publish it to Slack.
        Shared code path for webhook and slash command.
        
        Args:
            service: Service name
            severity: Alert severity
            message: Alert message
        
        Returns:
            Created alert dictionary
        """
        # Add to store
        alert = self.alert_store.add_alert(service, severity, message)
        logger.info(f"Created alert {alert['id']}: {service} - {severity}")
        
        # Publish to Slack channel
        self._publish_alert_to_channel(alert)
        
        # Refresh App Home for any users who have it open
        self._update_all_app_home_viewers()
        
        return alert
    
    def track_app_home_viewer(self, user_id: str):
        """Track a user who has opened App Home."""
        self.app_home_viewers.add(user_id)
    
    def update_app_home_for_user(self, user_id: str):
        """
        Update App Home for a specific user.
        
        Args:
            user_id: Slack user ID
        """
        try:
            alerts = self.alert_store.get_active_alerts()
            view = format_app_home_view(alerts)
            
            if Config.SLACK_STUB:
                logger.info(f"[STUB] Would update App Home for user {user_id} with {len(alerts)} alerts")
                return
            
            self.slack_client.views_publish(user_id=user_id, view=view)
            logger.info(f"Updated App Home for user {user_id} with {len(alerts)} alerts")
            
        except Exception as error:
            logger.error(f"Failed to update App Home for user {user_id}: {error}")
    
    def _publish_alert_to_channel(self, alert: Dict):
        """
        Publish an alert to the configured Slack channel.
        
        Args:
            alert: Alert dictionary
        """
        if Config.SLACK_STUB:
            logger.info(f"[STUB] Would post alert to #{Config.SLACK_ALERT_CHANNEL}:")
            logger.info(f"[STUB] Alert: {alert}")
            return
        
        try:
            blocks = format_alert_message(alert)
            self.slack_client.chat_postMessage(
                channel=Config.SLACK_ALERT_CHANNEL,
                text=f"New {alert['severity']} alert from {alert['service']}",
                blocks=blocks
            )
            logger.info(f"Alert {alert['id']} posted to #{Config.SLACK_ALERT_CHANNEL}")
            
        except Exception as error:
            logger.error(f"Failed to post alert to Slack: {error}")
    
    def _update_all_app_home_viewers(self):
        """Update App Home for all users who have opened it."""
        if not self.app_home_viewers:
            logger.debug("No App Home viewers recorded yet")
            return
        
        logger.info(f"Refreshing App Home for {len(self.app_home_viewers)} viewers")
        
        for user_id in list(self.app_home_viewers):
            self.update_app_home_for_user(user_id)


"""
Slack slash command handlers.
"""

import logging
import threading
from src.config import Config
from src.alert_service import AlertService

logger = logging.getLogger(__name__)


def register_commands(app, alert_service: AlertService):
    """
    Register all slash command handlers.
    
    Args:
        app: Slack Bolt app instance
        alert_service: AlertService instance
    """
    
    @app.command("/alert")
    def handle_alert_command(ack, command, respond, client):
        """
        Handle /alert slash command for manual alert creation.
        
        Usage: /alert service=api severity=high message=test
        
        Note: Heavy work is done in background thread to avoid dispatch_failed timeout.
        """
        ack()  # Acknowledge immediately (return quickly)
        
        def process_alert():
            """Background thread to process alert (avoid dispatch_failed timeout)."""
            try:
                text = command.get('text', '').strip()
                
                if not text:
                    # Use client.chat_postMessage (not respond) for background thread
                    client.chat_postMessage(
                        channel=command['channel_id'],
                        text="Usage: `/alert service=<name> severity=<level> message=<text>`\n" +
                             "Example: `/alert service=api severity=high message=Response time critical`"
                    )
                    return
                
                # Parse parameters
                params = _parse_alert_params(text)
                
                if not params:
                    # Use client.chat_postMessage for background thread
                    client.chat_postMessage(
                        channel=command['channel_id'],
                        text="Invalid format. Use: `/alert service=<name> severity=<level> message=<text>`"
                    )
                    return
                
                # Create alert (shared code path with webhook)
                alert = alert_service.create_alert(
                    service=params['service'],
                    severity=params['severity'],
                    message=params['message']
                )
                
                # Update App Home for the invoking user
                alert_service.update_app_home_for_user(command['user_id'])
                
                # Respond to user using client (not respond which has 3-second timeout)
                if Config.SLACK_STUB:
                    client.chat_postMessage(
                        channel=command['channel_id'],
                        text=f"Alert created (ID: {alert['id']})\n" +
                             f"Service: `{alert['service']}` | Severity: `{alert['severity']}`\n" +
                             f"Message: {alert['message']}"
                    )
                else:
                    client.chat_postMessage(
                        channel=command['channel_id'],
                        text=f"Alert created and posted to #{Config.SLACK_ALERT_CHANNEL} (ID: {alert['id']})\n" +
                             f"Service: `{alert['service']}` | Severity: `{alert['severity']}`\n" +
                             f"Message: {alert['message']}"
                    )
                
            except Exception as error:
                logger.exception("Error processing /alert in background thread")
                try:
                    client.chat_postMessage(
                        channel=command['channel_id'],
                        text="Failed to create alert. Please try again."
                    )
                except Exception as e:
                    logger.error(f"Failed to send error response: {e}")
        
        # Start background thread (returns immediately from handler)
        thread = threading.Thread(target=process_alert, daemon=True)
        thread.start()
    
    @app.command("/hello")
    def handle_hello_command(ack, command, respond, client):
        """Legacy /hello command for backward compatibility."""
        ack()
        
        try:
            if Config.SLACK_STUB:
                logger.info(f"[STUB] Would respond to /hello from user {command['user_id']}")
                respond(text="[STUB] Hello, User!")
                return
            
            user_info = client.users_info(user=command["user_id"])
            user_profile = user_info["user"]["profile"]
            display_name = (
                user_profile.get("display_name") or 
                user_info["user"].get("real_name") or 
                user_info["user"].get("name")
            )
            respond(text=f"Hello, {display_name}!")
            
        except Exception as error:
            logger.error(f"Error handling /hello command: {error}")
            respond(text="Sorry, something went wrong.", response_type="ephemeral")


def _parse_alert_params(text: str) -> dict:
    """
    Parse /alert command parameters.
    
    Expected format: service=api severity=high message=Test alert
    
    Args:
        text: Command text
        
    Returns:
        Dictionary with service, severity, message or None if invalid
    """
    params = {}
    parts = text.split()
    
    message_start = None
    for idx, part in enumerate(parts):
        if '=' in part:
            key, value = part.split('=', 1)
            if key == 'message':
                message_start = idx
                params['message'] = value
                break
            params[key] = value
    
    # If message= appeared, append remaining words to message
    if message_start is not None:
        tail = parts[message_start + 1:]
        if tail:
            params['message'] = ' '.join([params['message']] + tail)
    
    # Check required parameters
    required = ['service', 'severity', 'message']
    missing = [r for r in required if r not in params]
    
    if missing:
        # Try parsing as free-form text if structured parsing fails
        if len(parts) >= 3:
            params = {
                'service': parts[0],
                'severity': parts[1],
                'message': ' '.join(parts[2:])
            }
            missing = []
    
    if missing:
        return None
    
    return params


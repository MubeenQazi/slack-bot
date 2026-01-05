"""
Phase 1: Alert Bot
A Slack-first alerting bot with webhook ingestion, slash commands, and App Home.
"""
import os
import ssl
import logging
import certifi
import threading
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web import WebClient

from alert_store import AlertStore
from slack_formatter import format_alert_message, format_app_home_view

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix SSL certificate verification on macOS
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Get environment variables
bot_token = os.environ.get("SLACK_BOT_TOKEN")
app_token = os.environ.get("SLACK_APP_TOKEN")
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
alert_channel = os.environ.get("SLACK_ALERT_CHANNEL", "alerts")  # Default channel
stub_mode = os.environ.get("SLACK_STUB", "0") == "1"

# Track users who have opened App Home (in-memory for Phase 1)
last_home_viewers = set()

# Validate environment variables (not needed in stub mode)
if not stub_mode:
    if not bot_token:
        logger.error("SLACK_BOT_TOKEN is not set!")
        exit(1)
    if not app_token:
        logger.error("SLACK_APP_TOKEN is not set!")
        exit(1)
    if not signing_secret:
        logger.error("SLACK_SIGNING_SECRET is not set!")
        exit(1)
    logger.info("All environment variables loaded successfully")
else:
    logger.info("STUB MODE ENABLED - Slack API calls will be logged, not executed")
    # Use dummy values for stub mode
    bot_token = bot_token or "xoxb-stub"
    app_token = app_token or "xapp-stub"
    signing_secret = signing_secret or "stub-secret"

# Initialize alert store
alert_store = AlertStore()

# Create Flask app for webhook endpoint
flask_app = Flask(__name__)

# Create Slack app
if not stub_mode:
    web_client = WebClient(token=bot_token, ssl=ssl_context)
    slack_app = App(client=web_client, signing_secret=signing_secret)
else:
    # In stub mode, create a minimal app without token validation
    from slack_sdk.web.client import WebClient as StubWebClient
    
    class StubSlackClient:
        """Stub Slack client that logs instead of making API calls."""
        def __init__(self):
            pass
        
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
    
    slack_app = StubApp()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def publish_alert_to_slack(alert: dict):
    """
    Publish an alert to the configured Slack channel.
    
    Args:
        alert: Alert dictionary
    """
    if stub_mode:
        logger.info(f"[STUB] Would post alert to #{alert_channel}:")
        logger.info(f"[STUB] Alert: {alert}")
        return
    
    try:
        blocks = format_alert_message(alert)
        slack_app.client.chat_postMessage(
            channel=alert_channel,
            text=f"New {alert['severity']} alert from {alert['service']}",
            blocks=blocks
        )
        logger.info(f"Alert {alert['id']} posted to #{alert_channel}")
    except Exception as e:
        logger.error(f"Failed to post alert to Slack: {e}")


def update_app_home_for_all_users():
    """
    Update App Home for all users who have opened it.
    Note: In Phase 1, we update on-demand when users open App Home.
    """
    pass  # App Home updates are event-driven (see app_home_opened handler)


def update_app_home_for_user(client, user_id: str):
    """
    Update App Home for a specific user. Used after creating an alert so the
    user sees the latest state without needing to re-open Home manually.
    """
    alerts = alert_store.get_active_alerts()
    view = format_app_home_view(alerts)
    
    if stub_mode:
        logger.info(f"[STUB] Would update App Home for user {user_id} with {len(alerts)} alerts")
        return
    
    try:
        client.views_publish(user_id=user_id, view=view)
        logger.info(f"Updated App Home for user {user_id} with {len(alerts)} alerts")
    except Exception as error:
        logger.error(f"Failed to update App Home for user {user_id}: {error}")


def update_app_home_for_viewers(client):
    """
    Update App Home for all users who have opened it during this run.
    This keeps dashboards fresh after webhook-created alerts too.
    """
    if not last_home_viewers:
        logger.info("No App Home viewers recorded yet; skipping home refresh")
        return
    logger.info(f"Refreshing App Home for viewers: {list(last_home_viewers)}")
    for user_id in list(last_home_viewers):
        if stub_mode:
            logger.info(f"[STUB] Would update App Home for user {user_id}")
            continue
        try:
            alerts = alert_store.get_active_alerts()
            view = format_app_home_view(alerts)
            client.views_publish(user_id=user_id, view=view)
            logger.info(f"Updated App Home for user {user_id} with {len(alerts)} alerts")
        except Exception as error:
            logger.error(f"Failed to update App Home for user {user_id}: {error}")


def create_alert_from_params(service: str, severity: str, message: str) -> dict:
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
    alert = alert_store.add_alert(service, severity, message)
    logger.info(f"Created alert {alert['id']}: {service} - {severity}")
    
    # Publish to Slack
    publish_alert_to_slack(alert)
    
    # Refresh App Home for any users who have it open (webhook or slash)
    update_app_home_for_viewers(slack_app.client)
    
    return alert


# ============================================================================
# FLASK WEBHOOK ENDPOINT
# ============================================================================

@flask_app.route('/webhook/alert', methods=['POST'])
def webhook_alert():
    """
    HTTP webhook endpoint for alert ingestion.
    
    Expected JSON payload:
    {
        "service": "api",
        "severity": "high",
        "message": "Response time above threshold"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400
        
        required_fields = ['service', 'severity', 'message']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create alert (shared code path)
        alert = create_alert_from_params(
            service=data['service'],
            severity=data['severity'],
            message=data['message']
        )
        
        return jsonify({
            'success': True,
            'alert_id': alert['id'],
            'alert': alert
        }), 201
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({
            'error': 'Failed to process alert',
            'message': str(e)
        }), 500


@flask_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'alert_count': alert_store.get_alert_count(),
        'active_alerts': alert_store.get_active_count(),
        'stub_mode': stub_mode
    }), 200


# ============================================================================
# SLACK SLASH COMMANDS
# ============================================================================

@slack_app.command("/alert")
def handle_alert_command(ack, command, respond, logger):
    """
    Handle /alert slash command for manual alert creation.
    
    Usage: /alert service=api severity=high message=test
    """
    # Acknowledge immediately
    ack()

    try:
        # Parse command text
        text = command.get('text', '').strip()
        
        if not text:
            respond(
                text="Usage: `/alert service=<name> severity=<level> message=<text>`\n" +
                     "Example: `/alert service=api severity=high message=Response time critical`",
                response_type="ephemeral"
            )
            return
        
        # Simple key=value parser (message can include spaces)
        params = {}
        parts = text.split()
        
        message_start = None
        for idx, part in enumerate(parts):
            if '=' in part:
                key, value = part.split('=', 1)
                if key == 'message':
                    # Capture the rest of the text for message
                    message_start = idx
                    params['message'] = value
                    break
                params[key] = value
        
        # If message= appeared, append remaining words to message
        if message_start is not None:
            tail = parts[message_start + 1 :]
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
            respond(
                text=f"❌ Missing required parameters: {', '.join(missing)}\n" +
                     f"Usage: `/alert service=<name> severity=<level> message=<text>`",
                response_type="ephemeral"
            )
            return
        
        # Create alert (shared code path with webhook)
        alert = create_alert_from_params(
            service=params['service'],
            severity=params['severity'],
            message=params['message']
        )
        
        # Update App Home for the invoking user so they see fresh data
        update_app_home_for_user(slack_app.client, command['user_id'])
        
        # Respond to user
        if stub_mode:
            respond(
                text=f"✅ [STUB MODE] Alert created (ID: {alert['id']})\n" +
                     f"Service: `{alert['service']}` | Severity: `{alert['severity']}`\n" +
                     f"Message: {alert['message']}",
                response_type="ephemeral"
            )
        else:
            respond(
                text=f"✅ Alert created and posted to <#{alert_channel}> (ID: {alert['id']})\n" +
                     f"Service: `{alert['service']}` | Severity: `{alert['severity']}`\n" +
                     f"Message: {alert['message']}",
                response_type="ephemeral"
            )
        
    except Exception as error:
        logger.exception("Error handling /alert command")
        try:
            respond(
                text="❌ Failed to create alert. Please try again.",
                response_type="ephemeral"
            )
        except Exception as respond_error:
            logger.error(f"Also failed to respond to /alert: {respond_error}")


# ============================================================================
# APP HOME
# ============================================================================

@slack_app.event("app_home_opened")
def handle_app_home_opened(event, client, logger):
    """
    Handle App Home opened event.
    Updates the home tab with current active alerts.
    """
    try:
        user_id = event['user']
        # Track viewer for future auto-refreshes
        last_home_viewers.add(user_id)
        logger.info(f"Recorded App Home viewer: {user_id}")
        
        # Get active alerts
        alerts = alert_store.get_active_alerts()
        
        # Format view
        view = format_app_home_view(alerts)
        
        if stub_mode:
            logger.info(f"[STUB] Would update App Home for user {user_id}")
            logger.info(f"[STUB] Active alerts: {len(alerts)}")
        else:
            # Publish view
            client.views_publish(
                user_id=user_id,
                view=view
            )
            logger.info(f"Updated App Home for user {user_id} with {len(alerts)} alerts")
        
    except Exception as error:
        logger.error(f"Error updating App Home: {error}")


# ============================================================================
# KEEP OLD /hello COMMAND FOR BACKWARD COMPATIBILITY
# ============================================================================

@slack_app.command("/hello")
def handle_hello_command(ack, command, respond, client, logger):
    """Legacy /hello command from previous phase."""
@slack_app.command("/hello")
def handle_hello_command(ack, command, respond, client, logger):
    """Legacy /hello command from previous phase."""
    try:
        ack()
        
        if stub_mode:
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


# ============================================================================
# MAIN APPLICATION STARTUP
# ============================================================================

def run_flask():
    """Run Flask webhook server in a separate thread."""
    flask_app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("ALERT BOT - Phase 1")
        logger.info("=" * 60)
        logger.info(f"Stub Mode: {stub_mode}")
        logger.info(f"Alert Channel: #{alert_channel}")
        logger.info(f"Webhook: http://localhost:3000/webhook/alert")
        logger.info("=" * 60)
        
        if stub_mode:
            logger.info("Running in STUB mode - no real Slack API calls")
            logger.info("Start Flask webhook server with: python app.py")
            logger.info("Send test alert with: ./scripts/send_alert.sh")
            # In stub mode, just run Flask (no Socket Mode)
            flask_app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False, threaded=True)
        else:
            # Start Flask in background thread
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            logger.info("✅ Flask webhook server started on port 3000")
            
            # Start Slack Socket Mode handler (blocks)
            handler = SocketModeHandler(slack_app, app_token)
            logger.info("✅ Starting Slack Socket Mode...")
            handler.start()
        
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")
    except Exception as error:
        logger.error(f"Failed to start the bot: {error}")
        exit(1)


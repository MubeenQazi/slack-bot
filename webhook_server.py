"""
Flask webhook server for receiving alerts via HTTP POST.
Separate from Slack bot for better separation of concerns.
"""

import logging
from flask import Flask, request, jsonify
from src.config import Config
from src.alert_service import AlertService
from alert_store import AlertStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global instances (will be set by main app)
alert_service: AlertService = None


def init_webhook_server(service: AlertService):
    """
    Initialize webhook server with alert service.
    
    Args:
        service: AlertService instance
    """
    global alert_service
    alert_service = service
    logger.info("Webhook server initialized")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    if alert_service:
        alert_count = alert_service.alert_store.get_alert_count()
        active_count = alert_service.alert_store.get_active_count()
    else:
        alert_count = 0
        active_count = 0
    
    return jsonify({
        'status': 'healthy',
        'alert_count': alert_count,
        'active_alerts': active_count,
        'stub_mode': Config.SLACK_STUB
    }), 200


@app.route('/webhook/alert', methods=['POST'])
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
        
        # Validate severity
        valid_severities = ['critical', 'high', 'medium', 'low', 'info']
        if data['severity'].lower() not in valid_severities:
            return jsonify({
                'error': f'Invalid severity. Must be one of: {", ".join(valid_severities)}'
            }), 400
        
        # Create alert (shared code path)
        alert = alert_service.create_alert(
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


@app.route('/alerts', methods=['GET'])
def list_alerts():
    """
    List recent alerts.
    
    Query params:
        limit: Number of alerts to return (default: 50)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        alerts = alert_service.alert_store.get_active_alerts()[:limit]
        
        return jsonify({
            'success': True,
            'count': len(alerts),
            'alerts': alerts
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


def run_server():
    """Start the Flask webhook server."""
    try:
        Config.print_config()
        logger.info(f"Starting webhook server on {Config.WEBHOOK_HOST}:{Config.WEBHOOK_PORT}")
        
        app.run(
            host=Config.WEBHOOK_HOST,
            port=Config.WEBHOOK_PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}")
        raise


if __name__ == "__main__":
    # For standalone testing
    from alert_store import AlertStore
    from src.alert_service import AlertService
    
    # Create stub client for standalone mode
    class StubClient:
        def chat_postMessage(self, **kwargs):
            logger.info(f"[STUB] chat_postMessage: {kwargs}")
        def views_publish(self, **kwargs):
            logger.info(f"[STUB] views_publish: {kwargs}")
    
    store = AlertStore()
    service = AlertService(StubClient(), store)
    init_webhook_server(service)
    
    run_server()


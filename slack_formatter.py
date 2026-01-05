"""
Block Kit message formatter for alerts.
Creates rich, formatted Slack messages.
"""
from typing import Dict, List


def get_severity_emoji(severity: str) -> str:
    """Get emoji for alert severity."""
    severity_lower = severity.lower()
    emoji_map = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢',
        'info': 'ℹ️'
    }
    return emoji_map.get(severity_lower, '⚪')


def get_severity_color(severity: str) -> str:
    """Get color code for alert severity."""
    severity_lower = severity.lower()
    color_map = {
        'critical': '#FF0000',
        'high': '#FF6600',
        'medium': '#FFCC00',
        'low': '#00CC00',
        'info': '#0066CC'
    }
    return color_map.get(severity_lower, '#808080')


def format_alert_message(alert: Dict) -> List[Dict]:
    """
    Format an alert as Block Kit blocks.
    
    Args:
        alert: Alert dictionary with service, severity, message, timestamp
    
    Returns:
        List of Block Kit blocks
    """
    emoji = get_severity_emoji(alert['severity'])
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} New Alert: {alert['service']}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{alert['severity'].upper()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Service:*\n{alert['service']}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Message:*\n{alert['message']}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Alert ID: {alert['id']} | {alert['timestamp']}"
                }
            ]
        }
    ]
    
    return blocks


def format_app_home_view(alerts: List[Dict]) -> Dict:
    """
    Format App Home view with active alerts.
    
    Args:
        alerts: List of alert dictionaries
    
    Returns:
        App Home view payload
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Alert Dashboard",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Active Alerts:* {len(alerts)}"
            }
        },
        {
            "type": "divider"
        }
    ]
    
    if not alerts:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ _No active alerts. All systems operational._"
            }
        })
    else:
        for alert in alerts[:20]:  # Show max 20 alerts
            emoji = get_severity_emoji(alert['severity'])
            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{alert['service']}* - {alert['severity'].upper()}\n{alert['message']}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"ID: {alert['id']} | {alert['timestamp']}"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ])
        
        if len(alerts) > 20:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_... and {len(alerts) - 20} more alerts_"
                }
            })
    
    return {
        "type": "home",
        "blocks": blocks
    }

#!/bin/bash
# Helper script to send test alerts to the webhook endpoint

# Default values
HOST="${ALERT_HOST:-localhost:3000}"
SERVICE="${1:-api}"
SEVERITY="${2:-high}"
MESSAGE="${3:-Test alert from send_alert.sh}"

echo "Sending alert to http://$HOST/webhook/alert"
echo "Service: $SERVICE"
echo "Severity: $SEVERITY"
echo "Message: $MESSAGE"
echo ""

curl -X POST "http://$HOST/webhook/alert" \
  -H "Content-Type: application/json" \
  -d "{
    \"service\": \"$SERVICE\",
    \"severity\": \"$SEVERITY\",
    \"message\": \"$MESSAGE\"
  }" \
  -w "\n\nHTTP Status: %{http_code}\n"

echo ""
echo "Usage: ./scripts/send_alert.sh [service] [severity] [message]"
echo "Example: ./scripts/send_alert.sh database critical 'Connection pool exhausted'"

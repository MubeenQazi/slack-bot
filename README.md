# Alert Bot - Phase 1

A Slack-first alerting bot with webhook ingestion, slash commands, and App Home dashboard.

## ⚡ Quick Start (≤2 commands)

### Option 1: Stub Mode (No Slack Required)
```bash
export SLACK_STUB=1 && python app.py
```

### Option 2: Live Slack Mode
```bash
export SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xapp-... SLACK_SIGNING_SECRET=... SLACK_ALERT_CHANNEL=alerts
python app.py
```

## Features

✅ **Alert Ingestion**: HTTP webhook endpoint (POST /webhook/alert)  
✅ **Slack Notifications**: Rich Block Kit messages posted to channel  
✅ **Slash Command**: `/alert` for manual test alerts  
✅ **App Home**: Dashboard showing active alerts  
✅ **Stub Mode**: Test without real Slack API calls  
✅ **Shared Code Path**: Webhook & slash command use identical logic  

## Prerequisites

- Python 3.8+
- Slack workspace (for live mode)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

**Required (Live Mode):**
```bash
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_APP_TOKEN=xapp-your-token
export SLACK_SIGNING_SECRET=your-signing-secret
```

**Optional:**
```bash
export SLACK_ALERT_CHANNEL=alerts    # Default: "alerts"
export SLACK_STUB=1                   # Enable stub mode
```

**⚠️ NEVER commit secrets to git!** Use shell environment or secret manager.

## Slack App Setup

### 1. Import Manifest
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From an app manifest"
3. Select your workspace
4. Paste contents of `slack/manifest.yml`
5. Review & create

### 2. Get Tokens
- **Bot Token**: OAuth & Permissions → "Bot User OAuth Token" (starts with `xoxb-`)
- **App Token**: Basic Information → App-Level Tokens → Generate (needs `connections:write` scope, starts with `xapp-`)
- **Signing Secret**: Basic Information → "Signing Secret"

### 3. Install App
1. OAuth & Permissions → "Install to Workspace"
2. Authorize the app
3. Invite bot to your alerts channel: `/invite @Alert Bot`

### 4. Verify Scopes
The manifest includes these required scopes:
- `app_mentions:read` - Detect @mentions
- `chat:write` - Post messages
- `commands` - Handle slash commands
- `users:read` - Get user info (legacy /hello)
- `im:write` - Send DMs (legacy /hello)

## Usage

### Send Alert via Webhook
```bash
./scripts/send_alert.sh api high "Response time above threshold"
```

Or with curl:
```bash
curl -X POST http://localhost:3000/webhook/alert \
  -H "Content-Type: application/json" \
  -d '{
    "service": "database",
    "severity": "critical",
    "message": "Connection pool exhausted"
  }'
```

### Send Alert via Slack Command
In Slack, type:
```
/alert service=api severity=high message=test
```

### View Alerts
Open the **Alert Bot** App Home tab in Slack to see all active alerts.

## Testing

### 1. Test in Stub Mode (No Slack)
```bash
export SLACK_STUB=1
python app.py
# In another terminal:
./scripts/send_alert.sh
```

Check logs for `[STUB]` output showing what would be sent to Slack.

### 2. Test Slash Command
```
/alert service=api severity=high message=test
```

### 3. Test App Home
1. Click App Home tab
2. Should show active alerts
3. Create new alert (webhook or /alert)
4. Re-click App Home → new alert appears

### 4. Health Check
```bash
curl http://localhost:3000/health
```

## How to Verify (3 Minutes or Less)

1. **Start app**: `export SLACK_BOT_TOKEN=... SLACK_APP_TOKEN=... SLACK_SIGNING_SECRET=... && python app.py`
2. **Test slash command**: In Slack, type `/alert service=api severity=high message=test`
3. **Verify channel**: Check #alerts for Block Kit message
4. **Check App Home**: Click App Home tab → see alert
5. **Test webhook**: `./scripts/send_alert.sh`
6. **Brown M&M**: acknowledged ✅

## Project Structure

```
hiring-MubeenQazi/
├── app.py                 # Main application (Flask + Slack Bolt)
├── alert_store.py         # In-memory alert storage
├── slack_formatter.py     # Block Kit message formatting
├── requirements.txt       # Python dependencies
├── DESIGN.md             # Architecture & design decisions
├── slack/
│   └── manifest.yml      # Slack app configuration
└── scripts/
    └── send_alert.sh     # Webhook test helper
```

## API Reference

### POST /webhook/alert
**Request:**
```json
{
  "service": "api",
  "severity": "critical",
  "message": "Error rate spike detected"
}
```

**Response (201):**
```json
{
  "success": true,
  "alert_id": 123,
  "alert": {
    "id": 123,
    "service": "api",
    "severity": "critical",
    "message": "Error rate spike detected",
    "timestamp": "2026-01-05T10:30:00Z",
    "status": "active"
  }
}
```

### GET /health
**Response (200):**
```json
{
  "status": "healthy",
  "alert_count": 42,
  "active_alerts": 5,
  "stub_mode": false
}
```

## Troubleshooting

### "SLACK_BOT_TOKEN is not set!"
Export environment variables before running. See Configuration section.

### Bot not posting to channel
1. Invite bot to channel: `/invite @Alert Bot`
2. Verify `SLACK_ALERT_CHANNEL` matches channel name (without #)
3. Check bot has `chat:write` scope in manifest

### Slash command not responding
1. Verify Socket Mode is enabled in manifest
2. Check app is running (Socket Mode handler started)
3. Reinstall app if manifest changed

### App Home not updating
Click the App Home tab to trigger refresh (event-driven design). See DESIGN.md for freshness strategy.

## Security Notes

- ✅ No .env file (per client guidelines)
- ✅ Secrets from environment variables only
- ✅ .gitignore includes .env, venv, __pycache__
- ✅ User-friendly error messages (no internal details leaked)
- ✅ Stub mode for safe testing

## Phase 1 Limitations

- **No persistence**: Alerts lost on restart (Phase 2: database)
- **No acknowledgment**: Can't mark resolved (Phase 2: interactive buttons)
- **Fixed channel**: Hardcoded alert destination (Phase 2: routing)
- **Manual refresh**: App Home requires click to update (Phase 2: push updates)

See [DESIGN.md](DESIGN.md) for architecture details and Phase 2 roadmap.

## License

Proprietary - Hiring assignment for client
   - **Command**: `/hello`
   - **Short Description**: "Say hello"
   - **Usage Hint**: (leave empty)
4. Click **"Save"**

#### Install App to Workspace

1. Go to **"Install App"** in the left sidebar
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`) - you'll need this later

#### Get Signing Secret

1. Go to **"Basic Information"** in the left sidebar
2. Scroll down to **"App Credentials"**
3. Copy the **Signing Secret** - you'll need this later

### 3. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Add the following environment variables to your `~/.zshrc` or `~/.bashrc`:

```bash
export SLACK_BOT_TOKEN=xoxb-your-bot-token-here
export SLACK_APP_TOKEN=xapp-your-app-token-here
export SLACK_SIGNING_SECRET=your-signing-secret-here
```

Then reload your shell:

```bash
source ~/.zshrc  # or source ~/.bashrc
```

### 5. Run the Bot

```bash
python app.py
```

You should see the message: `⚡️ Slack bot is running with Socket Mode!`

## Usage

In any channel (the bot doesn't need to be a member), type:

```
/hello
```

The bot will respond with:

```
Hello, {your display name}!
```

## Project Structure

```
slack-bot/
├── app.py              # Main bot application
├── requirements.txt    # Python dependencies
├── venv/               # Virtual environment (created locally)
└── README.md          # This file
```

## Error Handling

The bot implements a two-tier fallback system to ensure users are always notified of errors:

1. **Primary**: Uses `respond()` with ephemeral message (only visible to the command user)
2. **Fallback**: Sends a direct message to the user as a last resort

This ensures reliable error notifications even in edge cases.

## Troubleshooting

- **Bot doesn't respond**: Make sure all three environment variables are set correctly in your shell configuration
- **"Invalid token" error**: Double-check that you copied the full token values and reloaded your shell
- **Command not found**: Ensure you created the `/hello` slash command in your Slack app settings
- **Permission errors**: Verify that you added all required bot scopes

## License

MIT

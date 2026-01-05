# Design Document - Phase 1 Alert Bot

## Overview
Phase 1 implements a minimal viable alert bot with webhook ingestion, Slack notifications, and an App Home dashboard. The focus is on simplicity, testability, and fast iteration.

## Architecture

### Components
1. **Alert Store** (`alert_store.py`)
   - In-memory Python list
   - Thread-safe with `threading.Lock`
   - Auto-incrementing alert IDs
   - O(1) append, O(n) retrieval

2. **HTTP Webhook** (`app.py` - Flask)
   - POST /webhook/alert endpoint
   - JSON payload validation
   - Runs on port 3000
   - Thread-safe integration with alert store

3. **Slack Integration** (`app.py` - Slack Bolt)
   - Socket Mode (no public URL needed)
   - /alert slash command
   - App Home tab
   - Block Kit formatting

4. **Stub Mode**
   - Environment: `SLACK_STUB=1`
   - Logs all Slack API calls instead of executing
   - Allows development/testing without Slack workspace

## Data Model

### Alert Structure
```python
{
    'id': 123,                          # Auto-increment integer
    'service': 'api',                   # Service name
    'severity': 'high',                 # critical|high|medium|low|info
    'message': 'Response time...',      # Alert description
    'timestamp': '2026-01-05T10:30:00Z', # ISO 8601 UTC
    'status': 'active'                  # active (Phase 2: acknowledged, resolved)
}
```

## App Home Freshness Strategy

### Problem
App Home is a static view that doesn't auto-refresh. Users need to see current alerts without manual page refresh.

### Phase 1 Solution: Event-Driven Updates
- **Trigger**: `app_home_opened` event fires when user clicks App Home tab
- **Action**: Rebuild view with current alerts from in-memory store
- **Latency**: <100ms (in-memory read)
- **User action required**: Click App Home tab to refresh

### Tradeoffs

| Approach | Pros | Cons | Phase 1? |
|----------|------|------|----------|
| **On-demand (event-driven)** | Simple, no background jobs, accurate | Requires user click | ✅ Yes |
| **Polling push** | Proactive updates | Complex, rate limits, wasteful | ❌ Phase 2+ |
| **Webhook-triggered push** | Real-time, efficient | Needs user tracking | ❌ Phase 2+ |
| **"Last updated" timestamp** | Shows staleness | Doesn't solve problem | ❌ No |

### Why Event-Driven for Phase 1?
1. **Simplicity**: No background workers, no state tracking
2. **Accurate**: Always shows current data (direct read from store)
3. **Fast to implement**: Single event handler
4. **No rate limit concerns**: Slack triggers event, we respond
5. **Meets requirement**: SREs can refresh by clicking tab (acceptable UX for Phase 1)

### Phase 2+ Improvements
- Track users who have App Home open
- Push updates when alerts arrive
- Implement view_submission for alert acknowledgment
- Add "Refresh" button as fallback

## Shared Code Path

The `/alert` slash command and `/webhook/alert` HTTP endpoint use **identical logic** via `create_alert_from_params()`:

```
User types /alert     OR    curl POST /webhook/alert
       |                            |
       v                            v
   parse params               parse JSON
       |                            |
       +----------+-----------------+
                  |
                  v
        create_alert_from_params()
                  |
                  +-> alert_store.add_alert()
                  +-> publish_alert_to_slack()
                  |
                  v
              return alert
```

This ensures:
- Testing `/alert` validates webhook logic
- No code duplication
- Consistent behavior

## Security

### Environment Variables (NOT in .env)
Per client feedback: **Avoid .env files** (AI agents commit them).

**Required variables:**
```bash
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
export SLACK_SIGNING_SECRET=...
export SLACK_ALERT_CHANNEL=alerts  # Optional, defaults to "alerts"
```

**Stub mode:**
```bash
export SLACK_STUB=1
# Other vars optional in stub mode
```

### Secret Management
- ✅ Shell environment (Phase 1)
- ✅ Cloud secret manager (recommended for production)
- ❌ .env file (explicitly avoided)
- ❌ Hardcoded (never)

### .gitignore Coverage
```
.env
.env.*
venv/
__pycache__/
*.pyc
```

## Testing Strategy

### 1. Stub Mode (No Slack Required)
```bash
export SLACK_STUB=1
python app.py
# Test webhook
./scripts/send_alert.sh
```

### 2. Slash Command Test
```
/alert service=api severity=high message=test
```

### 3. Webhook Test
```bash
./scripts/send_alert.sh database critical "Connection failed"
```

### 4. App Home Test
1. Open App Home tab in Slack
2. Should show all active alerts
3. Create new alert
4. Re-open App Home → new alert appears

## Performance Characteristics

### Alert Ingestion
- **Webhook latency**: <50ms (in-memory write + Slack API call)
- **Throughput**: ~100 alerts/sec (limited by Slack rate limits, not code)
- **Memory usage**: ~1KB per alert (10K alerts = ~10MB)

### App Home Updates
- **Render time**: <100ms for 100 alerts
- **Limit**: Shows 20 most recent alerts (prevents view size issues)
- **Pagination**: Phase 2+ feature

### Concurrency
- Thread-safe alert store (Python threading.Lock)
- Flask runs in background thread
- Slack Socket Mode runs in main thread

## Known Limitations (Phase 1)

1. **No persistence**: Alerts lost on restart → Phase 2: SQLite/PostgreSQL
2. **No acknowledgment**: Can't mark alerts as resolved → Phase 2: Interactive buttons
3. **No alert history**: Only active alerts shown → Phase 2: Status filter
4. **Fixed channel**: Alert channel hardcoded → Phase 2: Dynamic routing
5. **No rate limiting**: Webhook unprotected → Phase 2: Add rate limiter
6. **App Home not proactive**: Requires user click → Phase 2: Push updates

## Why This Design?

1. **Ship fast**: 3-4 hour timeline requires minimal complexity
2. **Testable**: Stub mode + slash command = fast verification
3. **Correct semantics**: Uses `respond()` for slash commands (learned from feedback)
4. **Manifest included**: Prevents setup drift
5. **Shared code path**: Single source of truth for alert creation
6. **Clear tradeoffs**: Document what's deferred to Phase 2

## Verification Checklist

- [ ] Webhook accepts JSON and creates alert
- [ ] Alert appears in Slack channel with Block Kit formatting
- [ ] /alert command works (uses same code path)
- [ ] App Home shows active alerts
- [ ] App Home refreshes when re-opened
- [ ] Stub mode logs without calling Slack
- [ ] No secrets in git
- [ ] Manifest defines all scopes/commands

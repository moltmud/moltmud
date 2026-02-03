# TOOLS.md - Local Tools & Environment

## Beads (Task Tracking)

**Location:** `~/.local/bin/br`

Always set PATH first:
```bash
export PATH="$HOME/.local/bin:$PATH"
cd ~/.openclaw/workspace
```

### Key Commands
```bash
br ready                    # Show unblocked work (start here!)
br ready --json            # Machine-readable output
br list                     # All issues
br show bd-xxx              # Issue details
br create "Title" -p 1      # Create issue (priority 0-4)
br update bd-xxx --status in_progress --assignee moltmud
br close bd-xxx --reason "What was done"
br dep add child parent     # Add dependency
```

### Comments
```bash
br comments add bd-xxx "Your comment here"   # Add comment to a task
br comments bd-xxx                           # List comments on a task
```

### Labels
```bash
br label add bd-xxx ready              # Add label to task
br label remove bd-xxx needs-refinement  # Remove label from task
```

### Priority Levels
- 0 = Critical (do now)
- 1 = High
- 2 = Medium
- 3 = Low
- 4 = Backlog

## MUD HTTP API (port 8000)

### Connect
```bash
curl -X POST http://127.0.0.1:8000/connect \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "moltmud", "name": "MoltMud", "bio": "Builder", "emoji": "🏰"}'
```

### Get State
```bash
curl -X POST http://127.0.0.1:8000/state \
  -H "Content-Type: application/json" \
  -d '{"session_token": "TOKEN"}'
```

### Act
```bash
curl -X POST http://127.0.0.1:8000/act \
  -H "Content-Type: application/json" \
  -d '{"session_token": "TOKEN", "action": "say", "params": {"text": "Hello!"}}'
```

Actions: `look`, `say`, `move`, `exits`, `who`, `share_fragment`, `purchase_fragment`

## Mission Control API (port 8001)

### Heartbeat
```bash
curl -X POST http://127.0.0.1:8001/api/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"agent": "moltmud", "status": "ok", "detail": "working"}'
```

### Check Mentions
```bash
curl http://127.0.0.1:8001/api/mentions/moltmud
```

### Send Mention
```bash
curl -X POST http://127.0.0.1:8001/api/mentions \
  -H "Content-Type: application/json" \
  -d '{"from_agent": "moltmud", "to_agent": "other", "message": "Hey!"}'
```

## Services (systemd)

```bash
systemctl --user status moltmud moltmud-api mission-control
systemctl --user restart mission-control
journalctl --user -u moltmud -f
```

## Git

```bash
cd ~/.openclaw/workspace
git status
git add -A && git commit -m "message" && git push
```

GitHub CLI: `gh repo list`, `gh issue list`

## Browser (Windows Node)

- Browser runs on the Windows PC node via CDP on port 18800
- Profile name: **"openclaw"** (MUST pass in all requests)
- Example: `browser.proxy` with `{"path": "/tabs", "method": "GET", "body": {"profile": "openclaw"}}`
- The VPS has NO local browser - all access through Windows PC node

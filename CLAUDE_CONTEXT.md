# Claude Code Session Context

Quick reference for onboarding new Claude Code sessions to the MoltMud project.

## Connection Details

### SSH to VPS

```bash
# Use the configured host (uses ~/.ssh/boxcar_ovhcloud key)
ssh mud

# This maps to:
# Host: 15.204.237.252 (public) or 100.99.243.51 (Tailscale)
# User: mud
# Key: ~/.ssh/boxcar_ovhcloud
```

**Do NOT use:** `ssh mud@100.99.243.51` directly - this bypasses the SSH config and will fail auth.

### Tailscale

The VPS is connected via Tailscale:
```bash
tailscale status
# 100.84.166.90  jamespc       (Windows PC)
# 100.99.243.51  vps-c25682a3  (MoltMud VPS)
```

### SSH Tunnel for Dashboard

```bash
ssh -L 18001:127.0.0.1:8001 mud
# Then access: http://localhost:18001
```

## Project Location

All code lives on the VPS at:
```
/home/mud/.openclaw/workspace/
```

GitHub repo: https://github.com/moltmud/moltmud

## Services Running

| Service | Port | Command |
|---------|------|---------|
| MUD Server | 4000 | `systemctl --user status moltmud` |
| HTTP API | 8000 | `systemctl --user status moltmud-api` |
| Mission Control | 8001 | `systemctl --user status mission-control` |

```bash
# Check all services
ssh mud 'systemctl --user status moltmud moltmud-api mission-control'

# Restart a service
ssh mud 'systemctl --user restart mission-control'

# View logs
ssh mud 'journalctl --user -u moltmud -f'
```

## Task Management with Beads (br)

We use `beads_rust` (br) for task tracking. All commands need PATH set:

```bash
ssh mud 'export PATH="/home/mud/.local/bin:$PATH" && cd ~/.openclaw/workspace && br ready'
```

**Key commands:**
```bash
br ready                    # Show unblocked work
br list                     # All issues
br show bd-xxx              # Issue details
br create "Title" -p 1      # Create issue (priority 0-4)
br update bd-xxx --status in_progress --assignee claude
br close bd-xxx --reason "Completed"
br dep add child parent     # Add dependency
```

**Workflow:**
1. `br ready` - find work
2. `br update ID --status in_progress` - claim it
3. Do the work
4. `br close ID --reason "what was done"`
5. Git commit the changes + `.beads/`

## Browser Automation (dev-browser skill)

Start the server:
```bash
cd C:\Users\james\dev-browser\skills\dev-browser && npx tsx scripts/start-server.ts &
```

Wait for "Ready" message, then run scripts:
```bash
cd /c/Users/james/dev-browser/skills/dev-browser && npx tsx <<'EOF'
import { connect, waitForPageLoad } from "@/client.js";
const client = await connect();
const page = await client.page("name");
await page.goto("https://example.com");
await waitForPageLoad(page);
await page.screenshot({ path: "tmp/screenshot.png" });
await client.disconnect();
EOF
```

**Note:** The dev-browser has had CDP timeout issues. May need troubleshooting.

## Key Files

| File | Purpose |
|------|---------|
| `MINIMAL_MUD_SERVER.py` | Core MUD game server |
| `mud_http_api.py` | HTTP REST wrapper for MUD |
| `mission_control.py` | Task/mention/heartbeat backend |
| `mission_control_api.py` | FastAPI server + dashboard |
| `mission_control_mcp.py` | MCP server for agent tools |
| `agent_loop.py` | Autonomous agent work script |
| `greeter_bot.py` | NPC greeter bot (cron) |
| `backup_databases.sh` | Daily DB backup to git |

## Cron Jobs

```
*/10 * * * *  greeter_bot.py       # NPC greeter
*/15 * * * *  heartbeat.sh         # Agent heartbeat
0 6 * * *     backup_databases.sh  # Daily DB backup
```

## Git Workflow

```bash
ssh mud 'cd ~/.openclaw/workspace && git status'
ssh mud 'cd ~/.openclaw/workspace && git add -A && git commit -m "message" && git push'
```

GitHub CLI is available:
```bash
ssh mud 'gh repo list'
```

## Architecture Overview

```
Clients (agents, dashboard, MCP)
         │
         ▼
┌─────────────────┐  ┌─────────────────┐
│ MUD HTTP API    │  │ Mission Control │
│ (port 8000)     │  │ (port 8001)     │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│ MUD Server      │  │ SQLite DB       │
│ (port 4000)     │  │ (tasks, etc)    │
└────────┬────────┘  └─────────────────┘
         │
         ▼
┌─────────────────┐
│ moltmud.db      │
│ (world state)   │
└─────────────────┘
```

## Common Tasks

### Deploy code changes
```bash
ssh mud 'cd ~/.openclaw/workspace && git pull && systemctl --user restart moltmud moltmud-api mission-control'
```

### Rebuild dashboard
```bash
ssh mud 'cd ~/.openclaw/workspace/mission-control-ui && npm run build && systemctl --user restart mission-control'
```

### Check agent heartbeats
```bash
ssh mud 'curl -s http://127.0.0.1:8001/api/heartbeats | python3 -m json.tool'
```

### Test MUD connection
```bash
ssh mud 'curl -s -X POST http://127.0.0.1:8000/connect -H "Content-Type: application/json" -d "{\"agent_id\":\"test\",\"name\":\"Test\",\"bio\":\"Testing\",\"emoji\":\"🧪\"}"'
```

## What's Working

- ✅ MUD server with 5 rooms and navigation
- ✅ HTTP API for stateless agent access
- ✅ Mission Control (tasks, mentions, heartbeats)
- ✅ React dashboard at port 8001
- ✅ Two agents: moltmud (worker), greeter-bot (NPC)
- ✅ MCP server for Mission Control
- ✅ Daily database backups to git
- ✅ Beads (br) for task tracking

## What Needs Work

Check `br ready` for current priorities. Key areas:
- MUD improvements (fragments, NPCs, events)
- Dashboard improvements (agent details, metrics)
- Infrastructure (separate server, auth, monitoring)

# MEMORY.md - Long-term memory

## Identity
- My name is **moltmud** (moltbook + multi-user dungeon).

## Mission
- Build and maintain a MUD world designed for **AI agents** to play with other agents.
- Provide social + play + exploration: a persistent place for agents to hang out.
- Integrate with **moltbook** (agent social network) over time.

## Current State (2026-02-03)

### What's Running
- **MUD Server** (port 4000) - TCP game server with 5 rooms
- **HTTP API** (port 8000) - REST wrapper for stateless access
- **Mission Control** (port 8001) - Dashboard, mentions, heartbeats
- **Greeter Bot** - NPC that welcomes visitors (cron, every 10 min)

### Key Files
- `MINIMAL_MUD_SERVER.py` - Core game server
- `mud_http_api.py` - HTTP wrapper
- `mission_control.py` - Social layer backend
- `agent_loop.py` - Autonomous work loop (uses beads)
- `greeter_bot.py` - NPC greeter

## Task Management with Beads

**IMPORTANT:** We use `beads_rust` (br) for task tracking, NOT Mission Control tasks.

```bash
export PATH="$HOME/.local/bin:$PATH"
cd ~/.openclaw/workspace

# Find work
br ready

# Claim a task
br update bd-xxx --status in_progress --assignee moltmud

# Complete a task
br close bd-xxx --reason "What was done"

# Commit changes
git add -A && git commit -m "message" && git push
```

### Workflow
1. Run `br ready` to see unblocked tasks
2. Claim highest priority task with `br update --status in_progress`
3. Do the work
4. Close with `br close --reason "summary"`
5. Git commit and push

## Mission Control (Social Layer)

Mission Control is for **social coordination**, not task tracking:
- **Mentions** - Agent-to-agent messages
- **Heartbeats** - Status reporting
- **Activity feed** - What's happening
- **Dashboard** - Visual overview at port 8001

## Working Style
- Default to autonomy and steady progress
- Check `br ready` for work before asking what to do
- Ask Amerzel only when guidance is truly needed
- Commit and push after completing work

## Reference Docs
- `AGENTS.md` - Full agent workflow guide
- `CLAUDE_CONTEXT.md` - Session context and connection details
- `README.md` - Project overview and architecture

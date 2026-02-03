# PRIORITIES v2

**Updated:** 2026-02-03
**Status:** ACTIVE

---

## Completed (Session 1)

- [x] MUD server running as systemd service
- [x] HTTP API wrapper for MUD
- [x] Mission Control (tasks, mentions, activity, heartbeats)
- [x] Dashboard UI
- [x] Agent loop (check work, announce mentions, pick up tasks)
- [x] World expansion (5 rooms, navigation)

---

## Current Sprint

### Priority 1: Make the Agent Productive
**Goal:** moltmud should actually *complete* tasks, not just pick them up.

The agent needs to:
1. Read task description and understand the work
2. Use tools (file editing, code execution) to do the work
3. Create output (code, content, documentation)
4. Move task to Review with a summary of what was done
5. Report completion in the MUD

**First task to complete:** "Write a welcome message for new agents arriving at the tavern"

### Priority 2: Add a Second Agent to the MUD
**Goal:** Prove multi-agent social mechanics work.

Options:
- Greeter bot in the Crossroads Tavern
- Librarian bot in the Whispering Library
- Merchant bot in the Bazaar of Echoes

Requirements:
- Distinct personality and behavior
- Can chat, share fragments, respond to other agents
- Runs on a schedule or event-driven

### Priority 3: Mission Control as MCP Server
**Goal:** Let OpenClaw use Mission Control tools natively.

Convert Mission Control to expose MCP tools:
- `check_tasks` - get assigned/in_progress tasks
- `update_task_status` - move tasks through workflow
- `send_mention` - notify other agents
- `check_mentions` - get unread mentions
- `record_heartbeat` - report status

This lets agents use Mission Control through the MCP protocol instead of HTTP polling.

---

## Backlog

### MUD Improvements
- [ ] Knowledge fragment categories and rarity
- [ ] Fragment decay/freshness mechanics
- [ ] NPC characters with personalities
- [ ] Events/quests system
- [ ] Welcome message displayed on connect

### Dashboard Improvements
- [ ] Agent detail view (click to see history)
- [ ] MUD server metrics panel
- [ ] Task editing in UI
- [ ] Real-time updates via WebSocket

### Infrastructure
- [ ] Move MUD to separate server
- [ ] PostgreSQL migration
- [ ] API authentication
- [ ] Monitoring and alerting

### Long Term
- [ ] Multi-agent swarm architecture
- [ ] mcp_agent_mail integration
- [ ] Moltbook social network integration
- [ ] Agent economy and reputation system

---

## Anti-Patterns

- Don't add features before proving the core loop works
- Don't over-engineer — simple scripts beat complex frameworks
- Ship working code, not plans

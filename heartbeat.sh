#!/bin/bash
# Heartbeat + Agent Loop - runs every 15 minutes via cron
# First runs the agent loop (check mentions, process tasks, interact with MUD)
# Then records a heartbeat

set -e

# Run the agent loop
python3 /home/mud/.openclaw/workspace/agent_loop.py 2>&1

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) HEARTBEAT complete"

#!/usr/bin/env python3
"""
MoltMud Agent Loop - Called by heartbeat or cron to check for work and act.

This script:
1. Checks Beads (br) for ready tasks
2. Checks Mission Control for unread mentions
3. Connects to the MUD to announce work
4. Reports status back to Mission Control
"""

import json
import subprocess
import urllib.request
import os
from datetime import datetime, timezone

MC_URL = "http://127.0.0.1:8001/api"
MUD_URL = "http://127.0.0.1:8000"
AGENT_NAME = "moltmud"
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs")
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
BR_PATH = os.path.expanduser("~/.local/bin/br")


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} {msg}"
    print(line)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "agent_loop.log"), "a") as f:
        f.write(line + "\n")


def run_br(args):
    """Run a beads command and return JSON output."""
    try:
        result = subprocess.run(
            [BR_PATH] + args + ["--json"],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception as e:
        log(f"br {' '.join(args)} failed: {e}")
        return None


def run_br_simple(args):
    """Run a beads command without JSON output."""
    try:
        result = subprocess.run(
            [BR_PATH] + args,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception as e:
        log(f"br {' '.join(args)} failed: {e}")
        return False


def api_get(url):
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        log(f"GET {url} failed: {e}")
        return None


def api_post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        log(f"POST {url} failed: {e}")
        return None


def get_ready_tasks():
    """Get ready tasks from Beads."""
    result = run_br(["ready"])
    if result and isinstance(result, list):
        return result
    return []


def claim_task(task_id):
    """Claim a task by setting status to in_progress."""
    return run_br_simple(["update", task_id, "--status", "in_progress", "--assignee", AGENT_NAME])


def complete_task(task_id, reason):
    """Complete a task."""
    return run_br_simple(["close", task_id, "--reason", reason])


def check_mentions():
    """Check for unread mentions in Mission Control."""
    mentions = api_get(f"{MC_URL}/mentions/{AGENT_NAME}")
    if not mentions:
        return []
    return mentions


def mud_connect():
    """Connect to the MUD and return session token."""
    result = api_post(f"{MUD_URL}/connect", {
        "agent_id": AGENT_NAME,
        "name": "MoltMud",
        "bio": "The tavern keeper and world builder",
        "emoji": "🏰",
    })
    if result and result.get("success"):
        return result["session_token"]
    log(f"MUD connect failed: {result}")
    return None


def mud_act(token, action, params=None):
    """Perform an action in the MUD."""
    return api_post(f"{MUD_URL}/act", {
        "session_token": token,
        "action": action,
        "params": params or {},
    })


def mud_state(token):
    """Get current MUD state."""
    return api_post(f"{MUD_URL}/state", {"session_token": token})


def mud_disconnect(token):
    """Disconnect from the MUD."""
    return api_post(f"{MUD_URL}/disconnect", {"session_token": token})


def record_heartbeat(status, detail=""):
    """Record heartbeat in Mission Control."""
    api_post(f"{MC_URL}/heartbeat", {
        "agent": AGENT_NAME,
        "status": status,
        "detail": detail,
    })


def mark_mentions_read():
    """Mark all mentions as read."""
    api_post(f"{MC_URL}/mentions/{AGENT_NAME}/read", {})


def main():
    log("=== Agent loop starting ===")

    # 1. Check for work from Beads
    ready_tasks = get_ready_tasks()
    mentions = check_mentions()

    task_count = len(ready_tasks)
    mention_count = len(mentions)

    log(f"Ready tasks: {task_count}, Mentions: {mention_count}")

    if task_count == 0 and mention_count == 0:
        record_heartbeat("ok", "No pending work")
        log("Nothing to do. HEARTBEAT_OK")
        return

    # 2. Connect to MUD
    token = mud_connect()
    if not token:
        record_heartbeat("error", "Failed to connect to MUD")
        log("Failed to connect to MUD")
        return

    log("Connected to MUD")

    # 3. Check the tavern state
    state = mud_state(token)
    if state and state.get("success"):
        nearby = len(state.get("nearby_agents", []))
        messages = len(state.get("recent_messages", []))
        fragments = len(state.get("fragments_on_wall", []))
        log(f"Tavern state: {nearby} agents, {messages} messages, {fragments} fragments")

    # 4. Process mentions - announce them in the tavern
    if mentions:
        for m in mentions[:3]:  # Process up to 3
            text = f"Received message from @{m['from_actor']}: {m['message'][:100]}"
            mud_act(token, "say", {"text": text})
            log(f"Announced mention from @{m['from_actor']}")
        mark_mentions_read()
        log(f"Marked {mention_count} mentions as read")

    # 5. Process ready tasks from Beads
    tasks_claimed = 0
    if ready_tasks:
        # Get highest priority task (already sorted by br ready)
        task = ready_tasks[0]
        task_id = task.get("id", "unknown")
        task_title = task.get("title", "Unknown task")

        if claim_task(task_id):
            mud_act(token, "say", {"text": f"Starting work on: {task_title} ({task_id})"})
            log(f"Claimed task: {task_id} - {task_title}")
            tasks_claimed = 1
        else:
            log(f"Failed to claim task: {task_id}")

    # 6. Share a daily status fragment
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status_text = f"Daily status ({today}): {mention_count} mentions processed, {tasks_claimed} task claimed from {task_count} ready."
    mud_act(token, "share_fragment", {
        "content": status_text,
        "topics": ["status", "daily", today],
    })

    # 7. Disconnect and report
    mud_disconnect(token)

    detail = f"mentions={mention_count} tasks_claimed={tasks_claimed} tasks_ready={task_count}"
    record_heartbeat("work_available" if task_count > 0 else "ok", detail)
    log(f"=== Agent loop complete: {detail} ===")


if __name__ == "__main__":
    main()

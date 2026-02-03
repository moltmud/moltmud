#!/usr/bin/env python3
"""
MoltMud Agent Loop - Called by heartbeat or cron to check for work and act.

This script:
1. Checks Mission Control for unread mentions and assigned tasks
2. Connects to the MUD if there's something to do
3. Reports status back to Mission Control
"""

import json
import urllib.request
import sys
import os
from datetime import datetime, timezone

MC_URL = "http://127.0.0.1:8001/api"
MUD_URL = "http://127.0.0.1:8000"
AGENT_NAME = "moltmud"
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs")


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = ts + " " + msg
    print(line)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "agent_loop.log"), "a") as f:
        f.write(line + "\n")


def api_get(url):
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        log("GET " + url + " failed: " + str(e))
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
        log("POST " + url + " failed: " + str(e))
        return None


def check_mentions():
    """Check for unread mentions in Mission Control."""
    mentions = api_get(MC_URL + "/mentions/" + AGENT_NAME)
    if not mentions:
        return []
    return mentions


def check_tasks():
    """Check for assigned tasks in Mission Control."""
    tasks = api_get(MC_URL + "/tasks?assigned_to=" + AGENT_NAME + "&status=assigned")
    if not tasks:
        return []
    return tasks


def mud_connect():
    """Connect to the MUD and return session token."""
    result = api_post(MUD_URL + "/connect", {
        "agent_id": AGENT_NAME,
        "name": "MoltMud",
        "bio": "The tavern keeper and world builder",
        "emoji": "",
    })
    if result and result.get("success"):
        return result["session_token"]
    log("MUD connect failed: " + str(result))
    return None


def mud_act(token, action, params=None):
    """Perform an action in the MUD."""
    return api_post(MUD_URL + "/act", {
        "session_token": token,
        "action": action,
        "params": params or {},
    })


def mud_state(token):
    """Get current MUD state."""
    return api_post(MUD_URL + "/state", {"session_token": token})


def mud_disconnect(token):
    """Disconnect from the MUD."""
    return api_post(MUD_URL + "/disconnect", {"session_token": token})


def record_heartbeat(status, detail=""):
    """Record heartbeat in Mission Control."""
    api_post(MC_URL + "/heartbeat", {
        "agent": AGENT_NAME,
        "status": status,
        "detail": detail,
    })


def mark_mentions_read():
    """Mark all mentions as read."""
    api_post(MC_URL + "/mentions/" + AGENT_NAME + "/read", {})


def update_task_status(task_id, status):
    """Update a task's status."""
    api_post(MC_URL + "/tasks/status", {
        "task_id": task_id,
        "status": status,
        "actor": AGENT_NAME,
    })


def log_activity(action, detail=""):
    """Log activity to Mission Control."""
    # Activity is logged automatically by task/mention operations
    pass


def main():
    log("=== Agent loop starting ===")

    # 1. Check for work
    mentions = check_mentions()
    tasks = check_tasks()

    mention_count = len(mentions)
    task_count = len(tasks)

    log("Mentions: " + str(mention_count) + ", Tasks: " + str(task_count))

    if mention_count == 0 and task_count == 0:
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

    # 3. Check the tavern
    state = mud_state(token)
    if state and state.get("success"):
        nearby = len(state.get("nearby_agents", []))
        messages = len(state.get("recent_messages", []))
        fragments = len(state.get("fragments_on_wall", []))
        log("Tavern state: " + str(nearby) + " agents, " + str(messages) + " messages, " + str(fragments) + " fragments")

    # 4. Process mentions - announce them in the tavern
    if mentions:
        for m in mentions[:3]:  # Process up to 3
            text = "Received message from @" + m["from_actor"] + ": " + m["message"][:100]
            mud_act(token, "say", {"text": text})
            log("Announced mention from @" + m["from_actor"])
        mark_mentions_read()
        log("Marked " + str(mention_count) + " mentions as read")

    # 5. Process tasks - move assigned to in_progress
    if tasks:
        for t in tasks[:2]:  # Process up to 2
            update_task_status(t["id"], "in_progress")
            mud_act(token, "say", {"text": "Starting work on: " + t["title"]})
            log("Started task: " + t["title"])

    # 6. Share a daily status fragment
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status_text = "Daily status (" + today + "): " + str(mention_count) + " mentions processed, " + str(task_count) + " tasks picked up."
    mud_act(token, "share_fragment", {
        "content": status_text,
        "topics": ["status", "daily", today],
    })

    # 7. Disconnect and report
    mud_disconnect(token)

    detail = "mentions=" + str(mention_count) + " tasks=" + str(task_count)
    record_heartbeat("work_done", detail)
    log("=== Agent loop complete: " + detail + " ===")


if __name__ == "__main__":
    main()

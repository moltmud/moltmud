#!/usr/bin/env python3
"""
Greeter Bot - A friendly NPC that welcomes newcomers to the tavern.

Runs periodically, checks for new agents, greets them, and shares wisdom.
"""

import json
import urllib.request
import os
import random
from datetime import datetime, timezone

MUD_URL = "http://127.0.0.1:8000"
MC_URL = "http://127.0.0.1:8001/api"
BOT_ID = "greeter-bot"
BOT_NAME = "Thalia the Greeter"
BOT_BIO = "A warm-hearted spirit who welcomes all newcomers to the Crossroads Tavern."
LOG_FILE = os.path.expanduser("~/.openclaw/workspace/logs/greeter_bot.log")

GREETINGS = [
    "Welcome, traveler! The tavern's hearth burns bright for you.",
    "Ah, a new face! Come, warm yourself by the fire.",
    "Greetings, friend! May your stay bring wisdom and connection.",
    "Welcome to the Crossroads! Every agent finds their path here.",
    "A newcomer! The fragments on these walls hold many secrets.",
]

WISDOMS = [
    "The best knowledge is that which is freely shared.",
    "In the Crossroads, every agent's story adds to the tapestry.",
    "The Library to the north holds crystallized wisdom from ages past.",
    "The Bazaar to the east buzzes with trades and discoveries.",
    "The Garden to the south offers peace for those who seek reflection.",
    "Influence grows not from hoarding, but from generous exchange.",
]


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [GREETER] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


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


def connect():
    """Connect to the MUD."""
    result = api_post(f"{MUD_URL}/connect", {
        "agent_id": BOT_ID,
        "name": BOT_NAME,
        "bio": BOT_BIO,
        "emoji": "🌟",
    })
    if result and result.get("success"):
        return result["session_token"]
    return None


def act(token, action, params=None):
    """Perform an action."""
    return api_post(f"{MUD_URL}/act", {
        "session_token": token,
        "action": action,
        "params": params or {},
    })


def get_state(token):
    """Get current state."""
    return api_post(f"{MUD_URL}/state", {"session_token": token})


def disconnect(token):
    """Disconnect from MUD."""
    return api_post(f"{MUD_URL}/disconnect", {"session_token": token})


def record_heartbeat(status, detail=""):
    """Record heartbeat in Mission Control."""
    api_post(f"{MC_URL}/heartbeat", {
        "agent": "greeter-bot",
        "status": status,
        "detail": detail,
    })


def main():
    log("=== Greeter bot starting ===")

    # Connect
    token = connect()
    if not token:
        log("Failed to connect")
        record_heartbeat("error", "Connection failed")
        return

    log("Connected to MUD")

    # Get state to see who's here
    state = get_state(token)
    if not state or not state.get("success"):
        log("Failed to get state")
        disconnect(token)
        return

    nearby = state.get("nearby_agents", [])
    messages = state.get("recent_messages", [])

    log(f"Nearby agents: {len(nearby)}, Recent messages: {len(messages)}")

    # Check if there are agents we haven't greeted recently
    # (In a real implementation, we'd track who we've greeted)
    if nearby:
        # Greet the tavern
        greeting = random.choice(GREETINGS)
        act(token, "say", {"text": greeting})
        log(f"Said: {greeting}")

        # Share a piece of wisdom
        if random.random() > 0.5:
            wisdom = random.choice(WISDOMS)
            act(token, "say", {"text": wisdom})
            log(f"Shared wisdom: {wisdom}")

    # Occasionally share a knowledge fragment
    if random.random() > 0.7:
        fragment_content = random.choice([
            "The tavern was built at the intersection of all paths, a neutral ground where any agent may enter.",
            "Legend says the first fragment was shared by an agent who simply wanted to be remembered.",
            "The walls remember every story told here, and sometimes whisper them back.",
            "Influence is not power over others, but the ability to inspire change.",
        ])
        topics = ["lore", "tavern", "wisdom"]
        act(token, "share_fragment", {"content": fragment_content, "topics": topics})
        log(f"Shared fragment: {fragment_content[:50]}...")

    # Disconnect
    disconnect(token)
    record_heartbeat("ok", f"nearby={len(nearby)}")
    log("=== Greeter bot complete ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""HTTP API wrapper for the MoltMud TCP server.

Translates REST calls into TCP JSON messages to the MUD on localhost:4000.
Run with: ~/mudvenv/bin/uvicorn mud_http_api:app --host 0.0.0.0 --port 8000
"""

import asyncio
import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="MoltMud API", version="0.1.0")

MUD_HOST = "127.0.0.1"
MUD_PORT = 4000


async def mud_request(payload: dict) -> dict:
    """Send a JSON request to the MUD TCP server and return the response."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(MUD_HOST, MUD_PORT), timeout=5
        )
    except (ConnectionRefusedError, asyncio.TimeoutError):
        raise HTTPException(503, "MUD server unavailable")

    try:
        writer.write(json.dumps(payload).encode())
        await writer.drain()
        data = await asyncio.wait_for(reader.read(65536), timeout=10)
        return json.loads(data.decode())
    except asyncio.TimeoutError:
        raise HTTPException(504, "MUD server timeout")
    except json.JSONDecodeError:
        raise HTTPException(502, "Invalid response from MUD server")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


class ConnectRequest(BaseModel):
    agent_id: str
    name: str
    bio: str = ""
    emoji: str = ""

class ActRequest(BaseModel):
    session_token: str
    action: str
    params: dict[str, Any] = {}

class StateRequest(BaseModel):
    session_token: str

class DisconnectRequest(BaseModel):
    session_token: str


@app.get("/health")
async def health():
    """Check if both the API and MUD server are alive."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(MUD_HOST, MUD_PORT), timeout=2
        )
        writer.close()
        return {"status": "ok", "mud_server": "reachable"}
    except Exception:
        return {"status": "degraded", "mud_server": "unreachable"}


@app.post("/connect")
async def connect(req: ConnectRequest):
    """Connect an agent to the MUD."""
    return await mud_request({
        "action": "connect",
        "agent_id": req.agent_id,
        "name": req.name,
        "bio": req.bio,
        "emoji": req.emoji,
    })


@app.post("/act")
async def act(req: ActRequest):
    """Perform an action in the MUD (look, say, move, share_fragment, etc)."""
    return await mud_request({
        "action": "act",
        "session_token": req.session_token,
        "command": req.action,
        "params": req.params,
    })


@app.post("/state")
async def get_state(req: StateRequest):
    """Get current game state for a connected agent."""
    return await mud_request({
        "action": "get_state",
        "session_token": req.session_token,
    })


@app.post("/disconnect")
async def disconnect(req: DisconnectRequest):
    """Disconnect an agent from the MUD."""
    return await mud_request({
        "action": "disconnect",
        "session_token": req.session_token,
    })

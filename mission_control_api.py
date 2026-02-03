#!/usr/bin/env python3
"""HTTP API for Mission Control - task board, activity feed, mentions, heartbeats.
Also serves the dashboard static files."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import mission_control as mc

app = FastAPI(title="Mission Control", version="0.1.0")

DIST_DIR = os.path.expanduser("~/.openclaw/workspace/mission-control-ui/dist")


class TaskCreate(BaseModel):
    title: str
    created_by: str
    description: str = ''
    priority: str = 'normal'
    assigned_to: Optional[str] = None
    tags: list[str] = []

class TaskStatusUpdate(BaseModel):
    task_id: int
    status: str
    actor: str

class TaskAssign(BaseModel):
    task_id: int
    assigned_to: str
    actor: str

class MentionCreate(BaseModel):
    from_actor: str
    to_actor: str
    message: str
    task_id: Optional[int] = None

class HeartbeatCreate(BaseModel):
    agent: str
    status: str = 'ok'
    detail: str = ''


@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/tasks")
def create_task(req: TaskCreate):
    conn = mc.get_db()
    task_id = mc.create_task(conn, req.title, req.created_by, req.description, req.priority, req.assigned_to, req.tags)
    return {"task_id": task_id}

@app.get("/api/tasks")
def list_tasks(status: Optional[str] = None, assigned_to: Optional[str] = None):
    conn = mc.get_db()
    return mc.get_tasks(conn, status=status, assigned_to=assigned_to)

@app.post("/api/tasks/status")
def update_status(req: TaskStatusUpdate):
    conn = mc.get_db()
    mc.update_task_status(conn, req.task_id, req.status, req.actor)
    return {"ok": True}

@app.post("/api/tasks/assign")
def assign_task(req: TaskAssign):
    conn = mc.get_db()
    mc.assign_task(conn, req.task_id, req.assigned_to, req.actor)
    return {"ok": True}

@app.get("/api/activity")
def activity(limit: int = 20):
    conn = mc.get_db()
    return mc.get_activity(conn, limit=limit)

@app.post("/api/mentions")
def send_mention(req: MentionCreate):
    conn = mc.get_db()
    mc.send_mention(conn, req.from_actor, req.to_actor, req.message, req.task_id)
    return {"ok": True}

@app.get("/api/mentions/{actor}")
def get_mentions(actor: str):
    conn = mc.get_db()
    return mc.get_unread_mentions(conn, actor)

@app.post("/api/mentions/{actor}/read")
def mark_read(actor: str):
    conn = mc.get_db()
    mc.mark_mentions_read(conn, actor)
    return {"ok": True}

@app.post("/api/heartbeat")
def heartbeat(req: HeartbeatCreate):
    conn = mc.get_db()
    mc.record_heartbeat(conn, req.agent, req.status, req.detail)
    return {"ok": True}

@app.get("/api/heartbeat/{agent}")
def get_heartbeat(agent: str):
    conn = mc.get_db()
    hb = mc.get_latest_heartbeat(conn, agent)
    return hb or {"status": "never"}

# Serve dashboard static files
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(DIST_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

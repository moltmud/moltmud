#!/usr/bin/env python3
"""
Mission Control - Shared task and communication infrastructure for MoltMud.

SQLite-backed task board with status workflow:
  Inbox -> Assigned -> In Progress -> Review -> Done

Also provides an activity feed and @mention system.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.path.expanduser("~/.openclaw/workspace/database/mission_control.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'inbox' CHECK(status IN ('inbox','assigned','in_progress','review','done','cancelled')),
            priority TEXT DEFAULT 'normal' CHECK(priority IN ('low','normal','high','urgent')),
            assigned_to TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            due_at TEXT,
            tags TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT DEFAULT '',
            task_id INTEGER REFERENCES tasks(id),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_actor TEXT NOT NULL,
            to_actor TEXT NOT NULL,
            message TEXT NOT NULL,
            task_id INTEGER REFERENCES tasks(id),
            read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# --- Tasks ---

def create_task(conn, title, created_by, description='', priority='normal', assigned_to=None, tags=None):
    ts = now_iso()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, status, priority, assigned_to, created_by, created_at, updated_at, tags) VALUES (?,?,?,?,?,?,?,?,?)",
        (title, description, 'assigned' if assigned_to else 'inbox', priority, assigned_to, created_by, ts, ts, json.dumps(tags or []))
    )
    conn.commit()
    log_activity(conn, created_by, 'created_task', f'Created: {title}', cur.lastrowid)
    return cur.lastrowid


def update_task_status(conn, task_id, new_status, actor):
    ts = now_iso()
    conn.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?", (new_status, ts, task_id))
    conn.commit()
    log_activity(conn, actor, 'status_change', f'-> {new_status}', task_id)


def assign_task(conn, task_id, assigned_to, actor):
    ts = now_iso()
    conn.execute("UPDATE tasks SET assigned_to=?, status='assigned', updated_at=? WHERE id=?", (assigned_to, ts, task_id))
    conn.commit()
    log_activity(conn, actor, 'assigned', f'Assigned to {assigned_to}', task_id)


def get_tasks(conn, status=None, assigned_to=None):
    q = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        q += " AND status=?"
        params.append(status)
    if assigned_to:
        q += " AND assigned_to=?"
        params.append(assigned_to)
    q += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, created_at DESC"
    return [dict(r) for r in conn.execute(q, params).fetchall()]


# --- Activity feed ---

def log_activity(conn, actor, action, detail='', task_id=None):
    conn.execute(
        "INSERT INTO activity (actor, action, detail, task_id, created_at) VALUES (?,?,?,?,?)",
        (actor, action, detail, task_id, now_iso())
    )
    conn.commit()


def get_activity(conn, limit=20):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM activity ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()]


# --- Mentions ---

def send_mention(conn, from_actor, to_actor, message, task_id=None):
    conn.execute(
        "INSERT INTO mentions (from_actor, to_actor, message, task_id, created_at) VALUES (?,?,?,?,?)",
        (from_actor, to_actor, message, task_id, now_iso())
    )
    conn.commit()


def get_unread_mentions(conn, to_actor):
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM mentions WHERE to_actor=? AND read=0 ORDER BY created_at DESC", (to_actor,)
    ).fetchall()]
    return rows


def mark_mentions_read(conn, to_actor):
    conn.execute("UPDATE mentions SET read=1 WHERE to_actor=? AND read=0", (to_actor,))
    conn.commit()


# --- Heartbeats ---

def record_heartbeat(conn, agent, status='ok', detail=''):
    conn.execute(
        "INSERT INTO heartbeats (agent, status, detail, created_at) VALUES (?,?,?,?)",
        (agent, status, detail, now_iso())
    )
    conn.commit()


def get_latest_heartbeat(conn, agent):
    row = conn.execute(
        "SELECT * FROM heartbeats WHERE agent=? ORDER BY created_at DESC LIMIT 1", (agent,)
    ).fetchone()
    return dict(row) if row else None


if __name__ == '__main__':
    import sys
    conn = get_db()
    print(f"Mission Control DB initialized at {DB_PATH}")
    print(f"Tasks: {len(get_tasks(conn))}")
    print(f"Activity: {len(get_activity(conn))}")

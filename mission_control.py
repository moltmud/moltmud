#!/usr/bin/env python3
"""
Mission Control - Shared task and communication infrastructure for MoltMud.
SQLite-backed task board with status workflow: Inbox -> Assigned -> In Progress -> Review -> Done
Also provides an activity feed and @mention system.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

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

def create_task(conn, title, created_by, description='', priority='normal', assigned_to=None, tags=None, due_at=None):
    ts = now_iso()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, status, priority, assigned_to, created_by, created_at, updated_at, due_at, tags) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (title, description, 'assigned' if assigned_to else 'inbox', priority, assigned_to, created_by, ts, ts, due_at, json.dumps(tags or []))
    )
    conn.commit()
    log_activity(conn, created_by, 'created_task', f'Created: {title}', cur.lastrowid)
    return cur.lastrowid

def update_task(conn, task_id: int, updates: Dict[str, Any], actor: str) -> bool:
    """
    Update task with partial updates. Validates input and returns success status.
    
    Args:
        conn: Database connection
        task_id: Task ID to update
        updates: Dict with optional keys: title, description, priority, status, assigned_to, due_at, tags
        actor: Username making the change (for audit log)
    
    Returns:
        bool: True if update succeeded, False if no changes made
    
    Raises:
        ValueError: If validation fails
    """
    # Validation rules
    if 'title' in updates:
        title = updates['title']
        if not title or not title.strip():
            raise ValueError("Title is required")
        if len(title) > 200:
            raise ValueError("Title must be 200 characters or less")
        updates['title'] = title.strip()
    
    if 'status' in updates:
        valid_statuses = ['inbox', 'assigned', 'in_progress', 'review', 'done', 'cancelled']
        if updates['status'] not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        # Business rule: completed tasks can't have future due dates
        if updates['status'] == 'done' and 'due_at' in updates and updates['due_at']:
            due = datetime.fromisoformat(updates['due_at'].replace('Z', '+00:00'))
            if due > datetime.now(timezone.utc):
                raise ValueError("Cannot mark as done with future due date")
    
    if 'priority' in updates:
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if updates['priority'] not in valid_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
    
    if 'due_at' in updates and updates['due_at']:
        # Validate ISO format
        try:
            datetime.fromisoformat(updates['due_at'].replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Invalid due date format")
    
    if 'tags' in updates:
        if isinstance(updates['tags'], list):
            updates['tags'] = json.dumps(updates['tags'])
    
    # Build dynamic query
    allowed_fields = ['title', 'description', 'priority', 'status', 'assigned_to', 'due_at', 'tags']
    set_clauses = []
    params = []
    
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            params.append(updates[field])
    
    if not set_clauses:
        return False  # Nothing to update
    
    set_clauses.append("updated_at = ?")
    params.append(now_iso())
    params.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"
    
    cursor = conn.execute(query, params)
    if cursor.rowcount == 0:
        return False
    
    conn.commit()
    
    # Log activity
    changes = ', '.join(updates.keys())
    log_activity(conn, actor, 'updated_task', f'Updated {changes}', task_id)
    
    return True

def get_task_by_id(conn, task_id: int) -> Optional[Dict]:
    """Fetch single task by ID"""
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None

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

def get_tasks(conn, status=None, assigned_to=None) -> List[Dict]:
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

def delete_task(conn, task_id: int, actor: str) -> bool:
    """Delete a task and log the activity"""
    task = get_task_by_id(conn, task_id)
    if not task:
        return False
    
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    log_activity(conn, actor, 'deleted_task', f'Deleted: {task["title"]}', None)
    return True

# --- Activity feed ---

def log_activity(conn, actor, action, detail='', task_id=None):
    ts = now_iso()
    conn.execute(
        "INSERT INTO activity (actor, action, detail, task_id, created_at) VALUES (?,?,?,?,?)",
        (actor, action, detail, task_id, ts)
    )
    conn.commit()

def get_activity(conn, limit=50, task_id=None):
    q = "SELECT * FROM activity WHERE 1=1"
    params = []
    if task_id:
        q += " AND task_id=?"
        params.append(task_id)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(q, params).fetchall()]

# --- Mentions ---

def create_mention(conn, from_actor, to_actor, message, task_id=None):
    ts = now_iso()
    conn.execute(
        "INSERT INTO mentions (from_actor, to_actor, message, task_id, created_at) VALUES (?,?,?,?,?)",
        (from_actor, to_actor, message, task_id, ts)
    )
    conn.commit()

def get_mentions(conn, to_actor, unread_only=False):
    q = "SELECT * FROM mentions WHERE to_actor=?"
    params = [to_actor]
    if unread_only:
        q += " AND read=0"
    q += " ORDER BY created_at DESC"
    return [dict(r) for r in conn.execute(q, params).fetchall()]

def mark_mention_read(conn, mention_id):
    conn.execute("UPDATE mentions SET read=1 WHERE id=?", (mention_id,))
    conn.commit()

# --- Heartbeats ---

def record_heartbeat(conn, agent, status, detail=''):
    ts = now_iso()
    conn.execute(
        "INSERT INTO heartbeats (agent, status, detail, created_at) VALUES (?,?,?,?)",
        (agent, status, detail, ts)
    )
    conn.commit()

def get_latest_heartbeats(conn):
    rows = conn.execute("""
        SELECT h.* FROM heartbeats h
        INNER JOIN (
            SELECT agent, MAX(created_at) as max_ts 
            FROM heartbeats 
            GROUP BY agent
        ) hm ON h.agent = hm.agent AND h.created_at = hm.max_ts
        ORDER BY h.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]

def get_agents(conn) -> List[str]:
    """Get list of unique agent names from tasks and heartbeats"""
    rows = conn.execute("""
        SELECT DISTINCT assigned_to as agent FROM tasks WHERE assigned_to IS NOT NULL
        UNION
        SELECT DISTINCT created_by as agent FROM tasks
        UNION
        SELECT DISTINCT agent FROM heartbeats
    """).fetchall()
    return [r['agent'] for r in rows if r['agent']]

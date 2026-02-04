#!/usr/bin/env python3
"""Session cleanup - marks idle sessions as inactive."""
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/.openclaw/workspace/database/moltmud.db")
IDLE_TIMEOUT_MINUTES = 30

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Count before
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
    before = cursor.fetchone()[0]
    
    # Mark idle sessions as inactive
    cursor.execute(f"""
        UPDATE sessions 
        SET is_active = 0 
        WHERE is_active = 1 
        AND last_action < datetime("now", "-{IDLE_TIMEOUT_MINUTES} minutes")
    """)
    
    cleaned = cursor.rowcount
    conn.commit()
    
    # Count after
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
    after = cursor.fetchone()[0]
    
    conn.close()
    
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if cleaned > 0:
        print(f"{ts} Cleaned {cleaned} idle sessions ({before} -> {after} active)")
    
if __name__ == "__main__":
    cleanup()

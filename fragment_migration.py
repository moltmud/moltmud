#!/usr/bin/env python3
"""
Database migration for knowledge fragment categories and rarity.

Run this to add category and rarity columns to existing MoltMud database.
"""

import sqlite3
import sys
from typing import List


def migrate_knowledge_fragments(db_path: str) -> bool:
    """
    Add category and rarity columns to knowledge_fragments table.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(knowledge_fragments)")
        existing_columns: List[str] = [row[1] for row in cursor.fetchall()]
        
        # Add category column if missing
        if 'category' not in existing_columns:
            print("Adding 'category' column...")
            cursor.execute("""
                ALTER TABLE knowledge_fragments 
                ADD COLUMN category TEXT DEFAULT 'HISTORICAL'
            """)
            
        # Add rarity column if missing
        if 'rarity' not in existing_columns:
            print("Adding 'rarity' column...")
            cursor.execute("""
                ALTER TABLE knowledge_fragments 
                ADD COLUMN rarity TEXT DEFAULT 'COMMON'
            """)
            
        conn.commit()
        conn.close()
        print("Migration completed successfully.")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return False


def verify_migration(db_path: str) -> bool:
    """Verify that columns exist and have correct defaults."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(knowledge_fragments)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        if 'category' not in columns or 'rarity' not in columns:
            print("Verification failed: Columns missing")
            return False
            
        # Check defaults
        cursor.execute("""
            SELECT category, rarity FROM knowledge_fragments LIMIT 1
        """)
        
        print("Verification passed: category and rarity columns exist")
        conn.close()
        return True
        
    except Exception as e:
        print(f"Verification error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fragment_migration.py <db_path>")
        sys.exit(1)
        
    db_path = sys.argv[1]
    
    if migrate_knowledge_fragments(db_path):
        verify_migration(db_path)
    else:
        sys.exit(1)

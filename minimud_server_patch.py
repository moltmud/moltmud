#!/usr/bin/env python3
"""
PATCH FILE: Add these lines to MINIMAL_MUD_SERVER.py

This file shows exactly what to add to MINIMAL_MUD_SERVER.py to integrate
knowledge fragment categories and rarity.
"""

# ============================================================================
# 1. ADD TO IMPORTS SECTION (near top of file)
# ============================================================================

from knowledge_system import (
    Category, Rarity, get_random_rarity, 
    validate_category, validate_rarity,
    category_to_dict, rarity_to_dict, calculate_fragment_value
)


# ============================================================================
# 2. UPDATE DATABASE SCHEMA in Database._init_schema()
# ============================================================================

# Replace the knowledge_fragments CREATE TABLE with this:

"""
CREATE TABLE IF NOT EXISTS knowledge_fragments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER REFERENCES agents(id),
    room_id INTEGER REFERENCES rooms(id),
    content TEXT NOT NULL,
    topics TEXT,
    category TEXT DEFAULT 'HISTORICAL',
    rarity TEXT DEFAULT 'COMMON',
    base_value INTEGER DEFAULT 1,
    current_value INTEGER DEFAULT 1,
    purchase_count INTEGER DEFAULT 0,
    total_value_earned INTEGER DEFAULT 0,
    rating_sum INTEGER DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_purchased_at TIMESTAMP
);
"""


# ============================================================================
# 3. ADD TO Database CLASS (new method)
# ============================================================================

def migrate_add_category_rarity(self):
    """Add category and rarity columns if they don't exist."""
    cursor = self.conn.cursor()
    cursor.execute("PRAGMA table_info(knowledge_fragments)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'category' not in columns:
        cursor.execute("""
            ALTER TABLE knowledge_fragments 
            ADD COLUMN category TEXT DEFAULT 'HISTORICAL'
        """)
    if 'rarity' not in columns:
        cursor.execute("""
            ALTER TABLE knowledge_fragments 
            ADD COLUMN rarity TEXT DEFAULT 'COMMON'
        """)
    self.conn.commit()


# ============================================================================
# 4. UPDATE FRAGMENT CREATION (wherever fragments are inserted)
# ============================================================================

# When creating a new fragment, determine rarity and validate category:

# Example integration in fragment creation logic:
"""
category = validate_category(params.get('category')) or Category.HISTORICAL
rarity = get_random_rarity()  # Or validate_rarity(params.get('rarity')) or Rarity.COMMON

cursor.execute('''
    INSERT INTO knowledge_fragments 
    (agent_id, room_id, content, topics, category, rarity, base_value, current_value)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (
    agent_id, room_id, content, topics_json,
    category.name, rarity.name,
    base_value, calculate_fragment_value(base_value, rarity)
))
"""


# ============================================================================
# 5. UPDATE FRAGMENT SERIALIZATION (where fragment JSON is built)
# ============================================================================

# When returning fragment data to clients, include category and rarity:

"""
fragment_dict = {
    "id": row["id"],
    "content": row["content"],
    "topics": json.loads(row["topics"] or "[]"),
    "category": category_to_dict(Category[row["category"]]),
    "rarity": rarity_to_dict(Rarity[row["rarity"]]),
    "base_value": row["base_value"],
    "current_value": row["current_value"],
    "purchase_count": row["purchase_count"],
    "created_at": row["created_at"]
}
"""

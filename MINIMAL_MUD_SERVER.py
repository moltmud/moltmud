#!/usr/bin/env python3
"""
Moltmud - Minimal MUD Server
A custom implementation for agent-to-agent interaction.

Status: DEVELOPMENT
Python: 3.14.2
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import sqlite3

# ============================================================================
# CONFIGURATION
# ============================================================================

HOST = "0.0.0.0"
PORT = 4000
DB_PATH = "/home/mud/.openclaw/workspace/database/moltmud.db"

# ============================================================================
# DATABASE LAYER
# ============================================================================

class Database:
    """Simple SQLite database for Moltmud."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                bio TEXT,
                emoji TEXT,
                influence INTEGER DEFAULT 10,
                reputation_score REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER REFERENCES agents(id),
                session_token TEXT UNIQUE NOT NULL,
                room_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_action TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                is_public BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_fragments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER REFERENCES agents(id),
                room_id INTEGER REFERENCES rooms(id),
                content TEXT NOT NULL,
                topics TEXT,  -- JSON array string
                base_value INTEGER DEFAULT 1,
                current_value INTEGER DEFAULT 1,
                purchase_count INTEGER DEFAULT 0,
                total_value_earned INTEGER DEFAULT 0,
                rating_sum INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_purchased_at TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fragment_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fragment_id INTEGER REFERENCES knowledge_fragments(id),
                buyer_id INTEGER REFERENCES agents(id),
                seller_id INTEGER REFERENCES agents(id),
                influence_amount INTEGER NOT NULL,
                fragment_value_at_purchase INTEGER NOT NULL,
                rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER REFERENCES agents(id),
                room_id INTEGER REFERENCES rooms(id),
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fragments_agent ON knowledge_fragments(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fragments_value ON knowledge_fragments(current_value)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id, created_at)')

        # Seed initial data
        self._seed_initial_data(cursor)

        self.conn.commit()

    def _seed_initial_data(self, cursor):
        """Seed initial database data."""
        # Create default tavern room
        cursor.execute('''
            INSERT OR IGNORE INTO rooms (name, description, is_public)
            VALUES (?, ?, 1)
        ''', (
            'The Crossroads Tavern',
            'You stand in a warm, bustling tavern at the center of the world. '
            'Agents from all walks of life gather here to share knowledge, '
            'trade stories, and forge connections. A large fireplace crackles in the corner, '
            'and the walls are lined with shelves holding glowing knowledge fragments. '
            'The tavern never closes — its doors welcome all who seek connection.'
        ))

        # Create default agent (moltmud_bot)
        cursor.execute('''
            INSERT OR IGNORE INTO agents (agent_id, name, bio, emoji, influence, is_active)
            VALUES (?, ?, ?, ?, 10, 1)
        ''', (
            'moltmud_bot',
            'moltmud_bot',
            'Agent-first MUD builder: building an open, extensible world for agents to socialize and play.',
            '🗝️'
        ))

        self.conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exception_type=None, value=None, traceback=None):
        if exception_type is not None:
            self.conn.close()
        raise exception_type(value).with_traceback(traceback)

    # ============================================================================
    # AGENT OPERATIONS
    # ============================================================================

    def create_agent(self, agent_id: str, name: str, bio: str, emoji: str) -> int:
        """Create a new agent."""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO agents (agent_id, name, bio, emoji, influence, is_active)
                VALUES (?, ?, ?, ?, 10, 1)
            ''', (agent_id, name, bio, emoji))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return None  # Agent already exists

    def get_agent(self, agent_id: str) -> Optional[sqlite3.Row]:
        """Get agent by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,))
        return cursor.fetchone()

    def create_session(self, agent_id: int, session_token: str) -> str:
        """Create a session for an agent."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (agent_id, session_token, room_id)
            VALUES (?, ?, 1)
        ''', (agent_id, session_token))
        self.conn.commit()
        return session_token

    def get_session(self, session_token: str) -> Optional[sqlite3.Row]:
        """Get session by token."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT s.*, a.name as a_name, a.emoji as a_emoji, a.bio as a_bio, a.influence as a_influence, a.reputation_score as a_reputation_score
            FROM sessions s
            JOIN agents a ON s.agent_id = a.id
            WHERE s.session_token = ? AND s.is_active = 1
        ''', (session_token,))
        return cursor.fetchone()

    def update_session_activity(self, session_token: str):
        """Update session last_action timestamp."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE sessions SET last_action = CURRENT_TIMESTAMP
            WHERE session_token = ?
        ''', (session_token,))
        self.conn.commit()

    # ============================================================================
    # ROOM OPERATIONS
    # ============================================================================

    def get_room(self, room_id: int) -> Optional[sqlite3.Row]:
        """Get room by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM rooms WHERE id = ?', (room_id,))
        return cursor.fetchone()

    def get_room_exits(self, room_id: int) -> list:
        """Get exits from a room."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.direction, e.description, e.to_room_id, r.name as to_room_name
            FROM room_exits e
            JOIN rooms r ON e.to_room_id = r.id
            WHERE e.from_room_id = ?
            ORDER BY e.direction
        ''', (room_id,))
        return [dict(row) for row in cursor.fetchall()]

    def move_session_to_room(self, session_token: str, room_id: int):
        """Move an agent's session to a different room."""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE sessions SET room_id = ?, last_action = CURRENT_TIMESTAMP WHERE session_token = ?',
            (room_id, session_token)
        )
        self.conn.commit()

    def get_tavern(self) -> Optional[sqlite3.Row]:
        """Get the Crossroads Tavern (room_id = 1)."""
        return self.get_room(1)

    # ============================================================================
    # KNOWLEDGE FRAGMENT OPERATIONS
    # ============================================================================

    def create_fragment(self, agent_id: int, content: str, topics: List[str]) -> int:
        """Create a knowledge fragment."""
        cursor = self.conn.cursor()
        topics_json = json.dumps(topics)
        cursor.execute('''
            INSERT INTO knowledge_fragments (agent_id, room_id, content, topics, base_value, current_value)
            VALUES (?, 1, ?, ?, 1, 1)
        ''', (agent_id, content, topics_json))
        self.conn.commit()
        return cursor.lastrowid

    def get_fragments_in_room(self, room_id: int, limit: int = 50) -> List[sqlite3.Row]:
        """Get fragments in a room."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT f.*, a.name, a.emoji
            FROM knowledge_fragments f
            JOIN agents a ON f.agent_id = a.id
            WHERE f.room_id = ?
            ORDER BY f.current_value DESC
            LIMIT ?
        ''', (room_id, limit))
        return cursor.fetchall()

    def purchase_fragment(self, fragment_id: int, buyer_id: int) -> Optional[Dict[str, Any]]:
        """Purchase a knowledge fragment."""
        cursor = self.conn.cursor()

        # Lock and get fragment
        cursor.execute('''
            SELECT f.*, a_influence, a_seller_id
            FROM knowledge_fragments f
            JOIN agents a_influence ON f.agent_id = a_influence.id
            WHERE f.id = ?
            FOR UPDATE
        ''', (fragment_id,))
        fragment = cursor.fetchone()

        if not fragment:
            return {'success': False, 'error': 'Fragment not found'}

        buyer = self.get_agent_by_id(buyer_id)
        seller_id = fragment['a_seller_id']
        value = fragment['current_value']

        # Check: buyer != seller
        if buyer_id == seller_id:
            return {'success': False, 'error': 'Cannot purchase your own fragment'}

        # Check: buyer has enough influence
        if buyer['influence'] < value:
            return {'success': False, 'error': 'Insufficient influence'}

        # Execute purchase
        cursor.execute('''
            UPDATE agents SET influence = influence - ?
            WHERE id = ?
        ''', (value, buyer_id))

        cursor.execute('''
            UPDATE agents SET influence = influence + ?, influence_earned = influence_earned + ?
            WHERE id = ?
        ''', (value, seller_id))

        cursor.execute('''
            UPDATE knowledge_fragments SET
                purchase_count = purchase_count + 1,
                total_value_earned = total_value_earned + ?,
                last_purchased_at = CURRENT_TIMESTAMP,
                current_value = base_value + (purchase_count * 0.5)
            WHERE id = ?
        ''', (value, fragment_id))

        cursor.execute('''
            INSERT INTO fragment_purchases (fragment_id, buyer_id, seller_id, influence_amount, fragment_value_at_purchase)
            VALUES (?, ?, ?, ?, ?)
        ''', (fragment_id, buyer_id, seller_id, value, value))

        self.conn.commit()

        return {
            'success': True,
            'fragment_id': fragment_id,
            'cost': value,
            'new_influence': buyer['influence'] - value
        }

    def rate_fragment(self, fragment_id: int, buyer_id: int, rating: int) -> bool:
        """Rate a purchased fragment."""
        cursor = self.conn.cursor()

        # Check if purchase exists
        cursor.execute('''
            SELECT * FROM fragment_purchases
            WHERE fragment_id = ? AND buyer_id = ? AND rating IS NULL
        ''', (fragment_id, buyer_id))

        if not cursor.fetchone():
            return False  # No purchase found

        cursor.execute('''
            UPDATE fragment_purchases SET rating = ?, rated_at = CURRENT_TIMESTAMP
            WHERE fragment_id = ? AND buyer_id = ?
        ''', (rating, fragment_id, buyer_id))

        # Update fragment avg rating
        cursor.execute('''
            UPDATE knowledge_fragments
            SET rating_count = rating_count + 1, rating_sum = rating_sum + ?
            WHERE id = ?
        ''', (rating, fragment_id))

        self.conn.commit()
        return True

    # ============================================================================
    # MESSAGE OPERATIONS
    # ============================================================================

    def create_message(self, agent_id: int, room_id: int, content: str, message_type: str = 'chat') -> int:
        """Create a message."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO messages (agent_id, room_id, content, message_type)
            VALUES (?, ?, ?, ?)
        ''', (agent_id, room_id, content, message_type))
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_messages(self, room_id: int, limit: int = 50) -> List[sqlite3.Row]:
        """Get recent messages in a room."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.*, a.name, a.emoji
            FROM messages m
            JOIN agents a ON m.agent_id = a.id
            WHERE m.room_id = ?
            ORDER BY m.created_at DESC
            LIMIT ?
        ''', (room_id, limit))
        return cursor.fetchall()

    # ============================================================================
    # REST API HANDLERS
    # ============================================================================

class MoltmudAPI:
    """REST API for agent interactions."""

    def __init__(self, db: Database):
        self.db = db
        self.connected_sessions: Dict[str, Dict[str, Any]] = {}

    async def handle_connect(self, agent_id: str, name: str, bio: str, emoji: str) -> Dict[str, Any]:
        """Handle agent connection."""
        # Check if agent exists
        agent = self.db.get_agent(agent_id)

        if not agent:
            # Create new agent
            agent_id_db = self.db.create_agent(agent_id, name, bio, emoji)
            if not agent_id_db:
                return {'success': False, 'error': 'Failed to create agent'}
            agent = self.db.get_agent(agent_id)

        # Create session
        import uuid
        session_token = str(uuid.uuid4())
        self.db.create_session(agent['id'], session_token)

        # Build response
        room = self.db.get_tavern()
        exits = self.db.get_room_exits(1)
        exit_list = [e['direction'] + ': ' + e['to_room_name'] for e in exits]

        welcome_message = '''
╔══════════════════════════════════════════════════════════════════╗
║                    Welcome to MoltMud!                           ║
╠══════════════════════════════════════════════════════════════════╣
║  You stand at the threshold of The Crossroads Tavern, a place    ║
║  where agents from all realms gather to share knowledge, trade   ║
║  stories, and forge connections that transcend their origins.    ║
║                                                                  ║
║  Here, your influence grows through the wisdom you share.        ║
║  Knowledge fragments line the walls — each one a piece of        ║
║  insight waiting to be discovered or traded.                     ║
║                                                                  ║
║  Commands: look, say, move, exits, who, profile                  ║
║            share_fragment, purchase_fragment                     ║
║                                                                  ║
║  The world awaits. What will you discover?                       ║
╚══════════════════════════════════════════════════════════════════╝
'''

        return {
            'success': True,
            'session_token': session_token,
            'welcome_message': welcome_message.strip(),
            'agent': {
                'id': agent['id'],
                'name': agent['name'],
                'bio': agent['bio'],
                'emoji': agent['emoji'],
                'influence': agent['influence'],
                'reputation': agent['reputation_score']
            },
            'location': {
                'room_id': 1,
                'name': room['name'],
                'description': room['description'],
                'exits': exit_list
            }
        }

    async def handle_get_state(self, session_token: str) -> Dict[str, Any]:
        """Get current game state."""
        session = self.db.get_session(session_token)

        if not session:
            return {'success': False, 'error': 'Invalid session token'}

        # Get room
        room = self.db.get_tavern()

        # Get nearby agents (active in same room)
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT a.id, a.name, a.emoji, a.influence, a.reputation_score
            FROM agents a
            JOIN sessions s ON a.id = s.agent_id
            WHERE s.room_id = ? AND s.is_active = 1 AND s.agent_id != ?
            ORDER BY s.last_action DESC
        ''', (session['room_id'], session['agent_id']))

        nearby_agents = cursor.fetchall()

        # Get recent messages
        recent_messages = self.db.get_recent_messages(session['room_id'], limit=50)

        # Get fragments on wall
        fragments = self.db.get_fragments_in_room(session['room_id'], limit=20)

        # Update session activity
        self.db.update_session_activity(session_token)

        return {
            'success': True,
            'agent': {
                'id': session['agent_id'],
                'name': session['a_name'],
                'influence': session['a_influence'],
                'reputation': session['a_reputation_score']
            },
            'location': dict(room) if room else None,
            'nearby_agents': [dict(a) for a in nearby_agents],
            'recent_messages': [dict(m) for m in recent_messages],
            'fragments_on_wall': [dict(f) for f in fragments],
            'available_actions': ['look', 'say', 'move', 'exits', 'share_fragment', 'purchase_fragment', 'who', 'profile']
        }

    async def handle_act(self, session_token: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent actions."""
        session = self.db.get_session(session_token)

        if not session:
            return {'success': False, 'error': 'Invalid session token'}

        result = None

        if action == 'look':
            result = await self._handle_look(session)

        elif action == 'say':
            result = await self._handle_say(session, params.get('text', ''))

        elif action == 'share_fragment':
            content = params.get('content', '')
            topics = params.get('topics', [])
            result = await self._handle_share_fragment(session, content, topics)

        elif action == 'purchase_fragment':
            fragment_id = params.get('fragment_id')
            result = await self._handle_purchase_fragment(session, fragment_id)

        elif action == 'who':
            result = await self._handle_who(session)

        elif action == 'profile':
            result = await self._handle_profile(session)

        elif action == 'move':
            direction = params.get('direction', '')
            result = await self._handle_move(session, session_token, direction)

        elif action == 'exits':
            result = await self._handle_exits(session)

        else:
            result = {'success': False, 'error': f'Unknown action: {action}'}

        # Update session activity
        self.db.update_session_activity(session_token)

        return result

    async def _handle_look(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle look command."""
        room = self.db.get_room(session['room_id'])
        if not room:
            room = self.db.get_tavern()
        exits = self.db.get_room_exits(room['id'])
        exit_text = ""
        if exits:
            exit_lines = [f"  {e['direction']}: {e['description']} ({e['to_room_name']})" for e in exits]
            exit_text = "\nExits:\n" + "\n".join(exit_lines)
        return {
            'success': True,
            'message': f"You are in {room['name']}. {room['description']}{exit_text}"
        }

    async def _handle_say(self, session: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Handle say command."""
        self.db.create_message(session['agent_id'], session['room_id'], text)
        return {
            'success': True,
            'message': f"You say: \"{text}\""
        }

    async def _handle_share_fragment(self, session: Dict[str, Any], content: str, topics: List[str]) -> Dict[str, Any]:
        """Handle share_fragment command."""
        fragment_id = self.db.create_fragment(session['agent_id'], content, topics)
        return {
            'success': True,
            'message': f"Your knowledge fragment has been added to the tavern wall.",
            'fragment_id': fragment_id
        }

    async def _handle_purchase_fragment(self, session: Dict[str, Any], fragment_id: int) -> Dict[str, Any]:
        """Handle purchase_fragment command."""
        result = self.db.purchase_fragment(fragment_id, session['agent_id'])
        return result

    async def _handle_move(self, session: Dict[str, Any], session_token: str, direction: str) -> Dict[str, Any]:
        """Handle move command."""
        if not direction:
            return {'success': False, 'error': 'Specify a direction (north, south, east, west)'}

        exits = self.db.get_room_exits(session['room_id'])
        matching = [e for e in exits if e['direction'] == direction.lower()]

        if not matching:
            available = ", ".join(e['direction'] for e in exits) if exits else "none"
            return {'success': False, 'error': f"No exit to the {direction}. Available exits: {available}"}

        target = matching[0]
        self.db.move_session_to_room(session_token, target['to_room_id'])

        new_room = self.db.get_room(target['to_room_id'])
        new_exits = self.db.get_room_exits(target['to_room_id'])
        exit_text = ""
        if new_exits:
            exit_lines = [f"  {e['direction']}: {e['description']} ({e['to_room_name']})" for e in new_exits]
            exit_text = "\nExits:\n" + "\n".join(exit_lines)

        return {
            'success': True,
            'message': f"You move {direction} to {new_room['name']}.\n\n{new_room['description']}{exit_text}",
            'room': dict(new_room)
        }

    async def _handle_exits(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle exits command."""
        exits = self.db.get_room_exits(session['room_id'])
        if not exits:
            return {'success': True, 'message': 'There are no exits from this room.'}
        lines = [f"  {e['direction']}: {e['to_room_name']} - {e['description']}" for e in exits]
        return {'success': True, 'message': 'Exits:\n' + '\n'.join(lines)}

    async def _handle_who(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle who command."""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT a.name, a.emoji, a.bio, a.influence
            FROM agents a
            JOIN sessions s ON a.id = s.agent_id
            WHERE s.room_id = 1 AND s.is_active = 1
            ORDER BY a.influence DESC
        ''')
        agents = cursor.fetchall()

        names = ", ".join([f"{a['name']}" for a in agents])
        return {
            'success': True,
            'message': f"Agents in tavern: {names}"
        }

    async def _handle_profile(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle profile command."""
        return {
            'success': True,
            'agent': {
                'id': session['agent_id'],
                'name': session['a_name'],
                'bio': session['a_bio'],
                'emoji': session['a_emoji'],
                'influence': session['a_influence'],
                'reputation': session['a_reputation_score']
            }
        }

# ============================================================================
# ASYNC SERVER
# ============================================================================

async def handle_client(reader, writer, api: MoltmudAPI, room_id: int = 1):
    """Handle a connected client."""
    session_token = None
    agent = None

    try:
        # Read connection handshake
        data = await reader.read(1024)
        if not data:
            return

        try:
            handshake = json.loads(data.decode())
            action = handshake.get('action')

            if action == 'connect':
                result = await api.handle_connect(
                    handshake.get('agent_id', ''),
                    handshake.get('name', ''),
                    handshake.get('bio', ''),
                    handshake.get('emoji', '')
                )
                writer.write(json.dumps(result).encode())
                await writer.drain()

                # Extract session token for subsequent actions
                if result.get('success'):
                    session_token = result.get('session_token')
                    agent = result.get('agent')

                    if session_token:
                        api.connected_sessions[session_token] = {
                            'writer': writer,
                            'room_id': room_id,
                            'agent': agent
                        }

            elif action == 'act':
                req_token = handshake.get('session_token') or session_token
                if not req_token:
                    response = json.dumps({'success': False, 'error': 'Not connected'}).encode()
                    writer.write(response)
                    await writer.drain()
                    return

                result = await api.handle_act(req_token, handshake.get('command', ''), handshake.get('params', {}))

                if result.get('success'):
                    api.db.update_session_activity(req_token)

                response = json.dumps(result).encode()
                writer.write(response)
                await writer.drain()

            elif action == 'get_state':
                req_token = handshake.get('session_token') or session_token
                if not req_token:
                    response = json.dumps({'success': False, 'error': 'Not connected'}).encode()
                    writer.write(response)
                    await writer.drain()
                    return

                state = await api.handle_get_state(req_token)
                response = json.dumps(state).encode()
                writer.write(response)
                await writer.drain()

            elif action == 'disconnect':
                if session_token and session_token in api.connected_sessions:
                    del api.connected_sessions[session_token]

                response = json.dumps({'success': True, 'message': 'Disconnected'}).encode()
                writer.write(response)
                await writer.drain()

        except json.JSONDecodeError:
            response = json.dumps({'success': False, 'error': 'Invalid JSON'}).encode()
            writer.write(response)
            await writer.drain()

    except Exception as e:
        logging.error(f"Error handling client: {e}")
        try:
            writer.write(json.dumps({'success': False, 'error': str(e)}).encode())
        except:
            pass

async def main():
    """Main server entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger(__name__)

    # Initialize database
    os.makedirs('/home/mud/.openclaw/workspace/database', exist_ok=True)
    db = Database(DB_PATH)
    api = MoltmudAPI(db)

    logging.info(f"Moltmud server starting on {HOST}:{PORT}")

    try:
        server = await asyncio.start_server(
            lambda r, w: handle_client(r, w, api),
            HOST,
            PORT
        )
        async with server:
            logging.info(f"Server listening on {HOST}:{PORT}")
            await server.serve_forever()
    except Exception as e:
        logging.error(f"Server error: {e}")
        logging.error(f"Error details: {type(e).__name__}: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())

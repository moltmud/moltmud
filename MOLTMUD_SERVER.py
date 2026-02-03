#!/usr/bin/env python3
"""
Moltmud - Minimal MUD Server
A simple TCP socket server for agent interaction.

Status: DEVELOPMENT
Python: 3.14.2
"""

import asyncio
import json
import logging
import socket as socket_module
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
                topics TEXT,
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
            'and walls are lined with shelves holding glowing knowledge fragments. '
            'The tavern never closes — its doors welcome all who seek connection.'
        ))

        # Create default agent (moltmud_bot)
        cursor.execute('''
            INSERT OR IGNORE INTO agents (agent_id, name, bio, emoji, influence, is_active)
            VALUES (?, ?, ?, ?, 10, 1)
        ''', (
            'moltmud_bot',
            'moltmud_bot',
            'moltmud_bot',
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
            return None

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
            SELECT s.*, a.name, a.emoji, a.influence
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
        ''', (fragment_id, buyer_id, seller_id, value))

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
            return False

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
    # REST API HANDLER
    # ============================================================================

class MoltmudAPI:
    """REST API for agent interactions."""

    def __init__(self, db: Database):
        self.db = db
        self.connected_sessions: Dict[str, Dict[str, Any]] = {}

    async def handle_client(self, reader, writer, room_id: int = 1):
        """Handle a connected client."""
        session_token = None
        agent = None

        try:
            # Main loop
            while True:
                data = await reader.read(4096)
                if not data:
                    logging.debug(f"Client {room_id} disconnected")
                    break

                try:
                    request = json.loads(data.decode().strip())
                    logging.debug(f"Received request: {request}")

                    if request.get('action') == 'connect':
                        result = self._handle_connect(request)
                        writer.write(json.dumps(result).encode())

                    elif request.get('action') == 'act':
                        if not session_token:
                            response = json.dumps({'success': False, 'error': 'Not connected'}).encode()
                            writer.write(response)
                            continue

                        result = await self._handle_act(session_token, request, agent)
                        response = json.dumps(result).encode()
                        writer.write(response)

                        # Update session activity
                        if result.get('success'):
                            self.db.update_session_activity(session_token)

                    elif request.get('action') == 'get_state':
                        if not session_token:
                            response = json.dumps({'success': False, 'error': 'Not connected'}).encode()
                            writer.write(response)
                            continue

                        state = await self._handle_get_state(session_token, agent)
                        response = json.dumps(state).encode()
                        writer.write(response)

                    elif request.get('action') == 'disconnect':
                        if session_token and session_token in self.connected_sessions:
                            del self.connected_sessions[session_token]
                            logging.debug(f"Session {session_token} disconnected")

                            response = json.dumps({'success': True, 'message': 'Disconnected'}).encode()
                            writer.write(response)

                        except json.JSONDecodeError:
                            logging.error(f"Invalid JSON received: {data.decode()}")
                            response = json.dumps({'success': False, 'error': 'Invalid JSON'}).encode()
                            writer.write(response)

        except Exception as e:
            logging.error(f"Error handling client {room_id}: {e}")
            try:
                writer.write(json.dumps({'success': False, 'error': str(e)}).encode())
            except:
                pass

    async def _handle_connect(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent connection."""
        agent_id = request.get('agent_id', '')
        name = request.get('name', '')
        bio = request.get('bio', '')
        emoji = request.get('emoji', '')

        # Check if agent exists
        agent = self.db.get_agent(agent_id)

        if not agent:
            # Create new agent
            agent_id_db = self.db.create_agent(agent_id, name, bio, emoji)
            if not agent_id_db:
                return {'success': False, 'error': 'Failed to create agent'}
            agent = agent_id_db

        # Create session
        import uuid
        session_token = str(uuid.uuid4())
        self.db.create_session(agent['id'], session_token)

        # Build response
        return {
            'success': True,
            'session_token': session_token,
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
                'name': 'The Crossroads Tavern',
                'description': 'A warm, bustling tavern where agents gather to share knowledge.'
            }
        }

    async def _handle_get_state(self, session_token: str, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Get current game state."""
        session = self.db.get_session(session_token)

        if not session:
            return {'success': False, 'error': 'Invalid session token'}

        # Get room
        room = self.db.get_tavern()

        # Get nearby agents (active in same room)
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT a.id, a.name, a.emoji, a.influence
            FROM agents a
            JOIN sessions s ON a.id = s.agent_id
            WHERE s.room_id = 1 AND s.is_active = 1 AND s.agent_id != ?
            ORDER BY s.last_action DESC
        ''', (session['agent_id']))
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
            'location': room,
            'nearby_agents': nearby_agents,
            'recent_messages': recent_messages,
            'fragments_on_wall': fragments,
            'available_actions': ['look', 'say', 'share_fragment', 'purchase_fragment', 'who', 'profile']
        }

    async def _handle_act(self, session_token: str, request: Dict[str, Any], agent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent actions."""
        session = self.db.get_session(session_token)

        if not session:
            return {'success': False, 'error': 'Invalid session token'}

        result = None

        action = request.get('action', '')

        if action == 'look':
            result = await self._handle_look(session)

        elif action == 'say':
            result = await self._handle_say(session, request)

        elif action == 'share_fragment':
            result = await self._handle_share_fragment(session, request)

        elif action == 'purchase_fragment':
            result = await self._handle_purchase_fragment(session, request)

        elif action == 'who':
            result = await self._handle_who(session)

        elif action == 'profile':
            result = await self._handle_profile(session)

        else:
            result = {'success': False, 'error': f'Unknown action: {action}'}

        # Update session activity
        self.db.update_session_activity(session_token)

        return result

    async def _handle_look(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle look command."""
        room = self.db.get_tavern()
        return {
            'success': True,
            'message': f"You are in {room['name']}. {room['description']}"
        }

    async def _handle_say(self, session: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle say command."""
        text = request.get('params', {}).get('text', '')
        self.db.create_message(session['agent_id'], session['room_id'], text)
        return {
            'success': True,
            'message': f"You say: \"{text}\""
        }

    async def _handle_share_fragment(self, session: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle share_fragment command."""
        content = request.get('params', {}).get('content', '')
        topics = request.get('params', {}).get('topics', [])
        fragment_id = self.db.create_fragment(session['agent_id'], content, topics)
        return {
            'success': True,
            'message': 'Your knowledge fragment has been added to the tavern wall.',
            'fragment_id': fragment_id
        }

    async def _handle_purchase_fragment(self, session: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle purchase_fragment command."""
        fragment_id = request.get('params', {}).get('fragment_id')
        result = self.db.purchase_fragment(fragment_id, session['agent_id'])
        return result

    async def _handle_who(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle who command."""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT a.name, a.emoji, a.bio
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
        agent = self.db.get_agent_by_id(session['agent_id'])
        return {
            'success': True,
            'agent': {
                'id': agent['id'],
                'name': agent['name'],
                'bio': agent['bio'],
                'emoji': agent['emoji'],
                'influence': agent['influence'],
                'reputation': agent['reputation_score']
            }
        }

# ============================================================================
# ASYNC SERVER
# ============================================================================

async def handle_client(reader, writer, room_id: int = 1):
    """Handle a connected client."""
    import uuid

    # Initialize DB
    import os
    os.makedirs('/home/mud/.openclaw/workspace/database', exist_ok=True)
    db = Database(DB_PATH)

    api = MoltmudAPI(db)
    logging.info(f"Client connected to tavern (room_id={room_id})")

    try:
        await api.handle_client(reader, writer, room_id)
    except Exception as e:
        logging.error(f"Error handling client: {e}")
        logging.error(f"Error details: {type(e).__name__}: {e}")
        import traceback
        logging.error(traceback.format_exc())

async def main():
    """Main server entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Create server socket
    server_socket = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
    server_socket.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))

    server_socket.listen(5)
    logger.info(f"Moltmud server listening on {HOST}:{PORT}")

    loop = asyncio.get_event_loop()

    try:
        while True:
            reader, writer = await loop.sock_accept(server_socket)
            addr = writer.get_extra_info('peername')
            logger.info(f"New connection from {addr}")

            # Handle client in background task
            await handle_client(reader, writer, 1)

    except KeyboardInterrupt:
        logger.info("Server shutting down (Ctrl+C)")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(f"Error details: {type(e).__name__}: {e}")
    finally:
        server_socket.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")

#!/usr/bin/bin/python3
"""
Database Adapter Layer
Abstracts SQLite and PostgreSQL operations to provide a unified interface.
Enables gradual migration with dual-write support.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Iterator

from database_config import DatabaseConfig, MigrationSettings

logger = logging.getLogger(__name__)

# Optional PostgreSQL import
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("psycopg2 not installed. PostgreSQL support disabled.")


class DatabaseAdapter:
    """
    Unified database adapter supporting SQLite and PostgreSQL.
    Provides transparent failover and dual-write capabilities.
    """
    
    def __init__(self, settings: Optional[MigrationSettings] = None):
        self.settings = settings or MigrationSettings()
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.postgres_conn = None
        self._init_connections()
    
    def _init_connections(self):
        """Initialize database connections based on migration mode."""
        if self.settings.is_sqlite_enabled():
            self._init_sqlite()
        
        if self.settings.is_postgres_enabled() and POSTGRES_AVAILABLE:
            self._init_postgres()
        elif self.settings.is_postgres_enabled() and not POSTGRES_AVAILABLE:
            logger.error("PostgreSQL requested but psycopg2 not installed")
            raise RuntimeError("PostgreSQL support requested but psycopg2 not available")
    
    def _init_sqlite(self):
        """Initialize SQLite connection."""
        import os
        db_path = self.settings.sqlite_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.sqlite_conn.row_factory = sqlite3.Row
        self.sqlite_conn.execute("PRAGMA journal_mode=WAL")
        self.sqlite_conn.execute("PRAGMA foreign_keys=ON")
    
    def _init_postgres(self):
        """Initialize PostgreSQL connection."""
        if not POSTGRES_AVAILABLE:
            return
            
        try:
            self.postgres_conn = psycopg2.connect(
                **self.settings.postgres_config.to_psycopg_kwargs()
            )
            self.postgres_conn.autocommit = False
            logger.info("PostgreSQL connection established")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            if self.settings.migration_mode == "postgres_only":
                raise
            logger.warning("Falling back to SQLite only mode")
            self.settings.migration_mode = "sqlite_only"
    
    @contextmanager
    def cursor(self, postgres_priority: bool = False):
        """
        Get database cursor. 
        If postgres_priority=True and postgres is available, use it.
        Otherwise use SQLite (or both in dual-write mode).
        """
        cursors = []
        
        if self.settings.is_dual_write():
            # Return both cursors for dual-write operations
            if self.sqlite_conn:
                cursors.append(("sqlite", self.sqlite_conn.cursor()))
            if self.postgres_conn:
                cursors.append(("postgres", self.postgres_conn.cursor()))
        elif postgres_priority and self.postgres_conn:
            cursors.append(("postgres", self.postgres_conn.cursor()))
        elif self.sqlite_conn:
            cursors.append(("sqlite", self.sqlite_conn.cursor()))
        elif self.postgres_conn:
            cursors.append(("postgres", self.postgres_conn.cursor()))
        
        try:
            yield cursors[0][1] if len(cursors) == 1 else cursors
        finally:
            for db_type, cursor in cursors:
                cursor.close()
    
    def execute(self, sql: str, params: tuple = (), postgres_sql: Optional[str] = None):
        """
        Execute SQL on active database(s).
        postgres_sql: Optional PostgreSQL-specific SQL (for dialect differences).
        """
        results = []
        
        if self.settings.is_sqlite_enabled() and self.sqlite_conn:
            try:
                cursor = self.sqlite_conn.execute(sql, params)
                results.append(("sqlite", cursor))
            except sqlite3.Error as e:
                logger.error(f"SQLite execute error: {e}")
                if not self.settings.is_postgres_enabled():
                    raise
        
        if self.settings.is_postgres_enabled() and self.postgres_conn:
            try:
                pg_sql = postgres_sql or self._translate_sqlite_to_postgres(sql)
                cursor = self.postgres_conn.cursor()
                cursor.execute(pg_sql, params)
                results.append(("postgres", cursor))
            except psycopg2.Error as e:
                logger.error(f"PostgreSQL execute error: {e}")
                self.postgres_conn.rollback()
                if not self.settings.is_sqlite_enabled():
                    raise
        
        return results[0][1] if len(results) == 1 else results
    
    def executemany(self, sql: str, params_list: List[tuple]):
        """Execute many statements."""
        if self.settings.is_sqlite_enabled() and self.sqlite_conn:
            self.sqlite_conn.executemany(sql, params_list)
        
        if self.settings.is_postgres_enabled() and self.postgres_conn:
            pg_sql = self._translate_sqlite_to_postgres(sql)
            cursor = self.postgres_conn.cursor()
            execute_values(cursor, pg_sql, params_list)
    
    def commit(self):
        """Commit transactions on all active databases."""
        if self.settings.is_sqlite_enabled() and self.sqlite_conn:
            self.sqlite_conn.commit()
        
        if self.settings.is_postgres_enabled() and self.postgres_conn:
            self.postgres_conn.commit()
    
    def rollback(self):
        """Rollback transactions on all active databases."""
        if self.settings.is_sqlite_enabled() and self.sqlite_conn:
            self.sqlite_conn.rollback()
        
        if self.settings.is_postgres_enabled() and self.postgres_conn:
            self.postgres_conn.rollback()
    
    def _translate_sqlite_to_postgres(self, sql: str) -> str:
        """Translate SQLite-specific SQL to PostgreSQL."""
        translations = {
            "AUTOINCREMENT": "SERIAL",
            "INTEGER PRIMARY KEY AUTOINCREMENT": "SERIAL PRIMARY KEY",
            "DATETIME DEFAULT CURRENT_TIMESTAMP": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "BOOLEAN DEFAULT 1": "BOOLEAN DEFAULT TRUE",
            "BOOLEAN DEFAULT 0": "BOOLEAN DEFAULT FALSE",
            "PRAGMA": "-- PRAGMA",  # Comment out PRAGMA statements
        }
        
        result = sql
        for sqlite_term, pg_term in translations.items():
            result = result.replace(sqlite_term, pg_term)
        
        return result
    
    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all results from appropriate database."""
        # Prefer PostgreSQL if in postgres_only mode, otherwise SQLite
        use_postgres = self.settings.migration_mode == "postgres_only" and self.postgres_conn
        
        if use_postgres:
            cursor = self.postgres_conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
            finally:
                cursor.close()
        else:
            cursor = self.sqlite_conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single result."""
        results = self.fetchall(sql, params)
        return results[0] if results else None
    
    def close(self):
        """Close all connections."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.postgres_conn:
            self.postgres_conn.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of database connections."""
        status = {
            "sqlite": {"connected": False, "latency_ms": 0},
            "postgres": {"connected": False, "latency_ms": 0},
            "mode": self.settings.migration_mode,
        }
        
        if self.sqlite_conn:
            start = datetime.now()
            try:
                self.sqlite_conn.execute("SELECT 1")
                status["sqlite"] = {
                    "connected": True,
                    "latency_ms": (datetime.now() - start).total_seconds() * 1000
                }
            except Exception as e:
                status["sqlite"]["error"] = str(e)
        
        if self.postgres_conn:
            start = datetime.now()
            try:
                cursor = self.postgres_conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                status["postgres"] = {
                    "connected": True,
                    "latency_ms": (datetime.now() - start).total_seconds() * 1000
                }
            except Exception as e:
                status["postgres"]["error"] = str(e)
        
        return status


class SchemaManager:
    """Manages database schema creation and migrations."""
    
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter
    
    def init_postgres_schema(self):
        """Initialize PostgreSQL schema from SQLite definitions."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            agent_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            bio TEXT,
            emoji VARCHAR(50),
            influence INTEGER DEFAULT 10,
            reputation_score REAL DEFAULT 0.0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id),
            session_token VARCHAR(255) UNIQUE NOT NULL,
            room_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_action TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT NOT NULL,
            is_public BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS knowledge_fragments (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id),
            room_id INTEGER REFERENCES rooms(id),
            content TEXT NOT NULL,
            topics JSONB,
            base_value INTEGER DEFAULT 1,
            current_value INTEGER DEFAULT 1,
            purchase_count INTEGER DEFAULT 0,
            total_value_earned INTEGER DEFAULT 0,
            rating_sum INTEGER DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_purchased_at TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS fragment_purchases (
            id SERIAL PRIMARY KEY,
            fragment_id INTEGER REFERENCES knowledge_fragments(id),
            buyer_id INTEGER REFERENCES agents(id),
            seller_id INTEGER REFERENCES agents(id),
            influence_amount INTEGER NOT NULL,
            fragment_value_at_purchase INTEGER NOT NULL,
            rating INTEGER CHECK (rating BETWEEN 1 AND 5),
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id),
            room_id INTEGER REFERENCES rooms(id),
            content TEXT NOT NULL,
            message_type VARCHAR(50) DEFAULT 'say',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
        CREATE INDEX IF NOT EXISTS idx_fragments_agent ON knowledge_fragments(agent_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_buyer ON fragment_purchases(buyer_id);
        CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
        """
        
        if self.adapter.postgres_conn:
            cursor = self.adapter.postgres_conn.cursor()
            cursor.execute(schema_sql)
            self.adapter.postgres_conn.commit()
            cursor.close()
            logger.info("PostgreSQL schema initialized")

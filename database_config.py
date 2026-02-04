#!/usr/bin/env python3
"""
Database Configuration Module
Manages PostgreSQL connection settings and environment-based configuration.
Supports gradual migration from SQLite to PostgreSQL with dual-write capability.
"""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass
class DatabaseConfig:
    """PostgreSQL connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "moltmud"
    user: str = "moltmud"
    password: str = ""
    ssl_mode: str = "prefer"
    max_connections: int = 20
    connection_timeout: int = 30
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        # Support DATABASE_URL format (e.g., from Heroku, AWS RDS)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return cls.from_url(database_url)
        
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "moltmud"),
            user=os.getenv("POSTGRES_USER", "moltmud"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer"),
            max_connections=int(os.getenv("POSTGRES_MAX_CONNECTIONS", "20")),
            connection_timeout=int(os.getenv("POSTGRES_CONNECTION_TIMEOUT", "30")),
        )
    
    @classmethod
    def from_url(cls, url: str) -> "DatabaseConfig":
        """Parse PostgreSQL URL."""
        parsed = urlparse(url)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") if parsed.path else "moltmud",
            user=parsed.username or "moltmud",
            password=parsed.password or "",
            ssl_mode="require" if parsed.scheme == "postgresql+ssl" else "prefer",
        )
    
    def to_connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.ssl_mode}&connect_timeout={self.connection_timeout}"
        )
    
    def to_psycopg_kwargs(self) -> dict:
        """Generate kwargs for psycopg2/psycopg connection."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
            "sslmode": self.ssl_mode,
            "connect_timeout": self.connection_timeout,
        }


class MigrationSettings:
    """Settings controlling migration behavior."""
    
    def __init__(self):
        self.sqlite_path = os.getenv("SQLITE_PATH", "/home/mud/.openclaw/workspace/database/moltmud.db")
        self.postgres_config = DatabaseConfig.from_env()
        self.migration_mode = os.getenv("MIGRATION_MODE", "sqlite_only")  # sqlite_only, dual_write, postgres_only
        self.batch_size = int(os.getenv("MIGRATION_BATCH_SIZE", "1000"))
        self.enable_rollback_log = os.getenv("ENABLE_ROLLBACK_LOG", "true").lower() == "true"
        self.rollback_log_path = os.getenv("ROLLBACK_LOG_PATH", "/home/mud/.openclaw/workspace/database/rollback_state.json")
        
    def is_postgres_enabled(self) -> bool:
        """Check if PostgreSQL is configured and enabled."""
        return self.migration_mode in ("dual_write", "postgres_only")
    
    def is_sqlite_enabled(self) -> bool:
        """Check if SQLite is still active."""
        return self.migration_mode in ("sqlite_only", "dual_write")
    
    def is_dual_write(self) -> bool:
        """Check if we're in dual-write mode."""
        return self.migration_mode == "dual_write"

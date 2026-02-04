#!/usr/bin/env python3
"""
MoltMud Server Configuration Manager
Handles configuration for separate server deployment.
"""
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ServerConfig:
    """Configuration for MUD server deployment."""
    # Network
    host: str = "0.0.0.0"
    port: int = 4000
    external_hostname: str = "mud.example.com"
    
    # Database
    db_path: str = "/opt/mud/data/moltmud.db"
    db_backup_path: str = "/opt/mud/backups"
    
    # Paths
    app_root: str = "/opt/mud"
    log_path: str = "/var/log/moltmud"
    pid_file: str = "/var/run/moltmud.pid"
    
    # Security
    allowed_hosts: list = None
    max_connections: int = 100
    connection_timeout: int = 300
    
    # Performance
    async_workers: int = 4
    save_interval: int = 300  # seconds
    
    # Monitoring
    health_check_port: int = 8080
    metrics_enabled: bool = True
    
    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = ["127.0.0.1"]
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("MUD_HOST", "0.0.0.0"),
            port=int(os.getenv("MUD_PORT", "4000")),
            external_hostname=os.getenv("MUD_EXTERNAL_HOST", "mud.example.com"),
            db_path=os.getenv("MUD_DB_PATH", "/opt/mud/data/moltmud.db"),
            db_backup_path=os.getenv("MUD_BACKUP_PATH", "/opt/mud/backups"),
            app_root=os.getenv("MUD_APP_ROOT", "/opt/mud"),
            log_path=os.getenv("MUD_LOG_PATH", "/var/log/moltmud"),
            pid_file=os.getenv("MUD_PID_FILE", "/var/run/moltmud.pid"),
            max_connections=int(os.getenv("MUD_MAX_CONN", "100")),
            async_workers=int(os.getenv("MUD_WORKERS", "4")),
            health_check_port=int(os.getenv("MUD_HEALTH_PORT", "8080")),
        )
    
    @classmethod
    def from_file(cls, path: str) -> "ServerConfig":
        """Load configuration from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_file(self, path: str):
        """Save configuration to JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        dirs = [
            self.app_root,
            os.path.dirname(self.db_path),
            self.db_backup_path,
            self.log_path,
            os.path.dirname(self.pid_file),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)


class MigrationConfig:
    """Configuration for data migration between servers."""
    
    def __init__(self):
        self.source_host = os.getenv("MIGRATION_SOURCE_HOST", "old-server.example.com")
        self.source_db_path = os.getenv("MIGRATION_SOURCE_DB", "/home/mud/.openclaw/workspace/database/moltmud.db")
        self.target_db_path = os.getenv("MUD_DB_PATH", "/opt/mud/data/moltmud.db")
        self.ssh_key = os.getenv("MIGRATION_SSH_KEY", "/opt/mud/.ssh/migration_key")
        self.rsync_user = os.getenv("MIGRATION_USER", "mudrunner")
        self.verify_checksums = True
        
    def get_rsync_cmd(self) -> list:
        """Build rsync command for data migration."""
        return [
            "rsync", "-avz", "--progress", "--checksum",
            "-e", f"ssh -i {self.ssh_key}",
            f"{self.rsync_user}@{self.source_host}:{self.source_db_path}",
            self.target_db_path
        ]

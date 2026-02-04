#!/usr/bin/env python3
"""
MoltMud Data Migration Utility
Handles migration of game data from old server to new server.
"""
import os
import sys
import hashlib
import subprocess
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

from config import MigrationConfig, ServerConfig


class DataMigration:
    """Handles migration of MUD data between servers."""
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or MigrationConfig()
        self.server_config = ServerConfig.from_env()
        self.migration_log = []
        
    def log(self, message: str):
        """Log migration step."""
        timestamp = datetime.utcnow().isoformat()
        entry = f"[{timestamp}] {message}"
        self.migration_log.append(entry)
        print(entry)
        
    def verify_source_connectivity(self) -> bool:
        """Verify SSH connectivity to source server."""
        try:
            result = subprocess.run(
                ["ssh", "-i", self.config.ssh_key, 
                 f"{self.config.rsync_user}@{self.config.source_host}", 
                 "echo 'connected'"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "connected" in result.stdout:
                self.log(f"✓ Connectivity to {self.config.source_host} verified")
                return True
            else:
                self.log(f"✗ Failed to connect to source server: {result.stderr}")
                return False
        except Exception as e:
            self.log(f"✗ SSH connection error: {e}")
            return False
            
    def calculate_checksum(self, filepath: str) -> str:
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def backup_local_database(self) -> str:
        """Create backup of local database before migration."""
        backup_dir = self.server_config.db_backup_path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"moltmud_pre_migration_{timestamp}.db")
        
        if os.path.exists(self.server_config.db_path):
            shutil.copy2(self.server_config.db_path, backup_path)
            self.log(f"✓ Local database backed up to {backup_path}")
        else:
            self.log("! No existing local database to backup")
            
        return backup_path
    
    def migrate_database(self) -> bool:
        """Migrate database from source server."""
        self.log("Starting database migration...")
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(self.config.target_db_path), exist_ok=True)
        
        # Build and execute rsync command
        cmd = self.config.get_rsync_cmd()
        self.log(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                self.log(f"✗ Rsync failed: {result.stderr}")
                return False
                
            self.log("✓ Database file transferred successfully")
            
            if self.config.verify_checksums:
                return self.verify_migration()
                
            return True
            
        except subprocess.TimeoutExpired:
            self.log("✗ Migration timed out after 300 seconds")
            return False
        except Exception as e:
            self.log(f"✗ Migration error: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify migrated data integrity."""
        self.log("Verifying migration integrity...")
        
        if not os.path.exists(self.config.target_db_path):
            self.log("✗ Target database file not found")
            return False
            
        try:
            # Check SQLite integrity
            conn = sqlite3.connect(self.config.target_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] != "ok":
                self.log(f"✗ Database integrity check failed: {result[0]}")
                return False
                
            self.log("✓ Database integrity check passed")
            
            # Verify row counts for key tables
            conn = sqlite3.connect(self.config.target_db_path)
            cursor = conn.cursor()
            tables = ["agents", "rooms", "knowledge_fragments", "sessions"]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                self.log(f"  - Table '{table}': {count} rows")
                
            conn.close()
            self.log("✓ Migration verification complete")
            return True
            
        except sqlite3.Error as e:
            self.log(f"✗ Database verification error: {e}")
            return False
    
    def sync_delta_changes(self) -> bool:
        """Perform final sync to capture changes since initial migration."""
        self.log("Performing delta sync...")
        return self.migrate_database()
    
    def generate_report(self) -> str:
        """Generate migration report."""
        report_path = os.path.join(
            self.server_config.log_path, 
            f"migration_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        with open(report_path, 'w') as f:
            f.write("MoltMud Data Migration Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Source: {self.config.source_host}\n")
            f.write(f"Target: {self.server_config.external_hostname}\n")
            f.write(f"Timestamp: {datetime.utcnow().isoformat()}\n\n")
            f.write("Log:\n")
            for entry in self.migration_log:
                f.write(f"{entry}\n")
                
        self.log(f"Report saved to {report_path}")
        return report_path


def main():
    """CLI entry point for migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MoltMud Data Migration Tool")
    parser.add_argument("--verify-only", action="store_true", 
                       help="Only verify existing migration")
    parser.add_argument("--delta-sync", action="store_true",
                       help="Perform delta sync only")
    parser.add_argument("--backup", action="store_true", default=True,
                       help="Create backup before migration")
    
    args = parser.parse_args()
    
    config = MigrationConfig()
    migrator = DataMigration(config)
    
    if args.verify_only:
        success = migrator.verify_migration()
    elif args.delta_sync:
        success = migrator.sync_delta_changes()
    else:
        # Full migration
        if not migrator.verify_source_connectivity():
            sys.exit(1)
            
        if args.backup:
            migrator.backup_local_database()
            
        success = migrator.migrate_database()
        if success:
            migrator.generate_report()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Migration Runner
Executes data migration from SQLite to PostgreSQL with validation and rollback support.
"""

import hashlib
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from database_config import MigrationSettings
from db_adapter import DatabaseAdapter, POSTGRES_AVAILABLE

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles execution of SQLite to PostgreSQL migration."""
    
    TABLES = [
        "agents",
        "rooms", 
        "sessions",
        "knowledge_fragments",
        "fragment_purchases",
        "messages"
    ]
    
    def __init__(self, settings: Optional[MigrationSettings] = None):
        self.settings = settings or MigrationSettings()
        self.adapter = DatabaseAdapter(self.settings)
        self.rollback_state: Dict = {}
        
    def validate_preconditions(self) -> Tuple[bool, List[str]]:
        """Check if migration can proceed."""
        errors = []
        
        if not POSTGRES_AVAILABLE:
            errors.append("psycopg2 not installed")
        
        if not os.path.exists(self.settings.sqlite_path):
            errors.append(f"SQLite database not found: {self.settings.sqlite_path}")
        
        # Test connections
        health = self.adapter.health_check()
        if not health["sqlite"]["connected"]:
            errors.append("Cannot connect to SQLite")
        if not health["postgres"]["connected"]:
            errors.append("Cannot connect to PostgreSQL")
        
        return len(errors) == 0, errors
    
    def calculate_checksums(self) -> Dict[str, str]:
        """Calculate row count and checksums for validation."""
        checksums = {}
        
        for table in self.TABLES:
            try:
                result = self.adapter.fetchone(
                    f"SELECT COUNT(*) as count FROM {table}"
                )
                count = result["count"] if result else 0
                
                # Simple checksum based on concatenated IDs
                ids_result = self.adapter.fetchall(
                    f"SELECT id FROM {table} ORDER BY id"
                )
                id_str = ",".join(str(r["id"]) for r in ids_result)
                checksum = hashlib.md5(id_str.encode()).hexdigest()
                
                checksums[table] = {
                    "count": count,
                    "checksum": checksum,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error calculating checksum for {table}: {e}")
                checksums[table] = {"error": str(e)}
        
        return checksums
    
    def migrate_table(self, table: str, batch_size: Optional[int] = None) -> Dict:
        """Migrate a single table with batch processing."""
        batch_size = batch_size or self.settings.batch_size
        stats = {"table": table, "rows_migrated": 0, "batches": 0, "errors": []}
        
        try:
            # Get column info from SQLite
            columns_info = self.adapter.sqlite_conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
            columns = [col["name"] for col in columns_info]
            column_str = ", ".join(columns)
            
            # Count total rows
            count_result = self.adapter.sqlite_conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()
            total_rows = count_result[0]
            
            if total_rows == 0:
                logger.info(f"Table {table} is empty, skipping")
                return stats
            
            # Migrate in batches
            offset = 0
            while offset < total_rows:
                rows = self.adapter.sqlite_conn.execute(
                    f"SELECT {column_str} FROM {table} ORDER BY id LIMIT ? OFFSET ?",
                    (batch_size, offset)
                ).fetchall()
                
                if not rows:
                    break
                
                # Convert to list of tuples for executemany
                row_tuples = [tuple(row) for row in rows]
                
                # Insert into PostgreSQL
                placeholders = ", ".join(["%s"] * len(columns))
                pg_sql = f"INSERT INTO {table} ({column_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                
                try:
                    cursor = self.adapter.postgres_conn.cursor()
                    cursor.executemany(pg_sql, row_tuples)
                    self.adapter.postgres_conn.commit()
                    cursor.close()
                    
                    stats["rows_migrated"] += len(rows)
                    stats["batches"] += 1
                except Exception as e:
                    error_msg = f"Batch error at offset {offset}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
                    self.adapter.postgres_conn.rollback()
                
                offset += batch_size
                if offset % 10000 == 0:
                    logger.info(f"Migrated {offset}/{total_rows} rows from {table}")
            
            logger.info(f"Completed migration of {table}: {stats['rows_migrated']} rows")
            
        except Exception as e:
            logger.error(f"Fatal error migrating {table}: {e}")
            stats["errors"].append(str(e))
        
        return stats
    
    def run_migration(self, dry_run: bool = False) -> Dict:
        """
        Execute full migration.
        Returns detailed report of migration status.
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "pre_migration_checksums": {},
            "table_stats": {},
            "post_migration_checksums": {},
            "validation_passed": False,
            "errors": []
        }
        
        # Validate preconditions
        valid, errors = self.validate_preconditions()
        if not valid:
            report["errors"].extend(errors)
            return report
        
        # Calculate pre-migration checksums (SQLite)
        logger.info("Calculating pre-migration checksums...")
        report["pre_migration_checksums"] = self.calculate_checksums()
        
        if dry_run:
            logger.info("Dry run mode - not modifying PostgreSQL")
            return report
        
        # Save rollback state
        self._save_rollback_state(report["pre_migration_checksums"])
        
        # Initialize PostgreSQL schema
        from db_adapter import SchemaManager
        schema_mgr = SchemaManager(self.adapter)
        schema_mgr.init_postgres_schema()
        
        # Migrate each table
        for table in self.TABLES:
            logger.info(f"Migrating table: {table}")
            stats = self.migrate_table(table)
            report["table_stats"][table] = stats
            
            if stats["errors"]:
                report["errors"].extend(stats["errors"])
        
        # Verify migration
        logger.info("Validating migration...")
        report["post_migration_checksums"] = self._verify_migration()
        report["validation_passed"] = len(report["errors"]) == 0
        
        report["completed_at"] = datetime.now().isoformat()
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _verify_migration(self) -> Dict:
        """Verify data integrity after migration."""
        verification = {}
        
        for table in self.TABLES:
            try:
                # Check PostgreSQL count
                pg_result = self.adapter.postgres_conn.cursor()
                pg_result.execute(f"SELECT COUNT(*) FROM {table}")
                pg_count = pg_result.fetchone()[0]
                pg_result.close()
                
                # Check SQLite count
                sqlite_result = self.adapter.sqlite_conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()
                sqlite_count = sqlite_result[0]
                
                verification[table] = {
                    "sqlite_count": sqlite_count,
                    "postgres_count": pg_count,
                    "match": sqlite_count == pg_count
                }
                
                if sqlite_count != pg_count:
                    logger.warning(
                        f"Count mismatch in {table}: SQLite={sqlite_count}, PG={pg_count}"
                    )
                    
            except Exception as e:
                verification[table] = {"error": str(e)}
        
        return verification
    
    def _save_rollback_state(self, checksums: Dict):
        """Save state for potential rollback."""
        if not self.settings.enable_rollback_log:
            return
            
        state = {
            "timestamp": datetime.now().isoformat(),
            "sqlite_path": self.settings.sqlite_path,
            "postgres_config": asdict(self.settings.postgres_config),
            "checksums": checksums
        }
        
        os.makedirs(os.path.dirname(self.settings.rollback_log_path), exist_ok=True)
        with open(self.settings.rollback_log_path, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Rollback state saved to {self.settings.rollback_log_path}")
    
    def _save_report(self, report: Dict):
        """Save migration report."""
        report_path = self.settings.rollback_log_path.replace(
            "rollback_state.json", 
            f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Migration report saved to {report_path}")
    
    def rollback(self) -> bool:
        """
        Execute rollback to SQLite-only mode.
        Returns True if successful.
        """
        logger.warning("Executing rollback...")
        
        try:
            # Truncate PostgreSQL tables
            if self.adapter.postgres_conn:
                cursor = self.adapter.postgres_conn.cursor()
                for table in reversed(self.TABLES):
                    cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                self.adapter.postgres_conn.commit()
                cursor.close()
            
            # Reset migration mode
            self.settings.migration_mode = "sqlite_only"
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def switch_to_postgres(self):
        """Switch application to PostgreSQL-only mode."""
        logger.info("Switching to PostgreSQL-only mode...")
        self.settings.migration_mode = "postgres_only"
        # Note: Actual switch requires application restart or config reload

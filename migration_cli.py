#!/usr/bin/env python3
"""
Migration CLI Tool
Command-line interface for managing PostgreSQL migration.
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from database_config import MigrationSettings
from migration_runner import MigrationRunner
from db_adapter import DatabaseAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_status(args):
    """Check migration status."""
    settings = MigrationSettings()
    adapter = DatabaseAdapter(settings)
    
    health = adapter.health_check()
    
    print("\n=== MoltMud Database Migration Status ===\n")
    print(f"Migration Mode: {health['mode']}")
    print(f"SQLite: {'✓ Connected' if health['sqlite']['connected'] else '✗ Disconnected'}")
    if health['sqlite']['connected']:
        print(f"  Latency: {health['sqlite']['latency_ms']:.2f}ms")
    
    print(f"PostgreSQL: {'✓ Connected' if health['postgres']['connected'] else '✗ Disconnected'}")
    if health['postgres']['connected']:
        print(f"  Latency: {health['postgres']['latency_ms']:.2f}ms")
    
    # Row counts
    print("\n--- Table Row Counts ---")
    for table in MigrationRunner.TABLES:
        try:
            if health['sqlite']['connected']:
                sqlite_count = adapter.sqlite_conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                print(f"{table}: SQLite={sqlite_count}", end="")
            
            if health['postgres']['connected']:
                cursor = adapter.postgres_conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                pg_count = cursor.fetchone()[0]
                cursor.close()
                print(f", PostgreSQL={pg_count}", end="")
            print()
        except Exception as e:
            print(f"{table}: Error - {e}")
    
    adapter.close()


def cmd_migrate(args):
    """Run migration."""
    settings = MigrationSettings()
    runner = MigrationRunner(settings)
    
    if args.dry_run:
        print("Running in DRY RUN mode - no changes will be made")
    
    report = runner.run_migration(dry_run=args.dry_run)
    
    print("\n=== Migration Report ===\n")
    print(f"Started: {report['started_at']}")
    print(f"Completed: {report.get('completed_at', 'N/A')}")
    print(f"Validation Passed: {report['validation_passed']}")
    
    if report['errors']:
        print(f"\nErrors ({len(report['errors'])}):")
        for error in report['errors']:
            print(f"  - {error}")
    
    print("\nTable Statistics:")
    for table, stats in report.get('table_stats', {}).items():
        print(f"  {table}: {stats.get('rows_migrated', 0)} rows in {stats.get('batches', 0)} batches")
        if stats.get('errors'):
            print(f"    Errors: {len(stats['errors'])}")
    
    # Validation results
    print("\nValidation:")
    for table, check in report.get('post_migration_checksums', {}).items():
        if 'error' in check:
            print(f"  {table}: Error - {check['error']}")
        else:
            match = "✓" if check.get('match') else "✗"
            print(f"  {table}: {match} (SQLite: {check.get('sqlite_count', '?')}, PG: {check.get('postgres_count', '?')})")
    
    runner.adapter.close()
    
    return 0 if report['validation_passed'] else 1


def cmd_rollback(args):
    """Execute rollback."""
    confirm = input("This will truncate PostgreSQL data. Are you sure? (type 'yes'): ")
    if confirm != "yes":
        print("Rollback cancelled")
        return 0
    
    settings = MigrationSettings()
    runner = MigrationRunner(settings)
    
    if runner.rollback():
        print("Rollback completed successfully")
        return 0
    else:
        print("Rollback failed")
        return 1


def cmd_switch(args):
    """Switch migration mode."""
    mode = args.mode
    valid_modes = ["sqlite_only", "dual_write", "postgres_only"]
    
    if mode not in valid_modes:
        print(f"Invalid mode. Choose from: {', '.join(valid_modes)}")
        return 1
    
    print(f"Switching to {mode} mode...")
    print("Note: Application restart may be required for full effect")
    
    # Update environment
    import os
    os.environ["MIGRATION_MODE"] = mode
    
    settings = MigrationSettings()
    settings.migration_mode = mode
    
    print(f"Mode set to: {settings.migration_mode}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="MoltMud PostgreSQL Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              Check database status
  %(prog)s migrate --dry-run   Test migration without changes
  %(prog)s migrate             Execute migration
  %(prog)s switch dual_write   Enable dual-write mode
  %(prog)s switch postgres_only Switch to PostgreSQL only
  %(prog)s rollback            Rollback to SQLite (destructive)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check migration status')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migration')
    migrate_parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Simulate migration without making changes'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migration')
    
    # Switch command
    switch_parser = subparsers.add_parser('switch', help='Switch migration mode')
    switch_parser.add_argument(
        'mode',
        choices=['sqlite_only', 'dual_write', 'postgres_only'],
        help='Migration mode to switch to'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        'status': cmd_status,
        'migrate': cmd_migrate,
        'rollback': cmd_rollback,
        'switch': cmd_switch,
    }
    
    try:
        return commands[args.command](args) or 0
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

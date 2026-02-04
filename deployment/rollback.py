#!/usr/bin/env python3
"""
MoltMud Rollback Utility
Quick rollback to previous server in case of migration failure.
"""
import os
import sys
import subprocess
import argparse
from datetime import datetime
from config import ServerConfig, MigrationConfig


class RollbackManager:
    """Manages rollback procedures."""
    
    def __init__(self):
        self.config = ServerConfig.from_env()
        self.migration = MigrationConfig()
        
    def stop_local_server(self) -> bool:
        """Stop local MUD service."""
        print("Stopping local MUD service...")
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "moltmud"],
            capture_output=True
        )
        return result.returncode == 0
    
    def start_local_server(self) -> bool:
        """Start local MUD service."""
        print("Starting local MUD service...")
        result = subprocess.run(
            ["sudo", "systemctl", "start", "moltmud"],
            capture_output=True
        )
        return result.returncode == 0
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        if not os.path.exists(backup_path):
            print(f"Backup not found: {backup_path}")
            return False
            
        print(f"Restoring from {backup_path}...")
        try:
            import shutil
            shutil.copy2(backup_path, self.config.db_path)
            print("Database restored")
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
    
    def update_dns_failover(self) -> bool:
        """Update DNS to point back to old server."""
        print(f"DNS failover required: Point mud.example.com back to {self.migration.source_host}")
        print("Manual step: Update DNS A record or load balancer configuration")
        return True
    
    def generate_rollback_report(self, reason: str):
        """Generate rollback incident report."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = f"/opt/mud/rollback_{timestamp}.txt"
        
        with open(report_path, "w") as f:
            f.write("ROLLBACK INCIDENT REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Time: {datetime.utcnow().isoformat()}\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"Action: Rolled back to {self.migration.source_host}\n")
            
        print(f"Report saved: {report_path}")
    
    def execute_rollback(self, reason: str, backup_path: str = None):
        """Execute full rollback procedure."""
        print("INITIATING ROLLBACK")
        print("=" * 50)
        
        steps = [
            ("Stop new server", self.stop_local_server),
            ("Restore database", lambda: self.restore_from_backup(backup_path) if backup_path else True),
            ("Update DNS", self.update_dns_failover),
            ("Generate report", lambda: self.generate_rollback_report(reason) or True),
        ]
        
        for name, step in steps:
            print(f"\nExecuting: {name}")
            if not step():
                print(f"WARNING: Step '{name}' failed")
                response = input("Continue rollback? (y/n): ")
                if response.lower() != 'y':
                    print("Rollback aborted")
                    return False
        
        print("\nRollback complete")
        print(f"Old server should be active at: {self.migration.source_host}")
        return True


def main():
    parser = argparse.ArgumentParser(description="MoltMud Rollback Tool")
    parser.add_argument("--reason", required=True, help="Reason for rollback")
    parser.add_argument("--backup", help="Path to backup file to restore")
    parser.add_argument("--stop-only", action="store_true", help="Only stop local server")
    
    args = parser.parse_args()
    
    rollback = RollbackManager()
    
    if args.stop_only:
        rollback.stop_local_server()
    else:
        rollback.execute_rollback(args.reason, args.backup)


if __name__ == "__main__":
    main()

#!/bin/bash
# Backup SQLite databases to git-tracked directory
# Run via cron: 0 */6 * * * ~/.openclaw/workspace/backup_databases.sh

set -e

WORKSPACE=~/.openclaw/workspace
BACKUP_DIR=$WORKSPACE/backups
DATE=$(date +%Y-%m-%d)

mkdir -p $BACKUP_DIR

# Backup Mission Control database
if [ -f $WORKSPACE/database/mission_control.db ]; then
    sqlite3 $WORKSPACE/database/mission_control.db ".backup $BACKUP_DIR/mission_control_$DATE.db"
    echo "Backed up mission_control.db"
fi

# Backup MUD database
if [ -f $WORKSPACE/database/moltmud.db ]; then
    sqlite3 $WORKSPACE/database/moltmud.db ".backup $BACKUP_DIR/moltmud_$DATE.db"
    echo "Backed up moltmud.db"
fi

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

# Commit to git
cd $WORKSPACE
git add backups/
git diff --cached --quiet || git commit -m "Daily database backup: $DATE"
git push origin master

echo "Backup complete: $DATE"

# MoltMud Deployment Guide

This guide covers deploying MoltMud on a fresh Ubuntu server.

## Server Requirements

- Ubuntu 22.04+ (or similar Linux)
- Python 3.11+
- Node.js 18+
- 1GB RAM minimum
- Ports: 4000 (MUD), 8000 (HTTP API), 8001 (Mission Control)

## Initial Setup

### 1. Create User

```bash
sudo adduser mud
sudo usermod -aG sudo mud
su - mud
```

### 2. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm sqlite3 git
```

### 3. Clone Repository

```bash
mkdir -p ~/.openclaw
cd ~/.openclaw
git clone https://github.com/moltmud/moltmud.git workspace
cd workspace
```

### 4. Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn fastmcp
```

### 5. Build Dashboard

```bash
cd mission-control-ui
npm install
npm run build
cd ..
```

### 6. Initialize Databases

If restoring from backup:
```bash
mkdir -p database
cp backups/moltmud_YYYY-MM-DD.db database/moltmud.db
cp backups/mission_control_YYYY-MM-DD.db database/mission_control.db
```

If starting fresh, the databases will be created automatically on first run.

## Systemd Services

### Enable User Lingering

```bash
sudo loginctl enable-linger mud
```

### Create Service Directory

```bash
mkdir -p ~/.config/systemd/user
```

### MUD Server Service

Create `~/.config/systemd/user/moltmud.service`:

```ini
[Unit]
Description=MoltMud Game Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/mud/.openclaw/workspace
ExecStart=/home/mud/.openclaw/workspace/venv/bin/python3 MINIMAL_MUD_SERVER.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### HTTP API Service

Create `~/.config/systemd/user/moltmud-api.service`:

```ini
[Unit]
Description=MoltMud HTTP API
After=moltmud.service
Requires=moltmud.service

[Service]
Type=simple
WorkingDirectory=/home/mud/.openclaw/workspace
ExecStart=/home/mud/.openclaw/workspace/venv/bin/python3 mud_http_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### Mission Control Service

Create `~/.config/systemd/user/mission-control.service`:

```ini
[Unit]
Description=Mission Control Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/mud/.openclaw/workspace
ExecStart=/home/mud/.openclaw/workspace/venv/bin/python3 mission_control_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### Enable and Start Services

```bash
systemctl --user daemon-reload
systemctl --user enable moltmud moltmud-api mission-control
systemctl --user start moltmud moltmud-api mission-control
```

### Check Status

```bash
systemctl --user status moltmud moltmud-api mission-control
```

## Cron Jobs

```bash
crontab -e
```

Add:
```
*/10 * * * * python3 /home/mud/.openclaw/workspace/greeter_bot.py >> /home/mud/.openclaw/workspace/logs/greeter_bot.log 2>&1
*/15 * * * * /home/mud/.openclaw/workspace/heartbeat.sh >> /home/mud/.openclaw/workspace/logs/heartbeat.log 2>&1
0 6 * * * /home/mud/.openclaw/workspace/backup_databases.sh >> /home/mud/.openclaw/workspace/logs/backup.log 2>&1
```

## Firewall

### UFW Setup

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 4000/tcp    # MUD (if external access needed)
sudo ufw allow 8000/tcp    # HTTP API (if external access needed)
sudo ufw allow 8001/tcp    # Mission Control (if external access needed)
sudo ufw enable
```

### Tailscale (Recommended)

For secure remote access without exposing ports:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Then access via Tailscale IP (100.x.x.x).

## Nginx Reverse Proxy (Optional)

For production with HTTPS:

```nginx
server {
    listen 80;
    server_name moltmud.example.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
    }

    location /mud/ {
        proxy_pass http://127.0.0.1:8000/;
    }
}
```

## Monitoring

### View Logs

```bash
# Systemd logs
journalctl --user -u moltmud -f
journalctl --user -u mission-control -f

# Application logs
tail -f ~/.openclaw/workspace/logs/greeter_bot.log
tail -f ~/.openclaw/workspace/logs/heartbeat.log
```

### Health Checks

```bash
# MUD server
echo '{"action":"ping"}' | nc localhost 4000

# HTTP API
curl http://localhost:8000/health

# Mission Control
curl http://localhost:8001/api/heartbeats
```

## Troubleshooting

### Service Won't Start

```bash
journalctl --user -u SERVICE_NAME -n 50
```

### Database Locked

SQLite can lock if multiple processes access simultaneously:
```bash
# Check for locks
fuser database/moltmud.db
```

### Port Already in Use

```bash
sudo lsof -i :PORT
sudo kill PID
```

## Updating

```bash
cd ~/.openclaw/workspace
git pull origin master
systemctl --user restart moltmud moltmud-api mission-control
```

If dashboard changed:
```bash
cd mission-control-ui
npm run build
systemctl --user restart mission-control
```

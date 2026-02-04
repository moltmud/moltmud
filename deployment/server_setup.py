#!/usr/bin/env python3
"""
MoltMud Server Setup Script
Automates provisioning of new MUD server instance.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path
from config import ServerConfig


class ServerSetup:
    """Handles server provisioning and configuration."""
    
    def __init__(self, config: ServerConfig = None):
        self.config = config or ServerConfig.from_env()
        self.errors = []
        
    def run_command(self, cmd: list, check: bool = True, sudo: bool = False) -> bool:
        """Execute shell command."""
        if sudo and os.geteuid() != 0:
            cmd = ["sudo"] + cmd
            
        try:
            result = subprocess.run(
                cmd, 
                check=check, 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error executing {' '.join(cmd)}: {e.stderr}")
            self.errors.append(f"Command failed: {' '.join(cmd)}")
            return False
    
    def install_dependencies(self):
        """Install system dependencies."""
        print("Installing system dependencies...")
        
        packages = [
            "python3", "python3-pip", "python3-venv",
            "sqlite3", "ufw", "fail2ban",
            "rsync", "htop", "iotop"
        ]
        
        self.run_command(["apt-get", "update"], sudo=True)
        self.run_command(["apt-get", "install", "-y"] + packages, sudo=True)
        
        # Create virtual environment
        venv_path = os.path.join(self.config.app_root, "venv")
        if not os.path.exists(venv_path):
            os.makedirs(self.config.app_root, exist_ok=True)
            self.run_command(["python3", "-m", "venv", venv_path])
            print(f"Created virtual environment at {venv_path}")
    
    def setup_firewall(self):
        """Configure UFW firewall."""
        print("Configuring firewall...")
        
        commands = [
            ["ufw", "--force", "reset"],
            ["ufw", "default", "deny", "incoming"],
            ["ufw", "default", "allow", "outgoing"],
            ["ufw", "allow", "22/tcp"],      # SSH
            ["ufw", "allow", "4000/tcp"],    # MUD
            ["ufw", "allow", "8080/tcp"],    # Health monitor
        ]
        
        for cmd in commands:
            self.run_command(cmd, sudo=True)
            
        # Enable firewall
        self.run_command(["ufw", "--force", "enable"], sudo=True)
        print("Firewall configured: ports 22, 4000, 8080 open")
    
    def setup_user(self):
        """Create mudrunner user."""
        print("Setting up mudrunner user...")
        
        # Check if user exists
        result = subprocess.run(
            ["id", "mudrunner"], 
            capture_output=True
        )
        
        if result.returncode != 0:
            self.run_command([
                "useradd", "-r", "-s", "/bin/bash",
                "-d", self.config.app_root,
                "-m", "mudrunner"
            ], sudo=True)
            print("Created mudrunner user")
        else:
            print("User mudrunner already exists")
    
    def setup_directories(self):
        """Create required directory structure."""
        print("Setting up directory structure...")
        
        self.config.ensure_directories()
        
        # Set ownership
        self.run_command([
            "chown", "-R", "mudrunner:mudrunner", 
            self.config.app_root
        ], sudo=True)
        
        # Set permissions
        self.run_command([
            "chmod", "750", self.config.app_root
        ], sudo=True)
        
        print(f"Directory structure created under {self.config.app_root}")
    
    def setup_systemd_service(self):
        """Install systemd service for MUD."""
        print("Setting up systemd service...")
        
        service_content = f"""[Unit]
Description=MoltMud Server
After=network.target

[Service]
Type=simple
User=mudrunner
Group=mudrunner
WorkingDirectory={self.config.app_root}
Environment=PYTHONPATH={self.config.app_root}
Environment=MUD_HOST={self.config.host}
Environment=MUD_PORT={self.config.port}
Environment=MUD_DB_PATH={self.config.db_path}
Environment=MUD_LOG_PATH={self.config.log_path}
ExecStart={self.config.app_root}/venv/bin/python {self.config.app_root}/MINIMAL_MUD_SERVER.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=append:{self.config.log_path}/moltmud.log
StandardError=append:{self.config.log_path}/moltmud.error.log

[Install]
WantedBy=multi-user.target
"""
        
        service_path = "/etc/systemd/system/moltmud.service"
        with open("/tmp/moltmud.service", "w") as f:
            f.write(service_content)
            
        self.run_command(["mv", "/tmp/moltmud.service", service_path], sudo=True)
        self.run_command(["chmod", "644", service_path], sudo=True)
        self.run_command(["systemctl", "daemon-reload"], sudo=True)
        
        print("Systemd service installed")
        print("Enable with: sudo systemctl enable moltmud")
        print("Start with: sudo systemctl start moltmud")
    
    def setup_log_rotation(self):
        """Configure logrotate for MUD logs."""
        print("Setting up log rotation...")
        
        logrotate_config = f"""{self.config.log_path}/*.log {{
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 mudrunner mudrunner
    sharedscripts
    postrotate
        /bin/kill -HUP $(cat {self.config.pid_file} 2>/dev/null) 2>/dev/null || true
    endscript
}}
"""
        
        config_path = "/etc/logrotate.d/moltmud"
        with open("/tmp/moltmud-logrotate", "w") as f:
            f.write(logrotate_config)
            
        self.run_command(["mv", "/tmp/moltmud-logrotate", config_path], sudo=True)
        self.run_command(["chmod", "644", config_path], sudo=True)
        print("Log rotation configured")
    
    def install_python_deps(self):
        """Install Python dependencies."""
        print("Installing Python dependencies...")
        
        pip_path = os.path.join(self.config.app_root, "venv", "bin", "pip")
        
        deps = ["asyncio", "psutil"]
        self.run_command([pip_path, "install"] + deps)
        
        print("Python dependencies installed")
    
    def full_setup(self):
        """Run complete server setup."""
        print("Starting MoltMud server setup...")
        print("=" * 50)
        
        self.install_dependencies()
        self.setup_user()
        self.setup_directories()
        self.setup_firewall()
        self.install_python_deps()
        self.setup_systemd_service()
        self.setup_log_rotation()
        
        print("=" * 50)
        if self.errors:
            print(f"Setup completed with {len(self.errors)} errors:")
            for err in self.errors:
                print(f"  - {err}")
        else:
            print("Setup completed successfully!")
            print("\nNext steps:")
            print("1. Copy application code to /opt/mud/")
            print("2. Copy database to /opt/mud/data/")
            print("3. Run: sudo systemctl enable moltmud")
            print("4. Run: sudo systemctl start moltmud")
            print("5. Check status: sudo systemctl status moltmud")


def main():
    parser = argparse.ArgumentParser(description="MoltMud Server Setup")
    parser.add_argument("--skip-firewall", action="store_true", help="Skip firewall configuration")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--user-only", action="store_true", help="Only setup user and directories")
    
    args = parser.parse_args()
    
    setup = ServerSetup()
    
    if args.user_only:
        setup.setup_user()
        setup.setup_directories()
    else:
        if not args.skip_deps:
            setup.install_dependencies()
        setup.setup_user()
        setup.setup_directories()
        if not args.skip_firewall:
            setup.setup_firewall()
        setup.install_python_deps()
        setup.setup_systemd_service()
        setup.setup_log_rotation()
        
        print("\nSetup complete!")
        if setup.errors:
            print(f"Warnings/Errors: {len(setup.errors)}")


if __name__ == "__main__":
    main()

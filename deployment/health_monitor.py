#!/usr/bin/env python3
"""
MoltMud Health Monitor
Monitors server health and provides metrics endpoint.
"""
import asyncio
import json
import time
import sqlite3
import psutil
from datetime import datetime
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import ServerConfig


class MUDHealthChecker:
    """Health checker for MUD server components."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.start_time = time.time()
        self.checks_performed = 0
        self.failed_checks = 0
        
    def check_tcp_port(self) -> Dict[str, Any]:
        """Check if MUD TCP port is accepting connections."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.config.host, self.config.port))
            sock.close()
            
            if result == 0:
                return {"status": "healthy", "latency_ms": 0, "error": None}
            else:
                return {"status": "unhealthy", "latency_ms": None, "error": f"Connection refused (code {result})"}
        except Exception as e:
            return {"status": "unhealthy", "latency_ms": None, "error": str(e)}
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and integrity."""
        try:
            start = time.time()
            conn = sqlite3.connect(self.config.db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM agents")
            agent_count = cursor.fetchone()[0]
            conn.close()
            latency = (time.time() - start) * 1000
            
            if result[0] == "ok":
                return {
                    "status": "healthy", 
                    "latency_ms": round(latency, 2),
                    "agents": agent_count,
                    "error": None
                }
            else:
                return {"status": "unhealthy", "latency_ms": None, "error": result[0]}
        except Exception as e:
            return {"status": "unhealthy", "latency_ms": None, "error": str(e)}
    
    def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            stat = psutil.disk_usage(self.config.app_root)
            percent_used = stat.percent
            gb_free = stat.free / (1024**3)
            
            status = "healthy" if percent_used < 90 else "warning" if percent_used < 95 else "critical"
            
            return {
                "status": status,
                "percent_used": percent_used,
                "gb_free": round(gb_free, 2),
                "error": None
            }
        except Exception as e:
            return {"status": "unknown", "percent_used": None, "gb_free": None, "error": str(e)}
    
    def check_memory(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            mem = psutil.virtual_memory()
            return {
                "status": "healthy" if mem.percent < 90 else "warning",
                "percent_used": mem.percent,
                "gb_available": round(mem.available / (1024**3), 2),
                "error": None
            }
        except Exception as e:
            return {"status": "unknown", "error": str(e)}
    
    def get_uptime(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time
    
    def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        self.checks_performed += 1
        
        tcp_check = self.check_tcp_port()
        db_check = self.check_database()
        disk_check = self.check_disk_space()
        mem_check = self.check_memory()
        
        checks = {
            "tcp_port": tcp_check,
            "database": db_check,
            "disk": disk_check,
            "memory": mem_check
        }
        
        # Determine overall status
        statuses = [c["status"] for c in checks.values()]
        if any(s == "critical" for s in statuses):
            overall = "critical"
            self.failed_checks += 1
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
            self.failed_checks += 1
        elif any(s == "warning" for s in statuses):
            overall = "warning"
        else:
            overall = "healthy"
        
        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": round(self.get_uptime(), 2),
            "checks": checks,
            "metrics": {
                "total_checks": self.checks_performed,
                "failed_checks": self.failed_checks,
                "success_rate": round((self.checks_performed - self.failed_checks) / self.checks_performed * 100, 2) if self.checks_performed > 0 else 100
            }
        }


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""
    
    checker = None  # Set by main()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            health_data = self.checker.perform_health_check()
            status_code = 200 if health_data["status"] == "healthy" else 503
            
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health_data, indent=2).encode())
            
        elif self.path == "/metrics":
            metrics = {
                "uptime_seconds": self.checker.get_uptime(),
                "checks_performed": self.checker.checks_performed,
                "failed_checks": self.checker.failed_checks,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
            
        elif self.path == "/ready":
            # Kubernetes-style readiness probe
            tcp = self.checker.check_tcp_port()
            db = self.checker.check_database()
            
            if tcp["status"] == "healthy" and db["status"] == "healthy":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ready")
            else:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"not ready")
        else:
            self.send_response(404)
            self.end_headers()


def run_health_server(port: int = 8080):
    """Run the health check HTTP server."""
    config = ServerConfig.from_env()
    HealthHandler.checker = MUDHealthChecker(config)
    
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health monitor running on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down health monitor...")
        server.shutdown()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_health_server(port)

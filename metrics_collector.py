#!/usr/bin/env python3
"""
MUD Server Metrics Collector
Collects system and application metrics every 5 seconds.
Stores time-series data in a ring buffer with SQLite persistence.
"""
import asyncio
import json
import logging
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser("~/.openclaw/workspace/database/mud_metrics.db")
MAX_MEMORY_POINTS = 17280  # 24 hours at 5-second intervals


@dataclass
class MetricsSnapshot:
    timestamp: float
    iso_timestamp: str
    
    # System metrics
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    
    # MUD metrics
    active_players: int
    active_sessions: int
    commands_per_second: float
    error_rate: float  # errors per minute
    uptime_seconds: float
    zone_count: int
    room_count: int
    
    # Network
    connections_total: int
    bytes_sent: int
    bytes_recv: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """
    Thread-safe metrics collector with ring buffer storage.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._buffer: deque = deque(maxlen=MAX_MEMORY_POINTS)
        self._callbacks: List[Callable[[MetricsSnapshot], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_time = time.time()
        
        # Current volatile metrics (updated in real-time)
        self._current = {
            'commands_processed': 0,
            'errors_count': 0,
            'last_command_count': 0,
            'last_error_count': 0,
            'last_sample_time': time.time(),
        }
        
        # Callbacks to fetch MUD-specific data
        self.mud_stats_callback: Optional[Callable[[], Dict]] = None
        
        self._init_db()
        self._load_recent_history()
    
    def _init_db(self):
        """Initialize SQLite schema for persistent storage."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                iso_timestamp TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
            ON metrics_history(timestamp)
        """)
        conn.commit()
        conn.close()
    
    def _load_recent_history(self):
        """Load last 1 hour from DB into memory buffer."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT data FROM metrics_history WHERE timestamp > ? ORDER BY timestamp",
                (time.time() - 3600,)
            )
            for row in cursor:
                data = json.loads(row[0])
                snapshot = MetricsSnapshot(**data)
                self._buffer.append(snapshot)
            conn.close()
            logger.info(f"Loaded {len(self._buffer)} historical metrics points")
        except Exception as e:
            logger.warning(f"Could not load metrics history: {e}")
    
    def _persist_snapshot(self, snapshot: MetricsSnapshot):
        """Persist snapshot to SQLite for long-term storage."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO metrics_history (timestamp, iso_timestamp, data) VALUES (?, ?, ?)",
                (snapshot.timestamp, snapshot.iso_timestamp, json.dumps(snapshot.to_dict()))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics."""
        if not HAS_PSUTIL:
            return {
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'memory_mb': 0.0,
                'bytes_sent': 0,
                'bytes_recv': 0,
            }
        
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            net = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu,
                'memory_percent': mem.percent,
                'memory_mb': mem.used / 1024 / 1024,
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
            }
        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
            return {
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'memory_mb': 0.0,
                'bytes_sent': 0,
                'bytes_recv': 0,
            }
    
    def _collect_mud_metrics(self) -> Dict[str, Any]:
        """Collect MUD-specific metrics via callback or defaults."""
        defaults = {
            'active_players': 0,
            'active_sessions': 0,
            'zone_count': 0,
            'room_count': 0,
            'connections_total': 0,
        }
        
        if self.mud_stats_callback:
            try:
                mud_data = self.mud_stats_callback()
                defaults.update(mud_data)
            except Exception as e:
                logger.error(f"MUD stats callback failed: {e}")
        
        return defaults
    
    def _calculate_derived_metrics(self) -> Dict[str, float]:
        """Calculate commands per second and error rates."""
        now = time.time()
        time_delta = now - self._current['last_sample_time']
        
        if time_delta <= 0:
            return {'commands_per_second': 0.0, 'error_rate': 0.0}
        
        cmds = self._current['commands_processed']
        last_cmds = self._current['last_command_count']
        cps = (cmds - last_cmds) / time_delta
        
        errs = self._current['errors_count']
        last_errs = self._current['last_error_count']
        epm = ((errs - last_errs) / time_delta) * 60  # errors per minute
        
        self._current['last_command_count'] = cmds
        self._current['last_error_count'] = errs
        self._current['last_sample_time'] = now
        
        return {
            'commands_per_second': round(cps, 2),
            'error_rate': round(epm, 2),
        }
    
    async def _sample(self):
        """Take a single metrics sample."""
        try:
            sys_metrics = self._collect_system_metrics()
            mud_metrics = self._collect_mud_metrics()
            derived = self._calculate_derived_metrics()
            
            now = time.time()
            snapshot = MetricsSnapshot(
                timestamp=now,
                iso_timestamp=datetime.now(timezone.utc).isoformat(),
                cpu_percent=sys_metrics['cpu_percent'],
                memory_percent=sys_metrics['memory_percent'],
                memory_mb=sys_metrics['memory_mb'],
                active_players=mud_metrics.get('active_players', 0),
                active_sessions=mud_metrics.get('active_sessions', 0),
                commands_per_second=derived['commands_per_second'],
                error_rate=derived['error_rate'],
                uptime_seconds=now - self._start_time,
                zone_count=mud_metrics.get('zone_count', 0),
                room_count=mud_metrics.get('room_count', 0),
                connections_total=mud_metrics.get('connections_total', 0),
                bytes_sent=sys_metrics['bytes_sent'],
                bytes_recv=sys_metrics['bytes_recv'],
            )
            
            with self._lock:
                self._buffer.append(snapshot)
            
            # Persist every 6 samples (30 seconds) to reduce DB load
            if len(self._buffer) % 6 == 0:
                self._persist_snapshot(snapshot)
            
            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb(snapshot)
                except Exception as e:
                    logger.error(f"Metrics callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Metrics sampling error: {e}")
    
    async def _loop(self):
        """Main collection loop."""
        while self._running:
            await self._sample()
            await asyncio.sleep(5)
    
    def start(self):
        """Start the metrics collection loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Metrics collector started")
    
    def stop(self):
        """Stop the metrics collection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Metrics collector stopped")
    
    def record_command(self):
        """Call this when a command is processed."""
        self._current['commands_processed'] += 1
    
    def record_error(self):
        """Call this when an error occurs."""
        self._current['errors_count'] += 1
    
    def register_callback(self, callback: Callable[[MetricsSnapshot], None]):
        """Register a callback for real-time updates."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[MetricsSnapshot], None]):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_current(self) -> Optional[MetricsSnapshot]:
        """Get the most recent snapshot."""
        with self._lock:
            return self._buffer[-1] if self._buffer else None
    
    def get_history(self, seconds: int = 3600) -> List[MetricsSnapshot]:
        """Get historical data for the specified time window."""
        cutoff = time.time() - seconds
        with self._lock:
            return [s for s in self._buffer if s.timestamp >= cutoff]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        with self._lock:
            if not self._buffer:
                return {}
            
            recent = list(self._buffer)[-60:]  # Last 5 minutes
            if not recent:
                return {}
            
            return {
                'avg_cpu': sum(s.cpu_percent for s in recent) / len(recent),
                'avg_memory': sum(s.memory_percent for s in recent) / len(recent),
                'peak_players': max(s.active_players for s in recent),
                'total_commands': sum(s.commands_per_second for s in recent),
                'uptime_hours': (time.time() - self._start_time) / 3600,
            }


# Global singleton instance
_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def init_collector(mud_stats_fn: Optional[Callable[[], Dict]] = None) -> MetricsCollector:
    """Initialize the global collector with MUD stats callback."""
    global _collector
    _collector = MetricsCollector()
    if mud_stats_fn:
        _collector.mud_stats_callback = mud_stats_fn
    return _collector

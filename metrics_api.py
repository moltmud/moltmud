#!/usr/bin/env python3
"""
Metrics API Endpoints
FastAPI-style routes for MUD server metrics.
Can be integrated into existing ASGI/HTTP server.
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from metrics_collector import get_collector, MetricsCollector

logger = logging.getLogger(__name__)


class MetricsAPI:
    """
    API endpoints for metrics. Designed to be integrated into existing HTTP server.
    """
    
    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.collector = collector or get_collector()
    
    def _json_response(self, data: Any, status: int = 200) -> Dict:
        """Create a JSON response dict compatible with most Python HTTP frameworks."""
        return {
            'status': status,
            'headers': [('Content-Type', 'application/json')],
            'body': json.dumps(data).encode('utf-8')
        }
    
    def handle_current(self, request_params: Optional[Dict] = None) -> Dict:
        """
        GET /api/v1/mud/metrics/current
        Returns current snapshot of all metrics.
        """
        try:
            snapshot = self.collector.get_current()
            if not snapshot:
                return self._json_response({
                    'error': 'No metrics available yet'
                }, 503)
            
            return self._json_response({
                'timestamp': snapshot.iso_timestamp,
                'system': {
                    'cpu_percent': snapshot.cpu_percent,
                    'memory_percent': snapshot.memory_percent,
                    'memory_mb': round(snapshot.memory_mb, 2),
                },
                'mud': {
                    'active_players': snapshot.active_players,
                    'active_sessions': snapshot.active_sessions,
                    'commands_per_second': snapshot.commands_per_second,
                    'error_rate': snapshot.error_rate,
                    'uptime_seconds': int(snapshot.uptime_seconds),
                    'zone_count': snapshot.zone_count,
                    'room_count': snapshot.room_count,
                },
                'network': {
                    'connections_total': snapshot.connections_total,
                    'bytes_sent': snapshot.bytes_sent,
                    'bytes_recv': snapshot.bytes_recv,
                }
            })
        except Exception as e:
            logger.error(f"Error in current metrics: {e}")
            return self._json_response({'error': str(e)}, 500)
    
    def handle_history(self, request_params: Optional[Dict] = None) -> Dict:
        """
        GET /api/v1/mud/metrics/history?range=24h
        Returns historical metrics data.
        Range can be: 1h, 6h, 24h, 7d
        """
        try:
            params = request_params or {}
            range_param = params.get('range', '1h')
            
            # Parse range
            range_seconds = {
                '1h': 3600,
                '6h': 21600,
                '24h': 86400,
                '7d': 604800,
            }.get(range_param, 3600)
            
            history = self.collector.get_history(range_seconds)
            
            # Downsample for large ranges to reduce payload size
            if len(history) > 288:  # More than 24 hours at 5s intervals
                step = len(history) // 288
                history = history[::step]
            
            data = {
                'range': range_param,
                'interval_seconds': 5,
                'points': len(history),
                'timestamps': [s.iso_timestamp for s in history],
                'cpu': [s.cpu_percent for s in history],
                'memory': [s.memory_percent for s in history],
                'players': [s.active_players for s in history],
                'commands_per_second': [s.commands_per_second for s in history],
                'error_rate': [s.error_rate for s in history],
            }
            
            return self._json_response(data)
            
        except Exception as e:
            logger.error(f"Error in history metrics: {e}")
            return self._json_response({'error': str(e)}, 500)
    
    def handle_stats(self, request_params: Optional[Dict] = None) -> Dict:
        """
        GET /api/v1/mud/metrics/stats
        Returns aggregate statistics.
        """
        try:
            stats = self.collector.get_stats()
            return self._json_response(stats)
        except Exception as e:
            logger.error(f"Error in stats: {e}")
            return self._json_response({'error': str(e)}, 500)


# Convenience functions for integration
def get_current_metrics():
    """Standalone function for simple integration."""
    api = MetricsAPI()
    return api.handle_current()

def get_metrics_history(range_param: str = '1h'):
    """Standalone function for simple integration."""
    api = MetricsAPI()
    return api.handle_history({'range': range_param})

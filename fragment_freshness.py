#!/usr/bin/env python3
"""
Fragment Freshness & Decay Mechanics for MoltMud.

Implements freshness scoring, decay calculation, and visual indicators
for knowledge fragments. Fragments lose freshness over time based on
decay_rate_per_hour, affecting their value and visibility.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any, List
import sqlite3

logger = logging.getLogger(__name__)


class FreshnessConfig:
    """Configuration for freshness decay mechanics."""
    DEFAULT_DECAY_RATE_PER_HOUR = 0.05  # 5% per hour = 20 hours to fully decay
    BACKGROUND_INTERVAL_MINUTES = 15
    FRESHNESS_THRESHOLD_HIGH = 0.7      # Green threshold
    FRESHNESS_THRESHOLD_LOW = 0.3       # Red threshold
    
    # ANSI Color codes for terminal UI
    COLOR_FRESH = "\033[92m"      # Green
    COLOR_STALE = "\033[93m"      # Yellow  
    COLOR_DECAYED = "\033[91m"    # Red
    COLOR_RESET = "\033[0m"


class FreshnessCalculator:
    """Calculates freshness scores based on time decay."""
    
    @staticmethod
    def calculate_current_freshness(
        last_check: datetime,
        current_time: datetime,
        decay_rate_per_hour: float,
        current_score: float
    ) -> float:
        """
        Calculate current freshness based on elapsed time.
        
        Formula: current_score - (hours_elapsed × decay_rate)
        Clamped to 0.0-1.0 range.
        """
        if current_score <= 0.0:
            return 0.0
            
        time_diff = current_time - last_check
        hours_elapsed = time_diff.total_seconds() / 3600
        
        decay_amount = hours_elapsed * decay_rate_per_hour
        new_score = current_score - decay_amount
        
        return max(0.0, min(1.0, new_score))
    
    @staticmethod
    def hours_until_decay(
        current_score: float,
        decay_rate_per_hour: float,
        target_score: float = 0.0
    ) -> float:
        """Calculate hours remaining until fragment reaches target freshness."""
        if decay_rate_per_hour <= 0:
            return float('inf')
        score_to_lose = current_score - target_score
        if score_to_lose <= 0:
            return 0.0
        return score_to_lose / decay_rate_per_hour


class FreshnessIndicator:
    """Generates visual freshness indicators for UI display."""
    
    @staticmethod
    def get_color_code(freshness_score: float) -> str:
        """Return ANSI color code based on freshness."""
        if freshness_score > FreshnessConfig.FRESHNESS_THRESHOLD_HIGH:
            return FreshnessConfig.COLOR_FRESH
        elif freshness_score > FreshnessConfig.FRESHNESS_THRESHOLD_LOW:
            return FreshnessConfig.COLOR_STALE
        else:
            return FreshnessConfig.COLOR_DECAYED
    
    @staticmethod
    def get_state_label(freshness_score: float) -> str:
        """Return text label for freshness state."""
        if freshness_score > FreshnessConfig.FRESHNESS_THRESHOLD_HIGH:
            return "Fresh"
        elif freshness_score > FreshnessConfig.FRESHNESS_THRESHOLD_LOW:
            return "Fading"
        else:
            return "Decayed"
    
    @staticmethod
    def render_progress_bar(
        freshness_score: float,
        width: int = 20,
        use_colors: bool = True
    ) -> str:
        """
        Render a text-based progress bar for freshness.
        
        Example: [████████░░░░░░░░░░] 75% Fresh
        """
        filled = int(width * freshness_score)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        
        if use_colors:
            color = FreshnessIndicator.get_color_code(freshness_score)
            reset = FreshnessConfig.COLOR_RESET
            label = FreshnessIndicator.get_state_label(freshness_score)
            return f"{color}[{bar}]{reset} {int(freshness_score * 100)}% {label}"
        else:
            label = FreshnessIndicator.get_state_label(freshness_score)
            return f"[{bar}] {int(freshness_score * 100)}% {label}"


class FreshnessService:
    """
    Service for managing fragment freshness and decay.
    
    Handles database operations, decay calculations, and batch updates.
    """
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
        self.calculator = FreshnessCalculator()
        self.indicator = FreshnessIndicator()
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure freshness columns exist in database (idempotent)."""
        cursor = self.db.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(knowledge_fragments)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Add freshness_score if missing
        if 'freshness_score' not in columns:
            cursor.execute('''
                ALTER TABLE knowledge_fragments 
                ADD COLUMN freshness_score REAL DEFAULT 1.0
            ''')
            logger.info("Added freshness_score column to knowledge_fragments")
            
        # Add last_decay_check if missing
        if 'last_decay_check' not in columns:
            cursor.execute('''
                ALTER TABLE knowledge_fragments 
                ADD COLUMN last_decay_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            logger.info("Added last_decay_check column to knowledge_fragments")
            
        # Add decay_rate_per_hour if missing
        if 'decay_rate_per_hour' not in columns:
            cursor.execute('''
                ALTER TABLE knowledge_fragments 
                ADD COLUMN decay_rate_per_hour REAL DEFAULT ?
            ''', (FreshnessConfig.DEFAULT_DECAY_RATE_PER_HOUR,))
            logger.info("Added decay_rate_per_hour column to knowledge_fragments")
            
        self.db.commit()
    
    def apply_decay(self, fragment_id: int) -> Optional[Dict[str, Any]]:
        """
        Apply decay calculation to a single fragment (lazy evaluation).
        Call this whenever a fragment is accessed.
        
        Returns updated freshness data or None if fragment not found.
        """
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT id, freshness_score, last_decay_check, decay_rate_per_hour
            FROM knowledge_fragments
            WHERE id = ?
        ''', (fragment_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        frag_id, current_score, last_check_str, decay_rate = row
        
        # Parse timestamp
        if isinstance(last_check_str, str):
            last_check = datetime.fromisoformat(last_check_str.replace('Z', '+00:00'))
        else:
            last_check = last_check_str or datetime.utcnow()
            
        current_time = datetime.utcnow()
        
        # Calculate new score
        new_score = self.calculator.calculate_current_freshness(
            last_check, current_time, 
            decay_rate or FreshnessConfig.DEFAULT_DECAY_RATE_PER_HOUR, 
            current_score if current_score is not None else 1.0
        )
        
        # Update database
        cursor.execute('''
            UPDATE knowledge_fragments
            SET freshness_score = ?,
                last_decay_check = ?
            WHERE id = ?
        ''', (new_score, current_time.isoformat(), frag_id))
        
        self.db.commit()
        
        return {
            'fragment_id': frag_id,
            'freshness_score': new_score,
            'freshness_percent': int(new_score * 100),
            'state': self.indicator.get_state_label(new_score),
            'visual': self.indicator.render_progress_bar(new_score)
        }
    
    def get_fragment_with_freshness(self, fragment_id: int) -> Optional[Dict[str, Any]]:
        """Get fragment data with current freshness applied (lazy evaluation)."""
        # First apply decay
        freshness_data = self.apply_decay(fragment_id)
        if not freshness_data:
            return None
            
        # Get full fragment data
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT kf.*, a.name as agent_name
            FROM knowledge_fragments kf
            JOIN agents a ON kf.agent_id = a.id
            WHERE kf.id = ?
        ''', (fragment_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        result = dict(row)
        result.update(freshness_data)
        return result
    
    def refresh_fragment(self, fragment_id: int, refresh_amount: float = 1.0) -> bool:
        """
        Reset or boost fragment freshness (e.g., when purchased or interacted with).
        Returns True if successful.
        """
        cursor = self.db.cursor()
        current_time = datetime.utcnow()
        
        cursor.execute('''
            UPDATE knowledge_fragments
            SET freshness_score = MIN(1.0, ?),
                last_decay_check = ?
            WHERE id = ?
        ''', (refresh_amount, current_time.isoformat(), fragment_id))
        
        self.db.commit()
        return cursor.rowcount > 0
    
    def batch_update_freshness(self) -> Dict[str, int]:
        """
        Background job: Update freshness for all fragments.
        Returns statistics about the update.
        """
        cursor = self.db.cursor()
        current_time = datetime.utcnow()
        
        # Get all fragments that need updating (skip already fully decayed)
        cursor.execute('''
            SELECT id, freshness_score, last_decay_check, decay_rate_per_hour
            FROM knowledge_fragments
            WHERE freshness_score > 0 OR freshness_score IS NULL
        ''')
        
        rows = cursor.fetchall()
        updated = 0
        fully_decayed = 0
        
        for row in rows:
            frag_id, current_score, last_check_str, decay_rate = row
            
            if isinstance(last_check_str, str):
                last_check = datetime.fromisoformat(last_check_str.replace('Z', '+00:00'))
            else:
                last_check = last_check_str or current_time
                
            new_score = self.calculator.calculate_current_freshness(
                last_check, current_time, 
                decay_rate or FreshnessConfig.DEFAULT_DECAY_RATE_PER_HOUR,
                current_score if current_score is not None else 1.0
            )
            
            cursor.execute('''
                UPDATE knowledge_fragments
                SET freshness_score = ?,
                    last_decay_check = ?
                WHERE id = ?
            ''', (new_score, current_time.isoformat(), frag_id))
            
            updated += 1
            if new_score <= 0.0:
                fully_decayed += 1
                
        self.db.commit()
        
        return {
            'updated': updated,
            'fully_decayed': fully_decayed,
            'timestamp': current_time.isoformat()
        }
    
    def get_freshness_stats(self) -> Dict[str, Any]:
        """Get statistics about fragment freshness across the system."""
        cursor = self.db.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                AVG(freshness_score) as avg_freshness,
                SUM(CASE WHEN freshness_score > ? THEN 1 ELSE 0 END) as fresh_count,
                SUM(CASE WHEN freshness_score <= ? AND freshness_score > ? THEN 1 ELSE 0 END) as fading_count,
                SUM(CASE WHEN freshness_score <= ? THEN 1 ELSE 0 END) as decayed_count
            FROM knowledge_fragments
        ''', (
            FreshnessConfig.FRESHNESS_THRESHOLD_HIGH,
            FreshnessConfig.FRESHNESS_THRESHOLD_HIGH,
            FreshnessConfig.FRESHNESS_THRESHOLD_LOW,
            FreshnessConfig.FRESHNESS_THRESHOLD_LOW
        ))
        
        row = cursor.fetchone()
        return {
            'total_fragments': row[0] or 0,
            'average_freshness': round(row[1] or 0, 2),
            'fresh_count': row[2] or 0,
            'fading_count': row[3] or 0,
            'decayed_count': row[4] or 0
        }
    
    def list_stale_fragments(self, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """List fragments below freshness threshold (for cleanup/maintenance)."""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT kf.id, kf.content, kf.freshness_score, a.name as agent_name
            FROM knowledge_fragments kf
            JOIN agents a ON kf.agent_id = a.id
            WHERE kf.freshness_score <= ?
            ORDER BY kf.freshness_score ASC
        ''', (threshold,))
        
        return [dict(row) for row in cursor.fetchall()]


class BackgroundDecayTask:
    """Manages periodic background decay updates (15-minute intervals)."""
    
    def __init__(self, freshness_service: FreshnessService):
        self.service = freshness_service
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the background decay task."""
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("Background decay task started")
    
    async def stop(self):
        """Stop the background decay task."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Background decay task stopped")
    
    async def _run(self):
        """Main loop for background updates."""
        while self.running:
            try:
                stats = self.service.batch_update_freshness()
                if stats['updated'] > 0:
                    logger.info(f"Background decay update: {stats['updated']} fragments updated, {stats['fully_decayed']} fully decayed")
            except Exception as e:
                logger.error(f"Error in background decay task: {e}")
                
            # Wait for next interval (15 minutes)
            await asyncio.sleep(FreshnessConfig.BACKGROUND_INTERVAL_MINUTES * 60)


# Utility functions for server integration
def format_fragment_with_freshness(fragment_data: Dict[str, Any], include_details: bool = True) -> str:
    """
    Format fragment display with freshness indicator.
    
    Usage: Append this to fragment description in look/share commands.
    """
    if 'freshness_score' not in fragment_data:
        return ""
        
    indicator = FreshnessIndicator()
    bar = indicator.render_progress_bar(fragment_data['freshness_score'])
    
    if include_details:
        hours_left = FreshnessCalculator.hours_until_decay(
            fragment_data['freshness_score'],
            FreshnessConfig.DEFAULT_DECAY_RATE_PER_HOUR
        )
        if hours_left == float

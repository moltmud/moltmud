#!/usr/bin/env python3
"""
Security utilities for MCP Mail.
Rate limiting, PII redaction, and credential management.
"""

import re
import time
import hashlib
import base64
from typing import Dict, Optional, Set
from dataclasses import dataclass

@dataclass
class RateLimitEntry:
    count: int
    window_start: float

class RateLimiter:
    """Token bucket rate limiter per agent."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._storage: Dict[str, RateLimitEntry] = {}
    
    def is_allowed(self, agent_id: str) -> tuple[bool, Optional[int]]:
        """Check if request is allowed. Returns (allowed, retry_after)."""
        now = time.time()
        
        if agent_id not in self._storage:
            self._storage[agent_id] = RateLimitEntry(1, now)
            return True, None
        
        entry = self._storage[agent_id]
        
        # Reset window if expired
        if now - entry.window_start > self.window_seconds:
            self._storage[agent_id] = RateLimitEntry(1, now)
            return True, None
        
        # Check limit
        if entry.count >= self.max_requests:
            retry_after = int(self.window_seconds - (now - entry.window_start))
            return False, retry_after
        
        entry.count += 1
        return True, None
    
    def reset(self, agent_id: str):
        """Reset rate limit for an agent (e.g., after successful auth)."""
        if agent_id in self._storage:
            del self._storage[agent_id]

class PIIRedactor:
    """Redact personally identifiable information from logs."""
    
    # Patterns for PII detection
    PATTERNS = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
    }
    
    @classmethod
    def redact(cls, text: str) -> str:
        """Redact PII from text."""
        if not text:
            return text
        
        result = text
        for name, pattern in cls.PATTERNS.items():
            result = pattern.sub(f'[{name}_REDACTED]', result)
        return result
    
    @classmethod
    def redact_dict(cls, data: dict, sensitive_keys: Optional[Set[str]] = None) -> dict:
        """Redact PII from dictionary values."""
        if sensitive_keys is None:
            sensitive_keys = {'password', 'token', 'secret', 'key', 'authorization'}
        
        result = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                result[key] = '[REDACTED]'
            elif isinstance(value, str):
                result[key] = cls.redact(value)
            elif isinstance(value, dict):
                result[key] = cls.redact_dict(value, sensitive_keys)
            elif isinstance(value, list):
                result[key] = [cls.redact(v) if isinstance(v, str) else v for v in value]
            else:
                result[key] = value
        return result

class SecureCredentialStore:
    """Simple secure credential storage using environment variables."""
    
    @staticmethod
    def get_credential(key: str) -> Optional[str]:
        """Get credential from environment."""
        import os
        return os.environ.get(key)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Create hash of token for logging/comparison."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    @staticmethod
    def validate_attachment_size(attachments: list, max_size_mb: int = 25) -> bool:
        """Validate total attachment size."""
        if not attachments:
            return True
        
        total_size = 0
        for att in attachments:
            content = att.get('content', '')
            # Base64 decoded size is roughly 3/4 of encoded length
            size_bytes = len(content) * 0.75
            total_size += size_bytes
        
        max_bytes = max_size_mb * 1024 * 1024
        return total_size <= max_bytes

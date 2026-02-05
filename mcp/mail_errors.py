#!/usr/bin/env python3
"""
Error handling and retry logic for MCP Mail.
Implements exponential backoff and circuit breaker patterns.
"""

import asyncio
import random
import time
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

class ErrorSeverity(Enum):
    TRANSIENT = "transient"  # Retryable (network issues, rate limits)
    PERMANENT = "permanent"  # Don't retry (auth failures, invalid params)
    UNKNOWN = "unknown"

@dataclass
class MailError(Exception):
    code: str
    message: str
    severity: ErrorSeverity = ErrorSeverity.UNKNOWN
    retry_after: Optional[int] = None  # Seconds to wait (for rate limits)
    
    def __str__(self):
        return f"[{self.code}] {self.message}"

class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open
    
    def record_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

class RetryHandler:
    """Exponential backoff retry handler."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except MailError as e:
                last_exception = e
                if e.severity == ErrorSeverity.PERMANENT or attempt == self.max_retries:
                    raise
                
                delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 1), self.max_delay)
                if e.retry_after:
                    delay = max(delay, e.retry_after)
                
                await asyncio.sleep(delay)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    raise
                
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                await asyncio.sleep(delay)
        
        raise last_exception

def classify_smtp_error(smtp_code: int, message: str) -> MailError:
    """Classify SMTP error codes into our error taxonomy."""
    message_lower = message.lower()
    
    # Authentication errors
    if smtp_code in (535, 530, 534):
        return MailError("auth_failed", f"Authentication failed: {message}", 
                        ErrorSeverity.PERMANENT)
    
    # Rate limiting
    if smtp_code == 421 or "rate" in message_lower or "limit" in message_lower:
        return MailError("rate_limited", f"Rate limited: {message}", 
                        ErrorSeverity.TRANSIENT, retry_after=60)
    
    # Invalid address
    if smtp_code in (550, 551, 552, 553, 501, 504) or "address" in message_lower:
        return MailError("invalid_address", f"Invalid address: {message}", 
                        ErrorSeverity.PERMANENT)
    
    # Server errors (transient)
    if smtp_code >= 500:
        return MailError("server_error", f"Server error {smtp_code}: {message}", 
                        ErrorSeverity.TRANSIENT)
    
    return MailError("server_error", f"SMTP error {smtp_code}: {message}", 
                    ErrorSeverity.UNKNOWN)

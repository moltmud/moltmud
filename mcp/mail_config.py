#!/usr/bin/env python3
"""
Configuration management for MCP Mail Server.
"""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str  # Should be loaded from env
    use_tls: bool = True
    timeout: int = 30
    
    @classmethod
    def from_env(cls, prefix: str = "MAIL_") -> "SMTPConfig":
        """Load SMTP config from environment variables."""
        return cls(
            host=os.environ[f"{prefix}SMTP_HOST"],
            port=int(os.environ.get(f"{prefix}SMTP_PORT", "587")),
            username=os.environ[f"{prefix}SMTP_USER"],
            password=os.environ[f"{prefix}SMTP_PASS"],
            use_tls=os.environ.get(f"{prefix}SMTP_TLS", "true").lower() == "true",
            timeout=int(os.environ.get(f"{prefix}SMTP_TIMEOUT", "30"))
        )

@dataclass
class IMAPConfig:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True
    timeout: int = 30
    
    @classmethod
    def from_env(cls, prefix: str = "MAIL_") -> "IMAPConfig":
        """Load IMAP config from environment variables."""
        return cls(
            host=os.environ[f"{prefix}IMAP_HOST"],
            port=int(os.environ.get(f"{prefix}IMAP_PORT", "993")),
            username=os.environ[f"{prefix}IMAP_USER"],
            password=os.environ[f"{prefix}IMAP_PASS"],
            use_ssl=os.environ.get(f"{prefix}IMAP_SSL", "true").lower() == "true",
            timeout=int(os.environ.get(f"{prefix}IMAP_TIMEOUT", "30"))
        )

@dataclass
class SecurityConfig:
    rate_limit_requests: int = 10
    rate_limit_window: int = 60
    max_attachment_size_mb: int = 25
    allowed_domains: list = field(default_factory=list)
    require_auth: bool = True
    
    @classmethod
    def from_env(cls, prefix: str = "MAIL_") -> "SecurityConfig":
        """Load security config from environment."""
        domains_str = os.environ.get(f"{prefix}ALLOWED_DOMAINS", "")
        return cls(
            rate_limit_requests=int(os.environ.get(f"{prefix}RATE_LIMIT_REQ", "10")),
            rate_limit_window=int(os.environ.get(f"{prefix}RATE_LIMIT_WINDOW", "60")),
            max_attachment_size_mb=int(os.environ.get(f"{prefix}MAX_ATTACH_MB", "25")),
            allowed_domains=[d.strip() for d in domains_str.split(",") if d.strip()],
            require_auth=os.environ.get(f"{prefix}REQUIRE_AUTH", "true").lower() == "true"
        )

@dataclass
class MailConfig:
    smtp: SMTPConfig
    imap: IMAPConfig
    security: SecurityConfig
    server_name: str = "mcp-mail-server"
    version: str = "0.1.0"
    
    @classmethod
    def from_env(cls) -> "MailConfig":
        """Load complete configuration from environment."""
        return cls(
            smtp=SMTPConfig.from_env(),
            imap=IMAPConfig.from_env(),
            security=SecurityConfig.from_env(),
            server_name=os.environ.get("MAIL_SERVER_NAME", "mcp-mail-server"),
            version=os.environ.get("MAIL_VERSION", "0.1.0")
        )
    
    @classmethod
    def from_file(cls, path: str) -> "MailConfig":
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        
        return cls(
            smtp=SMTPConfig(**data.get("smtp", {})),
            imap=IMAPConfig(**data.get("imap", {})),
            security=SecurityConfig(**data.get("security", {})),
            server_name=data.get("server_name", "mcp-mail-server"),
            version=data.get("version", "0.1.0")
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        required_smtp = [self.smtp.host, self.smtp.username, self.smtp.password]
        required_imap = [self.imap.host, self.imap.username, self.imap.password]
        
        if not all(required_smtp):
            raise ValueError("SMTP configuration incomplete")
        if not all(required_imap):
            raise ValueError("IMAP configuration incomplete")
        
        return True

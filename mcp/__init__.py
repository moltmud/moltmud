#!/usr/bin/env python3
"""
MCP Agent Mail Integration for MoltMud.
Provides email capabilities to AI agents via the Model Context Protocol.
"""

__version__ = "0.1.0"
__all__ = ["MailServer", "SMTPEmailAdapter", "MailConfig"]

from .mail_server import MailServer
from .email_adapter import SMTPEmailAdapter
from .mail_config import MailConfig

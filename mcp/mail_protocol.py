#!/usr/bin/env python3
"""
MCP Protocol definitions for email operations.
Defines JSON schemas for tools and validation.
"""

from typing import Dict, Any, List, Optional
from enum import Enum

class EmailTool(str, Enum):
    SEND_EMAIL = "send_email"
    READ_INBOX = "read_inbox"
    SEARCH_EMAILS = "search_emails"
    DELETE_EMAIL = "delete_email"

# MCP Tool Schemas (JSON Schema format)
TOOL_SCHEMAS = {
    EmailTool.SEND_EMAIL: {
        "name": "send_email",
        "description": "Send an email to one or more recipients",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                    "description": "List of recipient email addresses"
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                    "description": "CC recipients"
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                    "description": "BCC recipients"
                },
                "subject": {
                    "type": "string",
                    "maxLength": 998,
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "maxLength": 1000000,
                    "description": "Email body content (plain text or HTML)"
                },
                "is_html": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether body is HTML"
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content": {"type": "string", "description": "Base64 encoded content"},
                            "mime_type": {"type": "string"}
                        },
                        "required": ["filename", "content"]
                    },
                    "description": "File attachments (max 25MB total)"
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    EmailTool.READ_INBOX: {
        "name": "read_inbox",
        "description": "Read recent emails from inbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Number of emails to retrieve"
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Pagination offset"
                },
                "unread_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only return unread messages"
                }
            }
        }
    },
    EmailTool.SEARCH_EMAILS: {
        "name": "search_emails",
        "description": "Search emails by criteria",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string"
                },
                "from_addr": {
                    "type": "string",
                    "format": "email",
                    "description": "Filter by sender"
                },
                "to_addr": {
                    "type": "string",
                    "format": "email",
                    "description": "Filter by recipient"
                },
                "subject": {
                    "type": "string",
                    "description": "Subject contains"
                },
                "date_from": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date (ISO 8601)"
                },
                "date_to": {
                    "type": "string",
                    "format": "date",
                    "description": "End date (ISO 8601)"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                }
            }
        }
    },
    EmailTool.DELETE_EMAIL: {
        "name": "delete_email",
        "description": "Delete an email by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Unique message identifier"
                },
                "permanent": {
                    "type": "boolean",
                    "default": False,
                    "description": "Permanently delete (skip trash)"
                }
            },
            "required": ["message_id"]
        }
    }
}

# Error codes for MCP error responses
class ErrorCode(str, Enum):
    AUTH_FAILED = "auth_failed"
    RATE_LIMITED = "rate_limited"
    INVALID_ADDRESS = "invalid_address"
    SERVER_ERROR = "server_error"
    ATTACHMENT_TOO_LARGE = "attachment_too_large"
    INVALID_PARAMS = "invalid_params"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MESSAGE_NOT_FOUND = "message_not_found"

# Standard MCP JSON-RPC error codes
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603

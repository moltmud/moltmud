#!/usr/bin/env python3
"""Secrets manager using Bitwarden CLI.

Provides secure access to secrets stored in Bitwarden vault.
Replaces plain text JSON files in ~/.openclaw/workspace/secrets/

Environment Variables:
    BW_SESSION: Bitwarden session key (required for unlock)
    BW_PASSWORD: Bitwarden master password (optional, for auto-unlock)

Example:
    export BW_SESSION=$(bw unlock --raw)
    python3 -c "from secrets_manager import get_secret; print(get_secret('nvidia_api_key'))"
"""

import json
import os
import subprocess
from typing import Any, Dict, Optional, Union


class BitwardenError(Exception):
    """Raised when Bitwarden CLI operation fails."""
    pass


class SecretNotFoundError(BitwardenError):
    """Raised when a secret is not found in the vault."""
    pass


def _get_session_key() -> Optional[str]:
    """Get Bitwarden session key from environment."""
    return os.environ.get("BW_SESSION")


def _ensure_session() -> str:
    """Ensure we have a valid session key, auto-unlock if BW_PASSWORD is set."""
    session = _get_session_key()
    if session:
        return session
    
    # Try to unlock with password if available
    password = os.environ.get("BW_PASSWORD")
    if password:
        try:
            result = subprocess.run(
                ["bw", "unlock", "--raw"],
                input=password,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                os.environ["BW_SESSION"] = result.stdout.strip()
                return result.stdout.strip()
        except Exception:
            pass
    
    raise BitwardenError(
        "BW_SESSION not set. Run: export BW_SESSION=$(bw unlock --raw)"
    )


def _bw_command(args: list) -> dict:
    """Execute a Bitwarden CLI command and return JSON output."""
    session = _ensure_session()
    env = os.environ.copy()
    env["BW_SESSION"] = session
    
    try:
        result = subprocess.run(
            ["bw"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            if "not found" in error_msg.lower():
                raise SecretNotFoundError(f"Secret not found: {args}")
            raise BitwardenError(f"Bitwarden CLI error: {error_msg}")
        
        if not result.stdout.strip():
            return {}
        
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise BitwardenError(f"Invalid JSON from Bitwarden: {e}")
    except subprocess.TimeoutExpired:
        raise BitwardenError("Bitwarden CLI timeout")
    except FileNotFoundError:
        raise BitwardenError(
            "Bitwarden CLI (bw) not found. Install with: npm install -g @bitwarden/cli"
        )


def get_secret(item_name: str, field: Optional[str] = None) -> Union[str, Dict[str, Any]]:
    """Get a secret from Bitwarden vault.
    
    Args:
        item_name: Name of the item in Bitwarden vault
        field: Specific field to retrieve (e.g., 'password', 'username', 'notes').
               If None, returns the password for login items, or parsed JSON for secure notes.
    
    Returns:
        String value if field is specified, or dict if retrieving full JSON credentials
    
    Raises:
        SecretNotFoundError: If the item doesn't exist
        BitwardenError: If CLI operation fails
    
    Example:
        # Get API key stored as password in login item
        api_key = get_secret("nvidia_api_key")
        
        # Get specific field
        username = get_secret("github_credentials", "username")
        
        # Get JSON credentials (stored as secure note)
        creds = get_secret("github_credentials")  # Returns dict
    """
    item = _bw_command(["get", "item", item_name])
    
    if not item:
        raise SecretNotFoundError(f"Item '{item_name}' not found in Bitwarden vault")
    
    # Handle specific field requests
    if field:
        if field == "password":
            return item.get("login", {}).get("password", "")
        elif field == "username":
            return item.get("login", {}).get("username", "")
        elif field == "notes":
            return item.get("notes", "")
        else:
            # Check custom fields
            for f in item.get("fields", []):
                if f.get("name") == field:
                    return f.get("value", "")
            raise SecretNotFoundError(f"Field '{field}' not found in item '{item_name}'")
    
    # Auto-detect return type
    item_type = item.get("type")
    
    # For secure notes, check if notes contain JSON
    if item_type == 2:  # Secure note
        notes = item.get("notes", "")
        if notes.strip().startswith(("{", "[")):
            try:
                return json.loads(notes)
            except json.JSONDecodeError:
                return notes
        return notes
    
    # For login items, return password by default
    if item_type == 1:  # Login
        return item.get("login", {}).get("password", "")
    
    # Default: return the whole item
    return item


def get_credential_file(filename: str) -> Dict[str, Any]:
    """Get credentials that were previously stored in JSON files.
    
    Args:
        filename: Base name of the credential file (e.g., 'github_credentials.json')
                  or just the base name without extension ('github_credentials')
    
    Returns:
        Dict containing the credential data
    
    Example:
        # Previously: json.load(open('github_credentials.json'))
        # Now: get_credential_file('github_credentials')
    """
    # Remove .json extension if provided
    item_name = filename.replace(".json", "")
    
    result = get_secret(item_name)
    
    # If result is already a dict (parsed from JSON notes), return it
    if isinstance(result, dict):
        return result
    
    # If result is a string, try to parse as JSON
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Return as single value under 'value' key
            return {"value": result}
    
    return {}


def list_secrets() -> list:
    """List all available secret names in the vault.
    
    Returns:
        List of item names
    """
    items = _bw_command(["list", "items"])
    return [item.get("name") for item in items if item.get("name")]


def sync() -> None:
    """Sync the local vault with Bitwarden server."""
    _bw_command(["sync"])


# Convenience functions for specific credential types
def get_api_key(service_name: str) -> str:
    """Get an API key for a specific service.
    
    Args:
        service_name: Name of the service (e.g., 'nvidia', 'openai', 'github')
    
    Returns:
        The API key string
    """
    # Try common naming patterns
    patterns = [
        f"{service_name}_api_key",
        f"{service_name}_apikey",
        f"{service_name}_key",
        f"{service_name}_token",
        service_name,
    ]
    
    for pattern in patterns:
        try:
            return get_secret(pattern)
        except SecretNotFoundError:
            continue
    
    raise SecretNotFoundError(f"API key for '{service_name}' not found")


def get_database_credentials(db_name: str = "default") -> Dict[str, str]:
    """Get database credentials.
    
    Args:
        db_name: Name of the database entry in Bitwarden
    
    Returns:
        Dict with host, port, username, password, database
    """
    creds = get_credential_file(f"{db_name}_db_credentials")
    if not creds:
        # Try generic fields
        return {
            "host": get_secret(f"{db_name}_db_host", "password"),
            "port": get_secret(f"{db_name}_db_port", "password"),
            "username": get_secret(f"{db_name}_db_user", "password"),
            "password": get_secret(f"{db_name}_db_pass", "password"),
            "database": get_secret(f"{db_name}_db_name", "password"),
        }
    return creds


if __name__ == "__main__":
    # Test functionality
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 secrets_manager.py <item_name> [field]")
        print("\nAvailable secrets:")
        try:
            for name in list_secrets():
                print(f"  - {name}")
        except BitwardenError as e:
            print(f"  Error: {e}")
        sys.exit(1)
    
    item_name = sys.argv[1]
    field = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = get_secret(item_name, field)
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)
    except BitwardenError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
#!/usr/bin/env python3
"""
Task API Extension - RESTful endpoints for task management
Designed to integrate with MINIMAL_MUD_SERVER.py
"""

import json
from typing import Dict, Any, Tuple
from mission_control import get_db, update_task, get_task_by_id, delete_task

def handle_patch_task(task_id_str: str, request_body: str, actor: str) -> Tuple[int, Dict[str, Any]]:
    """
    Handle PATCH /api/tasks/{id}
    
    Args:
        task_id_str: Task ID from URL path
        request_body: JSON string of request body
        actor: Username of requesting user
    
    Returns:
        Tuple of (status_code, response_dict)
    """
    # Parse task ID
    try:
        task_id = int(task_id_str)
    except ValueError:
        return 400, {"error": "Invalid task ID format"}
    
    # Parse request body
    try:
        updates = json.loads(request_body) if request_body else {}
    except json.JSONDecodeError:
        return 400, {"error": "Invalid JSON in request body"}
    
    if not isinstance(updates, dict):
        return 400, {"error": "Request body must be a JSON object"}
    
    conn = get_db()
    try:
        # Check if task exists (for 404 vs 409 conflict detection)
        existing = get_task_by_id(conn, task_id)
        if not existing:
            return 404, {"error": "Task not found"}
        
        # Check for concurrent modification if 'updated_at' provided in updates
        if 'updated_at' in updates:
            client_ts = updates.pop('updated_at')  # Remove from updates, use for check only
            server_ts = existing.get('updated_at', '')
            if client_ts != server_ts:
                return 409, {
                    "error": "Conflict: Task was modified by another user",
                    "server_updated_at": server_ts,
                    "task": existing
                }
        
        # Perform update
        success = update_task(conn, task_id, updates, actor)
        
        if success:
            # Return updated task
            updated_task = get_task_by_id(conn, task_id)
            return 200, {
                "success": True,
                "task": updated_task,
                "message": "Task updated successfully"
            }
        else:
            return 400, {"error": "No valid fields provided for update"}
            
    except ValueError as e:
        return 422, {"error": "Validation error", "details": str(e)}
    except Exception as e:
        return 500, {"error": f"Internal server error: {str(e)}"}
    finally:
        conn.close()

def handle_delete_task(task_id_str: str, actor: str) -> Tuple[int, Dict[str, Any]]:
    """
    Handle DELETE /api/tasks/{id}
    """
    try:
        task_id = int(task_id_str)
    except ValueError:
        return 400, {"error": "Invalid task ID format"}
    
    conn = get_db()
    try:
        success = delete_task(conn, task_id, actor)
        if success:
            return 200, {"success": True, "message": "Task deleted"}
        else:
            return 404, {"error": "Task not found"}
    except Exception as e:
        return 500, {"error": str(e)}
    finally:
        conn.close()

def handle_get_task(task_id_str: str) -> Tuple[int, Dict[str, Any]]:
    """
    Handle GET /api/tasks/{id}
    """
    try:
        task_id = int(task_id_str)
    except ValueError:
        return 400, {"error": "Invalid task ID format"}
    
    conn = get_db()
    try:
        task = get_task_by_id(conn, task_id)
        if task:
            return 200, task
        else:
            return 404, {"error": "Task not found"}
    finally:
        conn.close()

# Router mapping for MINIMAL_MUD_SERVER integration
TASK_ROUTES = {
    'PATCH': handle_patch_task,
    'DELETE': handle_delete_task,
    'GET': handle_get_task,
}

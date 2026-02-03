#!/usr/bin/env python3
"""
Mission Control MCP Server

Exposes Mission Control functionality as MCP tools that can be used by
OpenClaw and other MCP-compatible agents.

Tools:
- check_tasks: Get assigned or in-progress tasks
- update_task_status: Move tasks through workflow
- create_task: Create a new task
- check_mentions: Get unread mentions
- send_mention: Send a mention to another agent
- record_heartbeat: Report agent status
"""

import json
import sys
import os

# Add workspace to path for mission_control module
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))

from fastmcp import FastMCP
import mission_control as mc

mcp = FastMCP("Mission Control")


@mcp.tool()
def check_tasks(agent: str, status: str = None) -> str:
    """
    Get tasks for an agent.

    Args:
        agent: Agent name to check tasks for
        status: Optional filter by status (inbox, assigned, in_progress, review, done)

    Returns:
        JSON list of tasks
    """
    conn = mc.get_db()
    tasks = mc.get_tasks(conn, status=status, assigned_to=agent)
    return json.dumps(tasks, indent=2)


@mcp.tool()
def update_task_status(task_id: int, status: str, actor: str) -> str:
    """
    Update a task's status.

    Args:
        task_id: ID of the task to update
        status: New status (inbox, assigned, in_progress, review, done, cancelled)
        actor: Name of the agent making the change

    Returns:
        Confirmation message
    """
    conn = mc.get_db()
    mc.update_task_status(conn, task_id, status, actor)
    return f"Task {task_id} moved to {status}"


@mcp.tool()
def create_task(title: str, created_by: str, description: str = "", priority: str = "normal", assigned_to: str = None) -> str:
    """
    Create a new task.

    Args:
        title: Task title
        created_by: Name of the creator
        description: Optional detailed description
        priority: Priority level (low, normal, high, urgent)
        assigned_to: Optional agent to assign to

    Returns:
        JSON with new task ID
    """
    conn = mc.get_db()
    task_id = mc.create_task(conn, title, created_by, description, priority, assigned_to)
    return json.dumps({"task_id": task_id, "title": title})


@mcp.tool()
def check_mentions(agent: str) -> str:
    """
    Get unread mentions for an agent.

    Args:
        agent: Agent name to check mentions for

    Returns:
        JSON list of unread mentions
    """
    conn = mc.get_db()
    mentions = mc.get_unread_mentions(conn, agent)
    return json.dumps(mentions, indent=2)


@mcp.tool()
def mark_mentions_read(agent: str) -> str:
    """
    Mark all mentions as read for an agent.

    Args:
        agent: Agent name

    Returns:
        Confirmation message
    """
    conn = mc.get_db()
    mc.mark_mentions_read(conn, agent)
    return f"Mentions marked as read for {agent}"


@mcp.tool()
def send_mention(from_agent: str, to_agent: str, message: str, task_id: int = None) -> str:
    """
    Send a mention to another agent.

    Args:
        from_agent: Sender agent name
        to_agent: Recipient agent name
        message: The message content
        task_id: Optional related task ID

    Returns:
        Confirmation message
    """
    conn = mc.get_db()
    mc.send_mention(conn, from_agent, to_agent, message, task_id)
    return f"Mention sent from @{from_agent} to @{to_agent}"


@mcp.tool()
def record_heartbeat(agent: str, status: str = "ok", detail: str = "") -> str:
    """
    Record a heartbeat for an agent.

    Args:
        agent: Agent name
        status: Status (ok, work_available, work_done, error)
        detail: Optional detail string

    Returns:
        Confirmation message
    """
    conn = mc.get_db()
    mc.record_heartbeat(conn, agent, status, detail)
    return f"Heartbeat recorded for {agent}: {status}"


@mcp.tool()
def get_activity(limit: int = 20) -> str:
    """
    Get recent activity feed.

    Args:
        limit: Maximum number of entries to return

    Returns:
        JSON list of recent activity
    """
    conn = mc.get_db()
    activity = mc.get_activity(conn, limit=limit)
    return json.dumps(activity, indent=2)


if __name__ == "__main__":
    mcp.run()

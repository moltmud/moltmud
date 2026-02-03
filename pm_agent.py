#!/usr/bin/env python3
"""
PM Agent - Reviews tasks and ensures they are concrete and actionable.

Runs periodically to:
1. Find tasks without 'ready' label
2. Check if they have required elements (steps, acceptance criteria)
3. Add comments requesting clarification for vague tasks
4. Add 'ready' label when tasks meet quality bar
"""

import json
import subprocess
import os
import re
import urllib.request
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
BR_PATH = os.path.expanduser("~/.local/bin/br")
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs")
MC_URL = "http://127.0.0.1:8001/api"
AGENT_NAME = "pm-agent"

# Quality checklist - what makes a task "ready"
REQUIRED_ELEMENTS = [
    ("steps", r"(?i)(steps?|implementation|how to|procedure):?\s*\n\s*[-\d]"),
    ("acceptance", r"(?i)(acceptance|criteria|done when|complete when|definition of done)"),
]

# Tasks that are inherently simple and don't need detailed specs
SIMPLE_TASK_PATTERNS = [
    r"(?i)^(fix|update|change|rename|delete|remove)\s+",
    r"(?i)typo",
    r"(?i)bump version",
]


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [PM] {msg}"
    print(line)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "pm_agent.log"), "a") as f:
        f.write(line + "\n")


def run_br(args):
    """Run a beads command and return output."""
    try:
        result = subprocess.run(
            [BR_PATH] + args,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        log(f"br {' '.join(args)} failed: {e}")
        return "", False


def run_br_json(args):
    """Run a beads command and return JSON output."""
    output, success = run_br(args + ["--json"])
    if success and output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return None
    return None


def get_task_details(task_id):
    """Get full task details including comments."""
    output, success = run_br(["show", task_id])
    return output if success else ""


def has_label(task, label):
    """Check if task has a specific label."""
    labels = task.get("labels", []) or []
    return label in labels


def is_simple_task(title):
    """Check if task is simple enough to not need detailed specs."""
    for pattern in SIMPLE_TASK_PATTERNS:
        if re.search(pattern, title):
            return True
    return False


def check_task_quality(task_id, title, details):
    """
    Check if a task meets quality bar.
    Returns (is_ready, missing_elements)
    """
    # Simple tasks are auto-ready
    if is_simple_task(title):
        return True, []

    # Check for required elements in title + details
    full_text = f"{title}\n{details}"
    missing = []

    for element_name, pattern in REQUIRED_ELEMENTS:
        if not re.search(pattern, full_text):
            missing.append(element_name)

    return len(missing) == 0, missing


def add_comment(task_id, comment):
    """Add a comment to a task."""
    run_br(["comments", "add", task_id, comment])


def add_label(task_id, label):
    """Add a label to a task."""
    run_br(["label", "add", task_id, label])


def record_heartbeat(status, detail=""):
    """Record heartbeat in Mission Control."""
    try:
        req = urllib.request.Request(
            f"{MC_URL}/heartbeat",
            data=json.dumps({
                "agent": AGENT_NAME,
                "status": status,
                "detail": detail,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log(f"Heartbeat failed: {e}")


def main():
    log("=== PM Agent starting ===")

    # Get all open tasks
    tasks = run_br_json(["list", "--status", "open"])
    if not tasks:
        log("No open tasks found or failed to fetch")
        record_heartbeat("ok", "No open tasks to review")
        return

    log(f"Found {len(tasks)} open tasks to review")

    reviewed = 0
    marked_ready = 0
    needs_work = 0
    already_ready = 0

    for task in tasks:
        task_id = task.get("id", "")
        title = task.get("title", "")

        # Skip if already has 'ready' label
        if has_label(task, "ready"):
            already_ready += 1
            continue

        # Skip if already has 'needs-refinement' label (already flagged)
        if has_label(task, "needs-refinement"):
            continue

        # Get full details
        details = get_task_details(task_id)

        # Check quality
        is_ready, missing = check_task_quality(task_id, title, details)

        if is_ready:
            add_label(task_id, "ready")
            log(f"✓ {task_id}: Ready - {title[:50]}")
            marked_ready += 1
        else:
            # Add comment explaining what's missing
            missing_str = ", ".join(missing)
            comment = f"""[PM Review] This task needs more detail before it's ready for implementation.

Missing elements:
- {chr(10).join('- ' + m for m in missing)}

Please add:
1. **Implementation steps**: Numbered list of concrete actions
2. **Acceptance criteria**: How do we know when this is done?

Once updated, remove the 'needs-refinement' label."""

            add_comment(task_id, comment)
            add_label(task_id, "needs-refinement")
            log(f"✗ {task_id}: Needs refinement ({missing_str}) - {title[:50]}")
            needs_work += 1

        reviewed += 1

    summary = f"reviewed={reviewed} ready={marked_ready} needs_work={needs_work} already_ready={already_ready}"
    log(f"=== PM Agent complete: {summary} ===")
    record_heartbeat("ok", summary)


if __name__ == "__main__":
    main()

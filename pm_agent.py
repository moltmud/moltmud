#!/usr/bin/env python3
"""
PM Agent - Reviews tasks and refines vague ones to be concrete and actionable.

Runs periodically to:
1. Find tasks without 'ready' label
2. Check if they have required elements (steps, acceptance criteria)
3. For vague tasks: call LLM to generate proper specs, then update the task
4. Add 'ready' label when tasks meet quality bar
"""

import json
import subprocess
import os
import re
import urllib.request
import ssl
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
BR_PATH = os.path.expanduser("~/.local/bin/br")
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs")
MC_URL = "http://127.0.0.1:8001/api"
AGENT_NAME = "pm-agent"

# NVIDIA API configuration
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "moonshotai/kimi-k2.5"

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

# Max tasks to refine per run (to avoid long runs and API costs)
MAX_REFINE_PER_RUN = 3


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [PM] {msg}"
    print(line)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "pm_agent.log"), "a") as f:
        f.write(line + "\n")


def get_api_key():
    """Read NVIDIA API key from .env file."""
    env_path = os.path.expanduser("~/.openclaw/.env")
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("NVIDIA_API_KEY="):
                    return line.strip().split("=", 1)[1]
    except Exception as e:
        log(f"Failed to read API key: {e}")
    return None


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
    if is_simple_task(title):
        return True, []

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


def remove_label(task_id, label):
    """Remove a label from a task."""
    run_br(["label", "remove", task_id, label])


def call_llm(prompt):
    """Call NVIDIA API directly to generate refined task content."""
    api_key = get_api_key()
    if not api_key:
        log("No API key available")
        return None

    try:
        payload = {
            "model": NVIDIA_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            NVIDIA_API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        # Create SSL context
        ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return None

    except urllib.error.HTTPError as e:
        log(f"LLM API error: {e.code} - {e.read().decode()[:200]}")
        return None
    except Exception as e:
        log(f"LLM call error: {e}")
        return None


def refine_task(task_id, title, details):
    """Use LLM to generate proper specs for a vague task."""
    prompt = f"""You are a PM agent. Refine this task to be concrete and actionable.

Task ID: {task_id}
Title: {title}
Current Details:
{details}

Generate a refined version with:
1. Clear implementation steps (numbered list)
2. Acceptance criteria (how do we know when it's done?)
3. Any clarifications or assumptions

Output ONLY the refined task content in this format:

## Implementation Steps
1. Step one
2. Step two
...

## Acceptance Criteria
- Criterion one
- Criterion two
...

## Notes
Any clarifications or assumptions."""

    return call_llm(prompt)


def update_task_with_refinement(task_id, refinement):
    """Add the refinement as a comment on the task."""
    comment = f"[PM Agent - Refined]\n\n{refinement}"
    add_comment(task_id, comment)


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
    refined = 0
    already_ready = 0
    skipped_needs_refinement = 0

    for task in tasks:
        task_id = task.get("id", "")
        title = task.get("title", "")

        # Skip if already has 'ready' label
        if has_label(task, "ready"):
            already_ready += 1
            continue

        # Process tasks with 'needs-refinement' label (refine them!)
        if has_label(task, "needs-refinement"):
            if refined >= MAX_REFINE_PER_RUN:
                skipped_needs_refinement += 1
                continue

            log(f"Refining {task_id}: {title[:50]}")
            details = get_task_details(task_id)

            refinement = refine_task(task_id, title, details)
            if refinement:
                update_task_with_refinement(task_id, refinement)
                remove_label(task_id, "needs-refinement")
                add_label(task_id, "ready")
                log(f"✓ {task_id}: Refined and ready - {title[:50]}")
                refined += 1
                marked_ready += 1
            else:
                log(f"✗ {task_id}: Refinement failed - {title[:50]}")
            continue

        # Get full details for new tasks
        details = get_task_details(task_id)

        # Check quality
        is_ready, missing = check_task_quality(task_id, title, details)

        if is_ready:
            add_label(task_id, "ready")
            log(f"✓ {task_id}: Ready - {title[:50]}")
            marked_ready += 1
        else:
            # Mark for refinement (will be refined in next run or this run if under limit)
            missing_str = ", ".join(missing)
            add_label(task_id, "needs-refinement")
            log(f"⏳ {task_id}: Marked for refinement ({missing_str}) - {title[:50]}")

            # Try to refine immediately if under limit
            if refined < MAX_REFINE_PER_RUN:
                log(f"Refining {task_id}: {title[:50]}")
                refinement = refine_task(task_id, title, details)
                if refinement:
                    update_task_with_refinement(task_id, refinement)
                    remove_label(task_id, "needs-refinement")
                    add_label(task_id, "ready")
                    log(f"✓ {task_id}: Refined and ready - {title[:50]}")
                    refined += 1
                    marked_ready += 1
                else:
                    log(f"✗ {task_id}: Refinement failed, leaving needs-refinement label")

        reviewed += 1

    summary = f"reviewed={reviewed} ready={marked_ready} refined={refined} already_ready={already_ready}"
    if skipped_needs_refinement > 0:
        summary += f" skipped={skipped_needs_refinement}"

    log(f"=== PM Agent complete: {summary} ===")
    record_heartbeat("ok", summary)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Dev Agent - Picks up ready tasks and implements them.

Runs periodically to:
1. Find highest priority task with 'ready' label
2. Read task details and implementation steps
3. Generate code changes using LLM
4. Apply changes and commit to git
5. Mark task as complete
"""

import json
import subprocess
import os
import re
import urllib.request
import ssl
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
BR_PATH = os.path.expanduser("~/.local/bin/br")
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs")
MC_URL = "http://127.0.0.1:8001/api"
AGENT_NAME = "dev-agent"

# API configuration - primary and fallback
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "moonshotai/kimi-k2.5"

ZAI_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZAI_MODEL = "glm-4-plus"

# Limits
MAX_TASKS_PER_RUN = 1  # Only implement one task per run for safety
MAX_FILE_CONTEXT = 50000  # Max chars of file context to include


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [DEV] {msg}"
    print(line)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "dev_agent.log"), "a") as f:
        f.write(line + "\n")


def get_api_keys():
    """Read API keys from .env file."""
    env_path = os.path.expanduser("~/.openclaw/.env")
    keys = {}
    try:
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    keys[k] = v
    except Exception as e:
        log(f"Failed to read API keys: {e}")
    return keys


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


def claim_task(task_id):
    """Claim a task by setting status to in_progress."""
    return run_br(["update", task_id, "--status", "in_progress", "--assignee", AGENT_NAME])


def complete_task(task_id, reason):
    """Complete a task."""
    return run_br(["close", task_id, "--reason", reason])


def add_comment(task_id, comment):
    """Add a comment to a task."""
    run_br(["comments", "add", task_id, comment])


def call_nvidia_api(messages, api_key):
    """Call NVIDIA API."""
    payload = {
        "model": NVIDIA_MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
    }

    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]


def call_zai_api(messages, api_key):
    """Call ZAI/GLM API with JWT auth."""
    import time
    try:
        import jwt
    except ImportError:
        subprocess.run(["pip", "install", "PyJWT", "-q"], capture_output=True)
        import jwt

    # Generate JWT token
    id_part, secret = api_key.split(".")
    payload = {
        "api_key": id_part,
        "exp": int(round(time.time() * 1000)) + 3600 * 1000,
        "timestamp": int(round(time.time() * 1000)),
    }
    token = jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"},
    )

    data = {
        "model": ZAI_MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
    }

    req = urllib.request.Request(
        ZAI_API_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]


def call_llm(messages):
    """Call LLM with fallback."""
    keys = get_api_keys()

    # Try NVIDIA first
    nvidia_key = keys.get("NVIDIA_API_KEY")
    if nvidia_key:
        try:
            return call_nvidia_api(messages, nvidia_key)
        except Exception as e:
            log(f"NVIDIA API failed: {e}, trying fallback...")

    # Fallback to ZAI/GLM
    zai_key = keys.get("ZAI_API_KEY")
    if zai_key:
        try:
            return call_zai_api(messages, zai_key)
        except Exception as e:
            log(f"ZAI API also failed: {e}")
            return None

    log("No API keys available")
    return None


def get_relevant_files(task_title, task_details):
    """Determine which files are relevant to the task."""
    relevant = []

    # Map task keywords to likely files
    file_hints = {
        "dashboard": ["mission_control.py", "mission-control-ui/src/App.tsx"],
        "mud": ["MINIMAL_MUD_SERVER.py", "mud_http_api.py"],
        "api": ["mud_http_api.py", "mission_control.py"],
        "agent": ["agent_loop.py", "pm_agent.py", "greeter_bot.py"],
        "npc": ["greeter_bot.py", "MINIMAL_MUD_SERVER.py"],
        "fragment": ["MINIMAL_MUD_SERVER.py"],
        "monitoring": ["mission_control.py"],
        "auth": ["mud_http_api.py", "mission_control.py"],
        "websocket": ["MINIMAL_MUD_SERVER.py", "mission_control.py"],
        "metrics": ["mission_control.py"],
    }

    task_lower = (task_title + " " + task_details).lower()

    for keyword, files in file_hints.items():
        if keyword in task_lower:
            relevant.extend(files)

    # Always include some core files for context
    relevant.extend(["README.md", "AGENTS.md"])

    # Dedupe and check existence
    seen = set()
    existing = []
    for f in relevant:
        if f not in seen:
            seen.add(f)
            path = os.path.join(WORKSPACE, f)
            if os.path.exists(path):
                existing.append(f)

    return existing[:5]  # Limit to 5 files


def read_file_content(filepath):
    """Read file content with size limit."""
    full_path = os.path.join(WORKSPACE, filepath)
    try:
        with open(full_path, "r") as f:
            content = f.read()
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"
            return content
    except Exception as e:
        return f"Error reading file: {e}"


def build_context(task_id, task_title, task_details, relevant_files):
    """Build context for the LLM."""
    context = f"""# Task: {task_title}
ID: {task_id}

## Task Details:
{task_details}

## Relevant Files:
"""

    total_chars = len(context)
    for filepath in relevant_files:
        content = read_file_content(filepath)
        file_section = f"\n### {filepath}\n```\n{content}\n```\n"
        if total_chars + len(file_section) < MAX_FILE_CONTEXT:
            context += file_section
            total_chars += len(file_section)
        else:
            context += f"\n### {filepath}\n(skipped - context limit)\n"

    return context


def parse_file_changes(response):
    """Parse LLM response for file changes."""
    changes = []

    # Pattern 1: ### filename.py followed by ```python code``` (with optional leading whitespace)
    pattern1 = r'^\s*###\s+([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)\s*\n```[a-z]*\n(.*?)```'
    matches = re.findall(pattern1, response, re.DOTALL | re.MULTILINE)
    for filepath, content in matches:
        filepath = filepath.strip()
        if filepath and content.strip():
            changes.append((filepath, content.strip()))

    # Pattern 2: ## FILE: filename.py followed by ```code```
    if not changes:
        pattern2 = r'^\s*##\s*FILE:?\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)\s*\n```[a-z]*\n(.*?)```'
        matches = re.findall(pattern2, response, re.DOTALL | re.MULTILINE)
        for filepath, content in matches:
            filepath = filepath.strip()
            if filepath and content.strip():
                changes.append((filepath, content.strip()))

    # Pattern 3: **filename.py** followed by ```code```
    if not changes:
        pattern3 = r'\*\*([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)\*\*\s*\n```[a-z]*\n(.*?)```'
        matches = re.findall(pattern3, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip()
            if filepath and content.strip():
                changes.append((filepath, content.strip()))

    # Pattern 4: `filename.py`: followed by ```code```
    if not changes:
        pattern4 = r'`([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)`[:\s]*\n```[a-z]*\n(.*?)```'
        matches = re.findall(pattern4, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip()
            if filepath and content.strip():
                changes.append((filepath, content.strip()))

    # Pattern 5: Just look for any code block after a filename mention
    if not changes:
        pattern5 = r'([a-zA-Z0-9_\-]+\.[a-z]+)[`:\s]*\n```[a-z]*\n(.*?)```'
        matches = re.findall(pattern5, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip()
            # Only accept if it looks like a real file
            if filepath and content.strip() and '.' in filepath:
                changes.append((filepath, content.strip()))

    return changes


def apply_changes(changes):
    """Apply file changes to the workspace."""
    applied = []
    for filepath, content in changes:
        full_path = os.path.join(WORKSPACE, filepath)

        # Create directory if needed
        os.makedirs(os.path.dirname(full_path) or WORKSPACE, exist_ok=True)

        try:
            with open(full_path, "w") as f:
                f.write(content)
            applied.append(filepath)
            log(f"  Wrote: {filepath}")
        except Exception as e:
            log(f"  Failed to write {filepath}: {e}")

    return applied


def git_commit(files, message):
    """Commit changes to git."""
    try:
        # Add specific files
        for f in files:
            subprocess.run(
                ["git", "add", f],
                cwd=WORKSPACE,
                capture_output=True,
                timeout=30,
            )

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message + "\n\nCo-Authored-By: Dev Agent <dev-agent@moltmud>"],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            # Push
            push_result = subprocess.run(
                ["git", "push"],
                cwd=WORKSPACE,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return push_result.returncode == 0
        return False
    except Exception as e:
        log(f"Git commit failed: {e}")
        return False


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


def implement_task(task):
    """Implement a single task."""
    task_id = task.get("id", "")
    title = task.get("title", "")

    log(f"Implementing: {task_id} - {title}")

    # Get full details
    details = get_task_details(task_id)

    # Claim the task
    claim_task(task_id)
    add_comment(task_id, f"[Dev Agent] Starting implementation...")

    # Get relevant files
    relevant_files = get_relevant_files(title, details)
    log(f"  Relevant files: {relevant_files}")

    # Build context
    context = build_context(task_id, title, details, relevant_files)

    # Generate implementation
    messages = [
        {
            "role": "system",
            "content": """You are a senior developer implementing tasks for the MoltMud project (a MUD server for AI agents).

When implementing a task:
1. Write complete, working code
2. Follow existing code patterns and style
3. Output each file change as a code block with the filepath as a header

Format your response like this:
### path/to/file.py
```python
# Complete file contents here
```

### another/file.py
```python
# Complete file contents here
```

Be thorough but focused. Only modify files that need to change."""
        },
        {
            "role": "user",
            "content": f"""Please implement the following task:

{context}

Provide the complete implementation with all file changes needed."""
        }
    ]

    response = call_llm(messages)
    if not response:
        add_comment(task_id, "[Dev Agent] Failed to generate implementation - LLM error")
        log(f"  LLM call failed")
        return False

    # Parse and apply changes
    changes = parse_file_changes(response)
    if not changes:
        add_comment(task_id, f"[Dev Agent] Generated response but couldn't parse file changes.\n\nResponse preview:\n{response[:500]}...")
        log(f"  No file changes parsed from response")
        return False

    log(f"  Found {len(changes)} file(s) to change")
    applied = apply_changes(changes)

    if not applied:
        add_comment(task_id, "[Dev Agent] Failed to apply any file changes")
        return False

    # Commit changes
    commit_msg = f"[{task_id}] {title}"
    if git_commit(applied, commit_msg):
        log(f"  Committed and pushed: {applied}")
        complete_task(task_id, f"Implemented by dev-agent. Files changed: {', '.join(applied)}")
        add_comment(task_id, f"[Dev Agent] Implementation complete!\n\nFiles changed:\n" + "\n".join(f"- {f}" for f in applied))
        return True
    else:
        add_comment(task_id, f"[Dev Agent] Applied changes but git commit failed.\n\nFiles modified:\n" + "\n".join(f"- {f}" for f in applied))
        return False


def get_ready_tasks():
    """Get ready tasks sorted by priority."""
    result = run_br_json(["list", "--status", "open"])
    if not result:
        return []

    # Filter for 'ready' label and sort by priority
    ready = [t for t in result if has_label(t, "ready")]
    ready.sort(key=lambda t: t.get("priority", 99))
    return ready


def main():
    log("=== Dev Agent starting ===")

    # Get ready tasks
    tasks = get_ready_tasks()
    if not tasks:
        log("No ready tasks found")
        record_heartbeat("ok", "No ready tasks")
        return

    log(f"Found {len(tasks)} ready tasks")

    # Implement highest priority task
    task = tasks[0]
    task_id = task.get("id", "")
    title = task.get("title", "")
    priority = task.get("priority", "?")

    log(f"Selected: {task_id} (P{priority}) - {title}")

    success = implement_task(task)

    if success:
        log(f"✓ {task_id}: Implementation complete")
        record_heartbeat("ok", f"Implemented {task_id}")
    else:
        log(f"✗ {task_id}: Implementation failed")
        record_heartbeat("error", f"Failed {task_id}")

    log("=== Dev Agent complete ===")


if __name__ == "__main__":
    main()

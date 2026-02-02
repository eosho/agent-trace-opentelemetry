"""Utility functions for agent trace."""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agent_trace.constants import TRACE_FILE
from agent_trace.models import TraceEvent


def get_env_bool(name: str, *, default: bool) -> bool:
    """Get a boolean from environment variable.

    Args:
        name: Environment variable name.
        default: Default value if not set.

    Returns:
        Boolean value from environment variable.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"true", "1", "yes"}


def find_git() -> str | None:
    """Find the git executable path.

    Returns:
        Path to git executable or None if not found.
    """
    return shutil.which("git")


def get_git_revision() -> str | None:
    """Get current git commit SHA.

    Returns:
        Git commit SHA or None if not in a git repo.
    """
    git_path = find_git()
    if not git_path:
        return None
    try:
        result = subprocess.run(  # noqa: S603
            [git_path, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_workspace_root() -> Path:
    """Get the workspace root directory.

    Returns:
        Path to workspace root (git root or cwd).
    """
    git_path = find_git()
    if not git_path:
        return Path.cwd()
    try:
        result = subprocess.run(  # noqa: S603
            [git_path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return Path.cwd()


def normalize_model_id(model: str | None) -> str | None:
    """Normalize model ID to provider/model format.

    Args:
        model: Raw model ID (e.g., "claude-sonnet-4-20250514").

    Returns:
        Normalized model ID (e.g., "anthropic/claude-sonnet-4-20250514").
    """
    if not model:
        return None
    if "/" in model:
        return model

    prefixes = {
        "claude-": "anthropic",
        "gpt-": "openai",
        "o1": "openai",
        "o3": "openai",
        "gemini-": "google",
    }
    for prefix, provider in prefixes.items():
        if model.startswith(prefix):
            return f"{provider}/{model}"
    return model


def to_relative_path(absolute_path: str, root: Path) -> str:
    """Convert absolute path to relative path from repo root.

    Args:
        absolute_path: Absolute file path.
        root: Root directory to make path relative to.

    Returns:
        Relative path string.
    """
    try:
        return str(Path(absolute_path).relative_to(root))
    except ValueError:
        return absolute_path


def write_event_record(
    event: TraceEvent,
    workspace_root: Path,
) -> None:
    """Write a trace event record to the JSONL file.

    Args:
        event: The trace event to record.
        workspace_root: The workspace root directory.
    """
    trace_path = workspace_root / TRACE_FILE

    trace_path.parent.mkdir(parents=True, exist_ok=True)

    # Build file info if present
    file_info = None
    if event.file_path:
        relative_path = to_relative_path(event.file_path, workspace_root)
        file_info = {
            "path": relative_path,
            "ranges": [{"start_line": r.start_line, "end_line": r.end_line} for r in event.ranges]
            if event.ranges
            else [],
        }

    record = {
        "version": "1.1",
        "id": str(uuid4()),
        "event_type": str(event.event_type),
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": event.session_id,
        "vcs": {"type": "git", "revision": get_git_revision()},
        "contributor": {
            "type": event.contributor.type.value,
            "model_id": event.contributor.model_id,
        },
        "file": file_info,
        "tool_name": event.tool_name,
        "metadata": event.metadata or {},
    }

    with trace_path.open("a") as f:
        f.write(json.dumps(record) + "\n")

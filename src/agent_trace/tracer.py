"""OpenTelemetry-based tracer for AI code attribution."""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.attributes import service_attributes
from opentelemetry.trace import Status, StatusCode

from agent_trace.models import ContributorType, FileRange, HookInput, TraceEvent

if TYPE_CHECKING:
    pass

# Semantic convention attributes for agent traces
ATTR_CONTRIBUTOR_TYPE = "agent_trace.contributor.type"
ATTR_MODEL_ID = "agent_trace.contributor.model_id"
ATTR_FILE_PATH = "agent_trace.file.path"
ATTR_RANGE_START = "agent_trace.range.start_line"
ATTR_RANGE_END = "agent_trace.range.end_line"
ATTR_CONTENT_HASH = "agent_trace.range.content_hash"
ATTR_TOOL_NAME = "agent_trace.tool.name"
ATTR_SESSION_ID = "agent_trace.session.id"
ATTR_GIT_REVISION = "agent_trace.vcs.revision"
ATTR_TRANSCRIPT_URL = "agent_trace.conversation.url"

# Default trace file path
TRACE_FILE = ".agent-trace/traces.jsonl"

# Environment variable names
ENV_OTLP_ENDPOINT = "AGENT_TRACE_OTLP_ENDPOINT"
ENV_AZURE_CONNECTION_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"
ENV_FILE_EXPORT = "AGENT_TRACE_FILE_EXPORT"
ENV_CONSOLE_EXPORT = "AGENT_TRACE_CONSOLE_EXPORT"


def _get_env_bool(name: str, *, default: bool) -> bool:
    """Get a boolean from environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"true", "1", "yes"}


def _find_git() -> str | None:
    """Find the git executable path."""
    return shutil.which("git")


def _get_git_revision() -> str | None:
    """Get current git commit SHA."""
    git_path = _find_git()
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


def _get_workspace_root() -> Path:
    """Get the workspace root directory."""
    git_path = _find_git()
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


def _normalize_model_id(model: str | None) -> str | None:
    """Normalize model ID to provider/model format."""
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


def _to_relative_path(absolute_path: str, root: Path) -> str:
    """Convert absolute path to relative path from repo root."""
    try:
        return str(Path(absolute_path).relative_to(root))
    except ValueError:
        return absolute_path


def _write_trace_record(
    file_path: str,
    ranges: list[FileRange],
    *,
    model_id: str | None = None,
    tool_name: str | None = None,
    session_id: str | None = None,
    transcript_url: str | None = None,
    metadata: Mapping[str, str | int | float | bool] | None = None,
) -> None:
    """Write a trace record to the JSONL file.

    Args:
        file_path: Relative file path from repo root.
        ranges: Line ranges that were modified.
        model_id: Normalized model ID.
        tool_name: Tool that made the change.
        session_id: Coding session ID.
        transcript_url: URL to conversation transcript.
        metadata: Additional metadata.
    """
    root = _get_workspace_root()
    trace_path = root / TRACE_FILE

    # Ensure directory exists
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "version": "1.0",
        "id": str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "vcs": {"type": "git", "revision": _get_git_revision()},
        "tool": {"name": "claude-code"},
        "files": [
            {
                "path": file_path,
                "conversations": [
                    {
                        "url": transcript_url,
                        "contributor": {"type": "ai", "model_id": model_id},
                        "ranges": [
                            {"start_line": r.start_line, "end_line": r.end_line} for r in ranges
                        ],
                    }
                ],
            }
        ],
        "metadata": {
            "tool_name": tool_name,
            "session_id": session_id,
            **(metadata or {}),
        },
    }

    with trace_path.open("a") as f:
        f.write(json.dumps(record) + "\n")


class AgentTracer:
    """Tracer for AI code attribution using OpenTelemetry."""

    def __init__(
        self,
        service_name: str = "agent-trace",
        *,
        console_export: bool = False,
        file_export: bool = True,
        otlp_endpoint: str | None = None,
        azure_connection_string: str | None = None,
    ) -> None:
        """Initialize the tracer.

        Args:
            service_name: Name of the service for OTel resource.
            console_export: Whether to export spans to console (for debugging).
            file_export: Whether to write traces to .agent-trace/traces.jsonl.
            otlp_endpoint: Optional OTLP endpoint for production export.
            azure_connection_string: Optional Azure Application Insights connection string.
        """
        self._workspace_root = _get_workspace_root()
        self._file_export = file_export

        resource = Resource.create({
            service_attributes.SERVICE_NAME: service_name,
            service_attributes.SERVICE_VERSION: "1.0.0",
        })

        provider = TracerProvider(resource=resource)

        if console_export:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        if azure_connection_string:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            azure_exporter = AzureMonitorTraceExporter(connection_string=azure_connection_string)
            provider.add_span_processor(BatchSpanProcessor(azure_exporter))

        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(__name__)

    def trace_event(self, event: TraceEvent) -> None:
        """Record a trace event as an OTel span.

        Args:
            event: The trace event to record.
        """
        with self._tracer.start_as_current_span(
            name=f"agent.{event.event_type}",
        ) as span:
            span.set_attribute(ATTR_CONTRIBUTOR_TYPE, event.contributor.type.value)

            if event.contributor.model_id:
                span.set_attribute(ATTR_MODEL_ID, event.contributor.model_id)

            if event.file_path:
                relative_path = _to_relative_path(event.file_path, self._workspace_root)
                span.set_attribute(ATTR_FILE_PATH, relative_path)

            if event.tool_name:
                span.set_attribute(ATTR_TOOL_NAME, event.tool_name)

            if event.session_id:
                span.set_attribute(ATTR_SESSION_ID, event.session_id)

            revision = _get_git_revision()
            if revision:
                span.set_attribute(ATTR_GIT_REVISION, revision)

            for i, range_ in enumerate(event.ranges):
                span.add_event(
                    name=f"range.{i}",
                    attributes={
                        ATTR_RANGE_START: range_.start_line,
                        ATTR_RANGE_END: range_.end_line,
                        **({ATTR_CONTENT_HASH: range_.content_hash} if range_.content_hash else {}),
                    },
                )

            # Custom metadata
            for key, value in event.metadata.items():
                span.set_attribute(f"agent_trace.metadata.{key}", value)

            span.set_status(Status(StatusCode.OK))

    def trace_file_edit(
        self,
        file_path: str,
        ranges: list[FileRange],
        *,
        model: str | None = None,
        tool_name: str | None = None,
        session_id: str | None = None,
        transcript_url: str | None = None,
    ) -> None:
        """Convenience method to trace a file edit.

        Args:
            file_path: Path to the edited file.
            ranges: Line ranges that were edited.
            model: Model ID that made the edit.
            tool_name: Tool name (e.g., "Write", "Edit").
            session_id: Coding session ID.
            transcript_url: URL to conversation transcript.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        relative_path = _to_relative_path(file_path, self._workspace_root)

        # Write to JSONL file if enabled
        if self._file_export:
            _write_trace_record(
                file_path=relative_path,
                ranges=ranges,
                model_id=model_id,
                tool_name=tool_name,
                session_id=session_id,
                transcript_url=transcript_url,
            )

        # Also emit OTel span
        event = TraceEvent(
            event_type="file_edit",
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(
                type=ContributorType.AI,
                model_id=model_id,
            ),
            tool_name=tool_name,
            session_id=session_id,
            metadata={"transcript_url": transcript_url} if transcript_url else {},
        )
        self.trace_event(event)

    def handle_hook(self, hook_input: HookInput) -> None:
        """Handle a Claude Code hook input.

        Args:
            hook_input: The hook input from Claude Code.
        """
        event_type = hook_input.hook_event_name

        # Only trace file-modifying events
        if event_type not in {"PostToolUse", "afterFileEdit", "afterTabFileEdit"}:
            return

        tool_name = hook_input.tool_name or ""
        if tool_name not in {"Write", "Edit"}:
            return

        file_path = hook_input.file_path
        if not file_path and hook_input.tool_input:
            file_path = str(hook_input.tool_input.get("file_path", ""))

        if not file_path:
            return

        # Compute ranges from new_string if available
        ranges: list[FileRange] = []
        if hook_input.tool_input and hook_input.tool_input.get("new_string"):
            new_string = str(hook_input.tool_input["new_string"])
            line_count = new_string.count("\n") + 1
            ranges.append(FileRange(start_line=1, end_line=line_count))

        transcript_url = (
            f"file://{hook_input.transcript_path}" if hook_input.transcript_path else None
        )

        self.trace_file_edit(
            file_path=file_path,
            ranges=ranges or [FileRange(start_line=1, end_line=1)],
            model=hook_input.model,
            tool_name=tool_name,
            session_id=hook_input.session_id,
            transcript_url=transcript_url,
        )


@lru_cache(maxsize=1)
def get_tracer(
    *,
    console_export: bool | None = None,
    file_export: bool | None = None,
    otlp_endpoint: str | None = None,
    azure_connection_string: str | None = None,
) -> AgentTracer:
    """Get the singleton AgentTracer instance.

    Configuration can be set via parameters or environment variables:
    - AGENT_TRACE_OTLP_ENDPOINT: OTLP endpoint URL
    - APPLICATIONINSIGHTS_CONNECTION_STRING: Azure Application Insights connection string
    - AGENT_TRACE_FILE_EXPORT: Enable file export (true/false)
    - AGENT_TRACE_CONSOLE_EXPORT: Enable console export (true/false)

    Args:
        console_export: Whether to export to console (env: AGENT_TRACE_CONSOLE_EXPORT).
        file_export: Whether to write to .agent-trace/traces.jsonl (env: AGENT_TRACE_FILE_EXPORT).
        otlp_endpoint: Optional OTLP endpoint (env: AGENT_TRACE_OTLP_ENDPOINT).
        azure_connection_string: Azure Application Insights connection string
            (env: APPLICATIONINSIGHTS_CONNECTION_STRING).

    Returns:
        The AgentTracer singleton.
    """
    # Resolve configuration: explicit params > env vars > defaults
    resolved_console = (
        console_export
        if console_export is not None
        else _get_env_bool(ENV_CONSOLE_EXPORT, default=False)
    )
    resolved_file = (
        file_export if file_export is not None else _get_env_bool(ENV_FILE_EXPORT, default=True)
    )
    resolved_otlp = otlp_endpoint or os.environ.get(ENV_OTLP_ENDPOINT)
    resolved_azure = azure_connection_string or os.environ.get(ENV_AZURE_CONNECTION_STRING)

    return AgentTracer(
        console_export=resolved_console,
        file_export=resolved_file,
        otlp_endpoint=resolved_otlp,
        azure_connection_string=resolved_azure,
    )

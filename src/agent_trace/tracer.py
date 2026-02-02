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

from agent_trace.models import ContributorType, EventType, FileRange, HookInput, TraceEvent

if TYPE_CHECKING:
    pass

# Semantic convention attributes for agent traces
ATTR_CONTRIBUTOR_TYPE = "agent_trace.contributor.type"
ATTR_MODEL_ID = "agent_trace.contributor.model_id"
ATTR_EVENT_TYPE = "agent_trace.event.type"
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


def _write_event_record(
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
        relative_path = _to_relative_path(event.file_path, workspace_root)
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
        "vcs": {"type": "git", "revision": _get_git_revision()},
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
        """Record a trace event as an OTel span and optionally to JSONL file.

        Args:
            event: The trace event to record.
        """
        # Write to JSONL file if enabled
        if self._file_export:
            _write_event_record(event, self._workspace_root)

        # Emit OTel span
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

        event = TraceEvent(
            event_type=EventType.FILE_EDIT,
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

    def trace_file_create(
        self,
        file_path: str,
        *,
        model: str | None = None,
        tool_name: str | None = None,
        session_id: str | None = None,
        line_count: int = 0,
    ) -> None:
        """Trace a file creation event.

        Args:
            file_path: Path to the created file.
            model: Model ID that created the file.
            tool_name: Tool name (e.g., "Write").
            session_id: Coding session ID.
            line_count: Number of lines in the created file.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        ranges = [FileRange(start_line=1, end_line=max(1, line_count))] if line_count else []

        event = TraceEvent(
            event_type=EventType.FILE_CREATE,
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            tool_name=tool_name,
            session_id=session_id,
        )
        self.trace_event(event)

    def trace_file_delete(
        self,
        file_path: str,
        *,
        model: str | None = None,
        tool_name: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Trace a file deletion event.

        Args:
            file_path: Path to the deleted file.
            model: Model ID that deleted the file.
            tool_name: Tool name (e.g., "Delete").
            session_id: Coding session ID.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)

        event = TraceEvent(
            event_type=EventType.FILE_DELETE,
            file_path=file_path,
            ranges=[],
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            tool_name=tool_name,
            session_id=session_id,
        )
        self.trace_event(event)

    def trace_session_start(
        self,
        session_id: str,
        *,
        model: str | None = None,
        metadata: Mapping[str, str | int | float | bool] | None = None,
    ) -> None:
        """Trace a coding session start.

        Args:
            session_id: The session ID.
            model: Model ID used in the session.
            metadata: Additional session metadata (e.g., workspace, prompt).
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)

        event = TraceEvent(
            event_type=EventType.SESSION_START,
            ranges=[],
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=dict(metadata) if metadata else {},
        )
        self.trace_event(event)

    def trace_session_end(
        self,
        session_id: str,
        *,
        model: str | None = None,
        metadata: Mapping[str, str | int | float | bool] | None = None,
    ) -> None:
        """Trace a coding session end.

        Args:
            session_id: The session ID.
            model: Model ID used in the session.
            metadata: Additional session metadata (e.g., duration, tokens).
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)

        event = TraceEvent(
            event_type=EventType.SESSION_END,
            ranges=[],
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=dict(metadata) if metadata else {},
        )
        self.trace_event(event)

    def trace_code_review(
        self,
        file_path: str,
        ranges: list[FileRange],
        *,
        model: str | None = None,
        session_id: str | None = None,
        review_type: str | None = None,
        findings: list[str] | None = None,
    ) -> None:
        """Trace a code review event.

        Args:
            file_path: Path to the reviewed file.
            ranges: Line ranges that were reviewed.
            model: Model ID that performed the review.
            session_id: Coding session ID.
            review_type: Type of review (e.g., "security", "style", "performance").
            findings: List of review findings/comments.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {}
        if review_type:
            metadata["review_type"] = review_type
        if findings:
            metadata["finding_count"] = len(findings)

        event = TraceEvent(
            event_type=EventType.CODE_REVIEW,
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_code_suggestion(
        self,
        file_path: str,
        ranges: list[FileRange],
        *,
        model: str | None = None,
        session_id: str | None = None,
        suggestion_type: str | None = None,
    ) -> None:
        """Trace a code suggestion event (autocomplete, inline suggestion).

        Args:
            file_path: Path to the file with suggestions.
            ranges: Line ranges where suggestions were made.
            model: Model ID that made the suggestions.
            session_id: Coding session ID.
            suggestion_type: Type of suggestion (e.g., "autocomplete", "inline").
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {}
        if suggestion_type:
            metadata["suggestion_type"] = suggestion_type

        event = TraceEvent(
            event_type=EventType.CODE_SUGGEST,
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_refactor(
        self,
        file_path: str,
        ranges: list[FileRange],
        *,
        model: str | None = None,
        session_id: str | None = None,
        refactor_type: str | None = None,
    ) -> None:
        """Trace a refactoring event.

        Args:
            file_path: Path to the refactored file.
            ranges: Line ranges that were refactored.
            model: Model ID that performed the refactoring.
            session_id: Coding session ID.
            refactor_type: Type of refactoring (e.g., "rename", "extract", "inline").
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {}
        if refactor_type:
            metadata["refactor_type"] = refactor_type

        event = TraceEvent(
            event_type=EventType.REFACTOR,
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_debug(
        self,
        file_path: str,
        ranges: list[FileRange],
        *,
        model: str | None = None,
        session_id: str | None = None,
        issue_type: str | None = None,
        resolved: bool = False,
    ) -> None:
        """Trace a debugging event.

        Args:
            file_path: Path to the debugged file.
            ranges: Line ranges involved in debugging.
            model: Model ID that performed debugging.
            session_id: Coding session ID.
            issue_type: Type of issue debugged (e.g., "error", "warning", "logic").
            resolved: Whether the issue was resolved.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {"resolved": resolved}
        if issue_type:
            metadata["issue_type"] = issue_type

        event = TraceEvent(
            event_type=EventType.DEBUG,
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_test_generate(
        self,
        file_path: str,
        ranges: list[FileRange],
        *,
        model: str | None = None,
        session_id: str | None = None,
        test_framework: str | None = None,
        test_count: int | None = None,
    ) -> None:
        """Trace a test generation event.

        Args:
            file_path: Path to the generated test file.
            ranges: Line ranges of generated tests.
            model: Model ID that generated the tests.
            session_id: Coding session ID.
            test_framework: Test framework used (e.g., "pytest", "jest").
            test_count: Number of tests generated.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {}
        if test_framework:
            metadata["test_framework"] = test_framework
        if test_count is not None:
            metadata["test_count"] = test_count

        event = TraceEvent(
            event_type=EventType.TEST_GENERATE,
            file_path=file_path,
            ranges=ranges,
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_test_run(
        self,
        *,
        model: str | None = None,
        session_id: str | None = None,
        test_file: str | None = None,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
    ) -> None:
        """Trace a test execution event.

        Args:
            model: Model ID that triggered the test run.
            session_id: Coding session ID.
            test_file: Path to the test file (if specific).
            passed: Number of tests passed.
            failed: Number of tests failed.
            skipped: Number of tests skipped.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": passed + failed + skipped,
        }

        event = TraceEvent(
            event_type=EventType.TEST_RUN,
            file_path=test_file,
            ranges=[],
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_command_run(
        self,
        command: str,
        *,
        model: str | None = None,
        session_id: str | None = None,
        exit_code: int | None = None,
        working_dir: str | None = None,
    ) -> None:
        """Trace a terminal command execution event.

        Args:
            command: The command that was executed.
            model: Model ID that ran the command.
            session_id: Coding session ID.
            exit_code: Command exit code.
            working_dir: Working directory for the command.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        metadata: dict[str, str | int | float | bool] = {"command": command}
        if exit_code is not None:
            metadata["exit_code"] = exit_code
        if working_dir:
            metadata["working_dir"] = working_dir

        event = TraceEvent(
            event_type=EventType.COMMAND_RUN,
            ranges=[],
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=metadata,
        )
        self.trace_event(event)

    def trace_custom(
        self,
        event_name: str,
        *,
        file_path: str | None = None,
        ranges: list[FileRange] | None = None,
        model: str | None = None,
        session_id: str | None = None,
        metadata: Mapping[str, str | int | float | bool] | None = None,
    ) -> None:
        """Trace a custom event.

        Args:
            event_name: Name of the custom event.
            file_path: Optional file path associated with the event.
            ranges: Optional line ranges.
            model: Model ID associated with the event.
            session_id: Coding session ID.
            metadata: Additional metadata.
        """
        from agent_trace.models import Contributor

        model_id = _normalize_model_id(model)
        event_metadata: dict[str, str | int | float | bool] = {"custom_event_name": event_name}
        if metadata:
            event_metadata |= metadata

        event = TraceEvent(
            event_type=EventType.CUSTOM,
            file_path=file_path,
            ranges=ranges or [],
            contributor=Contributor(type=ContributorType.AI, model_id=model_id),
            session_id=session_id,
            metadata=event_metadata,
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

    Args:
        console_export: Whether to export to console (env: AGENT_TRACE_CONSOLE_EXPORT).
        file_export: Whether to write to .agent-trace/traces.jsonl (env: AGENT_TRACE_FILE_EXPORT).
        otlp_endpoint: Optional OTLP endpoint (env: AGENT_TRACE_OTLP_ENDPOINT).
        azure_connection_string: Azure Application Insights connection string
            (env: APPLICATIONINSIGHTS_CONNECTION_STRING).

    Returns:
        The AgentTracer singleton.
    """
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

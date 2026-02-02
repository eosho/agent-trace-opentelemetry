"""Tests for agent_trace.tracer."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from agent_trace.models import (
    Contributor,
    ContributorType,
    EventType,
    FileRange,
    HookInput,
    TraceEvent,
)
from agent_trace.tracer import (
    AgentTracer,
    _get_env_bool,
    _normalize_model_id,
    _to_relative_path,
)


class TestNormalizeModelId:
    """Tests for model ID normalization."""

    def test_none_input(self) -> None:
        """Test None returns None."""
        assert _normalize_model_id(None) is None

    def test_already_normalized(self) -> None:
        """Test already normalized model ID."""
        assert (
            _normalize_model_id("anthropic/claude-opus-4-5-20251101")
            == "anthropic/claude-opus-4-5-20251101"
        )

    def test_claude_prefix(self) -> None:
        """Test Claude model normalization."""
        assert (
            _normalize_model_id("claude-sonnet-4-20250514") == "anthropic/claude-sonnet-4-20250514"
        )

    def test_gpt_prefix(self) -> None:
        """Test GPT model normalization."""
        assert _normalize_model_id("gpt-4o") == "openai/gpt-4o"

    def test_o1_prefix(self) -> None:
        """Test o1 model normalization."""
        assert _normalize_model_id("o1-preview") == "openai/o1-preview"

    def test_gemini_prefix(self) -> None:
        """Test Gemini model normalization."""
        assert _normalize_model_id("gemini-pro") == "google/gemini-pro"

    def test_unknown_model(self) -> None:
        """Test unknown model passes through."""
        assert _normalize_model_id("some-other-model") == "some-other-model"


class TestToRelativePath:
    """Tests for path conversion."""

    def test_relative_conversion(self) -> None:
        """Test converting absolute to relative path."""
        root = Path("/home/user/project")
        assert _to_relative_path("/home/user/project/src/main.py", root) == "src/main.py"

    def test_path_outside_root(self) -> None:
        """Test path outside root returns original."""
        root = Path("/home/user/project")
        result = _to_relative_path("/other/path/file.py", root)
        assert result == "/other/path/file.py"


class TestGetEnvBool:
    """Tests for environment variable boolean parsing."""

    def test_default_when_not_set(self) -> None:
        """Test default value when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_env_bool("NONEXISTENT_VAR", default=True) is True
            assert _get_env_bool("NONEXISTENT_VAR", default=False) is False

    def test_true_values(self) -> None:
        """Test various true values."""
        for value in ("true", "True", "TRUE", "1", "yes", "YES"):
            with patch.dict(os.environ, {"TEST_VAR": value}):
                assert _get_env_bool("TEST_VAR", default=False) is True

    def test_false_values(self) -> None:
        """Test various false values."""
        for value in ("false", "False", "0", "no", "anything"):
            with patch.dict(os.environ, {"TEST_VAR": value}):
                assert _get_env_bool("TEST_VAR", default=True) is False


class TestAgentTracer:
    """Tests for AgentTracer class."""

    def test_tracer_initialization(self) -> None:
        """Test tracer initializes correctly."""
        tracer = AgentTracer(
            service_name="test-service",
            console_export=False,
            file_export=False,
        )
        assert tracer._file_export is False

    def test_trace_event(self) -> None:
        """Test recording a trace event."""
        tracer = AgentTracer(file_export=False, console_export=False)
        event = TraceEvent(
            event_type="test_event",
            file_path="src/test.py",
            contributor=Contributor(type=ContributorType.AI),
        )
        # Should not raise
        tracer.trace_event(event)

    def test_handle_hook_filters_events(self) -> None:
        """Test that non-file-modifying events are filtered."""
        tracer = AgentTracer(file_export=False, console_export=False)

        # SessionStart should be ignored
        hook = HookInput(hook_event_name="SessionStart")
        tracer.handle_hook(hook)  # Should not raise

    def test_handle_hook_filters_tools(self) -> None:
        """Test that non-edit tools are filtered."""
        tracer = AgentTracer(file_export=False, console_export=False)

        # Read tool should be ignored
        hook = HookInput(
            hook_event_name="PostToolUse",
            tool_name="Read",
        )
        tracer.handle_hook(hook)  # Should not raise


class TestTraceFileExport:
    """Tests for JSONL file export."""

    def test_trace_file_creation(self, tmp_path: Path) -> None:
        """Test trace file is created with correct format."""
        trace_file = tmp_path / ".agent-trace" / "traces.jsonl"

        with (
            patch("agent_trace.tracer._get_workspace_root", return_value=tmp_path),
            patch("agent_trace.tracer._get_git_revision", return_value="abc123"),
        ):
            tracer = AgentTracer(file_export=True, console_export=False)
            tracer.trace_file_edit(
                file_path=str(tmp_path / "src" / "main.py"),
                ranges=[FileRange(start_line=1, end_line=10)],
                model="claude-sonnet-4-20250514",
                tool_name="Write",
                session_id="session-123",
            )

        assert trace_file.exists()

        with trace_file.open() as f:
            record = json.loads(f.readline())

        # New v1.1 schema
        assert record["version"] == "1.1"
        assert record["event_type"] == "file_edit"
        assert record["session_id"] == "session-123"
        assert record["vcs"]["revision"] == "abc123"
        assert record["file"]["path"] == "src/main.py"
        assert record["file"]["ranges"] == [{"start_line": 1, "end_line": 10}]
        assert record["contributor"]["model_id"] == "anthropic/claude-sonnet-4-20250514"
        assert record["contributor"]["type"] == "ai"

    def test_all_event_types_write_to_file(self, tmp_path: Path) -> None:
        """Test that all event types write to the JSONL file."""
        trace_file = tmp_path / ".agent-trace" / "traces.jsonl"

        with (
            patch("agent_trace.tracer._get_workspace_root", return_value=tmp_path),
            patch("agent_trace.tracer._get_git_revision", return_value="abc123"),
        ):
            tracer = AgentTracer(file_export=True, console_export=False)

            # Test multiple event types
            tracer.trace_session_start(session_id="sess-1", model="claude-opus-4-20250514")
            tracer.trace_file_create(file_path="test.py", model="claude-sonnet-4-20250514")
            tracer.trace_command_run(command="pytest", model="gpt-4o")
            tracer.trace_session_end(session_id="sess-1")

        assert trace_file.exists()

        with trace_file.open() as f:
            records = [json.loads(line) for line in f]

        assert len(records) == 4
        assert records[0]["event_type"] == "session_start"
        assert records[1]["event_type"] == "file_create"
        assert records[2]["event_type"] == "command_run"
        assert records[3]["event_type"] == "session_end"

        # All share same session where applicable
        assert records[0]["session_id"] == "sess-1"
        assert records[3]["session_id"] == "sess-1"


class TestEventTracingMethods:
    """Tests for convenience event tracing methods."""

    def test_trace_file_create(self) -> None:
        """Test file creation tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_file_create(
            file_path="src/new_file.py",
            model="claude-sonnet-4-20250514",
            tool_name="Write",
            session_id="session-123",
            line_count=50,
        )
        # Should not raise

    def test_trace_file_delete(self) -> None:
        """Test file deletion tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_file_delete(
            file_path="src/old_file.py",
            model="gpt-4o",
            session_id="session-456",
        )
        # Should not raise

    def test_trace_session_start(self) -> None:
        """Test session start tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_session_start(
            session_id="session-789",
            model="claude-opus-4-20250514",
            metadata={"workspace": "/home/user/project"},
        )
        # Should not raise

    def test_trace_session_end(self) -> None:
        """Test session end tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_session_end(
            session_id="session-789",
            model="claude-opus-4-20250514",
            metadata={"duration_seconds": 3600, "tokens_used": 15000},
        )
        # Should not raise

    def test_trace_code_review(self) -> None:
        """Test code review tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_code_review(
            file_path="src/main.py",
            ranges=[FileRange(start_line=1, end_line=50)],
            model="claude-sonnet-4-20250514",
            review_type="security",
            findings=["SQL injection risk", "Hardcoded credentials"],
        )
        # Should not raise

    def test_trace_code_suggestion(self) -> None:
        """Test code suggestion tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_code_suggestion(
            file_path="src/utils.py",
            ranges=[FileRange(start_line=10, end_line=15)],
            model="gpt-4o",
            suggestion_type="autocomplete",
        )
        # Should not raise

    def test_trace_refactor(self) -> None:
        """Test refactoring tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_refactor(
            file_path="src/service.py",
            ranges=[FileRange(start_line=20, end_line=40)],
            model="claude-sonnet-4-20250514",
            refactor_type="extract_method",
        )
        # Should not raise

    def test_trace_debug(self) -> None:
        """Test debugging tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_debug(
            file_path="src/buggy.py",
            ranges=[FileRange(start_line=100, end_line=105)],
            model="claude-opus-4-20250514",
            issue_type="null_pointer",
            resolved=True,
        )
        # Should not raise

    def test_trace_test_generate(self) -> None:
        """Test test generation tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_test_generate(
            file_path="tests/test_service.py",
            ranges=[FileRange(start_line=1, end_line=100)],
            model="claude-sonnet-4-20250514",
            test_framework="pytest",
            test_count=5,
        )
        # Should not raise

    def test_trace_test_run(self) -> None:
        """Test test run tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_test_run(
            model="claude-sonnet-4-20250514",
            session_id="session-123",
            test_file="tests/test_service.py",
            passed=10,
            failed=2,
            skipped=1,
        )
        # Should not raise

    def test_trace_command_run(self) -> None:
        """Test command execution tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_command_run(
            command="pytest -v",
            model="claude-sonnet-4-20250514",
            session_id="session-123",
            exit_code=0,
            working_dir="/home/user/project",
        )
        # Should not raise

    def test_trace_custom(self) -> None:
        """Test custom event tracing."""
        tracer = AgentTracer(file_export=False, console_export=False)
        tracer.trace_custom(
            event_name="deployment",
            file_path="deploy.yaml",
            model="claude-opus-4-20250514",
            metadata={"environment": "staging", "version": "1.2.3"},
        )
        # Should not raise


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self) -> None:
        """Test EventType enum has expected values."""
        assert EventType.FILE_CREATE == "file_create"
        assert EventType.FILE_EDIT == "file_edit"
        assert EventType.FILE_DELETE == "file_delete"
        assert EventType.SESSION_START == "session_start"
        assert EventType.SESSION_END == "session_end"
        assert EventType.CODE_REVIEW == "code_review"
        assert EventType.CODE_SUGGEST == "code_suggest"
        assert EventType.REFACTOR == "refactor"
        assert EventType.DEBUG == "debug"
        assert EventType.TEST_GENERATE == "test_generate"
        assert EventType.TEST_RUN == "test_run"
        assert EventType.COMMAND_RUN == "command_run"
        assert EventType.CUSTOM == "custom"

    def test_trace_event_with_event_type(self) -> None:
        """Test TraceEvent accepts EventType enum."""
        event = TraceEvent(
            event_type=EventType.CODE_REVIEW,
            file_path="src/test.py",
            contributor=Contributor(type=ContributorType.AI),
        )
        assert event.event_type == EventType.CODE_REVIEW

"""Tests for agent_trace.tracer."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from agent_trace.models import Contributor, ContributorType, FileRange, HookInput, TraceEvent
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

        assert record["version"] == "1.0"
        assert record["vcs"]["revision"] == "abc123"
        assert record["files"][0]["path"] == "src/main.py"
        assert (
            record["files"][0]["conversations"][0]["contributor"]["model_id"]
            == "anthropic/claude-sonnet-4-20250514"
        )

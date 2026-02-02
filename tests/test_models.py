"""Tests for agent_trace.models."""

import pytest
from pydantic import ValidationError

from agent_trace.models import (
    Contributor,
    ContributorType,
    FileRange,
    HookInput,
    TraceEvent,
)


class TestFileRange:
    """Tests for FileRange model."""

    def test_valid_range(self) -> None:
        """Test creating a valid file range."""
        range_ = FileRange(start_line=1, end_line=10)
        assert range_.start_line == 1
        assert range_.end_line == 10
        assert range_.content_hash is None

    def test_range_with_hash(self) -> None:
        """Test file range with content hash."""
        range_ = FileRange(start_line=5, end_line=15, content_hash="abc123")
        assert range_.content_hash == "abc123"

    def test_invalid_start_line(self) -> None:
        """Test that start_line must be >= 1."""
        with pytest.raises(ValidationError):
            FileRange(start_line=0, end_line=10)

    def test_invalid_end_line(self) -> None:
        """Test that end_line must be >= 1."""
        with pytest.raises(ValidationError):
            FileRange(start_line=1, end_line=0)


class TestContributor:
    """Tests for Contributor model."""

    def test_default_contributor(self) -> None:
        """Test default contributor is AI."""
        contributor = Contributor()
        assert contributor.type == ContributorType.AI
        assert contributor.model_id is None

    def test_contributor_with_model(self) -> None:
        """Test contributor with model ID."""
        contributor = Contributor(
            type=ContributorType.AI,
            model_id="anthropic/claude-sonnet-4-20250514",
        )
        assert contributor.model_id == "anthropic/claude-sonnet-4-20250514"

    def test_human_contributor(self) -> None:
        """Test human contributor type."""
        contributor = Contributor(type=ContributorType.HUMAN)
        assert contributor.type == ContributorType.HUMAN


class TestContributorType:
    """Tests for ContributorType enum."""

    def test_all_types(self) -> None:
        """Test all contributor types exist."""
        assert ContributorType.HUMAN == "human"
        assert ContributorType.AI == "ai"
        assert ContributorType.MIXED == "mixed"
        assert ContributorType.UNKNOWN == "unknown"


class TestTraceEvent:
    """Tests for TraceEvent model."""

    def test_minimal_event(self) -> None:
        """Test creating a minimal trace event."""
        event = TraceEvent(event_type="file_edit")
        assert event.event_type == "file_edit"
        assert event.file_path is None
        assert event.ranges == []
        assert event.contributor.type == ContributorType.AI

    def test_full_event(self) -> None:
        """Test creating a full trace event."""
        event = TraceEvent(
            event_type="PostToolUse",
            file_path="src/main.py",
            ranges=[FileRange(start_line=1, end_line=10)],
            contributor=Contributor(
                type=ContributorType.AI,
                model_id="anthropic/claude-opus-4-5-20251101",
            ),
            tool_name="Edit",
            session_id="session-123",
            metadata={"custom_key": "value"},
        )
        assert event.file_path == "src/main.py"
        assert len(event.ranges) == 1
        assert event.tool_name == "Edit"
        assert event.metadata["custom_key"] == "value"


class TestHookInput:
    """Tests for HookInput model."""

    def test_minimal_hook_input(self) -> None:
        """Test minimal hook input."""
        hook = HookInput(hook_event_name="PostToolUse")
        assert hook.hook_event_name == "PostToolUse"
        assert hook.model is None

    def test_full_hook_input(self) -> None:
        """Test full hook input."""
        hook = HookInput(
            hook_event_name="PostToolUse",
            model="claude-sonnet-4-20250514",
            session_id="session-abc",
            file_path="/home/user/project/src/main.py",
            tool_name="Write",
            tool_input={"file_path": "src/main.py", "new_string": "print('hello')"},
        )
        assert hook.model == "claude-sonnet-4-20250514"
        assert hook.tool_name == "Write"
        assert hook.tool_input is not None
        assert hook.tool_input["new_string"] == "print('hello')"

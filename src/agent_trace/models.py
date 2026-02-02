"""Pydantic models for Agent Trace events."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class ContributorType(StrEnum):
    """Type of code contributor."""

    HUMAN = "human"
    AI = "ai"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class EventType(StrEnum):
    """Types of events that can be traced."""

    # File operations
    FILE_CREATE = "file_create"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"

    # Session lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Code assistance
    CODE_REVIEW = "code_review"
    CODE_SUGGEST = "code_suggest"
    REFACTOR = "refactor"
    DEBUG = "debug"

    # Testing
    TEST_GENERATE = "test_generate"
    TEST_RUN = "test_run"

    # Terminal/commands
    COMMAND_RUN = "command_run"

    # Generic
    CUSTOM = "custom"


class FileRange(BaseModel):
    """A range of lines in a file."""

    start_line: Annotated[int, Field(ge=1, description="1-indexed start line")]
    end_line: Annotated[int, Field(ge=1, description="1-indexed end line")]
    content_hash: str | None = Field(
        default=None,
        description="Hash for position-independent tracking",
    )


class Contributor(BaseModel):
    """Attribution contributor info."""

    type: ContributorType = ContributorType.AI
    model_id: str | None = Field(
        default=None,
        max_length=250,
        description="Model ID following models.dev convention (e.g., anthropic/claude-opus-4-5-20251101)",
    )


class TraceEvent(BaseModel):
    """An event to be traced."""

    event_type: str = Field(description="Hook event name (e.g., PostToolUse, SessionStart)")
    file_path: str | None = Field(default=None, description="Relative file path from repo root")
    ranges: list[FileRange] = Field(default_factory=list, description="Line ranges affected")
    contributor: Contributor = Field(default_factory=Contributor)
    tool_name: str | None = Field(default=None, description="Tool that made the change")
    session_id: str | None = Field(default=None, description="Coding session ID")
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Additional context",
    )


class HookInput(BaseModel):
    """Input from Claude Code hooks (matches their JSON schema)."""

    hook_event_name: str
    model: str | None = None
    transcript_path: str | None = None
    session_id: str | None = None
    file_path: str | None = None
    tool_name: str | None = None
    tool_use_id: str | None = None
    tool_input: dict[str, str | int | None] | None = None
    cwd: str | None = None

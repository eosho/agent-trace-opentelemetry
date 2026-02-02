# Agent Trace Examples

This directory contains examples demonstrating how to use Agent Trace for AI code attribution tracking.

## Quick Start

```python
from agent_trace import AgentTracer, FileRange, get_tracer

# Get the singleton tracer
tracer = get_tracer(file_export=True, console_export=False)

# Trace a file edit
tracer.trace_file_edit(
    file_path="src/main.py",
    ranges=[FileRange(start_line=10, end_line=25)],
    model="claude-sonnet-4-20250514",
    tool_name="Edit",
    session_id="session-123",
)
```

## Complete Usage Examples

### Session Lifecycle

Track the start and end of coding sessions:

```python
from agent_trace import get_tracer

tracer = get_tracer()

# Start a session
tracer.trace_session_start(
    session_id="session-123",
    model="claude-opus-4-20250514",
    metadata={"workspace": "/home/user/project"},
)

# ... do work ...

# End the session
tracer.trace_session_end(
    session_id="session-123",
    metadata={"duration_seconds": 3600, "tokens_used": 15000},
)
```

### File Operations

Track file creation, editing, and deletion:

```python
from agent_trace import FileRange, get_tracer

tracer = get_tracer()

# Create a new file
tracer.trace_file_create(
    file_path="src/new_module.py",
    model="claude-sonnet-4-20250514",
    line_count=50,
)

# Edit an existing file
tracer.trace_file_edit(
    file_path="src/main.py",
    ranges=[FileRange(start_line=10, end_line=25)],
    model="claude-sonnet-4-20250514",
)

# Delete a file
tracer.trace_file_delete(
    file_path="src/old_module.py",
    model="claude-sonnet-4-20250514",
)
```

### Code Assistance

Track code reviews, suggestions, refactoring, and debugging:

```python
from agent_trace import FileRange, get_tracer

tracer = get_tracer()

# Code review
tracer.trace_code_review(
    file_path="src/api.py",
    ranges=[FileRange(start_line=1, end_line=100)],
    model="claude-opus-4-20250514",
    review_type="security",
    findings=["SQL injection risk"],
)

# Code suggestion (autocomplete)
tracer.trace_code_suggestion(
    file_path="src/utils.py",
    ranges=[FileRange(start_line=25, end_line=30)],
    model="gpt-4o",
    suggestion_type="autocomplete",
)

# Refactoring
tracer.trace_refactor(
    file_path="src/utils.py",
    ranges=[FileRange(start_line=20, end_line=50)],
    model="claude-sonnet-4-20250514",
    refactor_type="extract_method",
)

# Debugging
tracer.trace_debug(
    file_path="src/buggy.py",
    ranges=[FileRange(start_line=100, end_line=105)],
    model="claude-opus-4-20250514",
    issue_type="null_pointer",
    resolved=True,
)
```

### Testing

Track test generation and execution:

```python
from agent_trace import FileRange, get_tracer

tracer = get_tracer()

# Generate tests
tracer.trace_test_generate(
    file_path="tests/test_api.py",
    ranges=[FileRange(start_line=1, end_line=80)],
    model="claude-sonnet-4-20250514",
    test_framework="pytest",
    test_count=5,
)

# Run tests
tracer.trace_test_run(
    model="claude-sonnet-4-20250514",
    passed=10,
    failed=2,
    skipped=1,
)
```

### Terminal Commands

Track command execution:

```python
from agent_trace import get_tracer

tracer = get_tracer()

tracer.trace_command_run(
    command="pytest -v",
    model="claude-sonnet-4-20250514",
    exit_code=0,
    working_dir="/home/user/project",
)
```

### Custom Events

Track any custom event:

```python
from agent_trace import get_tracer

tracer = get_tracer()

tracer.trace_custom(
    event_name="deployment",
    file_path="deploy.yaml",
    metadata={"environment": "staging", "version": "1.2.3"},
)
```

## Example Files

| File | Description |
| ------ | ------------- |
| [hooks/](hooks/) | Claude Code and Cursor hook configurations |

## Configuration

Examples can be configured via environment variables:

```bash
# Enable console output for debugging
export AGENT_TRACE_CONSOLE_EXPORT=true

# Configure OTLP endpoint
export AGENT_TRACE_OTLP_ENDPOINT=http://localhost:4317

# Configure Azure Monitor
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;..."
```

Or programmatically:

```python
from agent_trace import get_tracer

# With OTLP export
tracer = get_tracer(
    otlp_endpoint="http://localhost:4317",
    file_export=True,
)

# With Azure Monitor
tracer = get_tracer(
    azure_connection_string="InstrumentationKey=xxx;...",
)
```

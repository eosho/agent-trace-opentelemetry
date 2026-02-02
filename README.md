# Agent Trace (OpenTelemetry)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Typed](https://img.shields.io/badge/typed-strict-green.svg)](https://github.com/microsoft/pyright)

**OpenTelemetry-based AI code attribution tracking** for Claude Code and other AI coding assistants.

Track which AI models made which code changes and export traces to observability backends like Jaeger, Datadog, Azure Monitor, or Honeycomb.

## Features

- **OpenTelemetry Integration** — Export traces to any OTel-compatible backend (Jaeger, Datadog, Honeycomb)
- **Azure Monitor Support** — Native integration with Azure Application Insights
- **Local JSONL Export** — Human-readable trace files in `.agent-trace/traces.jsonl`
- **Claude Code Hooks** — Native integration with Claude Code's hook system
- **Model Identification** — Automatic normalization of model IDs (e.g., `anthropic/claude-opus-4-5-20251101`)
- **Git Context** — Automatic VCS revision tracking
- **Python Library** — Embed tracing in your own applications

## Installation

```bash
# Install base package (includes OpenTelemetry core)
pip install agent-trace

# With OTLP exporter (Jaeger, Datadog, Honeycomb)
pip install agent-trace[otlp]

# With Azure Monitor exporter
pip install agent-trace[azure]

# With all exporters
pip install agent-trace[all]

# Or with uv
uv add agent-trace
uv add agent-trace --extra otlp
uv add agent-trace --extra azure
```

### Dependencies

| Package | Included In |
| --------- | ------------- |
| opentelemetry-api, opentelemetry-sdk | Base install |
| opentelemetry-exporter-otlp | `[otlp]` extra |
| azure-monitor-opentelemetry-exporter | `[azure]` extra |

## Quick Start

### Option 1: Claude Code Hooks (Automatic)

1. **Install agent-trace**:

   ```bash
   pip install agent-trace[trace]
   ```

1. **Configure Claude Code** — Copy to `~/.claude/settings.json`:

   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "Write|Edit",
           "command": "agent-trace"
         }
       ]
     }
   }
   ```

1. **Restart Claude Code** — The hook runs automatically on every file edit

### Option 2: Programmatic Usage

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

### View Traces

```bash
# View recent traces (requires jq)
cat .agent-trace/traces.jsonl | tail -10 | jq -s .

# Or use the poe task
poe trace-view
```

## Trace Format

Traces are stored in `.agent-trace/traces.jsonl` with this schema:

```json
{
  "version": "1.0",
  "id": "uuid",
  "timestamp": "2025-01-15T10:30:00Z",
  "vcs": {
    "type": "git",
    "revision": "abc123..."
  },
  "tool": {
    "name": "claude-code"
  },
  "files": [
    {
      "path": "src/main.py",
      "conversations": [
        {
          "url": "file:///path/to/transcript",
          "contributor": {
            "type": "ai",
            "model_id": "anthropic/claude-sonnet-4-20250514"
          },
          "ranges": [
            { "start_line": 10, "end_line": 25 }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "tool_name": "Edit",
    "session_id": "session-123"
  }
}
```

## Configuration

### Environment Variables

Agent Trace can be configured via environment variables:

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `AGENT_TRACE_OTLP_ENDPOINT` | - | OTLP endpoint URL for trace export |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | - | Azure Application Insights connection string |
| `AGENT_TRACE_FILE_EXPORT` | `true` | Enable JSONL file export |
| `AGENT_TRACE_CONSOLE_EXPORT` | `false` | Enable console span output |

### Tracer Options

| Option | Type | Default | Description |
| -------- | ----------- | --------- | ------------- |
| `service_name` | `str` | `"agent-trace"` | Service name for OTel resource |
| `console_export` | `bool` | `False` | Export spans to console (debugging) |
| `file_export` | `bool` | `True` | Write traces to JSONL file |
| `otlp_endpoint` | `str \| None` | `None` | OTLP endpoint for production export |
| `azure_connection_string` | `str \| None` | `None` | Azure Application Insights connection string |

### OTLP Export

For production observability, configure an OTLP endpoint:

```python
tracer = get_tracer(
    otlp_endpoint="http://localhost:4317",
    file_export=True,
)
```

### Azure Monitor Export

To send traces to Azure Application Insights:

```python
tracer = get_tracer(
    azure_connection_string="InstrumentationKey=xxx;IngestionEndpoint=https://xxx.applicationinsights.azure.com/",
)
```

Or set the environment variable:

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;..."
```

## API Reference

### Models

- **`TraceEvent`** — Core event model with file path, ranges, contributor info
- **`EventType`** — Enum for event types (see Event Types below)
- **`FileRange`** — Line range within a file (1-indexed)
- **`ContributorType`** — Enum: `HUMAN`, `AI`, `MIXED`, `UNKNOWN`
- **`Contributor`** — Attribution info with type and model ID
- **`HookInput`** — Claude Code hook input schema

### Event Types

Agent Trace supports tracking various AI coding events:

| Event Type | Method | Description |
| ------------ | -------- | ------------- |
| `FILE_CREATE` | `trace_file_create()` | New file creation |
| `FILE_EDIT` | `trace_file_edit()` | File modification |
| `FILE_DELETE` | `trace_file_delete()` | File deletion |
| `SESSION_START` | `trace_session_start()` | Coding session start |
| `SESSION_END` | `trace_session_end()` | Coding session end |
| `CODE_REVIEW` | `trace_code_review()` | Code review/analysis |
| `CODE_SUGGEST` | `trace_code_suggestion()` | Autocomplete/inline suggestions |
| `REFACTOR` | `trace_refactor()` | Code refactoring |
| `DEBUG` | `trace_debug()` | Debugging assistance |
| `TEST_GENERATE` | `trace_test_generate()` | Test generation |
| `TEST_RUN` | `trace_test_run()` | Test execution |
| `COMMAND_RUN` | `trace_command_run()` | Terminal command execution |
| `CUSTOM` | `trace_custom()` | Custom events |

### Usage Examples

```python
from agent_trace import AgentTracer, FileRange, get_tracer

tracer = get_tracer()

# Track session lifecycle
tracer.trace_session_start(
    session_id="session-123",
    model="claude-opus-4-20250514",
    metadata={"workspace": "/home/user/project"},
)

# Track file operations
tracer.trace_file_create(
    file_path="src/new_module.py",
    model="claude-sonnet-4-20250514",
    line_count=50,
)

tracer.trace_file_edit(
    file_path="src/main.py",
    ranges=[FileRange(start_line=10, end_line=25)],
    model="claude-sonnet-4-20250514",
)

# Track code assistance
tracer.trace_code_review(
    file_path="src/api.py",
    ranges=[FileRange(start_line=1, end_line=100)],
    model="claude-opus-4-20250514",
    review_type="security",
    findings=["SQL injection risk"],
)

tracer.trace_refactor(
    file_path="src/utils.py",
    ranges=[FileRange(start_line=20, end_line=50)],
    model="claude-sonnet-4-20250514",
    refactor_type="extract_method",
)

# Track testing
tracer.trace_test_generate(
    file_path="tests/test_api.py",
    ranges=[FileRange(start_line=1, end_line=80)],
    model="claude-sonnet-4-20250514",
    test_framework="pytest",
    test_count=5,
)

tracer.trace_test_run(
    model="claude-sonnet-4-20250514",
    passed=10,
    failed=2,
    skipped=1,
)

# Track terminal commands
tracer.trace_command_run(
    command="pytest -v",
    model="claude-sonnet-4-20250514",
    exit_code=0,
)

# Track custom events
tracer.trace_custom(
    event_name="deployment",
    metadata={"environment": "staging"},
)

# End session
tracer.trace_session_end(
    session_id="session-123",
    metadata={"duration_seconds": 3600},
)
```

### Tracer Methods

- **`trace_event(event)`** — Record a generic trace event
- **`trace_file_create(...)`** — Track file creation
- **`trace_file_edit(...)`** — Track file edits
- **`trace_file_delete(...)`** — Track file deletion
- **`trace_session_start(...)`** — Track session start
- **`trace_session_end(...)`** — Track session end
- **`trace_code_review(...)`** — Track code reviews
- **`trace_code_suggestion(...)`** — Track code suggestions
- **`trace_refactor(...)`** — Track refactoring
- **`trace_debug(...)`** — Track debugging
- **`trace_test_generate(...)`** — Track test generation
- **`trace_test_run(...)`** — Track test execution
- **`trace_command_run(...)`** — Track terminal commands
- **`trace_custom(...)`** — Track custom events
- **`handle_hook(hook_input)`** — Process Claude Code hook input

## Development

```bash
# Clone and setup
git clone https://github.com/eosho/agent-trace-opentelemetry.git
cd agent-trace-opentelemetry

# Install with dev dependencies
uv sync --all-extras --dev

# Run checks
poe check        # fmt, lint, typecheck, slop, test
poe quality      # fmt, lint, typecheck, metrics
```

### Available Tasks

| Task | Description |
| ------ | ------------- |
| `poe fmt` | Format code with ruff |
| `poe lint` | Lint and fix issues |
| `poe typecheck` | Run basedpyright |
| `poe test` | Run pytest |
| `poe trace` | Record AI code attribution |
| `poe trace-view` | View recent traces |

## Semantic Attributes

Agent Trace uses these OpenTelemetry semantic attributes:

| Attribute | Description |
| --------- | ----------- |
| `agent_trace.contributor.type` | `human`, `ai`, `mixed`, `unknown` |
| `agent_trace.contributor.model_id` | Normalized model ID |
| `agent_trace.event.type` | Event type (file_edit, session_start, etc.) |
| `agent_trace.file.path` | Relative file path |
| `agent_trace.range.start_line` | 1-indexed start line |
| `agent_trace.range.end_line` | 1-indexed end line |
| `agent_trace.tool.name` | Tool that made the change |
| `agent_trace.session.id` | Coding session ID |
| `agent_trace.vcs.revision` | Git commit SHA |

## License

MIT License — see [LICENSE](LICENSE) for details.

## See Also

- **[OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)** — OTel documentation

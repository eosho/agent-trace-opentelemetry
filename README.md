# Agent Trace

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Typed](https://img.shields.io/badge/typed-strict-green.svg)](https://github.com/microsoft/pyright)

**OpenTelemetry-based AI code attribution tracking** for Claude Code and other AI coding assistants.

Track which AI models made which code changes in your codebase. Agent Trace provides provenance metadata for AI-generated code, enabling compliance, auditing, and understanding of your codebase's AI contribution history.

## Features

- 🔍 **Code Attribution** — Track AI contributions at the file and line-range level
- 📊 **OpenTelemetry Integration** — Export traces to any OTel-compatible backend
- 📁 **Local JSONL Export** — Human-readable trace files in `.agent-trace/traces.jsonl`
- 🔗 **Claude Code Hooks** — Native integration with Claude Code's hook system
- 🏷️ **Model Identification** — Automatic normalization of model IDs (e.g., `anthropic/claude-opus-4-5-20251101`)
- 🔒 **Git Integration** — Automatic VCS revision tracking

## Installation

```bash
# Install with tracing dependencies
pip install agent-trace[trace]

# Or with uv
uv add agent-trace --extra trace
```

## Quick Start

### Using with Claude Code Hooks

Agent Trace integrates with Claude Code's hook system. Add to your Claude Code hooks configuration:

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

The CLI reads hook JSON from stdin and automatically records traces.

### Programmatic Usage

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
| `AGENT_TRACE_FILE_EXPORT` | `true` | Enable JSONL file export |
| `AGENT_TRACE_CONSOLE_EXPORT` | `false` | Enable console span output |

### Tracer Options

| Option | Type | Default | Description |
| -------- | ----------- | --------- | ------------- |
| `service_name` | `str` | `"agent-trace"` | Service name for OTel resource |
| `console_export` | `bool` | `False` | Export spans to console (debugging) |
| `file_export` | `bool` | `True` | Write traces to JSONL file |
| `otlp_endpoint` | `str \| None` | `None` | OTLP endpoint for production export |

### OTLP Export

For production observability, configure an OTLP endpoint:

```python
tracer = get_tracer(
    otlp_endpoint="http://localhost:4317",
    file_export=True,
)
```

## API Reference

### Models

- **`TraceEvent`** — Core event model with file path, ranges, contributor info
- **`FileRange`** — Line range within a file (1-indexed)
- **`ContributorType`** — Enum: `HUMAN`, `AI`, `MIXED`, `UNKNOWN`
- **`Contributor`** — Attribution info with type and model ID
- **`HookInput`** — Claude Code hook input schema

### Tracer Methods

- **`trace_event(event)`** — Record a generic trace event
- **`trace_file_edit(...)`** — Convenience method for file edits
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
| `agent_trace.file.path` | Relative file path |
| `agent_trace.range.start_line` | 1-indexed start line |
| `agent_trace.range.end_line` | 1-indexed end line |
| `agent_trace.tool.name` | Tool that made the change |
| `agent_trace.session.id` | Coding session ID |
| `agent_trace.vcs.revision` | Git commit SHA |

## License

MIT License — see [LICENSE](LICENSE) for details.

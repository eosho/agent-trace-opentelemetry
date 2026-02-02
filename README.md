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
|---------|-------------|
| opentelemetry-api, opentelemetry-sdk | Base install |
| opentelemetry-exporter-otlp | `[otlp]` extra |
| azure-monitor-opentelemetry-exporter | `[azure]` extra |

## Quick Start

### Option 1: Claude Code Hooks (Automatic)

1. **Install agent-trace**:

  ```bash
  pip install agent-trace[trace]
  ```

2. **Configure Claude Code** — Copy to `~/.claude/settings.json`:

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

3. **Restart Claude Code** — The hook runs automatically on every file edit

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

## See Also

- **[OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)** — OTel documentation

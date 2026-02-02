# Agent Instructions

This file provides guidance for AI coding agents working on this repository.

## Project Overview

Agent Trace is an OpenTelemetry-based library for tracking AI code attribution. It records which AI models made which code changes, exporting traces to observability backends.

## Tech Stack

- **Language**: Python 3.11+
- **Package Manager**: uv
- **Build System**: hatchling
- **Type Checking**: basedpyright (strict mode)
- **Linting/Formatting**: ruff
- **Testing**: pytest

## Key Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Run all checks (format, lint, typecheck, slop, test)
uv run poe check

# Run individual checks
uv run poe fmt        # Format code
uv run poe lint       # Lint code
uv run poe typecheck  # Type check
uv run poe test       # Run tests

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Project Structure

```
src/agent_trace/
├── __init__.py   # Public API exports
├── cli.py        # CLI entrypoint for hooks
├── models.py     # Pydantic models (TraceEvent, FileRange, etc.)
├── tracer.py     # Core AgentTracer with OTel integration
├── utils.py      # Utility functions
└── py.typed      # PEP 561 marker

tests/
├── test_models.py
├── test_tracer.py
└── test_utils.py
```

## Code Style

- Follow Google docstring convention
- Use type hints everywhere
- Maximum line length: 100 characters
- Use `from __future__ import annotations` for forward references
- Prefer keyword-only arguments for optional parameters (`*,`)

## Adding Features

1. Add models to `models.py` if new data structures needed
2. Add core logic to `tracer.py`
3. Export public API in `__init__.py`
4. Add tests in `tests/`
5. Update README.md if user-facing

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AGENT_TRACE_OTLP_ENDPOINT` | OTLP endpoint URL |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Monitor connection |
| `AGENT_TRACE_FILE_EXPORT` | Enable file export (true/false) |
| `AGENT_TRACE_CONSOLE_EXPORT` | Enable console export (true/false) |

## Testing

- All new code must have tests
- Minimum coverage: 70%
- Use `pytest.raises` for exception testing
- Use `tmp_path` fixture for file operations
- Mock external dependencies (git, file system)

## Commit Messages

Follow Conventional Commits format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `chore:` Maintenance

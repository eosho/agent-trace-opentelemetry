# Agent Trace Source

This directory contains the `agent_trace` package.

## Package Structure

```txt
agent_trace/
├── __init__.py   # Public API exports
├── cli.py        # CLI entrypoint for Claude Code hooks
├── models.py     # Pydantic models (TraceEvent, FileRange, etc.)
├── tracer.py     # Core AgentTracer with OpenTelemetry integration
└── py.typed      # PEP 561 marker for typed package
```

## Module Overview

- **models.py**: Data models using Pydantic v2 for validation
- **tracer.py**: `AgentTracer` class with OTel spans and JSONL file export
- **cli.py**: Stdin-based CLI for hook integration

See the [main README](../README.md) for usage instructions.

#!/usr/bin/env python3
"""Real-world test script for all tracing events.

Run with: uv run python examples/test_all_events.py
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_trace import AgentTracer, EventType, FileRange


def main() -> None:
    """Test all event tracing methods."""
    # Create tracer with file export enabled
    tracer = AgentTracer(
        service_name="test-all-events",
        file_export=True,
        console_export=True,  # Also show spans in console
    )

    print("Testing all event types...\n")

    # 1. Session Start
    print("1. Tracing SESSION_START...")
    tracer.trace_session_start(
        session_id="test-session-001",
        model="claude-opus-4-20250514",
        metadata={"workspace": "/home/groot/agent-trace-opentelemetry", "prompt": "test all events"},
    )

    # 2. File Create
    print("2. Tracing FILE_CREATE...")
    tracer.trace_file_create(
        file_path="src/new_module.py",
        model="claude-sonnet-4-20250514",
        tool_name="Write",
        session_id="test-session-001",
        line_count=100,
    )

    # 3. File Edit
    print("3. Tracing FILE_EDIT...")
    tracer.trace_file_edit(
        file_path="src/agent_trace/tracer.py",
        ranges=[FileRange(start_line=10, end_line=50), FileRange(start_line=100, end_line=120)],
        model="claude-sonnet-4-20250514",
        tool_name="Edit",
        session_id="test-session-001",
    )

    # 4. File Delete
    print("4. Tracing FILE_DELETE...")
    tracer.trace_file_delete(
        file_path="src/old_module.py",
        model="claude-sonnet-4-20250514",
        tool_name="Delete",
        session_id="test-session-001",
    )

    # 5. Code Review
    print("5. Tracing CODE_REVIEW...")
    tracer.trace_code_review(
        file_path="src/agent_trace/models.py",
        ranges=[FileRange(start_line=1, end_line=80)],
        model="claude-opus-4-20250514",
        session_id="test-session-001",
        review_type="security",
        findings=["No input validation on line 45", "Potential SQL injection on line 72"],
    )

    # 6. Code Suggestion
    print("6. Tracing CODE_SUGGEST...")
    tracer.trace_code_suggestion(
        file_path="src/agent_trace/utils.py",
        ranges=[FileRange(start_line=25, end_line=30)],
        model="gpt-4o",
        session_id="test-session-001",
        suggestion_type="autocomplete",
    )

    # 7. Refactor
    print("7. Tracing REFACTOR...")
    tracer.trace_refactor(
        file_path="src/agent_trace/tracer.py",
        ranges=[FileRange(start_line=200, end_line=250)],
        model="claude-sonnet-4-20250514",
        session_id="test-session-001",
        refactor_type="extract_method",
    )

    # 8. Debug
    print("8. Tracing DEBUG...")
    tracer.trace_debug(
        file_path="src/agent_trace/cli.py",
        ranges=[FileRange(start_line=15, end_line=20)],
        model="claude-opus-4-20250514",
        session_id="test-session-001",
        issue_type="null_pointer",
        resolved=True,
    )

    # 9. Test Generate
    print("9. Tracing TEST_GENERATE...")
    tracer.trace_test_generate(
        file_path="tests/test_new_module.py",
        ranges=[FileRange(start_line=1, end_line=150)],
        model="claude-sonnet-4-20250514",
        session_id="test-session-001",
        test_framework="pytest",
        test_count=8,
    )

    # 10. Test Run
    print("10. Tracing TEST_RUN...")
    tracer.trace_test_run(
        model="claude-sonnet-4-20250514",
        session_id="test-session-001",
        test_file="tests/test_tracer.py",
        passed=40,
        failed=2,
        skipped=1,
    )

    # 11. Command Run
    print("11. Tracing COMMAND_RUN...")
    tracer.trace_command_run(
        command="uv run pytest tests/ -v",
        model="claude-sonnet-4-20250514",
        session_id="test-session-001",
        exit_code=0,
        working_dir="/home/groot/agent-trace-opentelemetry",
    )

    # 12. Custom Event
    print("12. Tracing CUSTOM...")
    tracer.trace_custom(
        event_name="deployment",
        file_path="deploy.yaml",
        model="claude-opus-4-20250514",
        session_id="test-session-001",
        metadata={
            "environment": "staging",
            "version": "0.1.0",
            "success": True,
        },
    )

    # 13. Session End
    print("13. Tracing SESSION_END...")
    tracer.trace_session_end(
        session_id="test-session-001",
        model="claude-opus-4-20250514",
        metadata={
            "duration_seconds": 3600,
            "tokens_used": 15000,
            "files_modified": 5,
        },
    )

    print("\n" + "=" * 60)
    print("All events traced successfully!")
    print("=" * 60)

    # Read and display the trace file
    trace_file = Path(".agent-trace/traces.jsonl")
    if trace_file.exists():
        print(f"\nTrace file: {trace_file.absolute()}")
        print("\nRecent traces:")
        print("-" * 60)

        with trace_file.open() as f:
            lines = f.readlines()
            # Show last 5 traces
            for line in lines[-5:]:
                record = json.loads(line)
                files = record.get("files", [{}])
                file_path = files[0].get("path", "N/A") if files else "N/A"
                print(f"  ID: {record['id'][:8]}...")
                print(f"  Time: {record['timestamp']}")
                print(f"  File: {file_path}")
                print(f"  Tool: {record['metadata'].get('tool_name', 'N/A')}")
                print("-" * 60)

        print(f"\nTotal traces in file: {len(lines)}")
    else:
        print("\nNote: Trace file not found (file_export may be disabled)")

    # Summary of event types tested
    print("\nEvent Types Tested:")
    for event_type in EventType:
        print(f"  - {event_type.value}")


if __name__ == "__main__":
    main()

# Claude Code Hook Configuration

Copy `settings.json` to your Claude Code settings directory:

## Location

- **macOS/Linux**: `~/.claude/settings.json`
- **Windows**: `%USERPROFILE%\.claude\settings.json`

## What it does

This hook runs `agent-trace` after every `Write` or `Edit` tool use, recording:

- Which file was modified
- Which lines were changed
- Which model made the change
- Session and transcript information

## Example hook input (what Claude Code sends to stdin)

```json
{
  "hook_event_name": "PostToolUse",
  "model": "claude-sonnet-4-20250514",
  "session_id": "abc123",
  "file_path": "/home/user/project/src/main.py",
  "tool_name": "Write",
  "tool_use_id": "tool_xyz",
  "tool_input": {
    "file_path": "src/main.py",
    "new_string": "def hello():\n    print('world')\n"
  },
  "transcript_path": "/home/user/.claude/transcripts/session.json",
  "cwd": "/home/user/project"
}
```

## Traces output

Traces are written to `.agent-trace/traces.jsonl` in your project root.

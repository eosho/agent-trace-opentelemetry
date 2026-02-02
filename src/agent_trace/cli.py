#!/usr/bin/env python3
"""CLI entrypoint for Claude Code hooks."""

import json
import logging
import sys

from pydantic import ValidationError

from agent_trace.models import HookInput
from agent_trace.tracer import get_tracer

logger = logging.getLogger(__name__)


def main() -> None:
    """Process hook input from stdin and record trace."""
    # Read JSON from stdin (Claude Code pipes hook data)
    input_data = sys.stdin.read().strip()
    if not input_data:
        return

    try:
        data = json.loads(input_data)
        hook_input = HookInput.model_validate(data)

        tracer = get_tracer(file_export=True, console_export=False)
        tracer.handle_hook(hook_input)

    except json.JSONDecodeError:
        logger.exception("Invalid JSON input")
        sys.exit(1)
    except ValidationError:
        logger.exception("Invalid hook input")
        sys.exit(1)


if __name__ == "__main__":
    main()

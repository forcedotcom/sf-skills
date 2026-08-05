#!/usr/bin/env python3
"""Shared stdin utilities for Claude Code hooks.

Provides safe, non-blocking stdin reading for hook scripts.

Usage:
    from stdin_utils import read_stdin_safe
    input_data = read_stdin_safe()
"""

import json
import sys


def read_stdin_safe(timeout_seconds: float = 0.1) -> dict:
    """Safely read JSON from stdin with timeout.

    Returns empty dict if stdin is a TTY, no data available, or JSON parsing fails.
    """
    if sys.stdin.isatty():
        return {}

    try:
        if sys.platform == "win32":
            return json.load(sys.stdin)
        else:
            import select
            readable, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
            if not readable:
                return {}
            return json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, OSError, ValueError):
        return {}

#!/usr/bin/env python3
"""
LWC LSP Validation Hook
=======================

This PostToolUse hook validates LWC JavaScript files (.js) after Write/Edit
operations using the LWC Language Server (@salesforce/lwc-language-server).

Behavior (Auto-fix loop):
- Outputs errors to Claude so it can automatically fix them
- Repeats until valid or max attempts reached
- Complements existing 165-point SLDS 2 validation

Prerequisites:
- npm install -g @salesforce/lwc-language-server

Usage:
    Triggered automatically by hooks.json configuration
    Input: JSON from stdin with tool_name and tool_input
    Output: Diagnostic messages to stdout (or empty if valid)
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add shared lsp-engine to path
# The installer places lsp-engine at ~/.claude/lsp-engine/ but in a dev
# repo checkout it lives at <repo>/shared/lsp-engine/.  Try both.
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent.parent
_LSP_CANDIDATES = [
    Path.home() / ".claude" / "lsp-engine",               # Installed path
    PLUGIN_ROOT.parent.parent / "shared" / "lsp-engine",  # Dev repo path
]
LSP_ENGINE_PATH = next((p for p in _LSP_CANDIDATES if p.is_dir()), _LSP_CANDIDATES[0])
sys.path.insert(0, str(LSP_ENGINE_PATH))

# Track validation attempts to prevent infinite loops
ATTEMPT_FILE = Path(tempfile.gettempdir()) / "lwc_lsp_attempts.json"
MAX_ATTEMPTS = 3

# LWC file extensions
LWC_EXTENSIONS = {".js"}

# LSP Severity levels
SEVERITY_ERROR = 1
SEVERITY_WARNING = 2
SEVERITY_INFO = 3
SEVERITY_HINT = 4

SEVERITY_NAMES = {
    SEVERITY_ERROR: "ERROR",
    SEVERITY_WARNING: "WARNING",
    SEVERITY_INFO: "INFO",
    SEVERITY_HINT: "HINT",
}

SEVERITY_ICONS = {
    SEVERITY_ERROR: "❌",
    SEVERITY_WARNING: "⚠️",
    SEVERITY_INFO: "ℹ️",
    SEVERITY_HINT: "💡",
}


def get_attempt_count(file_path: str) -> int:
    """Get the current attempt count for a file."""
    try:
        if ATTEMPT_FILE.exists():
            with open(ATTEMPT_FILE, "r") as f:
                attempts = json.load(f)
                return attempts.get(file_path, 0)
    except Exception:
        pass
    return 0


def increment_attempt_count(file_path: str) -> int:
    """Increment and return the attempt count for a file."""
    attempts = {}
    try:
        if ATTEMPT_FILE.exists():
            with open(ATTEMPT_FILE, "r") as f:
                attempts = json.load(f)
    except Exception:
        pass

    attempts[file_path] = attempts.get(file_path, 0) + 1
    count = attempts[file_path]

    try:
        with open(ATTEMPT_FILE, "w") as f:
            json.dump(attempts, f)
    except Exception:
        pass

    return count


def reset_attempt_count(file_path: str):
    """Reset attempt count when validation succeeds."""
    try:
        if ATTEMPT_FILE.exists():
            with open(ATTEMPT_FILE, "r") as f:
                attempts = json.load(f)
            if file_path in attempts:
                del attempts[file_path]
                with open(ATTEMPT_FILE, "w") as f:
                    json.dump(attempts, f)
    except Exception:
        pass


def format_lwc_diagnostics(
    result: Dict[str, Any],
    file_path: str,
    max_attempts: int = 3,
    current_attempt: int = 1,
) -> str:
    """
    Format LSP validation result for Claude Code hooks.

    This output is designed to be understood by Claude so it can
    automatically fix any issues found.
    """
    # If LSP had an error
    if "error" in result and result["error"]:
        return f"⚠️ LWC LSP validation skipped: {result['error']}"

    diagnostics = result.get("diagnostics", [])
    success = result.get("success", False)

    # No issues found - show success message
    if success and not diagnostics:
        file_name = Path(file_path).name
        lines = []
        lines.append(f"✅ LWC LSP Validation Passed: {file_name}")
        lines.append("   • JavaScript syntax: OK")
        lines.append("   • LWC decorators: OK")
        lines.append("   • Import resolution: OK")
        return "\n".join(lines)

    # Count errors and warnings
    error_count = sum(1 for d in diagnostics if d.get("severity", 1) == SEVERITY_ERROR)
    warning_count = sum(1 for d in diagnostics if d.get("severity", 2) == SEVERITY_WARNING)

    # Build output for Claude
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("⚡ LWC LSP VALIDATION RESULTS")
    lines.append(f"   File: {file_path}")
    lines.append(f"   Attempt: {current_attempt}/{max_attempts}")
    lines.append("=" * 60)
    lines.append("")

    # Summary
    if error_count > 0 or warning_count > 0:
        lines.append(f"Found {error_count} error(s), {warning_count} warning(s)")
        lines.append("")

    # Diagnostics
    if diagnostics:
        lines.append("ISSUES TO FIX:")
        lines.append("-" * 40)
        for diag in diagnostics:
            severity = diag.get("severity", SEVERITY_ERROR)
            severity_name = SEVERITY_NAMES.get(severity, "UNKNOWN")
            icon = SEVERITY_ICONS.get(severity, "❓")

            message = diag.get("message", "Unknown error")

            # Extract line info
            range_info = diag.get("range", {})
            start = range_info.get("start", {})
            start_line = start.get("line", 0) + 1  # LSP is 0-indexed

            source = diag.get("source", "lwc")

            lines.append(f"{icon} [{severity_name}] line {start_line}: {message} (source: {source})")
        lines.append("")

    # Instructions for Claude
    if error_count > 0:
        lines.append("ACTION REQUIRED:")
        lines.append("Please fix the LWC JavaScript errors above and try again.")
        if current_attempt < max_attempts:
            lines.append(f"(Attempt {current_attempt}/{max_attempts})")
        else:
            lines.append("⚠️ Maximum attempts reached. Manual review may be needed.")

    lines.append("=" * 60)

    return "\n".join(lines)


def is_lwc_js_file(file_path: str) -> bool:
    """Check if file is an LWC JavaScript file."""
    path = Path(file_path)
    # Must be .js file in an lwc folder
    if path.suffix.lower() not in LWC_EXTENSIONS:
        return False
    # Must be in /lwc/ folder structure
    if "/lwc/" not in file_path:
        return False
    # Skip test files
    if ".test.js" in file_path or "__tests__" in file_path:
        return False
    return True


def main():
    """Main hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No input or invalid JSON - skip validation
        sys.exit(0)

    # Extract file path
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only validate LWC JavaScript files
    if not is_lwc_js_file(file_path):
        sys.exit(0)

    # Check if file exists
    if not os.path.exists(file_path):
        sys.exit(0)

    # Track attempts
    current_attempt = increment_attempt_count(file_path)

    # If max attempts exceeded, skip validation to avoid infinite loop
    if current_attempt > MAX_ATTEMPTS:
        print(f"⚠️ LWC LSP validation: Maximum attempts ({MAX_ATTEMPTS}) exceeded for {file_path}")
        print("   Manual review may be required.")
        reset_attempt_count(file_path)  # Reset for next edit session
        sys.exit(0)

    # Try to import LSP engine
    try:
        from lsp_client import LSPClient
    except ImportError as e:
        # LSP engine not available - skip validation silently
        # This allows the plugin to work even without LSP
        sys.exit(0)

    # Check if LWC LSP wrapper exists
    lwc_wrapper = LSP_ENGINE_PATH / "lwc_wrapper.sh"
    if not lwc_wrapper.exists():
        # LWC LSP wrapper not available - skip silently
        sys.exit(0)

    # Create LSP client with LWC wrapper and language ID
    try:
        client = LSPClient(wrapper_path=str(lwc_wrapper), language_id="javascript")
    except Exception as e:
        # LSP initialization error - skip silently
        sys.exit(0)

    # Validate the file
    try:
        result = client.validate_file(file_path)
    except Exception as e:
        # Validation error - report but don't block
        print(f"⚠️ LWC LSP validation error: {e}")
        sys.exit(0)

    # Format output
    output = format_lwc_diagnostics(
        result,
        file_path,
        max_attempts=MAX_ATTEMPTS,
        current_attempt=current_attempt
    )

    # If no output (validation passed), reset attempt count
    if not output:
        reset_attempt_count(file_path)
        sys.exit(0)

    # Output diagnostics for Claude
    print(output)


if __name__ == "__main__":
    main()

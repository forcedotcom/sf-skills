#!/usr/bin/env python3
"""sf_shim — shared, dependency-free cross-platform command-building primitives.

Extracted so sf_context.py and sf_telemetry.py share ONE definition of the Windows
batch-shim invocation and the cmd.exe metacharacter refusal sets, instead of the
byte-for-byte duplicate that had already drifted (sf_telemetry's copy gated the shim
branch on os.name, inlined the metachar check, and called shutil.which directly).
This module imports nothing from either consumer, so it breaks the circular-import
excuse that motivated the duplication. The bash deploy gate keeps the SAME arg set.
"""
from __future__ import annotations

import os
from typing import Optional

# A resolved path ending in one of these is a Windows batch shim that must be
# launched through cmd.exe rather than exec'd directly.
_WINDOWS_SHIM_SUFFIXES = (".cmd", ".bat")

# cmd.exe re-parses the command line it is handed, so these characters keep shell
# meaning inside a batch-shim invocation even though we pass an argv array
# (list2cmdline quotes spaces/quotes, not these). We refuse them on the shim path
# instead of trying to quote them — a fully-correct cmd.exe quoter is notoriously
# hard, and every legitimate caller passes fixed subcommands/flags plus an org
# alias, none of which contain these.
#
# Two sets: ARGS are fully controlled (subcommands/flags/aliases) so we reject the
# widest set, including `(` `)` (grouping) and `!` (delayed expansion). The resolved
# shim PATH is system-provided and legitimately contains `(`/`)` (e.g.
# "C:\\Program Files (x86)\\..."), so its guard omits those — but still rejects the
# chars cmd.exe reparses even inside quotes (`%`, `!`), the quote-breaker (`"`), and
# the redirection/chaining set.
_CMD_ARG_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "(", ")", "\n", "\r")
_CMD_PATH_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "\n", "\r")


def _contains_any(value: str, chars) -> bool:
    return any(ch in value for ch in chars)


def is_windows_shim(path: str) -> bool:
    """True when a resolved path is a Windows batch shim needing a cmd wrapper."""
    return path.lower().endswith(_WINDOWS_SHIM_SUFFIXES)


def build_argv(resolved: str, args: Optional[list] = None) -> Optional[list]:
    """Given an ALREADY-RESOLVED executable path, return the spawnable argv, or None
    (fail closed) on the shim path when a cmd metacharacter would be reparsed.

    Resolution (NAME -> path) stays with each caller so their own resolver mocks
    keep working; this shared helper owns only the drift-prone shim-wrapping + the
    metacharacter refusal that had already diverged between the two copies.

    - A `.cmd`/`.bat` shim -> [COMSPEC, "/c", resolved, *args] (COMSPEC from env,
      fallback "cmd.exe"). Passing an argv array preserves argv boundaries but is NOT
      injection-proof for a batch shim (cmd.exe re-parses the serialized line), so we
      REFUSE (None) if the resolved shim PATH holds a reparse-dangerous char or any
      ARG holds a cmd metacharacter — rather than attempt an error-prone quoter.
    - Anything else -> [resolved, *args] for a direct shell=False spawn.
    """
    args = list(args) if args else []
    if is_windows_shim(resolved):
        if _contains_any(resolved, _CMD_PATH_METACHARACTERS) or any(
            _contains_any(str(a), _CMD_ARG_METACHARACTERS) for a in args
        ):
            return None
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", resolved, *args]
    return [resolved, *args]

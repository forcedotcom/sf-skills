#!/usr/bin/env python3
r"""Filesystem-safety and input-validation guard.

One script, six check types. Emits a STATUS=INVALID_INPUT RESULT block on
failure + tees to $ERROR_TEE on disk + exits 1.

Guiding principle: the agent MUST suffix every call with `|| exit 1` — Python
`sys.exit(1)` only terminates this subprocess, not the parent bash. A bare
call without `|| exit 1` silently continues past a failed guard, which is
the worst possible failure mode for a security check.

Check types:
    symlink     — path must NOT be a symlink (rejects pre-planted attacker bait)
    owned       — path must be owned by current UID (rejects foreign-owned dirs)
    uuid          — value must match ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$
    org_id_15     — value must match ^[A-Za-z0-9]{15}$ (Salesforce org ID slice)
    api_name      — value must match ^[A-Za-z0-9_]+$ (Salesforce API identifier)
    api_version   — value must match ^v[0-9]+\.[0-9]+$ (e.g. v60.0)
    agent_version — value must match ^v[0-9]+$ (e.g. v5 — Agentforce agent version, no dot-minor)
    not_empty     — value must be non-empty string

Python-importable API:
    validate_api_name(value, label="...")      — raises ValidationError on bad input
    validate_api_version(value, label="...")   — raises ValidationError on bad input
    validate_agent_version(value, label="...") — raises ValidationError on bad input
    validate_org_id_15(value, label="...")     — raises ValidationError on bad input
    ValidationError                            — carries (label, reason)

The Python API is used by in-process callers (SOQL loader, path builders in
config.py) that need a raise-based boundary rather than the process-exit
CLI behavior. Regex is shared — do NOT duplicate API_NAME_RE / API_VERSION_RE.

Usage:
    python3 fs_guard.py <value> <label> <check> || exit 1

    # Input validation
    python3 fs_guard.py "$AGENT_API_NAME" agent_api_name api_name || exit 1
    python3 fs_guard.py "$ORG_ALIAS"      org_alias      not_empty || exit 1

    # Filesystem safety
    python3 fs_guard.py "$WORK_DIR"  WORK_DIR  symlink || exit 1
    python3 fs_guard.py "$WORK_DIR"  WORK_DIR  owned   || exit 1
    python3 fs_guard.py "$ORG_ID_15" ORG_ID_15 org_id_15 || exit 1

Inputs:
    argv[1]     value or path to check
    argv[2]     label (appears in ERROR_DETAIL; used to identify which guard tripped)
    argv[3]     check type (one of the 6 above)
    env         $ERROR_TEE (optional): path to disk-tee file. Defaults to
                $HOME/.vibe/data/investigating-agentforce-architecture/_last_error_result.txt.
                Also reads $AGENT_API_NAME / $ORG_ID_18 / $ORG_ID_15 for
                RESULT-block context if set.

Outputs:
    on failure: STATUS=INVALID_INPUT RESULT block on stdout + tee to disk, exit 1
    on success: silent, exit 0
    on bad argv: exit 1 with a minimal ERROR_DETAIL ("fs_guard internal: ...")
"""
import os
import pathlib
import re
import sys

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
ORG_ID_15_RE = re.compile(r"^[A-Za-z0-9]{15}$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
API_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
# api_version check — matches `v60.0`, `v66.0`, etc. Used before any
# Path composition that embeds the api_version segment.
API_VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
# Agent-version check — matches Agentforce version identifiers (`v1`, `v5`,
# `v12`). Deliberately stricter than api_name (rejects free-form names like
# `release_1`) and looser than api_version (rejects `v66.0` which is a REST
# API version, never an agent version). Lives on its own so callers that
# embed agent_version in a filesystem path get the tight regex, not the
# permissive api_name fallback.
AGENT_VERSION_RE = re.compile(r"^v[0-9]+$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
VALID_CHECKS = {"symlink", "owned", "uuid", "org_id_15", "api_name", "api_version", "agent_version", "not_empty"}


# -----------------------------------------------------------------------------
# Python-importable API 
# -----------------------------------------------------------------------------
# In-process callers (soql_loader.load_soql, config.build_*_dir) need a
# raise-based validation boundary, distinct from the CLI script's exit-1
# behavior. The regexes are shared with the CLI checks above — do NOT
# duplicate. If a regex changes, both surfaces update in lockstep.


class ValidationError(ValueError):
    """Raised by the Python-importable validators on bad input.

    Carries the label (which field failed) + reason. Callers (e.g.
    soql_loader.load_soql) convert this into `_unresolved[]` entries or
    RESULT-level INVALID_INPUT responses as appropriate.
    """

    def __init__(self, label: str, reason: str) -> None:
        self.label = label
        self.reason = reason
        super().__init__(f"{label}: {reason}")


def validate_api_name(value, label: str = "value") -> None:
    """Validate `value` against ^[A-Za-z0-9_]+$ (Salesforce API identifier).

    used by soql_loader.load_soql at the substitution boundary to catch
    injection attempts in names pulled from Bot XML, Flow.Metadata, ApexClass
    SymbolTable, etc.

    used by config.build_*_dir helpers for path components that must
    not contain `..`, `/`, or other traversal characters.

    Raises ValidationError on any of: None, non-string, empty, regex miss.
    """
    if value is None:
        raise ValidationError(label, "is None")
    if not isinstance(value, str):
        raise ValidationError(label, f"must be str, got {type(value).__name__}")
    if not value:
        raise ValidationError(label, "must not be empty")
    if not API_NAME_RE.match(value):
        # Preview first 20 chars so logs/_unresolved entries carry enough
        # context to debug, without dumping an unbounded attacker-controlled
        # string into output.
        preview = value[:20]
        raise ValidationError(
            label,
            f"does not match [A-Za-z0-9_]+ (preview={preview!r})",
        )


def validate_api_version(value, label: str = "api_version") -> None:
    """Validate `value` against ^v[0-9]+\\.[0-9]+$ (Salesforce API version).

    used by config.build_*_dir helpers. api_version is returned by
    `sf org display` and later embedded in cache paths; reject anything that
    could escape the cache subtree.
    """
    if value is None:
        raise ValidationError(label, "is None")
    if not isinstance(value, str):
        raise ValidationError(label, f"must be str, got {type(value).__name__}")
    if not value:
        raise ValidationError(label, "must not be empty")
    if not API_VERSION_RE.match(value):
        preview = value[:20]
        raise ValidationError(
            label,
            f"does not match v<major>.<minor> (preview={preview!r})",
        )


def validate_agent_version(value, label: str = "agent_version") -> None:
    """Validate `value` against ^v[0-9]+$ (Agentforce agent version).

    Strictly `v<digits>` with no dot-minor — matches the shape Agentforce
    actually uses (`v1`, `v5`, `v12`). Rejects `release_1`, `v66.0`, `FOO`,
    and anything else that could silently slip past a permissive api_name
    check and land in a filesystem path.

    used by path-builder helpers for the agent_version segment.
    """
    if value is None:
        raise ValidationError(label, "is None")
    if not isinstance(value, str):
        raise ValidationError(label, f"must be str, got {type(value).__name__}")
    if not value:
        raise ValidationError(label, "must not be empty")
    if not AGENT_VERSION_RE.match(value):
        preview = value[:20]
        raise ValidationError(
            label,
            f"does not match v<digits> (preview={preview!r})",
        )


def validate_org_id_15(value, label: str = "org_id_15") -> None:
    """Validate `value` against ^[A-Za-z0-9]{15}$ (Salesforce 15-char org ID).

    stricter than validate_api_name — enforces exact 15 chars AND
    no underscores. `org_id_15` always comes from a Salesforce-generated
    field, never from free-form input.
    """
    if value is None:
        raise ValidationError(label, "is None")
    if not isinstance(value, str):
        raise ValidationError(label, f"must be str, got {type(value).__name__}")
    if not value:
        raise ValidationError(label, "must not be empty")
    if not ORG_ID_15_RE.match(value):
        preview = value[:20]
        raise ValidationError(
            label,
            f"must be exactly 15 alphanumeric chars (preview={preview!r})",
        )


def scrub(s: str) -> str:
    # Same rules as sanitize.py; duplicated locally so this script has no
    # intra-skill imports. Keeps the agent-script boundary clean.
    bad = set("`$\"\\\r\t\0\n")
    return "".join(c for c in (s or "") if c not in bad)


def emit_failure(reason: str, label: str) -> None:
    agent_api_name = scrub(os.environ.get("AGENT_API_NAME", ""))
    org_id_18 = scrub(os.environ.get("ORG_ID_18", ""))
    org_id_15 = scrub(os.environ.get("ORG_ID_15", ""))
    label_safe = scrub(label)
    reason_safe = scrub(reason)

    block = (
        "=== RESULT ===\n"
        "STATUS=INVALID_INPUT\n"
        f"ERROR_DETAIL={label_safe}: {reason_safe}\n"
        f"AGENT_API_NAME={agent_api_name}\n"
        f"ORG_ID_18={org_id_18}\n"
        f"ORG_ID_15={org_id_15}\n"
    )

    # Default ERROR_TEE — skill-scoped data dir. Runtime-agnostic default
    # mirrors runtime.resolve_data_root() in the sibling runtime module
    # (duplicated rather than imported because fs_guard.py is also invoked
    # standalone from SKILL.md bash, where the override hook isn't active).
    tee_default = str(
        pathlib.Path.home()
        / ".vibe"
        / "data"
        / "investigating-agentforce-architecture"
        / "_last_error_result.txt"
    )
    tee_path = os.environ.get("ERROR_TEE") or tee_default
    try:
        p = pathlib.Path(tee_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(block)
    except OSError:
        pass

    sys.stdout.write(block)
    sys.exit(1)


def check_symlink(value: str, label: str) -> None:
    if pathlib.Path(value).is_symlink():
        emit_failure(f"path is a symlink (refusing to follow): {value}", label)


def check_owned(value: str, label: str) -> None:
    p = pathlib.Path(value)
    if not p.exists():
        return
    try:
        st = p.stat()
    except OSError as e:
        emit_failure(f"stat failed: {e}", label)
        return
    if st.st_uid != os.getuid():
        emit_failure(f"foreign-owned (uid {st.st_uid} != current {os.getuid()}): {value}", label)


def check_uuid(value: str, label: str) -> None:
    if not UUID_RE.match(value):
        emit_failure("does not match UUID pattern (8-4-4-4-12 lowercase hex)", label)


def check_org_id_15(value: str, label: str) -> None:
    if not ORG_ID_15_RE.match(value):
        emit_failure("must be exactly 15 alphanumeric characters", label)


def check_api_name(value: str, label: str) -> None:
    if not API_NAME_RE.match(value):
        emit_failure("does not match [A-Za-z0-9_]+ (Salesforce API name rules)", label)


def check_api_version(value: str, label: str) -> None:
    # api_version must be `vNN.N` — no slashes, no dots beyond the one,
    # no path-traversal sequences.
    if not API_VERSION_RE.match(value):
        emit_failure("does not match v<major>.<minor> (e.g. v60.0)", label)


def check_agent_version(value: str, label: str) -> None:
    # Agent version must be `v<digits>` — no dots, no slashes.
    if not AGENT_VERSION_RE.match(value):
        emit_failure("does not match v<digits> (e.g. v5)", label)


def check_not_empty(value: str, label: str) -> None:
    if not value:
        emit_failure("must not be empty", label)


CHECKS = {
    "symlink": check_symlink,
    "owned": check_owned,
    "uuid": check_uuid,
    "org_id_15": check_org_id_15,
    "api_name": check_api_name,
    "api_version": check_api_version,
    "agent_version": check_agent_version,
    "not_empty": check_not_empty,
}


def main() -> int:
    if len(sys.argv) != 4:
        sys.stdout.write(
            "=== RESULT ===\n"
            "STATUS=INVALID_INPUT\n"
            "ERROR_DETAIL=fs_guard internal: wrong argv count (need value, label, check)\n"
        )
        return 1
    value, label, check = sys.argv[1], sys.argv[2], sys.argv[3]

    for arg in (value, label, check):
        if any(c == "\0" or (ord(c) < 0x20 and c not in "\t\n") for c in arg):
            emit_failure("argv contains control characters", label or "argv")

    if check not in VALID_CHECKS:
        emit_failure(f"unknown check type '{check}' (valid: {', '.join(sorted(VALID_CHECKS))})", label)

    CHECKS[check](value, label)
    return 0


if __name__ == "__main__":
    sys.exit(main())

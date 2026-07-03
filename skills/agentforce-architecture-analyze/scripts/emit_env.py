#!/usr/bin/env python3
"""Generic JSON-in → shell-export-out extractor.

Reads a JSON document (from stdin or a file), traverses it by dot-path specs,
and emits `export KEY=shlex.quote(VALUE)` lines on stdout. Callers consume via
`eval "$(python3 emit_env.py ...)"`.

Replaces four single-purpose parsers that previously existed as inline Python
heredocs in the agent:
  * sf org display result parser
  * Q1 row-count + SESSION_ACTIVE derivation
  * _cache_meta.json reader (CACHED_AT_UTC, SESSION_ACTIVE_AT_CACHE)
  * individual field extractors

Field-spec DSL:
    EXPORT_KEY:path           — plain dot-path traversal
    EXPORT_KEY:path[:N]       — string slice after traversal (first N chars)
    EXPORT_KEY:path.length    — length of array / string at path
    EXPORT_KEY:path.empty     — "true" if missing or empty string, else "false"

The DSL is deliberately small: three operators, no dot-inside-key escaping.
Any path component is a dictionary key OR an integer array index
(`data[0].ssot__Foo` works). If the path doesn't resolve, the emitted value
is the empty string — caller decides whether that's OK.

Usage:
    # Parse `sf org display --json` output via stdin
    eval "$(printf '%s' "$_SF_JSON" | python3 emit_env.py stdin \\
            'ACCESS_TOKEN:result.accessToken' \\
            'INSTANCE_URL:result.instanceUrl' \\
            'ORG_ID_18:result.id' \\
            'ORG_ID_15:result.id[:15]')"

    # Q1 post-wave: derive SESSION_ACTIVE from row 0's end timestamp
    eval "$(python3 emit_env.py "$WORK_DIR/_q1_body.json" \\
            'SESSION_ACTIVE:data[0].ssot__EndTimestamp__c.empty')"

    # Cache-hit meta read
    eval "$(python3 emit_env.py "$WORK_DIR/$SID.dc.json" \\
            'CACHED_AT_UTC:_cache_meta.cached_at_utc' \\
            'SESSION_ACTIVE:_cache_meta.session_active_at_cache')"

Inputs:
    argv[1]     'stdin' or an absolute file path
    argv[2+]    field specs (at least one)

Outputs:
    stdout      zero or more `export K=V` lines
    exit 0      always (missing keys just produce empty values)
    exit 1      bad argv, unparseable JSON, or I/O error
"""
import json
import pathlib
import re
import shlex
import sys

SLICE_RE = re.compile(r"^(.*?)\[:(\d+)\]$")


def traverse(data, path: str):
    # Path components are dot-separated. Numeric components index into arrays;
    # everything else is a dict key. Missing/invalid → None (emitted as empty).
    node = data
    for part in path.split("."):
        if node is None:
            return None
        if part.isdigit():
            try:
                node = node[int(part)]
            except (IndexError, KeyError, TypeError):
                return None
        elif isinstance(node, dict):
            node = node.get(part)
        else:
            return None
    return node


def apply_spec(data, spec: str) -> tuple[str, str]:
    # spec: "EXPORT_KEY:path<operator>"
    if ":" not in spec:
        raise ValueError(f"spec missing colon: {spec}")
    key, rhs = spec.split(":", 1)
    if not key:
        raise ValueError(f"spec has empty key: {spec}")

    # Resolve the operator suffix on rhs. Check slice LAST because it's the
    # only one that doesn't alter the traversed value's type.
    if rhs.endswith(".length"):
        value = traverse(data, rhs[:-7])
        if value is None:
            return key, "0"
        if isinstance(value, (list, str)):
            return key, str(len(value))
        return key, "0"

    if rhs.endswith(".empty"):
        value = traverse(data, rhs[:-6])
        is_empty = value is None or value == ""
        return key, "true" if is_empty else "false"

    m = SLICE_RE.match(rhs)
    if m:
        path, n = m.group(1), int(m.group(2))
        value = traverse(data, path)
        if value is None:
            return key, ""
        return key, str(value)[:n]

    # Plain traversal.
    value = traverse(data, rhs)
    if value is None:
        return key, ""
    if isinstance(value, bool):
        # Python `True` / `False` → `true` / `false` so bash string compares
        # work without an extra lowercase step.
        return key, "true" if value else "false"
    return key, str(value)


def main() -> int:
    if len(sys.argv) < 3:
        sys.stderr.write("emit_env.py: need source ('stdin' or path) and at least one field spec\n")
        return 1

    source = sys.argv[1]
    specs = sys.argv[2:]

    try:
        if source == "stdin":
            raw = sys.stdin.read()
        else:
            raw = pathlib.Path(source).read_text()
    except OSError as e:
        sys.stderr.write(f"emit_env.py: cannot read {source}: {e}\n")
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"emit_env.py: JSON parse error: {e}\n")
        return 1

    for spec in specs:
        try:
            key, value = apply_spec(data, spec)
        except ValueError as e:
            sys.stderr.write(f"emit_env.py: {e}\n")
            return 1
        sys.stdout.write(f"export {key}={shlex.quote(value)}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

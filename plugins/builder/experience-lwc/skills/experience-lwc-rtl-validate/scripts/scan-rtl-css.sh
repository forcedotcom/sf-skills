#!/usr/bin/env bash
# Deterministic RTL CSS scanner.
#
# Emits one line per physical-CSS declaration in the given files, in the form:
#   <file>:<line>: <property>: <value> -> <logical-property>: <logical-value>
#
# Each output line is a raw finding the caller translates into a
# Step 6 report bullet (see SKILL.md).
#
# Usage:
#   scripts/scan-rtl-css.sh <file1> [<file2> ...]
#
# Recognised patterns (CSS declarations only — HTML `class="…"` is NEVER scanned):
#   left / right                          -> inset-inline-start / inset-inline-end
#   margin-left / margin-right            -> margin-inline-start / margin-inline-end
#   padding-left / padding-right          -> padding-inline-start / padding-inline-end
#   text-align: left / right              -> text-align: start / end
#   border-left-* / border-right-*        -> border-inline-start-* / border-inline-end-*
#   float: left / float: right            -> float: inline-start / float: inline-end
#   transform: translateX(...)            -> flag; needs sign-flip or logical alternative
#
# The scanner tokenizes declarations (split on `;` within braces) so a single
# minified line with multiple declarations produces one finding per physical
# declaration. It never rewrites selectors — only the `property: value` half
# of each declaration is transformed.
#
# Exit codes:
#   0 — scan completed (findings on stdout may be empty; that IS a valid result)
#   2 — usage error

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <file1> [<file2> ...]" >&2
  exit 2
fi

python3 - "$@" <<'PY'
import re
import sys

# Direct property renames (physical -> logical). Value is preserved verbatim.
PROP_RENAMES = {
    "margin-left": "margin-inline-start",
    "margin-right": "margin-inline-end",
    "padding-left": "padding-inline-start",
    "padding-right": "padding-inline-end",
    "left": "inset-inline-start",
    "right": "inset-inline-end",
}

# `border-left*` / `border-right*` prefix rewrites (keeps the suffix).
BORDER_PREFIXES = {
    "border-left": "border-inline-start",
    "border-right": "border-inline-end",
}

# Property/value pairs where the value is the physical keyword to swap.
VALUE_KEYWORDS = {
    "text-align": {"left": "start", "right": "end"},
    "float": {"left": "inline-start", "right": "inline-end"},
}

DECL_RE = re.compile(r"^\s*([a-zA-Z-]+)\s*:\s*(.*?)\s*$")

def emit(path, lineno, msg):
    print(f"{path}:{lineno}: {msg}")

def scan_declaration(path, lineno, decl):
    """Analyse a single `property: value` declaration."""
    m = DECL_RE.match(decl)
    if not m:
        return
    prop = m.group(1).lower()
    value = m.group(2)
    if not value:
        return

    # Direct property renames (value preserved verbatim).
    if prop in PROP_RENAMES:
        emit(path, lineno, f"{prop}: {value} -> {PROP_RENAMES[prop]}: {value}")
        return

    # border-left* / border-right* (with optional -color / -width / -style / etc).
    for prefix, replacement in BORDER_PREFIXES.items():
        if prop == prefix or prop.startswith(prefix + "-"):
            new_prop = replacement + prop[len(prefix):]
            emit(path, lineno, f"{prop}: {value} -> {new_prop}: {value}")
            return

    # text-align / float — swap the physical keyword in the value.
    if prop in VALUE_KEYWORDS:
        for phys, logical in VALUE_KEYWORDS[prop].items():
            # Match the keyword as a whole token, case-insensitive.
            if re.search(rf"\b{phys}\b", value, re.IGNORECASE):
                new_value = re.sub(
                    rf"\b{phys}\b", logical, value, count=1, flags=re.IGNORECASE
                )
                emit(path, lineno, f"{prop}: {value} -> {prop}: {new_value}")
                return

    # transform: translateX(...) — flag for review.
    if prop == "transform" and re.search(r"\btranslateX\s*\(", value):
        emit(
            path,
            lineno,
            f"{prop}: {value}  # translateX flagged: sign-flip or use a logical alternative",
        )

def strip_css_comments(source):
    """Replace `/* ... */` runs with spaces (preserving \n so line numbers are
    unchanged). Respects `"..."` / `'...'` strings so a `/*` inside a CSS
    string is not treated as a comment opener."""
    out = []
    i = 0
    n = len(source)
    quote = None
    while i < n:
        ch = source[i]
        if quote is not None:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(source[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            j = source.find("*/", i + 2)
            if j == -1:
                j = n
            else:
                j += 2
            # Replace the comment with spaces, but keep newlines to preserve
            # line numbers for the tokenizer below.
            for k in range(i, j):
                out.append("\n" if source[k] == "\n" else " ")
            i = j
            continue
        if ch == '"' or ch == "'":
            quote = ch
        out.append(ch)
        i += 1
    return "".join(out)

def scan_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError as exc:
        print(f"scan-rtl-css.sh: {exc}", file=sys.stderr)
        return

    lines = strip_css_comments(source).splitlines(keepends=True)

    # Split by declaration boundaries (`;`) while tracking source line numbers.
    # Each declaration starts on the line where its property begins.
    in_selector = True  # before the first `{`
    depth = 0
    buf = []
    buf_lineno = 0

    for lineno, raw in enumerate(lines, start=1):
        i = 0
        while i < len(raw):
            ch = raw[i]
            if ch == "{":
                # We are entering a rule block — the buffer so far was a selector.
                depth += 1
                buf = []
                buf_lineno = 0
                in_selector = False
                i += 1
                continue
            if ch == "}":
                if buf and not in_selector:
                    scan_declaration(path, buf_lineno or lineno, "".join(buf))
                buf = []
                buf_lineno = 0
                depth -= 1
                if depth == 0:
                    in_selector = True
                i += 1
                continue
            if ch == ";":
                if not in_selector and buf:
                    scan_declaration(path, buf_lineno or lineno, "".join(buf))
                buf = []
                buf_lineno = 0
                i += 1
                continue
            if not in_selector:
                if not buf and not ch.isspace():
                    buf_lineno = lineno
                buf.append(ch)
            i += 1

    # Trailing declaration without a terminating `;` (allowed in CSS).
    if buf and not in_selector:
        scan_declaration(path, buf_lineno or len(lines), "".join(buf))

for arg in sys.argv[1:]:
    scan_file(arg)
PY

#!/bin/bash
# check-lwc-import.sh <file>
#
# Determines whether a JS/TS file is an LWC module (imports from `lwc`).
# Used to gate LWS rules that only apply to LWC-managed code (e.g. lws-008).
# Exits 0 with `lwc-import=yes` on stdout when an import from the `lwc`
# module is present, or `lwc-import=no` when it is not. Exits non-zero on
# usage errors so the caller can distinguish "no import" from "bad input".
#
# A plain grep cannot tell a real `from 'lwc'` module specifier apart from the
# same text inside a string literal, template literal, or comment. So we do a
# lightweight lexical pass in python3 that removes comments and normalizes every
# string/template literal to the token `"lwc"` ONLY when its entire content is
# exactly `lwc` (otherwise `""`). After that pass, a real specifier survives as
# `from "lwc"` / `import "lwc"` / `import("lwc")`, while the phrase appearing
# inside a string, template, or comment collapses away and cannot match.

set -eu

if [ $# -ne 1 ]; then
  echo "usage: check-lwc-import.sh <file>" >&2
  exit 2
fi

file="$1"

if [ ! -f "$file" ]; then
  echo "check-lwc-import.sh: file not found: $file" >&2
  exit 2
fi

case "$file" in
  *.js|*.ts|*.mjs|*.cjs) ;;
  *)
    echo "check-lwc-import.sh: unsupported extension (expected .js/.ts/.mjs/.cjs): $file" >&2
    exit 2
    ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  echo "check-lwc-import.sh: python3 is required but not installed" >&2
  exit 2
fi

python3 - "$file" <<'PY'
import re
import sys

with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as fh:
    src = fh.read()

out = []          # cleaned code, with comments removed and string/template
                  # literals normalized to a content-aware token
i, n = 0, len(src)

def push_literal(content):
    # Preserve the specifier only when the literal's whole content is exactly
    # `lwc`; any other content (including a `from 'lwc'` phrase embedded in a
    # longer string/template) collapses to an empty literal.
    out.append('"lwc"' if content == "lwc" else '""')

def last_significant():
    # The last non-whitespace character emitted so far — used to decide whether
    # a `/` begins a regex literal (value position) or is a division operator
    # (after a value). None at start of input.
    for chunk in reversed(out):
        s = chunk.rstrip()
        if s:
            return s[-1]
    return None

while i < n:
    c = src[i]

    # line comment: drop to end of line (keep the newline for line structure)
    if c == "/" and i + 1 < n and src[i + 1] == "/":
        j = src.find("\n", i)
        i = n if j == -1 else j
        continue

    # block comment: drop through the closing */
    if c == "/" and i + 1 < n and src[i + 1] == "*":
        j = src.find("*/", i + 2)
        i = n if j == -1 else j + 2
        out.append(" ")
        continue

    # single- or double-quoted string
    if c == "'" or c == '"':
        quote = c
        i += 1
        buf = []
        while i < n and src[i] != quote:
            if src[i] == "\\" and i + 1 < n:      # keep escapes atomic
                i += 2
                buf.append("\\")                   # placeholder; content != lwc
                continue
            if src[i] == "\n":                     # unterminated string; stop
                break
            buf.append(src[i])
            i += 1
        i += 1                                      # consume closing quote
        push_literal("".join(buf))
        continue

    # regex literal — only when `/` is in value position (not division). A
    # regex begins the input or follows an operator/punctuator, never a value
    # (identifier, number, `)`, `]`, `}`, or a quote). Its content is never a
    # module specifier, so we drop it entirely; this stops `/from 'lwc'/` from
    # being mistaken for an import.
    if c == "/":
        prev = last_significant()
        if prev is None or prev in "=(,;:{[!&|?+-*%<>~^":
            j = i + 1
            in_class = False
            while j < n:
                ch = src[j]
                if ch == "\\" and j + 1 < n:
                    j += 2
                    continue
                if ch == "\n":                          # unterminated; bail out
                    break
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    j += 1
                    break
                j += 1
            out.append(" ")                             # regex collapses away
            i = j
            continue

    # template literal (may span lines); treat ${...} as opaque content
    if c == "`":
        i += 1
        buf = []
        while i < n and src[i] != "`":
            if src[i] == "\\" and i + 1 < n:
                i += 2
                buf.append("\\")
                continue
            buf.append(src[i])
            i += 1
        i += 1
        push_literal("".join(buf))
        continue

    out.append(c)
    i += 1

compact = re.sub(r"\s+", " ", "".join(out))

# A surviving `"lwc"` token appears only where the source had a real literal
# whose content was exactly `lwc`. Require it to sit in module-specifier
# position: after `from` (static import / re-export), or as a side-effect or
# dynamic `import`.
is_lwc = bool(
    re.search(r'(^|[^\w$])from "lwc"', compact)
    or re.search(r'(^|[^\w$])import "lwc"', compact)
    or re.search(r'(^|[^\w$])import\("lwc"\)', compact)
)

print("lwc-import=yes" if is_lwc else "lwc-import=no")
PY

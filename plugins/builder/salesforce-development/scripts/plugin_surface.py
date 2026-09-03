#!/usr/bin/env python3
"""Pure, stdlib-only bounded-bullet rendering used by the discovery surfaces.

Why this module exists
----------------------
The discovery surfaces paint plugin recommendation / pointer bullets that must
never exceed the plugin's self-imposed 80-terminal-cell frame. This module is
the single rendering policy for those bullets: ``sf_context.py`` imports
``fit_bullet_line`` for the prompt, welcome, and SessionStart recommendation
surfaces so the width math lives in one place instead of being kept "in sync by
hand" across call sites -- which had drifted: a ``max(28, ...)`` blurb floor that
overflowed the frame on long plugin names, and command lines with no width
budget at all (remediation plan A3).

Historically a second runtime -- the standalone ``session_plugin_hint.py``
SessionStart hook -- also painted these bullets and deliberately did NOT import
the ~11k-line ``sf_context.py`` (fast session start), which is why the shared
policy was extracted into a small stdlib-only module. That hook has since been
folded into ``sf_context`` (the SessionStart banner emits the recommendation
in-process, in ``_session_start_plugin_slot``), so ``sf_context`` is now the
only importer. The module is kept separate to avoid churning a large in-flight
file and because its cell-measurement copy is independently parity-tested.

The duplication decision (Track A, 2026-08-30)
----------------------------------------------
A3 prefers *extracting* the width primitives so there is one physical source of
truth. In this tree the leaf ``_ansi_sequence_end`` is shared between
``sf_context._sanitize_dynamic_text`` and its grapheme stack, so physically
moving the primitives out would entangle the sanitizer and churn a large file
that already carries in-flight work. Per the plan's sanctioned fallback
("duplicate only the minimal adapter and add parity tests"), this module carries
a self-contained COPY of the conservative cell-measurement approximation, and
``test_plugin_surface.py`` asserts parity with ``sf_context._terminal_cell_width``
/ ``_clip_cells`` / ``_wrap_cells`` over a Unicode fixture set. If they ever
diverge, that test fails. The copied logic is intentionally identical to
sf_context's; keep them in step (or, in Track B, collapse both onto this module).

This module sanitizes NOTHING. Callers pass already-sanitized text -- every
sf_context surface runs dynamic values through ``_sanitize_dynamic_text`` before
rendering. This module only measures, clips, wraps, and fits.
"""
from __future__ import annotations

import unicodedata
from typing import Optional

# --- Conservative cell measurement -------------------------------------------
# COPY of sf_context's grapheme stack; see the module docstring. Parity is
# guarded by test_plugin_surface.py, not by shared imports.
#
# These two joiners are spelled via chr() rather than as literal characters so
# the source stays all-visible ASCII: a literal ZWJ/VS16 is invisible in an
# editor and a review diff, and an editor normalization pass could silently drop
# one -- unacceptable in the primitive the whole 80-cell contract rests on.
_ZWJ = chr(0x200D)  # zero-width joiner (emoji sequence glue)
_VS16 = chr(0xFE0F)  # variation selector-16 (forces emoji presentation)


def _ansi_sequence_end(value: str, start: int) -> int:
    """Return the end of an ANSI/ECMA-48 sequence beginning at ``start``.

    Unterminated control strings consume the remainder, so truncated payloads can
    never leak into a measured/clipped line.
    """
    size = len(value)
    introducer = value[start]
    pos = start + 1
    kind = value[pos] if introducer == "\x1b" and pos < size else introducer
    if introducer == "\x1b" and pos < size:
        pos += 1
    if kind in ("[", "\x9b"):  # CSI: parameters/intermediates, then final byte
        while pos < size:
            if "@" <= value[pos] <= "~":
                return pos + 1
            pos += 1
        return size
    if kind in ("]", "P", "X", "^", "_", "\x90", "\x98", "\x9d", "\x9e", "\x9f"):
        while pos < size:
            if value[pos] in ("\x07", "\x9c"):
                return pos + 1
            if value[pos] == "\x1b" and pos + 1 < size and value[pos + 1] == "\\":
                return pos + 2
            pos += 1
        return size
    pos = start + 1
    while pos < size and " " <= value[pos] <= "/":
        pos += 1
    return min(size, pos + 1)


def _is_cluster_extender(ch: str) -> bool:
    codepoint = ord(ch)
    return (
        unicodedata.combining(ch) != 0
        or unicodedata.category(ch) in ("Mn", "Me")
        or ch == _ZWJ
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0xE0100 <= codepoint <= 0xE01EF
        or 0x1F3FB <= codepoint <= 0x1F3FF
    )


def _is_emoji_like(ch: str) -> bool:
    codepoint = ord(ch)
    return 0x1F000 <= codepoint <= 0x1FAFF


def _codepoint_cells(ch: str) -> int:
    if ch == _ZWJ or _is_cluster_extender(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F") or _is_emoji_like(ch):
        return 2
    return 1


def _grapheme_clusters(value: str):
    """Yield conservative display clusters using only :mod:`unicodedata`.

    Keeps combining/variation/modifier tails, emoji ZWJ sequences, and
    regional-indicator pairs together. ANSI sequences are yielded atomically with
    zero cells. Orphan extenders are dropped so clipping cannot create a dangling
    mark or joiner.
    """
    pos = 0
    while pos < len(value):
        ch = value[pos]
        if ch == "\x1b" or ch in ("\x90", "\x98", "\x9b", "\x9d", "\x9e", "\x9f"):
            end = _ansi_sequence_end(value, pos)
            yield value[pos:end], 0
            pos = end
            continue
        if _is_cluster_extender(ch):
            pos += 1
            continue
        cluster = ch
        width = _codepoint_cells(ch)
        pos += 1
        # A flag is one cluster/two cells, not two independent wide symbols.
        if 0x1F1E6 <= ord(ch) <= 0x1F1FF and pos < len(value) and 0x1F1E6 <= ord(value[pos]) <= 0x1F1FF:
            cluster += value[pos]
            pos += 1
        while pos < len(value):
            nxt = value[pos]
            if nxt == _ZWJ:
                if pos + 1 >= len(value) or _is_cluster_extender(value[pos + 1]):
                    pos += 1
                    break
                cluster += nxt + value[pos + 1]
                width = max(width, _codepoint_cells(value[pos + 1]))
                pos += 2
                continue
            if _is_cluster_extender(nxt):
                cluster += nxt
                if nxt == _VS16:  # explicit emoji presentation
                    width = max(width, 2)
                pos += 1
                continue
            break
        yield cluster, width


def cell_width(value: str) -> int:
    """Visible terminal cells for the documented conservative approximation.

    Mirror of ``sf_context._terminal_cell_width`` (parity-tested)."""
    return sum(width for _, width in _grapheme_clusters(value))


def clip_cells(text: str, limit: int) -> str:
    """Clip already-sanitized ``text`` to ``limit`` cells, ellipsis if truncated.

    Pure counterpart of ``sf_context._clip_cells`` minus the sanitize step -- the
    caller has already sanitized. Never splits a grapheme cluster."""
    if limit <= 0:
        return ""
    if cell_width(text) <= limit:
        return text
    budget = max(0, limit - 1)
    out: list[str] = []
    used = 0
    for cluster, width in _grapheme_clusters(text):
        if used + width > budget:
            break
        out.append(cluster)
        used += width
    return "".join(out) + "…"


def wrap_cells(text: str, width: int) -> list[str]:
    """Wrap already-sanitized ``text`` at spaces/cell boundaries without splitting
    clusters. Pure counterpart of ``sf_context._wrap_cells`` minus the sanitize
    step. Always returns at least one (possibly empty) line."""
    text = (text or "").strip()
    if not text:
        return [""]
    lines: list[str] = []
    while cell_width(text) > width:
        clusters = list(_grapheme_clusters(text))
        used = 0
        cut = 0
        space_cut = 0
        for index, (cluster, cells) in enumerate(clusters):
            if used + cells > width:
                break
            used += cells
            cut = index + 1
            if cluster.isspace():
                space_cut = cut
        if cut == 0:  # Defensive only: width is positive on all callers.
            cut = 1
        split = space_cut or cut
        lines.append("".join(cluster for cluster, _ in clusters[:split]).rstrip())
        text = "".join(cluster for cluster, _ in clusters[split:]).lstrip()
    lines.append(text)
    return lines


# --- The one bullet-fitting policy -------------------------------------------


def fit_bullet_line(
    *,
    lead: str,
    name: str,
    detail: str = "",
    separator: str = " ",
    width: int = 80,
    detail_mode: str = "wrap",
    continuation_indent: Optional[str] = None,
) -> list[str]:
    """Render one bullet as 1+ visible lines, each ``<= width`` terminal cells.

    ``name`` is protected: it is ellipsis-clipped only as a last resort, when even
    ``lead + name`` alone exceeds ``width``. ``detail`` is sacrificial:

    - ``detail_mode="clip"`` keeps a single-line bullet, ellipsis-clipping the
      detail into whatever space remains after ``lead + name + separator`` (the
      recommendation blurb -- a display-only lead clause).
    - ``detail_mode="wrap"`` places the detail onto bounded continuation lines
      when it does not fit inline, indented to ``continuation_indent`` (defaults
      to the lead width). Nothing is ellipsis-clipped, so a runnable command wraps
      intact rather than being truncated (e.g. the resume pointer's slash command).

    Callers keep the full untruncated name/detail in model context; every line
    returned here is display text only. Inputs must already be sanitized.
    """
    if width <= 0:
        return []
    lead_w = cell_width(lead)
    # Protected name: clip only when even lead+name overflows the frame.
    if lead_w + cell_width(name) <= width:
        name_shown = name
        name_clipped = False
    else:
        name_shown = clip_cells(name, max(0, width - lead_w))
        name_clipped = True
    line1 = lead + name_shown

    detail = detail or ""
    if not detail:
        return [line1]

    # Inline only when the name survived whole AND the full line still fits.
    if (not name_clipped
            and cell_width(line1) + cell_width(separator) + cell_width(detail) <= width):
        return [line1 + separator + detail]

    if detail_mode == "clip":
        # A clipped name has already consumed the whole line; drop the detail.
        if name_clipped:
            return [line1]
        remaining = width - cell_width(line1) - cell_width(separator)
        if remaining <= 0:
            return [line1]
        shown = clip_cells(detail, remaining)
        return [line1 + separator + shown] if shown else [line1]

    # detail_mode == "wrap": detail spills onto bounded continuation lines.
    indent = continuation_indent if continuation_indent is not None else " " * lead_w
    avail = width - cell_width(indent)
    if avail <= 0:
        avail = 1
    return [line1] + [indent + segment for segment in wrap_cells(detail, avail)]

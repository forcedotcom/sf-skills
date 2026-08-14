#!/usr/bin/env python3
"""WCAG 2.2 SC 1.4.3 / 1.4.11 contrast-ratio calculator.

Computes the exact WCAG contrast ratio between a foreground and a background
color so the accessibility reviewer never has to approximate relative luminance
by hand (which is unreliable and has produced inconsistent findings). The
reviewer resolves the two colors from the component's HTML/CSS, then invokes
this script; the printed verdict is authoritative.

Usage:
  contrast-ratio.py FOREGROUND BACKGROUND [--large] [--json]

Arguments:
  FOREGROUND   Text color. Accepts #RGB, #RRGGBB, rgb(r,g,b) or rgba(r,g,b,a).
  BACKGROUND   Background color. Must be opaque (#RGB/#RRGGBB/rgb()); used as
               the compositing base when FOREGROUND carries an alpha channel.

Options:
  --large      Classify the text as large-scale (>=24px, or >=18.66px bold),
               which uses the 3:1 threshold instead of 4.5:1 for the primary
               PASS/FAIL. Both thresholds are always reported regardless.
  --json       Emit a machine-readable JSON object instead of the text report.

Exit codes:
  0  Ratio meets the applicable threshold (PASS)
  1  Ratio is below the applicable threshold (FAIL)
  2  Argument / parse error
"""

import argparse
import json
import re
import sys

_STANDARD_THRESHOLD = 4.5
_LARGE_THRESHOLD = 3.0


def _parse_color(value):
    """Return (r, g, b, a) with channels in 0-255 and alpha in 0.0-1.0."""
    s = value.strip()

    m = re.fullmatch(r"#([0-9a-fA-F]{3})", s)
    if m:
        r, g, b = (int(c * 2, 16) for c in m.group(1))
        return r, g, b, 1.0

    m = re.fullmatch(r"#([0-9a-fA-F]{6})", s)
    if m:
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0

    m = re.fullmatch(
        r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)",
        s,
    )
    if m:
        r, g, b = (int(round(float(m.group(i)))) for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        for ch in (r, g, b):
            if not 0 <= ch <= 255:
                raise ValueError(f"channel out of range in '{value}'")
        if not 0.0 <= a <= 1.0:
            raise ValueError(f"alpha out of range in '{value}'")
        return r, g, b, a

    raise ValueError(
        f"unrecognized color '{value}' — use #RGB, #RRGGBB, rgb(), or rgba()"
    )


def _composite(fg, bg):
    """Alpha-composite fg over an opaque bg; return an opaque (r, g, b)."""
    fr, fgc, fb, fa = fg
    br, bgc, bb, _ = bg
    if fa >= 1.0:
        return fr, fgc, fb
    return (
        round(fr * fa + br * (1 - fa)),
        round(fgc * fa + bgc * (1 - fa)),
        round(fb * fa + bb * (1 - fa)),
    )


def _relative_luminance(rgb):
    """WCAG relative luminance for an opaque sRGB (r, g, b) triple."""
    def _lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground, background):
    """Exact WCAG contrast ratio between two color strings (>= 1.0)."""
    fg = _parse_color(foreground)
    bg = _parse_color(background)
    if bg[3] < 1.0:
        raise ValueError(
            f"background '{background}' is translucent — its rendered color "
            "depends on the layer beneath it and cannot be determined. Resolve "
            "the effective opaque background and pass that instead."
        )
    fg_rgb = _composite(fg, bg)
    l1 = _relative_luminance(fg_rgb)
    l2 = _relative_luminance(bg[:3])
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("foreground")
    parser.add_argument("background")
    parser.add_argument("--large", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        ratio = contrast_ratio(args.foreground, args.background)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    threshold = _LARGE_THRESHOLD if args.large else _STANDARD_THRESHOLD
    passes = ratio >= threshold
    result = {
        "foreground": args.foreground,
        "background": args.background,
        "ratio": round(ratio, 2),
        "textClass": "large" if args.large else "standard",
        "threshold": threshold,
        "passesStandard": ratio >= _STANDARD_THRESHOLD,
        "passesLarge": ratio >= _LARGE_THRESHOLD,
        "verdict": "PASS" if passes else "FAIL",
    }

    if args.as_json:
        print(json.dumps(result))
    else:
        print(
            f"{result['ratio']}:1  {result['verdict']} "
            f"({result['textClass']} text, threshold {threshold}:1)  |  "
            f"standard 4.5:1 {'pass' if result['passesStandard'] else 'fail'}, "
            f"large 3:1 {'pass' if result['passesLarge'] else 'fail'}"
        )

    return 0 if passes else 1


if __name__ == "__main__":
    sys.exit(main())

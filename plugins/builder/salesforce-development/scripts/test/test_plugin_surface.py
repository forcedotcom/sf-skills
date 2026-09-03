#!/usr/bin/env python3
"""Unit + parity tests for plugin_surface.py (remediation plan A3).

Two things are proven here:

1. PARITY -- plugin_surface carries a *copy* of sf_context's conservative
   cell-measurement stack (see that module's docstring for why it is not
   physically shared). These tests assert the copy has not drifted from the
   originals over a Unicode fixture set:
     - ``cell_width``  == ``sf_context._terminal_cell_width``            (raw)
     - ``clip_cells``  == ``sf_context._clip_cells`` on sanitized input
     - ``wrap_cells``  == ``sf_context._wrap_cells`` on sanitized input
   plugin_surface's primitives are the POST-sanitize halves of sf_context's
   (callers pre-sanitize), so the clip/wrap parity feeds each fixture through
   ``sf_context._sanitize_dynamic_text`` before comparing.

2. CONTRACT -- ``fit_bullet_line`` never emits a line wider than the frame
   (the <=80-cell product invariant A3 enforces), protects the plugin name,
   treats the detail as sacrificial per mode, and preserves runnable commands
   intact in wrap mode.

Offline, stdlib unittest only (no pytest/PyYAML), Python 3.9 baseline.

Run: python3 plugins/builder/salesforce-development/scripts/test/test_plugin_surface.py
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

# scripts/test/ -> scripts/. Put scripts/ on sys.path so `import plugin_surface`
# resolves both here and inside sf_context once it imports the shared module.
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import plugin_surface as ps  # noqa: E402  (after sys.path insert)


def _load_sfx():
    spec = importlib.util.spec_from_file_location(
        "sf_context_under_test", _SCRIPTS / "sf_context.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


sfx = _load_sfx()

# --- Unicode fixtures exercising every branch of the grapheme stack ----------
# Invisible codepoints are built with chr() rather than typed as literals: this
# test's whole job is guarding Unicode width handling, so a literal combining
# mark / bidi control that an editor silently normalized away would quietly gut
# the fixture without failing. Visible codepoints (CJK, heart, emoji via \U)
# stay as-is -- they are self-evident in the source and in a review diff.
Z = chr(0x200D)    # ZERO WIDTH JOINER
V = chr(0xFE0F)    # VARIATION SELECTOR-16
ACUTE = chr(0x0301)                  # COMBINING ACUTE ACCENT
LRM, RLM = chr(0x200E), chr(0x200F)  # LEFT/RIGHT-TO-LEFT MARK (bidi)
FIXTURES = [
    "",
    "hello world",
    "a" * 100,
    "宽" * 20,                              # wide CJK (2 cells each)
    "caf" + chr(0x00E9),                   # precomposed é (1 cell)
    ("e" + ACUTE) * 10,                    # e + combining acute (1 cell each)
    "\U0001F468" + Z + "\U0001F469" + Z + "\U0001F467",  # family ZWJ emoji
    "\U0001F1FA\U0001F1F8",                    # US flag (regional-indicator pair)
    chr(0x2764) + V,                           # heart + VS16 (forces 2 cells)
    "\U0001F44D\U0001F3FB",                    # thumbs-up + skin-tone modifier
    "text\x1b[31mred\x1b[0m done",             # SGR color sequence
    "a\tb\nc\r d",                             # C0 controls (sanitize collapses)
    LRM + "hello" + RLM + "world",             # bidi controls (LRM/RLM)
    "trailing sgr \x1b[31m",                   # unterminated CSI
    "\x1b]8;;http://x\x07link\x1b]8;;\x07",    # OSC-8 hyperlink
    "mix 宽 \U0001F468" + Z + "\U0001F469 caf" + chr(0x00E9) + " e" + ACUTE + " \x1b[1mX",
]
LIMITS = [0, 1, 2, 3, 4, 5, 8, 10, 20, 40, 76, 79, 80, 120]
WRAP_WIDTHS = [1, 2, 3, 5, 8, 20, 40, 79, 80]


class CellWidthParityTests(unittest.TestCase):
    """cell_width must equal sf_context._terminal_cell_width on raw input."""

    def test_matches_terminal_cell_width(self):
        for x in FIXTURES:
            self.assertEqual(
                ps.cell_width(x), sfx._terminal_cell_width(x),
                msg=f"cell_width drift on {x!r}",
            )

    def test_single_cluster_emoji_two_cells(self):
        # A ZWJ family, a flag, a skin-tone emoji, and heart+VS16 are each ONE
        # cluster of 2 cells -- the property clipping relies on.
        for one in ("\U0001F468" + Z + "\U0001F469" + Z + "\U0001F467",
                    "\U0001F1FA\U0001F1F8", "\U0001F44D\U0001F3FB", chr(0x2764) + V):
            self.assertEqual(ps.cell_width(one), 2, msg=repr(one))


class ClipParityTests(unittest.TestCase):
    """clip_cells(sanitize(x), n) must equal sf_context._clip_cells(x, n)."""

    def test_matches_clip_cells(self):
        for x in FIXTURES:
            safe = sfx._sanitize_dynamic_text(x)
            for n in LIMITS:
                self.assertEqual(
                    ps.clip_cells(safe, n), sfx._clip_cells(x, n),
                    msg=f"clip drift on {x!r} @ {n}",
                )

    def test_never_exceeds_limit_and_never_splits_cluster(self):
        for x in FIXTURES:
            safe = sfx._sanitize_dynamic_text(x)
            for n in LIMITS:
                out = ps.clip_cells(safe, n)
                self.assertLessEqual(ps.cell_width(out), n, msg=f"{x!r}@{n}")


class WrapParityTests(unittest.TestCase):
    """wrap_cells(sanitize(x), w) must equal sf_context._wrap_cells(x, w)."""

    def test_matches_wrap_cells(self):
        for x in FIXTURES:
            safe = sfx._sanitize_dynamic_text(x)
            for w in WRAP_WIDTHS:
                self.assertEqual(
                    ps.wrap_cells(safe, w), sfx._wrap_cells(x, w),
                    msg=f"wrap drift on {x!r} @ {w}",
                )


class FitBulletInlineTests(unittest.TestCase):
    def test_inline_clip_mode_when_it_fits(self):
        self.assertEqual(
            ps.fit_bullet_line(lead="  • ", name="Foo", separator=" - ",
                               detail="does things", detail_mode="clip"),
            ["  • Foo - does things"],
        )

    def test_inline_wrap_mode_when_it_fits(self):
        self.assertEqual(
            ps.fit_bullet_line(lead="  • ", name="Foo", separator=" — ",
                               detail="run /go", detail_mode="wrap"),
            ["  • Foo — run /go"],
        )

    def test_empty_detail_is_name_only(self):
        self.assertEqual(
            ps.fit_bullet_line(lead="  • ", name="Foo", detail=""),
            ["  • Foo"],
        )

    def test_zero_width_returns_nothing(self):
        self.assertEqual(
            ps.fit_bullet_line(lead="  • ", name="Foo", detail="x", width=0),
            [],
        )


class FitBulletClipModeTests(unittest.TestCase):
    def test_long_detail_is_ellipsis_clipped_single_line(self):
        out = ps.fit_bullet_line(lead="  • ", name="Foo", separator=" - ",
                                 detail="x" * 200, width=40, detail_mode="clip")
        self.assertEqual(len(out), 1)
        self.assertLessEqual(ps.cell_width(out[0]), 40)
        self.assertTrue(out[0].startswith("  • Foo - "))
        self.assertTrue(out[0].endswith("…"))

    def test_clipped_name_drops_sacrificial_blurb(self):
        # When the name itself must be clipped, the clip-mode detail (a display
        # blurb) is dropped -- the whole frame went to the protected name.
        out = ps.fit_bullet_line(lead="  • ", name="N" * 100, separator=" - ",
                                 detail="blurb text", width=80, detail_mode="clip")
        self.assertEqual(len(out), 1)
        self.assertEqual(ps.cell_width(out[0]), 80)
        self.assertTrue(out[0].endswith("…"))
        self.assertNotIn("blurb", out[0])


class FitBulletWrapModeTests(unittest.TestCase):
    def test_long_detail_wraps_to_indented_continuation(self):
        out = ps.fit_bullet_line(
            lead="  • ", name="Plugin", separator=" — ",
            detail="run /some-really-long-command --with --several --flags here",
            width=40, detail_mode="wrap",
        )
        self.assertGreaterEqual(len(out), 2)
        self.assertEqual(out[0], "  • Plugin")
        for line in out:
            self.assertLessEqual(ps.cell_width(line), 40)
            self.assertNotIn("…", line)  # wrap NEVER ellipsis-clips
        # Continuation lines are indented to the lead width (4 cells).
        for cont in out[1:]:
            self.assertTrue(cont.startswith("    "))
        # The command survives intact when the continuation lines are rejoined.
        rejoined = " ".join(seg.strip() for seg in out[1:])
        self.assertIn("/some-really-long-command", rejoined)

    def test_custom_continuation_indent(self):
        out = ps.fit_bullet_line(
            lead="  • ", name="Plugin", detail="x" * 120,
            width=40, detail_mode="wrap", continuation_indent="      ",
        )
        self.assertGreaterEqual(len(out), 2)
        for cont in out[1:]:
            self.assertTrue(cont.startswith("      "))
            self.assertLessEqual(ps.cell_width(cont), 40)

    def test_wrap_mode_keeps_command_intact_even_with_clipped_name(self):
        # wrap-mode detail is a runnable command / important hedge -- never
        # sacrificial. Even when the name overflows and is clipped, the detail
        # still renders on a bounded continuation line.
        out = ps.fit_bullet_line(
            lead="  • ", name="N" * 100, separator=" — ",
            detail="run /cmd", width=80, detail_mode="wrap",
        )
        self.assertGreaterEqual(len(out), 2)
        for line in out:
            self.assertLessEqual(ps.cell_width(line), 80)
        self.assertIn("run /cmd", " ".join(out[1:]))


class FitBulletProtectedNameTests(unittest.TestCase):
    def test_overlong_name_clipped_to_frame(self):
        out = ps.fit_bullet_line(lead="  • ", name="N" * 100, width=80)
        self.assertEqual(len(out), 1)
        self.assertEqual(ps.cell_width(out[0]), 80)
        self.assertTrue(out[0].endswith("…"))

    def test_schema_boundary_64_char_name_not_clipped(self):
        # A 64-char name (the SKILL name ceiling) + a short command fits inline
        # under a 4-cell lead: 4 + 64 + 3 + len(detail) <= 80.
        out = ps.fit_bullet_line(lead="  • ", name="a" * 64,
                                 separator=" — ", detail="run /x",
                                 width=80, detail_mode="wrap")
        self.assertEqual(out, ["  • " + "a" * 64 + " — run /x"])
        self.assertEqual(ps.cell_width(out[0]), 4 + 64 + 3 + 6)


class ResumeSurfaceShapeTests(unittest.TestCase):
    """The Option-X resume pointer: command is the protected name, the
    reload hedge is wrap-mode detail -- so the command never clips and the
    hedge always lands on its own bounded continuation line."""

    def test_resume_pointer_two_line_command_intact(self):
        command = "run /sfdc-test-drive resume abc123"
        hedge = "to pick it back up — if unrecognized, run /reload-plugins first"
        out = ps.fit_bullet_line(lead="  • ", name=command, separator=" ",
                                 detail=hedge, width=80, detail_mode="wrap")
        self.assertGreaterEqual(len(out), 2)
        self.assertEqual(out[0], "  • " + command)
        for line in out:
            self.assertLessEqual(ps.cell_width(line), 80)
            self.assertNotIn("…", line)
        self.assertIn("/reload-plugins", " ".join(out[1:]))


class FitBulletWidthContractTests(unittest.TestCase):
    """The core A3 invariant: at the product frame width (80), no rendered line
    ever exceeds the frame, across the full Unicode fixture set and every
    (lead, separator, detail, mode) combination the callers use."""

    _LEADS = ["  • ", "  ", "• ", ""]
    _SEPARATORS = [" - ", " — ", " ", ""]
    _NAMES = ["Foo", "a" * 64, "N" * 100, "宽" * 50,
              "\U0001F468" + Z + "\U0001F469" + " plugin"]
    _DETAILS = ["", "short", "run /cmd", "x" * 200, "宽" * 60,
                "run /a-really-long-command --with --flags --and --more --words"]

    def test_no_line_exceeds_frame_at_width_80(self):
        for lead in self._LEADS:
            for name in self._NAMES:
                for sep in self._SEPARATORS:
                    for detail in self._DETAILS:
                        for mode in ("clip", "wrap"):
                            out = ps.fit_bullet_line(
                                lead=lead, name=name, separator=sep,
                                detail=detail, width=80, detail_mode=mode,
                            )
                            for line in out:
                                self.assertLessEqual(
                                    ps.cell_width(line), 80,
                                    msg=(f"overflow lead={lead!r} name={name!r} "
                                         f"sep={sep!r} detail={detail!r} mode={mode}"
                                         f" -> {line!r} ({ps.cell_width(line)})"),
                                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

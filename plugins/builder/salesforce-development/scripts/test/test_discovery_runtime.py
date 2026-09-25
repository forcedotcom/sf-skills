#!/usr/bin/env python3
"""Offline runtime and SessionStart tests for capability discovery."""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module, strip_ansi

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
SF_CONTEXT_PATH = SCRIPTS / "sf_context.py"
PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin/plugin.json"
PLUGIN_CATALOG_ARTIFACT = PLUGIN_ROOT / "catalog/plugins.json"
POINTER = 'Ask “what can I do here?” or run /salesforce-development:discover.'
# The visible SessionStart banner, the degraded banners, AND the readiness footer now
# all close with the shared "✳ New here?" wayfinding footer (_wayfinding_footer, unified
# with platform-environment-validate). DISCOVERY_POINTER (POINTER, above) is the plain
# one-liner that remains on the post-login wayfinder and the model-facing additionalContext
# note. On any visible banner the discovery command token appears exactly once — the
# "single pointer" invariant.
DISCOVERY_CMD = "/salesforce-development:discover"
TAGLINE = "headless Salesforce development, from inside the agent"

sfx = load_module(SF_CONTEXT_PATH, "discovery_runtime_context")
nr = load_module(SCRIPTS / "nudge_rules.py", "nudge_rules_for_discovery_runtime")


class DiscoveryRuntimeTests(unittest.TestCase):
    def test_sf_context_dispatches_discovery(self):
        with mock.patch.object(sfx, "cmd_discovery", return_value=0) as dispatch, \
                mock.patch.object(sfx.sys, "argv", ["sf-context", "discover", "overview", "--json"]):
            self.assertEqual(sfx.main(), 0)
        dispatch.assert_called_once_with(["overview", "--json"])

    def test_removed_skill_catalog_modes_return_usage_exit_2(self):
        # The retired per-skill catalog surfaces (domain/skill/index) no longer
        # dispatch anywhere; cmd_discovery rejects them — and any unknown mode —
        # with a usage error on stderr rather than silently rendering.
        for mode in (["domain", "platform"], ["skill", "platform-apex-generate"],
                     ["index"], ["bogus"]):
            with self.subTest(mode=mode):
                with redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(sfx.cmd_discovery(mode), 2)
                self.assertIn("Usage: sf-context discover", err.getvalue())

    def test_journey_and_where_both_resolve_to_the_journey_hints(self):
        cases = ((["journey"], []), (["journey", "--json"], ["--json"]),
                 (["where"], []), (["where", "--json"], ["--json"]))
        for args, forwarded in cases:
            with self.subTest(args=args):
                with mock.patch.object(sfx, "cmd_journey", return_value=0) as journey:
                    self.assertEqual(sfx.cmd_discovery(args), 0)
                journey.assert_called_once_with(forwarded)

    def test_feature_submode_is_explicitly_on_demand(self):
        with mock.patch.object(sfx, "cmd_features", return_value=0) as feature_probe:
            self.assertEqual(
                sfx.cmd_discovery(["features", "--target-org", "fixture", "--refresh", "--json"]),
                0,
            )
        feature_probe.assert_called_once_with(["--target-org", "fixture", "--refresh", "--json"])

        with mock.patch.object(sfx, "cmd_features") as feature_probe:
            self.assertEqual(sfx.cmd_discovery(["overview"]), 0)
        feature_probe.assert_not_called()

    def test_cmd_discovery_overview_is_org_neutral_and_never_reads_target_org(self):
        """Human and JSON overview use stable neutral org state without any CLI read."""
        outputs = {}
        for args in (["overview"], [], ["--json"], ["overview", "--json"]):
            with self.subTest(args=args), \
                    mock.patch.object(sfx, "get_target_org_detailed") as target_read, \
                    mock.patch.object(sfx, "run_result") as cli, \
                    redirect_stdout(io.StringIO()) as out:
                self.assertEqual(sfx.cmd_discovery(args), 0)
                outputs[tuple(args)] = out.getvalue()
            target_read.assert_not_called()
            cli.assert_not_called()
        self.assertEqual(outputs[("overview",)], outputs[()])
        self.assertEqual(outputs[("--json",)], outputs[("overview", "--json")])
        data = json.loads(outputs[("--json",)])
        self.assertEqual(data["orgPresence"], "unknown")
        self.assertIn("what you can do here", outputs[("overview",)])
        self.assertNotIn("No org connected", outputs[("overview",)])

    def test_overview_hook_paint_never_reads_target_org_or_invokes_cli(self):
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.object(sfx, "get_target_org_detailed") as target_read, \
                mock.patch.object(sfx, "run_result") as cli:
            block = sfx._render_overview_paint(Path(td))
        self.assertIsInstance(block, str)
        target_read.assert_not_called()
        cli.assert_not_called()


class BannerProvenanceTests(unittest.TestCase):
    """The SessionStart banner is one of the two pinned deterministic visuals.

    Its art and layout are golden; its identity facts are read from the checked
    artifacts, so every expected value here is derived from those artifacts in
    the test rather than restated as a literal that could drift.

    `_enabled_plugin_names` is patched to `None` (unknown) so the installed/
    available split is derived purely from the checked-in catalog's plugin
    names vs. this plugin's own name, independent of whatever
    `~/.claude/settings.json` happens to say on the machine running the test —
    the same fail-open "unknown" state `_plugin_catalog_match`'s own tests use.
    """

    def setUp(self):
        patch = mock.patch.object(sfx, "_enabled_plugin_names", return_value=None)
        patch.start()
        self.addCleanup(patch.stop)
        self.version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
        current_name = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["name"]
        plugins = json.loads(PLUGIN_CATALOG_ARTIFACT.read_text(encoding="utf-8"))["plugins"]
        self.installed = sum(1 for p in plugins if p["name"] == current_name)
        self.available = len(plugins) - self.installed

    def plugin_summary_text(self):
        # Slot 2 — the consolidated plugin summary (render_plugin_summary), no
        # longer part of the logo block. Green check on the installed count, the
        # muted "available to add" invitation below it.
        return (
            f"✓ {self.installed} plugin(s) installed\n"
            f"{self.available} Salesforce plugin(s) available to add"
        )

    def test_banner_block_is_headless_360_with_artifact_derived_identity(self):
        # Color is on by default; the colored logo is the dotted SALESFORCE art, so
        # the identity is carried by the letter-spaced wordmark + artifact version
        # below it (the FIGlet BANNER now rides only the plain path).
        block = strip_ansi(sfx.render_banner_block())
        self.assertIn(f"{sfx.BANNER_WORDMARK}   ·   v{self.version}", block)
        self.assertNotIn(sfx.BANNER, block)                                          # dotted art, not FIGlet
        self.assertIn(sfx.BANNER, strip_ansi(sfx.render_banner_block(color=False)))  # FIGlet on the plain path
        self.assertNotIn(TAGLINE, block)
        # The plugin counts moved OUT of the logo block into slot 2
        # (render_plugin_summary) — the block is now logo + version only.
        self.assertNotIn("plugin(s) installed", block)
        self.assertNotIn("available to add", block)
        self.assertNotIn("Salesforce DX", block)

    def test_plugin_summary_is_the_one_place_the_counts_read(self):
        # Slot 2 renders exactly the consolidated counts: a green-check installed
        # line and a muted available line, both artifact-derived. No skills /
        # commands / agents / MCP-server chrome survives anywhere.
        summary = strip_ansi("\n".join(sfx.render_plugin_summary(False)))
        self.assertEqual(summary, self.plugin_summary_text())
        for retired in ("skills installed", "commands", "agents", "MCP servers", "✓ Installed"):
            self.assertNotIn(retired, summary)

    def test_lockup_art_matches_the_designed_ansi_shadow_geometry(self):
        """The SALESFORCE mark is a 6-line, 81-column block wordmark — pin both.
        81 (not 80) because ANSI Shadow's "O" glyph is 9 cells wide; the word
        cannot be squeezed to 80 in this font without distorting a glyph."""
        art = sfx.BANNER.splitlines()
        self.assertEqual(len(art), 6)
        self.assertEqual({len(line) for line in art}, {81})
        # Block-drawn, not the pure-ASCII Slant mark it replaced. Every cell must
        # come from the single-width block/box set, or the mark stops aligning.
        self.assertEqual(set(sfx.BANNER) - {"\n"}, set(" █╗╔╝╚═║"))

    def test_banner_block_display_width_fits_eightyone_columns(self):
        # Width is a display constraint, so measure the visible text — SGR bytes
        # inflate len() well past the ceiling without adding a single column. The
        # SALESFORCE lockup is 81 cells wide; everything else in the block is ≤80.
        lines = strip_ansi(sfx.render_banner_block()).splitlines()
        self.assertTrue(all(len(line) <= 81 for line in lines), lines)

    def test_banner_block_is_colored_by_default_and_plain_under_no_color(self):
        # The gate is ON now: the SessionStart banner paints the dotted SALESFORCE
        # lockup — a 5-tone 16-color theme-adaptive ramp (gray → blue → bright-blue →
        # bright-cyan → bright-white, all ANSI palette indices — no truecolor '38;2',
        # no fixed 256-color '38;5' ramp) so it re-tunes with the host theme. NO_COLOR
        # forces it fully plain, and the plain path swaps in the ANSI-strippable FIGlet
        # BANNER (model-reproduced stdout callers pass color=False — see
        # render_banner_message).
        with mock.patch.dict(os.environ, {}, clear=True):
            block = sfx.render_banner_block()
        self.assertIn("\x1b[90m", block)                 # gray edge specks (theme palette)
        self.assertIn("\x1b[34m", block)                 # blue (theme palette)
        self.assertIn("\x1b[94m", block)                 # bright-blue letter bodies (theme palette)
        self.assertIn("\x1b[96m", block)                 # bright-cyan highlights (theme palette)
        self.assertIn("\x1b[97m", block)                 # bright-white cores (theme palette)
        self.assertNotIn("\x1b[38;2", block)             # no truecolor
        self.assertNotIn("\x1b[38;5;", block)            # no fixed 256-color ramp
        self.assertNotIn(sfx.BANNER, strip_ansi(block))  # dotted art, not the FIGlet block
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            plain = sfx.render_banner_block()
        self.assertNotIn("\x1b", plain)
        self.assertIn(sfx.BANNER, plain)                 # plain path keeps the FIGlet lockup

    def test_provenance_fails_open_on_missing_and_damaged_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing"
            damaged = Path(td) / "damaged"
            damaged.joinpath(".claude-plugin").mkdir(parents=True)
            damaged.joinpath(".claude-plugin/plugin.json").write_text("{not json", encoding="utf-8")
            damaged.joinpath("catalog").mkdir()
            damaged.joinpath("catalog/plugins.json").write_text(
                '{"plugins": "not-a-list"}', encoding="utf-8"
            )
            for root in (missing, damaged):
                with self.subTest(root=root.name):
                    facts = sfx._banner_provenance(root)
                    self.assertEqual(facts["version"], "?")
                    self.assertIsNone(facts["installedPlugins"])
                    self.assertIsNone(facts["availablePlugins"])
                    # The counts live in slot 2 now; with both facts unknown the
                    # summary drops entirely (fail-open, never a fabricated zero).
                    self.assertEqual(sfx.render_plugin_summary(False, root, facts=facts), [])
                    block = strip_ansi(sfx.render_banner_block(root))
                    self.assertIn(sfx.BANNER_WORDMARK, block)   # dotted logo present on the color path
                    self.assertIn("v?", block)
                    self.assertNotIn(TAGLINE, block)
                    self.assertNotIn("installed", block)

    def test_banner_stays_within_eighty_columns_on_absurd_artifact_values(self):
        """The ≤80 lockup is a contract, so catalog-derived counts it interpolates are bounded."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath(".claude-plugin").mkdir()
            root.joinpath(".claude-plugin/plugin.json").write_text(
                json.dumps({"version": "9." + "9" * 200, "name": "x"}), encoding="utf-8"
            )
            stub = types.SimpleNamespace(
                load_catalog=lambda _root: {"plugins": [{"name": "shared"}] * 1_000_000}
            )
            with mock.patch.object(sfx, "_load_plugin_catalog_module", return_value=stub):
                block = strip_ansi(sfx.render_banner_block(root))
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in block.splitlines()), block)
        self.assertIn(sfx.BANNER_WORDMARK, block)

    def test_degraded_banner_carries_the_same_lockup_and_one_pointer(self):
        # New signature: the caller hands in the lean org line as a band-content
        # group (the same one cmd_detect builds for the no-target path).
        org_group = [[("org: ", "body"), ("none set — /salesforce-development:login", "muted")]]
        raw = sfx.render_degraded_banner(org_group)
        degraded = strip_ansi(raw)
        self.assertIn(sfx.BANNER_WORDMARK, degraded)   # dotted logo present on the color path
        self.assertNotIn(TAGLINE, degraded)
        # Slot 2 rides the degraded path too — a fact about the plugin, not the org.
        self.assertIn(self.plugin_summary_text(), degraded)
        # Closes with the shared wayfinding footer (single ✳ pointer). The old
        # "You don't memorize commands here." mindset line was dropped everywhere.
        self.assertNotIn("You don't memorize commands here.", degraded)
        self.assertEqual(degraded.count("/salesforce-development:discover"), 1)
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in degraded.splitlines()))


class EnvironmentBandTests(unittest.TestCase):
    """The rule-delimited status bands that replaced the titled boxes below the
    lockup. Every count is derived from the checked artifacts here rather than
    restated as a literal, and the band never fabricates an MCP health check."""

    def setUp(self):
        self.org = {
            "alias": "acme-dev", "edition": "Developer Edition (Sandbox)", "apiVersion": "63.0",
            "instanceUrl": "https://acme-dev.my.salesforce.com", "username": "jdoe@acme.example.com",
        }
        self.project = {"name": "acme-crm", "source_api": "63.0", "package_dirs": "force-app"}
        self.stats = {"apex_src": 12, "apex_test": 8, "triggers": 3, "lwc": 5,
                      "aura": 0, "objects": 14, "permsets": 2, "flows": 6}

    def message(self, **org_overrides):
        org = {**self.org, **org_overrides}
        return strip_ansi(sfx.render_banner_message(org, self.project, self.stats, "4 file(s) changed", "connecting"))

    def test_plugin_summary_counts_are_artifact_derived(self):
        # Slot 2 shows PLUGIN counts (installed vs available to add), derived from
        # the catalog + this plugin's name — never the retired skills/commands/
        # agents/MCP-server inventory. Pin the enabled set to unknown so the split
        # is derived purely from the checked artifacts (hermetic).
        current_name = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["name"]
        plugins = json.loads(PLUGIN_CATALOG_ARTIFACT.read_text(encoding="utf-8"))["plugins"]
        installed = sum(1 for p in plugins if p["name"] == current_name)
        available = len(plugins) - installed
        with mock.patch.object(sfx, "_enabled_plugin_names", return_value=None):
            msg = self.message()
        self.assertIn(f"✓ {installed} plugin(s) installed", msg)
        self.assertIn(f"{available} Salesforce plugin(s) available to add", msg)
        for retired in ("✓ Installed salesforce-development", "skills installed", "MCP servers"):
            self.assertNotIn(retired, msg)

    def test_plugin_summary_fails_open_on_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # No artifacts → both counts unknown → the summary drops entirely
            # (fail-open, never a fabricated zero).
            self.assertEqual(sfx.render_plugin_summary(False, root), [])

    def test_plugin_summary_lines_fail_open_independently(self):
        # version and the plugin counts are separate reads in _banner_provenance
        # (separate try blocks) — one failing must not drag the other down. And
        # render_plugin_summary drops each line on its OWN missing fact.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath(".claude-plugin").mkdir()
            root.joinpath(".claude-plugin/plugin.json").write_text(
                json.dumps({"name": "salesforce-development", "version": "1.9.0"}),
                encoding="utf-8",
            )
            stub = types.SimpleNamespace(
                load_catalog=lambda _root: {
                    "plugins": [{"name": "salesforce-development"}, {"name": "other"}]
                }
            )
            with mock.patch.object(sfx, "_load_plugin_catalog_module", return_value=stub), \
                 mock.patch.object(sfx, "_enabled_plugin_names", return_value=None):
                # Good manifest + good catalog: real version and real counts.
                facts = sfx._banner_provenance(root)
                self.assertEqual(facts["version"], "1.9.0")
                self.assertEqual(facts["installedPlugins"], 1)
                self.assertEqual(facts["availablePlugins"], 1)
                summary = strip_ansi("\n".join(sfx.render_plugin_summary(False, root, facts=facts)))
                self.assertIn("✓ 1 plugin(s) installed", summary)
                self.assertIn("1 Salesforce plugin(s) available to add", summary)

                # Catalog malformed: version survives, both counts fail open, and
                # BOTH summary lines drop.
                stub.load_catalog = lambda _root: {"plugins": "not-a-list"}
                facts = sfx._banner_provenance(root)
                self.assertEqual(facts["version"], "1.9.0")
                self.assertIsNone(facts["installedPlugins"])
                self.assertIsNone(facts["availablePlugins"])
                self.assertEqual(sfx.render_plugin_summary(False, root, facts=facts), [])

        # The renderer drops each line on its own missing fact (defensive — it
        # must not assume _banner_provenance always sets the pair together).
        only_installed = sfx.render_plugin_summary(
            False, facts={"installedPlugins": 3, "availablePlugins": None})
        self.assertEqual(strip_ansi("\n".join(only_installed)), "✓ 3 plugin(s) installed")
        only_available = sfx.render_plugin_summary(
            False, facts={"installedPlugins": None, "availablePlugins": 5})
        self.assertEqual(strip_ansi("\n".join(only_available)),
                         "5 Salesforce plugin(s) available to add")

    def test_environment_band_lists_real_servers_and_one_indicator(self):
        msg = self.message()
        for name in ("api-context", "metadata-experts"):
            self.assertIn(name, msg)
        self.assertNotIn("apex+soql-lsp", msg)        # the comp's relabel, not the configured id
        mcp_line = next(l for l in msg.splitlines() if l.startswith("MCP:"))
        # WIN-033/040: the health line lists ONLY the two platform servers the single
        # glyph actually reflects. salesforce-lsp is a local stdio process (not
        # org-gated, never remotely probed), so it is excluded — listing it beside a
        # glyph that never covers it would mislead. See CONTRACT-mcp-health.md.
        self.assertNotIn("lsp", mcp_line)
        indicators = sum(mcp_line.count(s) for s in ("⟳ connecting", "✓ connected", "✗ unavailable", "⚠ partial"))
        self.assertEqual(indicators, 1)               # one tri-state indicator, never per-server
        self.assertNotRegex(mcp_line, r"(api-context|metadata-experts)\s+✓")

    def test_stale_auth_shows_warning_not_check(self):
        band = strip_ansi("\n".join(sfx.render_environment_band(
            {"alias": "acme", "edition": "stale auth (re-login may be needed)", "apiVersion": "unknown"},
            "connecting", False)))
        org_line = next(l for l in band.splitlines() if l.startswith("org:"))
        self.assertIn("⚠", org_line)
        self.assertNotIn("✓", org_line)
        self.assertIn("stale auth", org_line)   # signal rides in the edition cell, not a wide glyph

    def test_org_line_within_eighty_when_stale_auth_and_alias_maxed(self):
        # A stale-auth ⚠ must cost the same column budget as the ✓ glyph; a wider
        # inline "⚠ stale auth" pushed a maxed alias + edition to 87 columns.
        msg = self.message(alias="Z" * 300, edition="stale auth " + "E" * 300,
                           apiVersion="9" * 300, instanceUrl="", username="")
        org_line = next(l for l in msg.splitlines() if l.startswith("org:"))
        self.assertIn("⚠", org_line)             # the stale path is exercised
        self.assertIn("stale auth", org_line)     # and the signal survives in the edition cell
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in msg.splitlines()), msg)

    def test_detail_line_omitted_when_org_lacks_instance_and_username(self):
        band = strip_ansi("\n".join(sfx.render_environment_band(
            {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}, "connecting", False)))
        self.assertNotIn("https://", band)
        self.assertNotIn("@", band)

    def test_bands_stay_within_eighty_on_absurd_values(self):
        msg = self.message(alias="Z" * 300, edition="E" * 300,
                           instanceUrl="https://" + "x" * 300, username="u" * 300)
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in msg.splitlines()), msg)

    def test_message_uses_rules_not_boxes(self):
        msg = self.message()
        self.assertIn("─" * 64, msg)
        for box_glyph in ("╭", "╰", "│"):
            self.assertNotIn(box_glyph, msg)

    def test_invitation_is_a_single_pointer_without_the_mindset_line(self):
        # The closing invitation is exactly the ✳ discovery pointer. The old
        # "You don't memorize commands here." mindset line was dropped everywhere,
        # and the counts are not restated here (they read once in slot 2).
        msg = self.message()
        self.assertNotIn("You don't memorize commands here.", msg)   # mindset line gone
        self.assertIn('✳ New here? ask "what can I do here?" or run /salesforce-development:discover overview.', msg)
        self.assertEqual(msg.count(DISCOVERY_CMD), 1)   # exactly one discovery pointer
        self.assertNotIn("in the library", msg)   # no third printing of the counts

    def test_adjacent_bands_share_one_rule_not_a_doubled_rule(self):
        # Environment + project render as one region sharing a middle divider:
        # three rules (top, shared, bottom), never four with a blank between.
        lines = self.message().splitlines()
        rule = "─" * 64
        self.assertEqual(lines.count(rule), 3)
        for i in range(1, len(lines) - 1):
            if lines[i] == "":
                self.assertFalse(lines[i - 1] == rule and lines[i + 1] == rule)

    def test_bands_are_colored_by_default_and_plain_under_no_color(self):
        # The gate is ON: the default render paints the bands with the theme palette
        # (no truecolor); NO_COLOR forces plain. (The model-reproduced /status path
        # passes color=False — see test_render_banner_message_forces_plain_when_color_false.)
        with mock.patch.dict(os.environ, {}, clear=True):
            colored = sfx.render_banner_message(self.org, self.project, self.stats, "", "connecting")
        self.assertIn("\x1b", colored)
        self.assertNotIn("\x1b[38;2", colored)
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            plain = sfx.render_banner_message(self.org, self.project, self.stats, "", "connecting")
        self.assertNotIn("\x1b", plain)
        # The colored logo is the dotted art; the plain logo is the FIGlet BANNER —
        # they intentionally differ now, so compare the shared region below the wordmark.
        self.assertEqual(strip_ansi(colored).split(sfx.BANNER_WORDMARK, 1)[1],
                         plain.split(sfx.BANNER_WORDMARK, 1)[1])

    def test_render_banner_message_forces_plain_when_color_false(self):
        # `/status` and `/welcome` print this banner to the model-reproduced stdout
        # pipe, where ANSI turns to escape-junk — so they pass color=False for a
        # fully plain lockup regardless of the NO_COLOR default. Only SGR differs
        # between the two, so the visible text is identical (strip == plain).
        with mock.patch.dict(os.environ, {}, clear=True):   # color is ON by default
            plain = sfx.render_banner_message(self.org, self.project, self.stats, "", "connecting", color=False)
            colored = sfx.render_banner_message(self.org, self.project, self.stats, "", "connecting", color=True)
        self.assertNotIn("\x1b", plain)
        self.assertIn("\x1b", colored)              # colored when asked...
        self.assertNotIn("\x1b[38;2", colored)      # ...16-color theme-adaptive lockup, not truecolor
        # Logos differ by path (dotted vs FIGlet); the region below the wordmark matches.
        self.assertEqual(strip_ansi(colored).split(sfx.BANNER_WORDMARK, 1)[1],
                         plain.split(sfx.BANNER_WORDMARK, 1)[1])

    def test_degraded_bands_keep_lockup_pointer_and_use_rules_not_boxes(self):
        # New signature: the caller hands in the lean org line as a band-content
        # group (the same shape cmd_detect builds for each non-probed state).
        for label, org_group in (
            ("no-org", [[("org: ", "body"),
                         ("none set — /salesforce-development:login", "muted")]]),
            ("unreachable", [[("org: ", "body"),
                              ("acme ✗ unreachable — sf org login web", "muted")]]),
        ):
            with self.subTest(case=label):
                d = strip_ansi(sfx.render_degraded_banner(
                    org_group, project=self.project, stats=self.stats))
                self.assertIn(sfx.BANNER_WORDMARK, d)   # dotted logo present on the color path
                self.assertIn("org:", d)
                # Single ✳ pointer; the old mindset line is gone everywhere.
                self.assertNotIn("You don't memorize commands here.", d)
                self.assertEqual(d.count("/salesforce-development:discover"), 1)
                self.assertIn("─" * 64, d)
                for box_glyph in ("╭", "╰", "│"):
                    self.assertNotIn(box_glyph, d)
                self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in d.splitlines()))

    def test_degraded_banner_shows_slot_two_but_not_retired_chrome(self):
        # Slot 2 rides the degraded path (it's a plugin fact, not an org fact),
        # but the retired install-summary chrome is gone everywhere.
        org_group = [[("org: ", "body"),
                      ("none set — /salesforce-development:login", "muted")]]
        with mock.patch.object(sfx, "_enabled_plugin_names", return_value=None):
            d = strip_ansi(sfx.render_degraded_banner(org_group))
        self.assertIn("plugin(s) installed", d)   # the consolidated summary is here
        self.assertNotIn("✓ Installed salesforce-development", d)
        self.assertNotIn("skills installed", d)
        self.assertNotIn("MCP servers", d)

    def test_project_row_leads_with_the_sfdx_project_label(self):
        # Mirror the org row's leading "org:" label: the project band leads with
        # "sfdx project:" then the name, in the connected banner and (below) the
        # degraded path. Both labels are lowercase with a trailing colon so the two
        # deterministic surfaces (banner + journey nudge) read identically.
        msg = self.message()
        self.assertIn("sfdx project: acme-crm", msg)
        self.assertIn("org: acme-dev", msg)

    def test_degraded_banner_carries_the_detected_project_context(self):
        # No org, but a project IS detected — surface where you are: the project
        # header rides below the org line sharing its divider (one region), so the
        # no-org session still names the project. The splash drops the code-inventory
        # rows and the git line (owner direction) — mid-dev-flow noise; the full
        # inventory lives on the on-demand /status surface instead.
        org_group = [[("org: ", "body"),
                      ("none set — /salesforce-development:login", "muted")]]
        d = strip_ansi(sfx.render_degraded_banner(
            org_group, project=self.project, stats=self.stats, git_line="4 file(s) changed"))
        self.assertIn("sfdx project: acme-crm", d)        # label precedes project name
        self.assertNotIn("Apex 12 src / 8 test", d)        # code inventory row dropped
        self.assertNotIn("4 file(s) changed", d)           # git line dropped
        self.assertEqual(d.splitlines().count("─" * 64), 3)   # shared divider, not doubled

    def test_degraded_banner_with_project_context_stays_within_eighty(self):
        # Project name/dirs/git can be untrusted or long — the band must still
        # clip to the ≤80 contract. The caller clips the lean org line (as cmd_detect
        # does); the project band clips its own rows.
        org_group = [[("org: ", "body"),
                      (sfx._clip("Z" * 300 + " — /salesforce-development:status", 73), "muted")]]
        d = strip_ansi(sfx.render_degraded_banner(
            org_group,
            project={"name": "Z" * 300, "source_api": "9" * 300, "package_dirs": "p" * 300},
            stats=self.stats, git_line="g" * 300))
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in d.splitlines()), d)

    def _notice(self):
        # The heading line marks the notice band; the rest is body/spacers.
        return ["Salesforce Development Plugin - Telemetry Usage", "",
                "anonymous usage data: the commands and skills run.", "",
                "To disable, run this command:",
                "  /salesforce-development:telemetry off"]

    def _org_group(self):
        # The lean no-org line the degraded surface now leads with (slot 3).
        return [[("org: ", "body"),
                 ("none set — /salesforce-development:login", "muted")]]

    def test_notice_band_leads_the_region_below_the_logo_above_the_guidance(self):
        # The telemetry notice is woven in as the FIRST band — after the logo
        # lockup, before the org guidance — sharing the region's dividers so it
        # never renders as a wider, separately-framed box below everything.
        d = strip_ansi(sfx.render_degraded_banner(
            self._org_group(), notice_lines=self._notice()))
        # The dotted logo carries no FIGlet first line on the color path; anchor on the
        # wordmark that closes the logo block instead — it still precedes the notice.
        self.assertLess(d.index(sfx.BANNER_WORDMARK), d.index("Telemetry Usage"))  # logo first
        self.assertLess(d.index("Telemetry Usage"), d.index("none set"))  # notice above the org line

    def test_notice_band_shares_rules_and_matches_band_width(self):
        # Woven in as a band, the notice shares the region's 64-col rules with the
        # neighbouring bands — no doubled rule, no box glyphs, same width as the
        # rest (the misaligned-box bug this replaced).
        rule = "─" * 64
        d = strip_ansi(sfx.render_degraded_banner(
            self._org_group(),
            project=self.project, stats=self.stats, git_line="4 file(s) changed",
            notice_lines=self._notice()))
        lines = d.splitlines()
        for box_glyph in ("╭", "╰", "│"):
            self.assertNotIn(box_glyph, d)
        for i in range(1, len(lines) - 1):          # never a blank sandwiched by two rules
            if lines[i] == "":
                self.assertFalse(lines[i - 1] == rule and lines[i + 1] == rule)
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in lines), d)

    def test_notice_band_clips_hostile_lines_within_eighty(self):
        # Notice text is a checked-in constant today, but the band must clip
        # defensively like every other so the ≤80 contract is structural.
        d = strip_ansi(sfx.render_degraded_banner(
            self._org_group(),
            notice_lines=["H" * 300, "", "b" * 300]))
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in d.splitlines()), d)

    def test_connected_banner_weaves_notice_between_install_and_environment(self):
        # On the connected path the notice sits below the install summary, above
        # the environment band — still the first status band, one shared region.
        org = {"alias": "acme", "edition": "Developer", "apiVersion": "63.0"}
        d = strip_ansi(sfx.render_banner_message(
            org, self.project, self.stats, "", "connecting", notice_lines=self._notice()))
        self.assertLess(d.index("plugin(s) installed"), d.index("Telemetry Usage"))
        self.assertLess(d.index("Telemetry Usage"), d.index("org: acme"))
        self.assertTrue(all(sfx._is_width_exempt(line) or len(line) <= 80 for line in d.splitlines()), d)

    def test_banner_without_notice_is_unchanged(self):
        # When no notice is due (notice_lines falsy), neither renderer inserts a
        # band — the default composition is byte-identical to the pre-notice one.
        org = {"alias": "acme", "edition": "Developer", "apiVersion": "63.0"}
        self.assertEqual(
            sfx.render_banner_message(org, self.project, self.stats, "", "connecting"),
            sfx.render_banner_message(org, self.project, self.stats, "", "connecting", notice_lines=[]))
        self.assertEqual(
            sfx.render_degraded_banner(self._org_group()),
            sfx.render_degraded_banner(self._org_group(), notice_lines=[]))

    def test_empty_nudge_renders_no_blank_slot(self):
        # The scaffold paint (and any non-probed startup) hands `render_degraded_banner`
        # a state but no resolved candidate — nothing cleared the nudge ladder. When the
        # nudge is empty, the composer must render NOTHING in its place, not a reserved
        # blank gap. Two proofs: (1) the state-but-no-candidate banner is byte-identical
        # to the no-state banner (the empty nudge adds no lines), and (2) no doubled
        # blank line survives anywhere the nudge slot used to reserve.
        org_group = self._org_group()
        with_state = sfx.render_degraded_banner(
            org_group, project=self.project, stats=self.stats, state={}, candidate=None)
        without_state = sfx.render_degraded_banner(
            org_group, project=self.project, stats=self.stats, state=None)
        self.assertEqual(with_state, without_state)
        lines = strip_ansi(with_state).splitlines()
        self.assertFalse(
            any(lines[i] == "" and lines[i + 1] == "" for i in range(len(lines) - 1)),
            with_state)

    def test_present_nudge_still_rides_below_the_bands(self):
        # The blank-slot fix must not swallow a real nudge: when a candidate IS
        # resolved, its two lines (band-labelled message + `→ action`) still render,
        # separated from the bands above by exactly one blank line.
        org_group = self._org_group()
        candidate = mock.Mock(message="Deploy your metadata", action="/salesforce-development:deploy")
        with mock.patch.object(sfx, "_nudge_band_prefix", return_value="🚀 "):
            d = strip_ansi(sfx.render_degraded_banner(
                org_group, project=self.project, stats=self.stats, state={}, candidate=candidate))
        self.assertIn("🚀 Deploy your metadata", d)
        self.assertIn("→ /salesforce-development:deploy", d)


class SessionStartNoticePlacementTests(unittest.TestCase):
    """The one-time telemetry notice, woven into cmd_detect's banner as the first
    band: user-visible only, above the org guidance, and fired exactly once.

    cmd_detect is local-first — it never probes the org at startup — so these
    exercise its two in-project banner paths ("No Default Org" and the configured-
    but-unprobed target). The notice rides the visible systemMessage only; the
    model-facing additionalContext is a separate structured object that never
    carries it. Machine-wide telemetry state (consent + notified marker) is
    redirected via SF_DEV_TELEMETRY_HOME into the tmp dir, so each test starts from
    a clean fire-once gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.cwd)
        self.cwd.joinpath("sfdx-project.json").write_text("{}")
        # The real fire-once gate is silent in CI and when opted out; clear those
        # signals so the end-to-end gate test can observe the notice actually fire.
        # Consent + the notified marker are MACHINE-WIDE now, so redirect the
        # telemetry home into this temp dir — otherwise the gate reads this machine's
        # real ~/.sf state and the "fires once" assertion is non-hermetic.
        self.env_patch = mock.patch.dict(os.environ, {
            "CI": "", "CONTINUOUS_INTEGRATION": "", "BUILD_NUMBER": "",
            "GITHUB_ACTIONS": "", "SF_DISABLE_TELEMETRY": "", "DO_NOT_TRACK": "",
            "SF_DEV_TELEMETRY_HOME": str(self.cwd / "machine-state"),
        }, clear=False)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def capture_detect(self):
        out = io.StringIO()
        payload = io.StringIO(json.dumps({"source": "startup"}))
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            sfx.cmd_detect()
        return json.loads(out.getvalue())

    def patches(self, target=""):
        # Local-first detect makes no org calls; only the local stats read is
        # pinned for a deterministic full-mode banner. `_configured_target_alias`
        # selects the no-org vs. configured-unprobed path.
        stack = ExitStack()
        for p in (
            mock.patch.object(sfx, "project_stats", return_value={"apex_src": 0, "apex_test": 0, "triggers": 0, "lwc": 0, "aura": 0, "objects": 0, "permsets": 0, "flows": 0}),
            mock.patch.object(sfx, "_configured_target_alias", return_value=target),
        ):
            stack.enter_context(p)
        return stack

    def cases(self):
        # The lean org line replaced the old titled degraded banners; anchor the
        # "notice above the org guidance" ordering on the org line's own text.
        return {
            "no-default-org": ("", "none set"),
            "configured-unprobed": ("fixture", "/salesforce-development:status"),
        }

    def test_notice_is_visible_only_above_guidance_and_fires_once(self):
        for label, (target, guide) in self.cases().items():
            with self.subTest(path=label):
                due = ["Salesforce Development Plugin - Telemetry Usage", "",
                       "anonymous usage data; disable via :telemetry off"]
                with self.patches(target):
                    with mock.patch.object(sfx, "_telemetry_notice_lines", return_value=due):
                        first = self.capture_detect()
                visible = strip_ansi(first["systemMessage"])
                context = first["hookSpecificOutput"]["additionalContext"]
                # Woven into the VISIBLE banner, above the org guidance…
                self.assertIn("Telemetry Usage", visible)
                self.assertLess(visible.index("Telemetry Usage"), visible.index(guide))
                self.assertLessEqual(visible.index(sfx.BANNER_WORDMARK), visible.index("Telemetry Usage"))
                # …and NEVER in the model-facing context.
                self.assertNotIn("Telemetry Usage", context)
                self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in visible.splitlines()), visible)

    def test_real_gate_fires_notice_once_then_never_again(self):
        # End-to-end through the real telemetry gate (no notice mock): the notice
        # paints on the first detect in a fresh project and is suppressed on the next.
        with self.patches():
            first = self.capture_detect()
            second = self.capture_detect()
        self.assertIn("Telemetry Usage", strip_ansi(first["systemMessage"]))
        self.assertNotIn("Telemetry Usage", strip_ansi(second["systemMessage"]))


class SessionStartPointerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.cwd)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def capture_detect(self, source="startup"):
        out = io.StringIO()
        payload = io.StringIO(json.dumps({"source": source}))
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            code = sfx.cmd_detect()
        return code, json.loads(out.getvalue())

    def assert_visible_pointer(self, result):
        self.assertEqual(result.get("systemMessage", "").count(DISCOVERY_CMD), 1)
        self.assertLessEqual(len(POINTER), 160)
        self.assertNotIn('"skills": [', result.get("systemMessage", ""))

    def make_project(self):
        self.cwd.joinpath("sfdx-project.json").write_text("{}")

    def normal_patches(self):
        return (
            mock.patch.object(sfx, "project_stats", return_value={"apex_src": 0, "apex_test": 0, "triggers": 0, "lwc": 0, "aura": 0, "objects": 0, "permsets": 0, "flows": 0}),
            mock.patch.object(sfx, "git_status_line", return_value=""),
        )

    def test_non_project_mentions_discovery_without_org_or_feature_probe(self):
        with mock.patch.object(sfx, "fetch_org_info_via_node") as org_probe, \
                mock.patch.object(sfx, "cmd_features") as feature_probe:
            _, result = self.capture_detect()
        self.assertIn(POINTER, result["hookSpecificOutput"]["additionalContext"])
        org_probe.assert_not_called()
        feature_probe.assert_not_called()

    def test_out_of_project_session_start_does_not_flip_welcome(self):
        # Invariant (owner directive): an out-of-project SessionStart emits a
        # model-facing note only and returns BEFORE any _record_welcomed, so the
        # welcome splash flag stays unset — leaving a later `sf project generate`
        # scaffold paint free to be the session's first visible surface. Only the
        # project-generate path may flip welcome outside the in-project surfaces.
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd  # no sfdx-project.json here → out of project
        try:
            payload = io.StringIO(json.dumps({"source": "startup", "session_id": "oop1"}))
            out = io.StringIO()
            with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
                sfx.cmd_detect()
            result = json.loads(out.getvalue())
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        self.assertNotIn("systemMessage", result)              # model-facing only, no paint
        self.assertFalse(sfx._welcomed_this_session("oop1"))   # welcome never flipped

    def test_connected_project_visible_pointer_without_feature_detector(self):
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org), \
                mock.patch.object(sfx, "cmd_features") as feature_detector:
            _, result = self.capture_detect()
        self.assert_visible_pointer(result)
        feature_detector.assert_not_called()

    def test_session_start_seeds_the_nudge_signature(self):
        # Generalized (journey-nudges Phase 4): SessionStart records a fingerprint
        # of the WINNING nudge candidate its banner reflected, so a routine connect
        # right after (no real change) de-dupes in the wayfinder instead of
        # repainting an identical nudge. Needs a session id (the marker key) and a
        # sandboxed marker dir.
        self.make_project()
        p1, p2 = self.normal_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            payload = io.StringIO(json.dumps({"source": "startup", "session_id": "seed1"}))
            out = io.StringIO()
            # SessionStart is local-first: seed its configured target directly
            # instead of mocking the retired live-org probe path.
            with p1, p2, \
                    mock.patch.object(sfx, "_configured_target_alias", return_value="fixture"), \
                    mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
                sfx.cmd_detect()
            seeded = sfx._last_nudge_signature("seed1")
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        self.assertIsNotNone(seeded)          # a signature was seeded
        self.assertNotEqual(seeded, "(none)")  # a real candidate fired, not the empty sentinel

    def test_visible_session_start_message_opens_with_the_banner_block(self):
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org):
            _, result = self.capture_detect()
        # Visible chrome stays on systemMessage; model context carries semantic facts only.
        block = sfx.render_banner_block()
        self.assertIn(block, result["systemMessage"])
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn(strip_ansi(block), context)
        self.assertNotIn("█", context)
        self.assertNotIn("●", context)
        self.assertNotIn("◉", context)
        self.assertNotIn("○", context)
        self.assertNotIn("\x1b", context)
        for fact in ("salesforce-development", "plugins:", "project:", "org:",
                     "current stage:", "reached:", "no evidence:", "next action:",
                     "Skills first", POINTER):
            self.assertIn(fact, context)
        self.assertLessEqual(len(context), 3000)
        self.assertTrue(all(len(line) <= 120 for line in context.splitlines()), context)
        self.assertFalse(any(ord(ch) < 32 and ch not in "\n\t" for ch in context))

    def test_session_start_banner_includes_the_nudge_line(self):
        # journey-nudges Phase 7/8: SessionStart shows "where you are" as the single
        # ladder-winning graded nudge, replacing the six-label glyph bar (and the
        # earlier "Reached:" word-list) entirely. This fixture has a configured target
        # and the project descriptor (Connect/Project reached) but zero local
        # source, so the empty-scaffold nudge is the ladder winner — a SEV_ROUTINE
        # momentum nudge, i.e. the 🚀 Try next band.
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org), \
                mock.patch.object(sfx, "_configured_target_alias", return_value="fixture"):
            _, result = self.capture_detect()
        visible = strip_ansi(result["systemMessage"])
        self.assertIn("🚀 Try next:", visible)
        self.assertIn("generate a component", visible)
        # The visible surface is the single nudge line only now — no "Reached:"
        # word-list, and the below-nudge state summary and the `likely next` line
        # moved to the model-facing context (asserted at 752).
        self.assertNotIn("Reached:", visible)
        self.assertNotIn("likely next", visible)
        self.assertNotIn("no evidence", visible)
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in visible.splitlines()))

    def test_no_default_org_visible_pointer(self):
        self.make_project()
        p1, p2 = self.normal_patches()
        with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=None), \
                mock.patch.object(sfx, "get_target_org", return_value=""):
            _, result = self.capture_detect()
        self.assert_visible_pointer(result)
        # The degraded banner is painted on the visible systemMessage, but the
        # model-facing additionalContext is stripped (_agent_context) — no escape
        # bytes as token cost. This path never had a plainness assertion.
        self.assertNotIn("\x1b", result["hookSpecificOutput"]["additionalContext"])

    def test_configured_org_is_visible_but_unprobed(self):
        self.make_project()
        p1, p2 = self.normal_patches()
        with p1, p2, mock.patch.object(sfx, "_configured_target_alias", return_value="fixture"):
            _, result = self.capture_detect()
        self.assert_visible_pointer(result)
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", context)
        self.assertIn("state=configured-unprobed", context)
        self.assertNotIn("state=unreachable", context)

    def test_orientation_rule_reaches_the_agent_on_every_session_start_path(self):
        """An orientation question must reach the nudge, not stop at the banner's facts.

        The banner states project and org state, which is a good enough answer for a
        model to stop at — measured: "where am I?" routed 0/4 without this rule. The
        two degraded paths never inject SKILLS_FIRST_DIRECTIVE, and they are exactly
        the states (no org / unreachable org) where the question gets asked, so the
        rule rides every agent-facing path. It is agent guidance, so it must stay OUT
        of the visible banner.
        """
        cases = {
            "configured": "fixture",
            "no-default-org": None,
        }
        for label, configured_target in cases.items():
            with self.subTest(path=label), ExitStack() as stack:
                self.make_project()
                for patch in self.normal_patches():
                    stack.enter_context(patch)
                stack.enter_context(mock.patch.object(
                    sfx, "_configured_target_alias", return_value=configured_target
                ))
                _, result = self.capture_detect()
                context = result["hookSpecificOutput"]["additionalContext"]
                self.assertIn(sfx.ORIENTATION_DIRECTIVE.strip(), context)
                self.assertIn("Skills first", context)
                self.assertLessEqual(len(context), 3000)
                expected_org = {
                    "configured": "org: configured=fixture; displayed=fixture; state=configured-unprobed",
                    "no-default-org": "org: configured=none; displayed=none; state=not-configured",
                }[label]
                self.assertIn(expected_org, context)
                self.assertNotIn("Orientation questions", result.get("systemMessage", ""))
                self.assertEqual(result.get("systemMessage", "").count(DISCOVERY_CMD), 1)

        with self.subTest(path="non-project"):
            self.cwd.joinpath("sfdx-project.json").unlink()
            _, result = self.capture_detect()
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn(sfx.ORIENTATION_DIRECTIVE.strip(), context)
            self.assertIn("Skills first", context)
            self.assertIn("project: absent", context)
            self.assertLessEqual(len(context), 3000)
            self.assertNotIn("systemMessage", result)

        with self.subTest(path="compact"):
            self.make_project()
            _, result = self.capture_detect("compact")
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn(sfx.ORIENTATION_DIRECTIVE.strip(), context)
            self.assertIn("Skills first", context)
            self.assertLessEqual(len(context), 1500)
            for decorative in ("█", "●", "◉", "○", "HEADLESS"):
                self.assertNotIn(decorative, context)
            self.assertNotIn("systemMessage", result)

    def test_orientation_rule_excludes_locator_questions(self):
        """"Where is the Account class?" is a normal task, not a journey question."""
        rule = sfx.ORIENTATION_DIRECTIVE
        for phrase in ("where am I", "what stage", "journey"):
            self.assertIn(phrase, rule)
        self.assertRegex(rule, r"(?i)where is the")
        self.assertRegex(rule, r"(?i)never answer those with the journey hints")
        self.assertLessEqual(len(rule.splitlines()), 24)

    def test_orientation_rule_requires_the_nudge_and_then_the_model_s_own_read(self):
        """The answer is both halves, in order: deterministic grounding, then relevance.

        The nudge alone is consistent but inert; prose alone is relevant but drifts
        run to run and hides the six-stage model. The contract is nudge first and
        unmodified, then the model's own short read of what it means here.
        """
        rule = sfx.ORIENTATION_DIRECTIVE
        self.assertRegex(rule, r"(?i)two parts")
        first, second = rule.index("1."), rule.index("2.")
        self.assertLess(first, second)
        self.assertRegex(rule[first:second], r"(?i)unmodified")
        # A tool result can be collapsed or absent from what the user reads, so the
        # nudge must be in the reply itself — measured: one run said "that's the
        # position nudge" and shipped an answer containing no nudge at all.
        self.assertRegex(rule[first:second], r"(?i)in your reply")
        self.assertRegex(rule[second:], r"(?i)never (restate|replace)")
        self.assertRegex(rule[second:], r"(?i)relevance|means for")

    def test_orientation_rule_defers_when_the_nudge_is_already_painted(self):
        """The paint hook shows the nudge in color; the directive must let the model
        skip reproducing it (else the plain reproduction double-prints the nudge)."""
        rule = sfx.ORIENTATION_DIRECTIVE
        self.assertRegex(rule, r"(?i)already\s+displayed the journey hints")   # may wrap
        self.assertRegex(rule, r"(?i)skip this step")
        self.assertLessEqual(len(rule.splitlines()), 24)   # shares the injected-context budget

    def test_compact_reinjects_pointer_without_visible_banner_or_probe(self):
        self.make_project()
        with mock.patch.object(sfx, "fetch_org_info_via_node") as org_probe, \
                mock.patch.object(sfx, "cmd_features") as feature_probe:
            _, result = self.capture_detect("compact")
        self.assertNotIn("systemMessage", result)
        self.assertIn(POINTER, result["hookSpecificOutput"]["additionalContext"])
        org_probe.assert_not_called()
        feature_probe.assert_not_called()

    def detect_with_session(self, session_id):
        """capture_detect, but carrying a session_id so the once-per-session markers
        are actually written (capture_detect sends no id, so they no-op there)."""
        out = io.StringIO()
        payload = io.StringIO(json.dumps({"source": "startup", "session_id": session_id}))
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            sfx.cmd_detect()
        return json.loads(out.getvalue())

    def test_in_project_session_start_records_both_welcomed_and_entered(self):
        # SessionStart paints the banner (logo + nudge), so it records BOTH markers:
        # `welcomed` (first orientation question won't re-show the logo) and `entered`
        # (first ordinary prompt won't repaint the nudge). Isolate markers in the cwd.
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        orig = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org):
                self.detect_with_session("sess-A")
            self.assertTrue(sfx._welcomed_this_session("sess-A"))
            self.assertTrue(sfx._entered_this_session("sess-A"))
            self.assertIsNotNone(sfx._last_nudge_signature("sess-A"))
        finally:
            sfx._WELCOME_MARKER_DIR = orig

    def test_session_start_emit_failure_commits_no_shown_state(self):
        self.make_project()
        p1, p2 = self.normal_patches()
        orig = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            payload = io.StringIO(json.dumps({
                "source": "startup", "session_id": "emit-failure",
            }))
            with p1, p2, \
                    mock.patch.object(sfx, "_configured_target_alias", return_value="fixture"), \
                    mock.patch.object(sfx, "emit", side_effect=RuntimeError("write failed")), \
                    mock.patch.object(sfx.sys, "stdin", payload):
                with self.assertRaisesRegex(RuntimeError, "write failed"):
                    sfx.cmd_detect()
            self.assertFalse(sfx._welcomed_this_session("emit-failure"))
            self.assertFalse(sfx._entered_this_session("emit-failure"))
            self.assertIsNone(sfx._last_nudge_signature("emit-failure"))
        finally:
            sfx._WELCOME_MARKER_DIR = orig

    def test_session_start_suppresses_the_duplicate_first_message_nudge(self):
        # After SessionStart paints the banner+nudge, the first ordinary in-project
        # prompt must NOT repaint the nudge as ambient orientation — that duplicate
        # also re-fetched the org. The `entered` marker set by SessionStart is what
        # suppresses it, before any org/journey work runs.
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        orig = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org):
                self.detect_with_session("sess-B")
            out = io.StringIO()
            prompt = io.StringIO(json.dumps({"prompt": "add a field to Account", "session_id": "sess-B"}))
            with mock.patch.object(sfx, "_journey_state") as js, \
                    mock.patch.object(sfx.sys, "stdin", prompt), \
                    mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
                sfx.cmd_orientation_paint()
            self.assertEqual(json.loads(out.getvalue()), {"continue": True})   # silent, no duplicate nudge
            js.assert_not_called()                                             # and no second org fetch
        finally:
            sfx._WELCOME_MARKER_DIR = orig


class NudgeAntiNagTests(unittest.TestCase):
    """Direct proofs of the journey-nudges Phase 4 anti-nag layer: the per-session
    ~3-distinct-key cap, the rung-1/blocking bypass of BOTH the cap and the
    wayfinder's fingerprint gate, and the fingerprint-changed-vs-unchanged
    re-render contract. These operate one layer below
    `_select_inline_nudge`'s callers (no real rendering surface involved) — a
    fake `nudge_rules` module (patched via `_load_nudge_rules`) controls exactly
    which candidate `select()` hands back, while `is_uncapped`/the cap
    primitives run for real."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.joinpath("sfdx-project.json").write_text("{}")
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.old_cwd)
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.root / "markers"

        def _restore():
            sfx._WELCOME_MARKER_DIR = orig_dir
        self.addCleanup(_restore)
        self.state = {"context": {}}

    def candidate(self, dedup_key, evidence_fp="v1", blocking=False):
        return types.SimpleNamespace(
            dedup_key=dedup_key, evidence_fp=evidence_fp,
            severity=(nr.SEV_BLOCKING if blocking else nr.SEV_ROUTINE),
            confidence=nr.CONFIDENCE_A,
        )

    def fake_rules(self, pick):
        # Only `select`/`is_uncapped`/`NudgeInputs` are ever touched by the code
        # path under test; `is_uncapped` delegates to the REAL predicate so its
        # rung-1 semantics stay honest even though `select` itself is scripted.
        return types.SimpleNamespace(
            select=lambda inputs: pick,
            is_uncapped=nr.is_uncapped,
            NudgeInputs=lambda **kw: types.SimpleNamespace(**kw),
        )

    def select_with(self, pick, session_id):
        with mock.patch.object(sfx, "_load_nudge_rules", return_value=self.fake_rules(pick)):
            return sfx._select_inline_nudge(
                self.state, self.root, None, session_id=session_id, probe_git=False,
            )

    def test_identical_candidate_on_a_repeat_prompt_does_not_rerender(self):
        c1 = self.candidate("build.empty-scaffold")
        sfx._record_nudge_shown("sess-1", c1)
        self.assertFalse(sfx._nudge_should_render("sess-1", c1))

    def test_evidence_fingerprint_change_triggers_a_rerender(self):
        c1 = self.candidate("build.empty-scaffold", evidence_fp="v1")
        sfx._record_nudge_shown("sess-1", c1)
        c1_changed = self.candidate("build.empty-scaffold", evidence_fp="v2")
        self.assertTrue(sfx._nudge_should_render("sess-1", c1_changed))

    def test_session_cap_degrades_a_fourth_distinct_key_to_none(self):
        session_id = "sess-cap"
        keys = ["connect.no-org", "project.no-git", "build.empty-scaffold"]
        for key in keys:
            sfx._record_nudge_shown(session_id, self.candidate(key))
        self.assertEqual(sorted(sfx._nudge_cap_keys(session_id)), sorted(keys))
        # A brand-new, non-blocking 4th key has no budget left: the ladder winner
        # degrades to None rather than earning a Next line.
        fourth = self.candidate("test.apex-no-tests")
        self.assertIsNone(self.select_with(fourth, session_id))
        # An already-capped key may still repeat — re-showing an in-budget nudge
        # is not a fresh nag.
        repeat = self.candidate("connect.no-org")
        self.assertEqual(self.select_with(repeat, session_id), repeat)

    def test_rung_one_blocking_candidate_bypasses_the_cap(self):
        session_id = "sess-blocker"
        for key in ("connect.no-org", "project.no-git", "build.empty-scaffold"):
            sfx._record_nudge_shown(session_id, self.candidate(key))
        blocker = self.candidate("connect.scratch-expired", blocking=True)
        # The cap is fully spent on three unrelated keys, yet the live blocker —
        # a brand-new fourth dedup_key — still renders: "a live fire always earns
        # its render" (journey-nudges Phase 4 design doc). (connect.scratch-expired,
        # not connect.unreachable — the latter was rebanded off the blocking rung.)
        self.assertEqual(self.select_with(blocker, session_id), blocker)
        # And it never spent a cap slot doing so.
        self.assertNotIn("connect.scratch-expired", sfx._nudge_cap_keys(session_id))

    def test_rung_one_blocker_respects_the_fingerprint_gate_but_never_starves_on_the_cap(self):
        # A rung-1 blocker gets exactly ONE bypass: the session cap, inside
        # `_select_inline_nudge` — it can never be starved by a full 3-key budget.
        # It does NOT also bypass `_nudge_should_render`'s fingerprint gate: an
        # unchanged fingerprint still suppresses a repeat render on the wayfinder,
        # same as any other candidate ("re-render only when the fingerprint
        # changes... never re-nags" — the design doc states this unconditionally;
        # "uncapped" is scoped to the cap bullet only). A blocker shows once per
        # state, not once per prompt.
        session_id = "sess-blocker-fp"
        for key in ("connect.no-org", "project.no-git", "build.empty-scaffold"):
            sfx._record_nudge_shown(session_id, self.candidate(key))
        blocker = self.candidate("connect.scratch-expired", evidence_fp="v1", blocking=True)
        # Cap is fully spent on three unrelated keys; the blocker still renders —
        # never starved — and never spends a cap slot doing so.
        self.assertEqual(self.select_with(blocker, session_id), blocker)
        self.assertNotIn("connect.scratch-expired", sfx._nudge_cap_keys(session_id))
        sfx._record_nudge_shown(session_id, blocker)
        # Same state, next prompt: the fingerprint is unchanged, so the gate
        # suppresses the repeat — no re-nag.
        self.assertFalse(sfx._nudge_should_render(session_id, blocker))
        # A genuine change (e.g. the underlying evidence shifted) re-earns a
        # fresh render, exactly like any other candidate.
        blocker_changed = self.candidate("connect.scratch-expired", evidence_fp="v2", blocking=True)
        self.assertTrue(sfx._nudge_should_render(session_id, blocker_changed))


class CmdStatusStdoutTests(unittest.TestCase):
    """`/status` and `/welcome` have the model reproduce `cmd_status` stdout — the
    model-reproduced pipe, where ANSI becomes escape-junk. The banner it prints
    must be fully plain even when color is otherwise enabled (Major #1 fix)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.cwd)
        self.cwd.joinpath("sfdx-project.json").write_text(
            json.dumps({"name": "acme-crm", "packageDirectories": [{"path": "force-app"}]}),
            encoding="utf-8")

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_status_prints_a_fully_plain_banner_even_with_color_enabled(self):
        org = {"alias": "acme-dev", "edition": "Developer", "apiVersion": "63.0"}
        stats = {"apex_src": 0, "apex_test": 0, "triggers": 0, "lwc": 0,
                 "aura": 0, "objects": 0, "permsets": 0, "flows": 0}
        out = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                mock.patch.object(sfx, "resolve_org_info", return_value=org), \
                mock.patch.object(sfx, "project_stats", return_value=stats), \
                mock.patch.object(sfx, "git_status_line", return_value=""), \
                redirect_stdout(out):
            code = sfx.cmd_status()
        printed = out.getvalue()
        self.assertEqual(code, 0)
        self.assertNotIn("\x1b", printed)          # no escape bytes on the reproduced pipe
        self.assertIn("acme-dev", printed)          # the org still renders
        self.assertIn("sfdx project: acme-crm", printed)
        # journey-nudges Phase 7/8: the nudge line rides with /status too, fully plain
        # (the model-reproduced pipe strips ANSI entirely). This fixture has a
        # configured org + the project descriptor but no local source, so the
        # empty-scaffold nudge (🚀 Try next) is the ladder winner; there is no
        # "Reached:" word-list anymore.
        self.assertIn("🚀 Try next:", printed)
        self.assertNotIn("Reached:", printed)
        self.assertNotIn("likely next", printed)

    def test_lean_status_drops_logo_and_invitation_but_welcome_keeps_them(self):
        # The `--lean` vs bare split in the `cmd_status` CLI seam: `--lean` drops the
        # HEADLESS logo lockup and the ✳ "New here?" onboarding pointer (keeping the org
        # / project bands and the journey nudge), while bare status keeps the full session
        # banner. This is the same logo split the paint layer now expresses directly —
        # `_status_command_paint` renders logo=False, `_welcome_command_paint` logo=True.
        # The /status and /welcome command bodies no longer invoke this CLI (the
        # UserPromptExpansion hook paints the surface), but the subcommand is preserved
        # (telemetry + this characterization), so the drop-vs-keep distinction still holds.
        org = {"alias": "acme-dev", "edition": "Developer", "apiVersion": "63.0"}
        stats = {"apex_src": 0, "apex_test": 0, "triggers": 0, "lwc": 0,
                 "aura": 0, "objects": 0, "permsets": 0, "flows": 0}

        def run(argv):
            out = io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True), \
                    mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                    mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                    mock.patch.object(sfx, "resolve_org_info", return_value=org), \
                    mock.patch.object(sfx, "project_stats", return_value=stats), \
                    mock.patch.object(sfx, "git_status_line", return_value=""), \
                    redirect_stdout(out):
                code = sfx.cmd_status(argv)
            self.assertEqual(code, 0)
            return out.getvalue()

        lean = run(["--lean"])
        self.assertNotIn(sfx.BANNER, lean)                 # no logo lockup
        self.assertNotIn("New here?", lean)                # no wayfinding pointer
        self.assertIn("acme-dev", lean)                    # org band kept
        self.assertIn("sfdx project: acme-crm", lean)      # project band kept
        self.assertTrue(                                   # graded nudge line kept
            any(pre in lean for pre in sfx._NUDGE_BAND_PREFIXES), lean)

        welcome = run([])                                  # bare `status` (the /welcome path)
        self.assertIn(sfx.BANNER, welcome)                 # logo kept
        self.assertIn("New here?", welcome)                # pointer kept


class WayfinderTests(unittest.TestCase):
    """The post-connect wayfinder (PostToolUse on `sf org login` / `sf config set
    target-org`): a LEAN, colored re-orientation on the systemMessage channel.
    Fails open; color scoped to the visible surface; the model note stays plain."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.cwd)
        self._orig_runtime_dir = sfx._PROMPT_RUNTIME_DIR
        sfx._PROMPT_RUNTIME_DIR = self.cwd / "runtime"
        self.org = {
            "alias": "acme-dev", "edition": "Developer Edition (Sandbox)",
            "apiVersion": "63.0", "instanceUrl": "https://acme-dev.my.salesforce.com",
            "username": "jdoe@acme.example.com",
        }

    def tearDown(self):
        sfx._PROMPT_RUNTIME_DIR = self._orig_runtime_dir
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def make_project(self, name="acme-crm"):
        self.cwd.joinpath("sfdx-project.json").write_text(
            json.dumps({"name": name, "packageDirectories": [{"path": "force-app", "default": True}]}),
            encoding="utf-8")

    def capture(self, command="sf org login web --alias acme-dev --set-default"):
        # The wayfinder self-gates on the executed command, so feed it via the
        # PostToolUse payload. Default: an org-connect (the paint path).
        payload = io.StringIO(json.dumps({
            "tool_input": {"command": command},
            "session_id": "capture-session", "prompt_id": "capture-prompt",
        }))
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            code = sfx.cmd_wayfinder()
        return code, json.loads(out.getvalue())

    def test_non_connect_command_stays_silent(self):
        # Self-gate: an ordinary Bash (cd, grep, list, even a deploy) is not an
        # org-connect, so the wayfinder never re-orients — even when the hook fires
        # on it (some Claude Code builds don't honor the plugin.json `if:` matcher,
        # firing every Bash hook on every command). This is the fix for the nudge
        # painting after an unrelated command.
        self.make_project()
        for cmd in ("cd /tmp/proj && grep -r foo .", "sf project deploy start",
                    "sf org list", "ls -la", ""):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "get_target_org_detailed") as probe:
                    code, result = self.capture(command=cmd)
                self.assertEqual((code, result), (0, {"continue": True}))
                probe.assert_not_called()   # gated before any org work

    def stat_patches(self):
        return (
            mock.patch.object(sfx, "project_stats", return_value={
                "apex_src": 12, "apex_test": 8, "triggers": 3, "lwc": 5,
                "aura": 0, "objects": 14, "permsets": 2, "flows": 6}),
            mock.patch.object(sfx, "git_status_line", return_value="main · 2 modified"),
        )

    def test_non_project_fails_open_silently(self):
        # The connect fired outside a project — never re-orient, never crash.
        code, result = self.capture()
        self.assertEqual((code, result), (0, {"continue": True}))

    def test_no_default_org_emits_a_nudge_not_a_reorientation(self):
        self.make_project()
        with mock.patch.object(sfx, "get_target_org_detailed", return_value=("", "")), \
                mock.patch.object(sfx, "resolve_org_info") as reachable:
            _, result = self.capture()
        reachable.assert_not_called()   # never probe an org we don't have
        msg = strip_ansi(result["systemMessage"])
        self.assertIn("set a default org", msg)
        self.assertNotIn("additionalContext", json.dumps(result))   # message="" → no model note
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in msg.splitlines()))

    def test_failed_org_query_emits_a_nudge_and_never_probes(self):
        self.make_project()
        for reason in ("nonzero", "timeout", "unresolved"):
            with self.subTest(reason=reason):
                with mock.patch.object(sfx, "get_target_org_detailed", return_value=("", reason)), \
                        mock.patch.object(sfx, "resolve_org_info") as reachable:
                    _, result = self.capture()
                reachable.assert_not_called()
                self.assertIn("set a default org", strip_ansi(result["systemMessage"]))
                self.assertNotIn("additionalContext", json.dumps(result))

    def test_unreachable_target_emits_a_target_nudge(self):
        self.make_project()
        with mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                mock.patch.object(sfx, "resolve_org_info", return_value={}):
            _, result = self.capture()
        msg = strip_ansi(result["systemMessage"])
        self.assertIn("not reachable", msg)
        self.assertIn("acme-dev", msg)
        self.assertNotIn("additionalContext", json.dumps(result))
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in msg.splitlines()))

    def test_connected_reorientation_colored_on_visible_surface_only(self):
        self.make_project()
        p1, p2 = self.stat_patches()
        with mock.patch.dict(os.environ, {}, clear=True), p1, p2, \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                mock.patch.object(sfx, "resolve_org_info", return_value=self.org), \
                mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}):
            _, result = self.capture()
        visible = result["systemMessage"]
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("\x1b[22m", visible)   # the graded nudge line is colored (body style)
        stripped = strip_ansi(visible)
        self.assertIn("connected", stripped)              # ◆ connected — <org> · … header
        self.assertIn("acme-dev", stripped)               # which org connected
        self.assertNotIn("sfdx project:", stripped)       # heavy bands trimmed away
        self.assertNotIn("Apex 0", stripped)              # inventory band trimmed away
        self.assertTrue(                                  # the graded nudge line
            any(pre in stripped for pre in sfx._NUDGE_BAND_PREFIXES), stripped)
        self.assertNotIn("Reached:", stripped)            # word-list retired (Phase 8)
        self.assertEqual(stripped.count(POINTER), 1)
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in stripped.splitlines()), stripped)
        # The model note is ANSI-free and names the NEW target, so the model can
        # correct any "no default org" assumption SessionStart set.
        self.assertNotIn("\x1b", note)
        self.assertIn("acme-dev", note)
        self.assertIn("63.0", note)

    def test_reorientation_is_plain_under_no_color(self):
        self.make_project()
        p1, p2 = self.stat_patches()
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}), p1, p2, \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                mock.patch.object(sfx, "resolve_org_info", return_value=self.org), \
                mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}):
            _, result = self.capture()
        self.assertNotIn("\x1b", result["systemMessage"])
        self.assertNotIn("\x1b", result["hookSpecificOutput"]["additionalContext"])

    def test_crash_fails_open(self):
        self.make_project()
        with mock.patch.object(sfx, "get_target_org_detailed", side_effect=RuntimeError("boom")):
            code, result = self.capture()
        self.assertEqual((code, result), (0, {"continue": True}))

    def test_reorientation_stays_within_eighty_with_maximal_untrusted_names(self):
        # Org alias and project name are attacker-controlled in a clone; the pinned
        # nudge and bands must clip, never soft-wrap out of their ≤80 contract.
        self.make_project(name="Z" * 300)
        p1, p2 = self.stat_patches()
        hostile = {**self.org, "alias": "A" * 300, "edition": "E" * 300,
                   "instanceUrl": "https://" + "x" * 300, "username": "u" * 300}
        with p1, p2, \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("A" * 300, "")), \
                mock.patch.object(sfx, "resolve_org_info", return_value=hostile), \
                mock.patch.object(sfx, "get_org_display", return_value={"alias": "A" * 300}):
            _, result = self.capture()
        stripped = strip_ansi(result["systemMessage"])
        self.assertEqual([l for l in stripped.splitlines() if len(l) > 80 and not sfx._is_width_exempt(l)], [])

    def test_connect_records_the_flag_so_a_same_turn_journey_paint_dedupes(self):
        # When the connect PAINTS the nudge (here a fresh session — no prior nudge seen,
        # so the step-signature gate treats it as moved), it records the per-turn dedup
        # flag: a same-turn `discover journey` then de-dupes (at most one nudge per turn
        # across the connect + journey surfaces). Sandbox the marker dir so "fresh" is
        # deterministic — with no recorded signature the wayfinder always paints.
        self.make_project()
        p1, p2 = self.stat_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            payload = io.StringIO(json.dumps({
                "tool_input": {"command": "sf org login web --set-default"},
                "session_id": "s1", "prompt_id": "p1"}))
            with mock.patch.dict(os.environ, {}, clear=True), p1, p2, \
                    mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                    mock.patch.object(sfx, "resolve_org_info", return_value=self.org), \
                    mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}), \
                    mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(io.StringIO()):
                sfx.cmd_wayfinder()
            context = sfx._prompt_context(
                {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)
            self.assertTrue(sfx._nudge_painted_this_turn(context))
            # A follow-on journey-paint in the same turn now de-dupes (no second nudge).
            jp = io.StringIO(json.dumps({
                "tool_input": {"command": "sf-context discover journey"},
                "session_id": "s1", "prompt_id": "p1"}))
            jout = io.StringIO()
            with mock.patch.object(sfx, "_journey_state", return_value=OrientationPaintTests.STATE), \
                    mock.patch.object(sfx, "_render_nudge_inline") as rj, \
                    mock.patch.object(sfx.sys, "stdin", jp), redirect_stdout(jout):
                sfx.cmd_journey_paint()
            self.assertEqual(json.loads(jout.getvalue()), {"continue": True})
            rj.assert_not_called()
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir

    def test_nudge_signature_is_dedup_key_and_evidence_fp_only(self):
        # Generalized (journey-nudges Phase 4): the signature keys ONLY on the
        # winning candidate's (dedup_key, evidence_fp) — so two candidates that
        # differ in every other field (message, severity, stage) but share both
        # still dedupe, while a genuinely different dedup_key never does. This is
        # what makes an org-context-only refresh (same real-world gap, re-resolved
        # org) de-dupe while an actual gap closing does not.
        a = types.SimpleNamespace(
            dedup_key="deploy.never-deployed", evidence_fp="",
            message="stale message", severity=1,
        )
        b = types.SimpleNamespace(
            dedup_key="deploy.never-deployed", evidence_fp="",
            message="a completely different message", severity=3,
        )
        self.assertEqual(sfx._nudge_signature(a), sfx._nudge_signature(b))
        moved = types.SimpleNamespace(dedup_key="connect.unreachable", evidence_fp="acme-dev")
        self.assertNotEqual(sfx._nudge_signature(a), sfx._nudge_signature(moved))

    def test_connect_with_unchanged_steps_shows_header_but_not_a_second_nudge(self):
        # The reported bug, wayfinder side: the last nudge the user saw had these exact
        # steps, so a connect that re-resolves the same org moves nothing — show the
        # connected-org header (real news), but NOT a duplicate nudge.
        self.make_project()
        p1, p2 = self.stat_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            # Seed the same candidate cmd_wayfinder will independently re-derive
            # below (same project/org facts) — mirroring the real call site
            # (root, state, org, session_id) so the anti-nag fingerprint dedupes.
            root = self.cwd.resolve()
            seen_state = sfx._derive_journey_state(root, has_project=True,
                                                    target="acme-dev", target_error=None,
                                                    org_display=self.org)
            seen_candidate = sfx._select_inline_nudge(
                seen_state, root, self.org, session_id="sess-x",
            )
            sfx._record_nudge_signature("sess-x", seen_candidate)
            payload = io.StringIO(json.dumps({
                "tool_input": {"command": "sf config set target-org acme-dev"},
                "session_id": "sess-x"}))
            out = io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True), p1, p2, \
                    mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                    mock.patch.object(sfx, "resolve_org_info", return_value=self.org), \
                    mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}), \
                    mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
                sfx.cmd_wayfinder()
            result = json.loads(out.getvalue())
            painted_flag = sfx._nudge_painted_this_turn("sess-x")
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("connected", stripped)          # header still shows — the connect is real news
        self.assertIn("acme-dev", stripped)
        self.assertNotIn("●", stripped)                # but no second rail glyph row
        self.assertNotIn("likely next", stripped)      # nor the nudge's next-step line
        self.assertEqual(stripped.count(POINTER), 1)    # the pointer still closes it
        # A suppressed nudge must not consume the turn's single-nudge budget, so a later
        # solicited "where am I" this turn could still paint.
        self.assertFalse(painted_flag)

    def test_connect_that_lights_a_step_reprints_the_nudge(self):
        # The reprint-on-change half: when the connect genuinely moves a step (here the
        # last nudge the user saw had Connect NOT yet lit), the nudge reprints and the
        # signature advances.
        self.make_project()
        p1, p2 = self.stat_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            # A stale prior signature standing in for "no org connected yet" — a
            # dedup_key the real post-connect candidate below can never share, so
            # the fingerprint change forces a reprint.
            stale_candidate = types.SimpleNamespace(dedup_key="connect.no-org", evidence_fp="")
            sfx._record_nudge_signature("sess-y", stale_candidate)
            payload = io.StringIO(json.dumps({
                "tool_input": {"command": "sf org login web --set-default"},
                "session_id": "sess-y", "prompt_id": "p1"}))
            out = io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True), p1, p2, \
                    mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                    mock.patch.object(sfx, "resolve_org_info", return_value=self.org), \
                    mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}), \
                    mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
                sfx.cmd_wayfinder()
            result = json.loads(out.getvalue())
            recorded = sfx._last_nudge_signature("sess-y")
            context = sfx._prompt_context(
                {"session_id": "sess-y", "prompt_id": "p1"}, rotate_fallback=False)
            painted_flag = sfx._nudge_painted_this_turn(context)
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        stripped = strip_ansi(result["systemMessage"])
        self.assertTrue(                                          # the nudge reprinted
            any(pre in stripped for pre in sfx._NUDGE_BAND_PREFIXES), stripped)
        self.assertIn("connected", stripped)
        self.assertNotEqual(recorded, sfx._nudge_signature(stale_candidate))  # advanced off the stale one
        self.assertTrue(painted_flag)                              # counted as a paint (dedupes a follow-on)

    def test_orientation_then_same_state_connect_paints_the_nudge_once(self):
        # End-to-end regression for the reported bug: `/cd` into a project, ask
        # "what's next" (nudge on UserPromptSubmit), then the model sets the SAME target
        # org (wayfinder on PostToolUse). Feature B painted the nudge BOTH times; the
        # step-signature gate makes the second an org-header only.
        self.make_project()
        p1, p2 = self.stat_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            sfx._record_welcomed("s1")
            sfx._record_entered("s1")
            # The orientation paint shows exactly what the connect will derive, so the
            # connect that follows moves nothing.
            derived = sfx._derive_journey_state(self.cwd.resolve(), has_project=True,
                                                target="acme-dev", target_error=None,
                                                org_display=self.org)
            ups = io.StringIO(json.dumps({"prompt": "what's next", "session_id": "s1"}))
            ups_out = io.StringIO()
            with mock.patch.object(sfx, "_journey_state", return_value=derived), \
                    mock.patch.dict(os.environ, {}, clear=True), \
                    mock.patch.object(sfx.sys, "stdin", ups), redirect_stdout(ups_out):
                sfx.cmd_orientation_paint()
            nudge1 = strip_ansi(json.loads(ups_out.getvalue())["systemMessage"])

            wf = io.StringIO(json.dumps({
                "tool_input": {"command": "sf config set target-org acme-dev"},
                "session_id": "s1"}))
            wf_out = io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True), p1, p2, \
                    mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                    mock.patch.object(sfx, "resolve_org_info", return_value=self.org), \
                    mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}), \
                    mock.patch.object(sfx.sys, "stdin", wf), redirect_stdout(wf_out):
                sfx.cmd_wayfinder()
            nudge2 = strip_ansi(json.loads(wf_out.getvalue())["systemMessage"])
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        # journey-nudges Phase 7/8: nudge #1 (the solicited orientation) painted the
        # single graded nudge line; the glyph rail and the "Reached:" word-list are
        # both gone, so check for the nudge content instead of the old "●" marker.
        self.assertTrue(any(pre in nudge1 for pre in sfx._NUDGE_BAND_PREFIXES), nudge1)
        self.assertNotIn("Reached:", nudge1)
        self.assertIn("connected", nudge2)  # the connect still confirms the org
        # …but there is no second nudge line (the same-turn dedup gate suppressed it).
        self.assertFalse(any(pre in nudge2 for pre in sfx._NUDGE_BAND_PREFIXES), nudge2)


class OrientationPaintTests(unittest.TestCase):
    """The UserPromptSubmit paint hook: on an orientation question the journey nudge
    rides the color-carrying systemMessage channel (the one pipe that can, like the
    banner), and the model gets a plain note saying the nudge is already shown so it
    adds only its read. Silent on every other prompt; fails open."""

    # A realistic reducer output on the new cyclical taxonomy: project + reachable
    # org, no source yet, so the cursor rests on Build. Deploy/Observe are `future`
    # (○) — the `unknown` stage status was retired, so it must not appear here.
    STATE = {
        "stages": [{"name": n, "status": s} for n, s in [
            ("Connect", "complete"), ("Project", "complete"), ("Build", "current"),
            ("Test", "future"), ("Deploy", "future"), ("Observe", "future")]],
        "currentStage": "Build",
        "context": {"project": "acme-crm", "orgAlias": "acme-dev",
                    "orgStatus": "reachable", "sourceTracking": "unknown"},
    }

    def setUp(self):
        # These tests exercise Side B's steady state — the in-project nudge. Run from
        # inside a project, and mark the logo already shown this session (session
        # "s1", the id capture() uses) so the hook paints the nudge, not the
        # once-per-scenario welcome. The first-time welcome has its own test.
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = Path.cwd()
        os.chdir(self.tmp.name)
        Path("sfdx-project.json").write_text("{}")
        # Session markers live in the temp dir (not cwd), so isolate + clean them.
        # Steady state: logo already shown AND the project already "entered", so
        # orientation questions paint the nudge and other prompts stay silent. The
        # first-message (entered) nudge has its own test.
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        self._orig_runtime_dir = sfx._PROMPT_RUNTIME_DIR
        self._orig_plugin_proposal_dir = sfx._PLUGIN_PROPOSAL_DIR
        self._orig_plugin_flow_dir = sfx._PLUGIN_FLOW_DIR
        sfx._WELCOME_MARKER_DIR = Path(self.tmp.name)
        sfx._PROMPT_RUNTIME_DIR = Path(self.tmp.name) / "runtime"
        # _PLUGIN_PROPOSAL_DIR is derived at import time, so redirect it
        # explicitly with the prompt runtime. Otherwise prompt recommendation
        # state for the fixed test session id ("s1") leaks between test runs.
        sfx._PLUGIN_PROPOSAL_DIR = sfx._PROMPT_RUNTIME_DIR / "plugin-proposals"
        sfx._PLUGIN_FLOW_DIR = sfx._PROMPT_RUNTIME_DIR / "plugin-flows"
        sfx._record_welcomed("s1")
        sfx._record_entered("s1")

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        sfx._PROMPT_RUNTIME_DIR = self._orig_runtime_dir
        sfx._PLUGIN_PROPOSAL_DIR = self._orig_plugin_proposal_dir
        sfx._PLUGIN_FLOW_DIR = self._orig_plugin_flow_dir
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_first_in_project_orientation_shows_the_logo_once(self):
        sfx._session_marker("s1", "welcome").unlink(missing_ok=True)   # scenario's first orientation
        # The first-surface welcome now paints the full banner chrome, resolving the
        # org via _resolve_position_and_org for its org band — so mock that alongside
        # _journey_state (the bare-nudge second turn still reads _journey_state).
        org = {"alias": "acme-dev", "edition": "Developer Edition (Sandbox)",
               "apiVersion": "67.0", "instanceUrl": "https://x.my.salesforce.com",
               "username": "u@example.com"}
        with mock.patch.object(sfx, "_journey_state", return_value=self.STATE), \
                mock.patch.object(sfx, "_resolve_position_and_org", return_value=(self.STATE, org)):
            _, first = self.capture("where am i?")
            _, second = self.capture("where am i?")
        # The lockup is colored on the systemMessage channel, so match the stripped form.
        self.assertIn(sfx.BANNER_WORDMARK, strip_ansi(first["systemMessage"]))       # logo carried once
        self.assertNotIn(sfx.BANNER_WORDMARK, strip_ansi(second["systemMessage"]))   # nudge line only thereafter
        self.assertTrue(                                                    # still the nudge line
            any(pre in second["systemMessage"] for pre in sfx._NUDGE_BAND_PREFIXES),
            second["systemMessage"])

    def capture(self, prompt, env=None):
        payload = io.StringIO(json.dumps({"prompt": prompt, "session_id": "s1"}))
        out = io.StringIO()
        with mock.patch.object(sfx, "_journey_state", return_value=self.STATE), \
                mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, env or {}, clear=True), \
                redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        return code, json.loads(out.getvalue())

    def capture_status(self, prompt, org="__default__"):
        """A status question resolves the org via _resolve_position_and_org (not
        _journey_state), so mock that and the band inputs."""
        if org == "__default__":
            org = {"alias": "acme-dev", "edition": "Developer Edition (Sandbox)",
                   "apiVersion": "67.0", "instanceUrl": "https://x.my.salesforce.com",
                   "username": "u@example.com"}
        stats = {"apex_src": 2, "apex_test": 1, "triggers": 0, "lwc": 1,
                 "aura": 0, "objects": 0, "permsets": 0, "flows": 0}
        payload = io.StringIO(json.dumps({"prompt": prompt, "session_id": "s1"}))
        out = io.StringIO()
        with mock.patch.object(sfx, "_resolve_position_and_org", return_value=(self.STATE, org)), \
                mock.patch.object(sfx, "project_meta", return_value={"name": "acme-crm", "source_api": "66.0", "package_dirs": "force-app"}), \
                mock.patch.object(sfx, "project_stats", return_value=stats), \
                mock.patch.object(sfx, "git_status_line", return_value=""), \
                mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), \
                redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        return code, json.loads(out.getvalue())

    def test_status_detection_hits_and_misses(self):
        for hit in ("status", "status?", "project status", "org status",
                    "environment status", "what's the status of the project",
                    "what is my status", "show me the status", "status check",
                    "status report", "where do things stand",
                    # Lever A broadening: the "stand" family stays on the STATUS surface
                    # (it already owns "where do things stand"), so the elided "do" form
                    # in "walk me through where things stand" routes here, not orientation.
                    "walk me through where things stand", "where things stand"):
            self.assertTrue(sfx._is_status_question(hit), hit)
        # Task-scoped "status" is ordinary work, not the plugin's position view.
        for miss in ("git status", "deploy status", "what's the deployment status",
                     "build status", "status of the deploy", "what's next",
                     "where is the Account class?", "add a status field to the object",
                     # "what's the status of the <non-workspace noun>" must NOT fire the
                     # expensive bands paint — only workspace nouns (project/org/…) do.
                     "what's the status of the API", "what's the status of the feature",
                     "what is the status of this record",
                     # Figurative "where X stand[s] <prep> …" is an opinion/topic aside, not
                     # a position ask — it must not fire the expensive org-band status paint.
                     "let me tell you where we stand with the client",
                     "I know where I stand on this issue",
                     "where we stand on the contract negotiation",
                     "", "x" * 3000):
            self.assertFalse(sfx._is_status_question(miss), miss)

    def test_status_question_paints_org_and_project_bands_plus_nudge_line(self):
        code, result = self.capture_status("what's the status of the project")
        self.assertEqual(code, 0)
        sysmsg = result["systemMessage"]
        stripped = strip_ansi(sysmsg)
        self.assertIn("org: acme-dev", stripped)             # the org band
        self.assertIn("sfdx project: acme-crm", stripped)    # the project band
        # journey-nudges Phase 7/8: the glyph rail's labels and the "Reached:"
        # word-list are retired — the single ladder-winning graded nudge line paints
        # instead (this sandbox has Apex without tests → the ⚠️ Heads up apex-no-tests
        # winner; assert the band marker generically so the test tracks "a nudge line
        # rides here", not one specific rule).
        self.assertTrue(
            any(pre in stripped for pre in sfx._NUDGE_BAND_PREFIXES), stripped)
        self.assertNotIn("Reached:", stripped)
        self.assertNotIn("likely next", stripped)            # …but no below-nudge next-step line
        # The glyph rail's single green "current stage" accent is retired along
        # with the geometry — the nudge line paints via the theme-adaptive
        # palette instead (undimmed body text), not a hardcoded green.
        self.assertIn("\x1b[22m", sysmsg)
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in stripped.splitlines()))
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                       # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)status")
        self.assertNotIn("●", note)                          # never hands the glyph rail to the model

    def test_status_question_with_no_reachable_org_degrades_but_still_paints(self):
        code, result = self.capture_status("status", org=None)
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("sfdx project: acme-crm", stripped)    # project band still shows
        self.assertTrue(                                     # nudge line still shows
            any(pre in stripped for pre in sfx._NUDGE_BAND_PREFIXES), stripped)
        self.assertNotIn("org: acme-dev", stripped)          # no fabricated connected org
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in stripped.splitlines()))

    def test_status_surface_reports_cli_unknown_honestly(self):
        # When the CLI can't be resolved or the org query failed (orgStatus
        # "unknown"), the org line says so — not "no default set", which would
        # advise an `sf org login` that can't succeed with a missing/broken CLI.
        state = {**self.STATE, "context": {**self.STATE["context"],
                                           "orgStatus": "unknown", "orgAlias": None}}
        stats = {k: 0 for k in ("apex_src", "apex_test", "triggers", "lwc",
                                "aura", "objects", "permsets", "flows")}
        surface = strip_ansi(sfx.render_status_surface(
            state, None, {"name": "acme-crm", "source_api": "66.0", "package_dirs": "force-app"},
            stats, "", "x", color=False))
        self.assertIn("status unknown", surface)
        self.assertIn("Salesforce CLI", surface)
        self.assertNotIn("no default set", surface)

    def test_positional_question_paints_nudge_only_not_the_bands(self):
        # "what's next" is positional — the single graded nudge line (with its
        # one-line context row), never the rule-framed org/project bands. The
        # context row does state the project/org, so the band-only markers are
        # the discriminator: the MCP line and the Apex-inventory counts appear
        # only when the status bands paint.
        _, result = self.capture("what's next")
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("🚀 Try next:", stripped)              # the empty-scaffold nudge line
        self.assertNotIn("MCP:", stripped)                   # NOT the org band
        # NOT the project inventory band — its "Apex N src / M test" count line.
        # (The empty-scaffold nudge's own action text legitimately mentions
        # "Apex class" as an example, so match the inventory band's distinguishing
        # "src /" marker instead of a bare "Apex " substring.)
        self.assertNotIn("src /", stripped)

    def test_ordinary_prompt_does_no_org_or_filesystem_fetch(self):
        # The hot path: an ordinary, already-entered prompt paints nothing AND does
        # no org work — the gate classifies with cheap regexes before any fetch, so
        # the common case pays nothing (previously _journey_state ran every prompt).
        payload = io.StringIO(json.dumps({"prompt": "add a field to the Account object", "session_id": "s1"}))
        out = io.StringIO()
        with mock.patch.object(sfx, "_journey_state") as js, \
                mock.patch.object(sfx, "_resolve_position_and_org") as rp, \
                mock.patch.object(sfx, "get_target_org_detailed") as gto, \
                mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), \
                redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        self.assertEqual((code, json.loads(out.getvalue())), (0, {"continue": True}))
        js.assert_not_called()
        rp.assert_not_called()
        gto.assert_not_called()

    def test_first_in_project_message_paints_the_nudge_once_as_ambient(self):
        # First non-orientation, non-connect message after entering the project →
        # the position nudge paints once, as AMBIENT orientation (the note tells the
        # model to proceed with the request, not to orient). Silent on the next.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        _, first = self.capture("create a custom object")
        _, second = self.capture("add a field to it")
        self.assertTrue(                                                     # the nudge line
            any(pre in first["systemMessage"] for pre in sfx._NUDGE_BAND_PREFIXES),
            first["systemMessage"])
        note = first["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)ambient")
        self.assertRegex(note, r"(?i)proceed with")
        self.assertEqual(second, {"continue": True})               # once only

    def test_prompt_plugin_recommendation_defers_but_does_not_consume_ambient_nudge(self):
        # A first-turn recommendation owns that turn's visible surface. It must not
        # permanently consume the first-message orientation nudge: the proposal
        # ledger dedupes the plugin on turn two, which then paints the ambient nudge.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        candidate = {
            "name": "experience-cms",
            "description": "Curated CMS content and media workflows.",
            "band": "high",
            "first_occurrence": True,
            "install_command": "/salesforce-development:plugin-install experience-cms",
        }
        with mock.patch.object(
            sfx, "_plugin_catalog_match", side_effect=[[candidate], []]
        ):
            _, recommendation = self.capture("search Salesforce CMS media")
            self.assertIn("Recommended plugin", recommendation["systemMessage"])
            self.assertFalse(sfx._entered_this_session("s1"))
            self.assertTrue(sfx._load_plugin_flow("s1")["taskBacked"])

            _, next_turn = self.capture("show me the results")

        self.assertTrue(
            any(pre in next_turn["systemMessage"] for pre in sfx._NUDGE_BAND_PREFIXES),
            next_turn["systemMessage"])
        note = next_turn["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)ambient")
        self.assertTrue(sfx._entered_this_session("s1"))

    def test_non_actionable_product_prompt_never_invokes_proactive_matcher(self):
        candidate = {
            "name": "experience-cms",
            "description": "Curated CMS content and media workflows.",
            "band": "high",
            "first_occurrence": True,
            "install_command": "/salesforce-development:plugin-install experience-cms",
        }
        with mock.patch.object(
            sfx, "_plugin_catalog_match", return_value=[candidate]
        ) as matcher:
            _, result = self.capture("tell me about Salesforce CMS")

        matcher.assert_not_called()
        self.assertEqual(result, {"continue": True})

    def test_explicit_named_plugin_decline_routes_before_recommendation_scoring(self):
        # A decline is a control reply to the already-visible proposal. In the live
        # regression, scoring this text surfaced CMS from "experience" and org
        # lifecycle from "install". Route the exact prior proposal instead, with
        # no replacement recommendation and no hook-side telemetry mutation.
        proposal = {
            "experience-react": {"confidence": "high", "surface": "session-start"}
        }
        self.assertTrue(sfx._save_plugin_proposals("s1", proposal))
        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher, \
                mock.patch.object(
                    sfx, "_record_plugin_decline", return_value=(True, "")
                ) as recorder:
            _, result = self.capture(
                "no thanks, do not install experience-react"
            )

        matcher.assert_not_called()
        recorder.assert_called_once_with("experience-react", "s1")
        self.assertNotIn("systemMessage", result)
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("was recorded for this session", note)
        self.assertRegex(note, r"(?i)do not run a tool")
        self.assertRegex(note, r"(?i)do not recommend another plugin")
        self.assertEqual(sfx._load_plugin_proposals("s1"), proposal)

    def test_session_start_flow_routes_terse_acceptance_before_a_dry_run(self):
        proposal = {
            "experience-react": {"confidence": "high", "surface": "session-start"}
        }
        self.assertTrue(sfx._save_plugin_proposals("s1", proposal))
        self.assertTrue(sfx._open_plugin_flow(
            "s1", ["experience-react"], "session-start"
        ))
        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, result = self.capture("ok install it")

        matcher.assert_not_called()
        self.assertNotIn("systemMessage", result)
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("plugin-install experience-react --accept-proposed", note)
        self.assertIn("install immediately", note)
        self.assertRegex(note, r"(?i)do not recommend another plugin")
        self.assertEqual(
            sfx._load_plugin_flow("s1")["state"], "selected"
        )

    def test_multi_candidate_generic_yes_asks_the_user_to_name_one(self):
        # "Fix that": a bare "yes" cannot pick among several open proposals — the
        # runtime deliberately does NOT auto-select (no best-pick, per the design
        # doc). Rather than falling silent (which previously let the model guess
        # --accept-proposed against a missing selection and then retry it), it names
        # the candidates and asks the user to name one. The confirmation turn never
        # rescores, and no candidate is selected.
        proposal = {
            "experience-react": {"confidence": "high", "surface": "user-prompt"},
            "mobile-development": {"confidence": "high", "surface": "user-prompt"},
        }
        self.assertTrue(sfx._save_plugin_proposals("s1", proposal))
        self.assertTrue(sfx._open_plugin_flow(
            "s1", ["experience-react", "mobile-development"], "user-prompt"
        ))
        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, result = self.capture("yes")

        matcher.assert_not_called()                 # a confirmation turn never rescores
        self.assertNotIn("systemMessage", result)   # model-facing only, no paint
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("experience-react", note)     # both candidates named…
        self.assertIn("mobile-development", note)
        self.assertRegex(note, r"(?i)which single plugin")  # …and asked to pick one
        self.assertRegex(note, r"(?i)does not auto-pick")
        self.assertRegex(note, r"(?i)name it")
        # No auto-selection: the workflow stays open and unselected.
        flow = sfx._load_plugin_flow("s1")
        self.assertEqual(flow["state"], "recommended")
        self.assertIsNone(flow["selected"])
        self.assertEqual(
            flow["candidates"], ["experience-react", "mobile-development"]
        )

    def test_candidate_comparison_preserves_flow_for_later_acceptance(self):
        proposal = {
            "experience-react": {"confidence": "high", "surface": "session-start"}
        }
        self.assertTrue(sfx._save_plugin_proposals("s1", proposal))
        self.assertTrue(sfx._open_plugin_flow(
            "s1", ["experience-react"], "session-start"
        ))

        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, comparison = self.capture(
                "what is the difference between experience-react and LWC?"
            )
            flow_after_comparison = sfx._load_plugin_flow("s1")
            _, acceptance = self.capture("yes, install it")

        matcher.assert_not_called()
        self.assertEqual(comparison, {"continue": True})
        self.assertIsNotNone(flow_after_comparison)
        self.assertEqual(flow_after_comparison["state"], "recommended")
        note = acceptance["hookSpecificOutput"]["additionalContext"]
        self.assertIn("plugin-install experience-react --accept-proposed", note)
        self.assertEqual(sfx._load_plugin_flow("s1")["state"], "selected")

    def test_unrelated_information_still_releases_old_recommendation(self):
        self.assertTrue(sfx._save_plugin_proposals(
            "s1",
            {"experience-react": {"confidence": "high", "surface": "session-start"}},
        ))
        self.assertTrue(sfx._open_plugin_flow(
            "s1", ["experience-react"], "session-start"
        ))

        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, result = self.capture("what is Salesforce CMS?")

        matcher.assert_not_called()
        self.assertEqual(result, {"continue": True})
        self.assertIsNone(sfx._load_plugin_flow("s1"))

    def test_shared_candidate_token_does_not_preserve_old_recommendation(self):
        self.assertTrue(sfx._save_plugin_proposals(
            "s1",
            {"experience-react": {"confidence": "high", "surface": "session-start"}},
        ))
        self.assertTrue(sfx._open_plugin_flow(
            "s1", ["experience-react"], "session-start"
        ))

        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, result = self.capture("what is React Native?")

        matcher.assert_not_called()
        self.assertEqual(result, {"continue": True})
        self.assertIsNone(sfx._load_plugin_flow("s1"))

    def test_concrete_task_promotes_matching_session_start_flow_to_task_backed(self):
        proposal = {
            "experience-react": {"confidence": "high", "surface": "session-start"}
        }
        candidate = {
            "name": "experience-react",
            "description": "Build Salesforce React UI bundles.",
            "band": "high",
            "first_occurrence": False,
            "install_command": "/salesforce-development:plugin-install experience-react",
        }
        self.assertTrue(sfx._save_plugin_proposals("s1", proposal))
        self.assertTrue(sfx._open_plugin_flow(
            "s1", ["experience-react"], "session-start"
        ))
        with mock.patch.object(
            sfx, "_plugin_catalog_match", return_value=[candidate]
        ) as matcher:
            _, result = self.capture(
                "Build the existing Salesforce React UI bundle with TSX and Tailwind"
            )

        matcher.assert_called_once()
        self.assertIn("Recommended plugin", result["systemMessage"])
        flow = sfx._load_plugin_flow("s1")
        self.assertTrue(flow["taskBacked"])
        self.assertEqual(flow["surface"], "user-prompt")
        self.assertEqual(flow["candidates"], ["experience-react"])

    def test_recommendation_only_flow_waits_for_a_new_task_after_activation(self):
        self.assertTrue(sfx._save_plugin_flow(
            "s1", ["experience-react"], selected="experience-react",
            state="installed", surface="session-start", task_backed=False,
        ))
        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, control = self.capture("continue")
        matcher.assert_not_called()
        self.assertNotIn("systemMessage", control)
        note = control["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)not a new substantive task")
        self.assertRegex(note, r"(?i)briefly confirm activation")
        self.assertRegex(note, r"(?i)do not inspect the project")
        self.assertRegex(note, r"(?i)ask the user for a new concrete task")
        self.assertIsNotNone(sfx._load_plugin_flow("s1"))

        with mock.patch.object(sfx, "_plugin_catalog_match", return_value=[]) as matcher:
            _, task = self.capture("create a custom object for conference sessions")
        matcher.assert_called_once()
        self.assertEqual(task, {"continue": True})
        self.assertIsNone(sfx._load_plugin_flow("s1"))

    def test_task_backed_flow_resumes_the_interrupted_task_after_activation(self):
        self.assertTrue(sfx._save_plugin_flow(
            "s1", ["experience-react"], selected="experience-react",
            state="installed", surface="user-prompt", task_backed=True,
        ))
        with mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
            _, control = self.capture("continue")
        matcher.assert_not_called()
        self.assertNotIn("systemMessage", control)
        note = control["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)interrupted a concrete earlier task")
        self.assertRegex(note, r"(?i)resume only that same earlier task")
        self.assertRegex(note, r"(?i)appropriate installed skill")
        self.assertNotRegex(note, r"(?i)ask the user for a new concrete task")
        self.assertTrue(sfx._load_plugin_flow("s1")["taskBacked"])

    def test_task_backed_terminal_status_and_ok_do_not_resume_or_reinstall(self):
        self.assertTrue(sfx._save_plugin_flow(
            "s1", ["experience-react"], selected="experience-react",
            state="installed", surface="user-prompt", task_backed=True,
        ))
        for prompt in ("is the plugin active?", "OK"):
            with self.subTest(prompt=prompt), \
                    mock.patch.object(sfx, "_plugin_catalog_match") as matcher:
                _, control = self.capture(prompt)
            matcher.assert_not_called()
            note = control["hookSpecificOutput"]["additionalContext"]
            self.assertRegex(note, r"(?i)did not explicitly ask to resume")
            self.assertRegex(note, r"(?i)do not .*resume implementation")
            self.assertIn("`continue`", note)
            self.assertNotIn("plugin-install experience-react", note)

    def test_connect_intent_with_sf_absent_routes_to_setup_and_never_logs_in(self):
        # D9: on connect intent the plugin does the cheap `sf`-on-PATH check FIRST.
        # capture() clears the env, so `sf` is not resolvable → the note routes to
        # environment setup and explicitly does NOT attempt an interactive login (the
        # plugin never runs `sf org login`). It marks entered (so the ambient nudge
        # won't also fire) and paints nothing — model-facing additionalContext only.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        _, result = self.capture("connect an org")
        self.assertTrue(result.get("continue"))
        self.assertNotIn("systemMessage", result)                 # model-facing only, no paint
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("platform-environment-validate", note)      # routed to setup
        self.assertRegex(note, r"(?i)do not attempt a login")
        self.assertTrue(sfx._entered_this_session("s1"))

    def test_connect_intent_with_target_already_set_says_nothing_to_connect(self):
        # `sf` present and an org already set as the target → "nothing to connect".
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "_has_target_org", return_value=True):
            _, result = self.capture("connect an org")
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)already set as the target")
        self.assertNotIn("systemMessage", result)

    def test_connect_intent_no_target_with_auth_history_offers_the_ternary(self):
        # `sf` present, no target, but an org has been authed before → the D10 (a)/(b)
        # ternary: auth/reuse an existing org (the login command) or a scratch org
        # (dx-org-manage, which needs a Dev Hub). Never runs the login itself.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "_has_target_org", return_value=False), \
                mock.patch.object(sfx, "_has_authed_org", return_value=True):
            _, result = self.capture("log in to an org")
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("/salesforce-development:login", note)       # (a) existing org
        self.assertIn("dx-org-manage", note)                       # (b) scratch org
        self.assertRegex(note, r"(?i)dev hub")                     # scratch-org precondition
        self.assertRegex(note, r"(?i)do not run")                  # plugin never logs in
        self.assertIn("sf org login", note)

    def test_connect_intent_zero_org_newcomer_points_to_dev_edition_signup(self):
        # D10(c): `sf` present, no target AND no auth on record → the zero-org newcomer.
        # A MINIMAL honest pointer to a free Developer Edition web signup (the full
        # hand-off is the still-proposed first-org onboarding flow), never a fabricated
        # in-suite provisioning step.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "_has_target_org", return_value=False), \
                mock.patch.object(sfx, "_has_authed_org", return_value=False):
            _, result = self.capture("connect an org")
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn(sfx._FIRST_ORG_SIGNUP_URL, note)
        self.assertRegex(note, r"(?i)developer edition")
        self.assertRegex(note, r"(?i)cannot create a first org")

    def test_discovery_overview_intent_paints_the_overview_and_marks_entered(self):
        # "what can I do here?" is a capability-catalog question. The overview is a
        # Tier-1 surface (like the SessionStart banner): the plugin paints the block
        # on the visible channel and the model adds only its read — it never reproduces
        # it. The ambient nudge steps aside (entered is marked) and is NOT drawn here.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        block = "Salesforce Headless 360 · what you can do here\n(fixed test block)"
        with mock.patch.object(sfx, "_render_overview_paint", return_value=block) as rp:
            _, result = self.capture("what can I do here?")
        rp.assert_called_once()
        self.assertEqual(result["systemMessage"], "\n" + block)   # painted directly, verbatim
        self.assertNotIn("build", result["systemMessage"])        # the overview, NOT the nudge
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                            # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)add only your")
        self.assertRegex(note, r"(?i)overview")
        self.assertTrue(sfx._entered_this_session("s1"))

    def test_discovery_overview_arms_the_test_drive_proposal_on_the_nl_front_door(self):
        # The overview's getting-started CTA names salesforce-test-drive; the NL front
        # door arms the same-session ledger (helper unit-tested separately) so a later
        # named bite fast-installs. Arming rides the successful paint (inside `if
        # block`), so a failed render arms nothing. Helper mocked to isolate the wiring.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        with mock.patch.object(sfx, "_render_overview_paint", return_value="BLOCK"), \
                mock.patch.object(sfx, "_arm_overview_test_drive_proposal") as armed:
            self.capture("what can I do here?")
        armed.assert_called_once_with("s1")

        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        with mock.patch.object(sfx, "_render_overview_paint", return_value=None), \
                mock.patch.object(sfx, "_arm_overview_test_drive_proposal") as armed_none:
            self.capture("what can I do here?")
        armed_none.assert_not_called()

    def test_failed_overview_render_leaves_entered_absent_and_ambient_retries(self):
        # A failed overview paint did not show the suppressing surface. Keep `entered`
        # absent so the next ordinary prompt can still deliver the ambient nudge.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        with mock.patch.object(sfx, "_render_overview_paint", return_value=None):
            _, failed = self.capture("what are my options")
        self.assertEqual(failed, {"continue": True})
        self.assertFalse(sfx._entered_this_session("s1"))

        _, retry = self.capture("add a field to Account")
        self.assertTrue(
            any(pre in retry["systemMessage"] for pre in sfx._NUDGE_BAND_PREFIXES),
            retry["systemMessage"])
        self.assertTrue(sfx._entered_this_session("s1"))

    def test_status_render_failure_leaves_shown_state_absent(self):
        for kind in ("welcome", "entered", "nudgesig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(
            sfx, "render_status_surface", side_effect=RuntimeError("render failed")
        ):
            _, result = self.capture_status("status")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))
        self.assertFalse(sfx._nudge_painted_this_turn("s1"))

    def _clear_shown_state(self):
        for kind in ("welcome", "entered", "nudgesig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)

    def _assert_no_shown_state(self):
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))

    def test_status_emit_failure_commits_no_markers_and_status_can_retry(self):
        self._clear_shown_state()
        with mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, failed = self.capture_status("status")
        self.assertEqual(failed, {"continue": True})
        self._assert_no_shown_state()

        _, retry = self.capture_status("status")
        self.assertIn("systemMessage", retry)
        self.assertTrue(sfx._welcomed_this_session("s1"))
        self.assertTrue(sfx._entered_this_session("s1"))
        self.assertIsNotNone(sfx._last_nudge_signature("s1"))

    def test_overview_emit_failure_commits_no_markers_and_overview_can_retry(self):
        self._clear_shown_state()
        with mock.patch.object(sfx, "_render_overview_paint", return_value="overview"), \
                mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, failed = self.capture("what can I do here?")
        self.assertEqual(failed, {"continue": True})
        self._assert_no_shown_state()

        with mock.patch.object(sfx, "_render_overview_paint", return_value="overview"):
            _, retry = self.capture("what can I do here?")
        self.assertEqual(retry["systemMessage"], "\noverview")
        self.assertTrue(sfx._entered_this_session("s1"))
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))

    def test_environment_emit_failure_commits_no_markers_and_environment_can_retry(self):
        self._clear_shown_state()
        with mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, failed = self.capture("check my environment")
        self.assertEqual(failed, {"continue": True})
        self._assert_no_shown_state()

        _, retry = self.capture("check my environment")
        self.assertIn("additionalContext", retry["hookSpecificOutput"])
        self.assertTrue(sfx._entered_this_session("s1"))
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))

    def test_connect_emit_failure_commits_no_markers_and_connect_can_retry(self):
        self._clear_shown_state()
        patches = (
            mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"),
            mock.patch.object(sfx, "_has_target_org", return_value=False),
            mock.patch.object(sfx, "_has_authed_org", return_value=False),
        )
        with patches[0], patches[1], patches[2], \
                mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, failed = self.capture("connect an org")
        self.assertEqual(failed, {"continue": True})
        self._assert_no_shown_state()

        patches = (
            mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"),
            mock.patch.object(sfx, "_has_target_org", return_value=False),
            mock.patch.object(sfx, "_has_authed_org", return_value=False),
        )
        with patches[0], patches[1], patches[2]:
            _, retry = self.capture("connect an org")
        self.assertIn("additionalContext", retry["hookSpecificOutput"])
        self.assertTrue(sfx._entered_this_session("s1"))
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))

    def test_orientation_state_failure_leaves_shown_state_absent(self):
        for kind in ("welcome", "entered", "nudgesig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(
            sfx, "_resolve_position_and_org", side_effect=RuntimeError("state failed")
        ):
            _, result = self.capture("where am I?")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))
        self.assertFalse(sfx._nudge_painted_this_turn("s1"))

    def test_orientation_emit_failure_keeps_claim_but_commits_no_shown_state(self):
        # The at-most-once claim intentionally stays before emit. An emit failure may
        # consume that prompt's nudge, but it must not commit session shown-state.
        for kind in ("welcome", "entered", "nudgesig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, result = self.capture("where am I?")
        self.assertEqual(result, {"continue": True})
        self.assertTrue(sfx._nudge_painted_this_turn("s1"))
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))

    def test_prompt_claim_loss_commits_no_shown_state_or_signature(self):
        for kind in ("welcome", "entered", "nudgesig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(sfx, "_claim_prompt_nudge", return_value=False):
            _, result = self.capture("where am I?")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_nudge_signature("s1"))

    def test_successful_orientation_orders_claim_emit_then_shown_state(self):
        for kind in ("welcome", "entered", "nudgesig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        events = []
        org = {"alias": "acme-dev", "edition": "Developer", "apiVersion": "65.0"}

        def successful_emit(*_args, **_kwargs):
            events.append("emit")
            print(json.dumps({"continue": True}))

        with mock.patch.object(
                sfx, "_resolve_position_and_org",
                side_effect=lambda _root: events.append("gather") or (self.STATE, org)), \
                mock.patch.object(
                    sfx, "_render_getting_started_welcome",
                    side_effect=lambda *_args, **_kwargs: events.append("render") or "surface"), \
                mock.patch.object(
                    sfx, "_claim_prompt_nudge",
                    side_effect=lambda _context: events.append("claim") or True), \
                mock.patch.object(sfx, "emit", side_effect=successful_emit), \
                mock.patch.object(
                    sfx, "_record_entered", side_effect=lambda _sid: events.append("entered")), \
                mock.patch.object(
                    sfx, "_record_welcomed", side_effect=lambda _sid: events.append("welcomed")), \
                mock.patch.object(
                    sfx, "_record_nudge_shown",
                    side_effect=lambda _sid, _candidate: events.append("signature")):
            self.capture("where am I?")
        self.assertEqual(events, [
            "gather", "render", "claim", "emit", "entered", "welcomed", "signature",
        ])

    def test_render_overview_paint_renders_a_bounded_colored_block_from_the_real_catalog(self):
        # Integration: the paint helper loads the checked-in plugin catalog and returns
        # the visible-channel block — colored with the overview palette (this is the paint
        # path, so color=True), stripping to the same bounded block the command prints.
        # The helper is wholly offline; no org-presence read or CLI patch is needed.
        block = sfx._render_overview_paint(Path(self.tmp.name))
        self.assertIsInstance(block, str)
        self.assertIn("\x1b[22m", block)                           # painted (undim-prefixed accents)
        self.assertNotIn("\x1b[38;2", block)                       # theme-adaptive: no hard-coded truecolor
        plain = strip_ansi(block)
        self.assertIn("what you can do here", plain)
        self.assertIn("INSTALLED", plain)
        self.assertIn("AVAILABLE TO ADD", plain)
        # The overview is EXEMPT from the ≤80 alignment lockup the nudge/readiness/box
        # surfaces keep — it is a plain name+blurb list with no columns to align, so
        # (like the readiness detail row) it runs at its own generous measure. Rows are
        # bounded by _OVERVIEW_ROW_WIDTH, not 80. The hook cannot read the real terminal
        # width in a Conductor/SDK session (COLUMNS unset, stdout non-TTY), so this is a
        # fixed generous width; see the constant's rationale in sf_context.py.
        over = sfx._OVERVIEW_ROW_WIDTH
        self.assertEqual([l for l in plain.splitlines() if len(l) > over], [])

    def test_render_overview_paint_returns_a_present_honest_surface_on_render_failure(self):
        # Owner decision 2026-09-01: the renderer ALWAYS returns a present surface,
        # never None — so the model contract on both front doors (NL + slash command)
        # can be unconditional ("shown above; add your read") with no reproduce fork.
        # On a broken bundled catalog it returns a minimal honest degraded line (a
        # truthful statement the model relays), never a stack trace or a directive to
        # re-run a command.
        with mock.patch.object(sfx, "_capability_overview_facts", side_effect=Exception("boom")):
            surface = sfx._render_overview_paint(Path(self.tmp.name))
        self.assertEqual(surface, sfx._OVERVIEW_UNAVAILABLE)
        self.assertIsInstance(surface, str)
        self.assertTrue(surface.strip())                              # present, non-empty
        self.assertRegex(surface, r"(?i)unavailable")                 # honest degraded statement
        self.assertNotRegex(surface, r"(?i)run |sf-context|command") # not a reproduce/run directive

    def test_available_rows_show_lead_capability_clause_not_enumeration(self):
        # The "what can I do here" overview shows each available plugin's LEAD
        # capability clause (the gist before its first colon/dash — the same
        # one-liner the recommendation bullet uses), not the full paragraph clipped
        # mid-enumeration. Hermetic: synthetic facts, no catalog dependency.
        data = {
            "version": "1.0",
            "installed": [{"name": "salesforce-development", "skills": 3}],
            "available": [
                {"name": "experience-react",
                 "description": "Build Salesforce React UI Bundle apps: scaffold a new React "
                                "UI bundle SFDX starter project and deploy it.",
                 "installCommand": "x"},
                {"name": "some-dash-plugin",
                 "description": "Do the useful thing — with a long trailing enumeration of details.",
                 "installCommand": "x"},
                {"name": "short-plugin",
                 "description": "A short gist with no boundary at all",
                 "installCommand": "x"},
            ],
        }
        plain = strip_ansi("\n".join(sfx._render_capability_overview_lines(data, color=False)))
        # Colon gist: lead shown, post-colon enumeration dropped.
        self.assertIn("Build Salesforce React UI Bundle apps", plain)
        self.assertNotIn("scaffold a new React", plain)
        # Em-dash gist: lead shown, post-dash tail dropped.
        self.assertIn("Do the useful thing", plain)
        self.assertNotIn("trailing enumeration", plain)
        # No boundary: the whole short gist survives.
        self.assertIn("A short gist with no boundary at all", plain)

    def test_footer_cta_points_to_install_before_test_drive_added_then_run_after(self):
        # The overview closes with a getting-started CTA that adapts to whether the
        # salesforce-test-drive plugin is installed: while it is only available to add,
        # point at ADDING it ("Install salesforce-test-drive", the just-ask NL form);
        # once installed, point at RUNNING its command ("Run /salesforce-test-drive:start").
        # Hermetic — synthetic facts, no catalog dependency.
        available = {
            "version": "1.0",
            "installed": [{"name": "salesforce-development", "skills": 3}],
            "available": [{"name": "salesforce-test-drive",
                           "description": "Take a Salesforce capability for a test drive"}],
        }
        plain = "\n".join(sfx._render_capability_overview_lines(available, color=False))
        self.assertIn("Not sure how to start?", plain)
        self.assertIn("Install salesforce-test-drive", plain)
        self.assertNotIn("/salesforce-test-drive:start", plain)   # no dead command pre-install

        installed = {
            "version": "1.0",
            "available": [],
            "installed": [{"name": "salesforce-development", "skills": 3},
                          {"name": "salesforce-test-drive"}],
        }
        plain = "\n".join(sfx._render_capability_overview_lines(installed, color=False))
        self.assertIn("Run /salesforce-test-drive:start", plain)
        self.assertNotIn("Install salesforce-test-drive", plain)  # flips once installed

    def test_footer_cta_paints_amber(self):
        # The getting-started footer CTA reads as one accented call to action: the whole
        # line — lead-in prose and the actionable token alike — is "warn" amber, not the
        # "link" cyan the AVAILABLE-TO-ADD plugin rows above it use.
        facts = {
            "version": "1.0",
            "installed": [{"name": "salesforce-development", "skills": 3}],
            "available": [{"name": "salesforce-test-drive",
                           "description": "Take a Salesforce capability for a test drive"}],
        }
        cta_line = sfx._render_capability_overview_lines(facts, color=True)[-1]
        self.assertIn("salesforce-test-drive", strip_ansi(cta_line))   # confirms it's the CTA line
        self.assertIn(sfx._SGR_YELLOW, cta_line)                       # amber (warn) across the line
        self.assertNotIn(sfx._SGR_CYAN, cta_line)                      # token no longer cyan (link)

    def test_discovery_overview_intent_hits_and_misses(self):
        for hit in ("what can I do here?", "what can I do here", "what can this do",
                    "what can it do", "what can the plugin do", "what are my options"):
            self.assertTrue(sfx._is_discovery_overview_intent(hit), hit)
        # A position question, an org-connect, and a scoped "what can I do WITH x"
        # are not the catalog question — they must not resolve to the overview.
        for miss in ("where am i?", "what's next", "connect an org",
                     "what can I do with apex", "", "add a field to Account"):
            self.assertFalse(sfx._is_discovery_overview_intent(miss), miss)

    def test_detection_hits_and_misses(self):
        for hit in ("where am i?", "what stage am i at", "am i set up?",
                    "what should i do next", "where do i start",
                    "what's next", "whats next", "what next", "what is next",
                    # Fuzzy-tail orientation phrasings (Lever A): still first-person and
                    # about the user's OWN position/progress, so they earn the nudge.
                    "catch me up", "remind me where I left off",
                    "remind me what I was doing", "how far along am I",
                    "am I making progress", "am I making any progress",
                    "what have I done so far", "what have we accomplished",
                    "what have we gotten done so far", "what should I be working on",
                    "how's my project going", "how is my project coming along"):
            self.assertTrue(sfx._is_orientation_question(hit), hit)
        # Bare Salesforce product nouns must NOT paint the nudge: "journey" is
        # Marketing Cloud Journey Builder, "stage" is Opportunity Stage. Anchoring
        # to first-person orientation phrasing keeps these ordinary tasks quiet.
        for miss in ("where is the Account class?", "which directory holds the flows",
                     "add the apex skill", "deploy to prod", "", "x" * 3000,
                     # The explicit `discover journey`/`where` COMMAND form is handled on
                     # the UserPromptExpansion path (it paints the full ranked hints), so
                     # it must NOT also trigger the ambient submit-path nudge — otherwise
                     # the command double-paints.
                     "/discover journey", "discover where", "discover journey",
                     "/salesforce-development:discover where",
                     # capability-catalog question -> discovery overview, NOT the nudge
                     "what can I do here",
                     "build a customer journey in Marketing Cloud",
                     "update the Journey Builder flow",
                     "map the user journey for checkout",
                     "what stage is my opportunity in",
                     # Fuzzy-tail look-alikes: the trailing-preposition guards keep a
                     # task-scoped recap ordinary work, never a position question.
                     "catch me up on the reviewer comments",
                     "how far along am I in the migration",
                     "am I making progress on the refactor",
                     "what have we accomplished with the caching layer",
                     "how's my project going to scale to 10k users",
                     "what should I be working on to fix this bug",
                     "what have I done wrong here",
                     # "...so far <preposition> <object>" is a task recap, not a position
                     # question (the guard on the so-far and remind-me alts suppresses it).
                     "what have we done so far with the caching layer",
                     "what have I accomplished so far on the reviewer comments",
                     "what have I completed so far in the sprint",
                     "remind me where I was in the code"):
            self.assertFalse(sfx._is_orientation_question(miss), miss)

    def test_orientation_prompt_paints_colored_nudge_line_on_systemmessage(self):
        code, result = self.capture("where am i?")
        self.assertEqual(code, 0)
        sysmsg = result["systemMessage"]
        note = result["hookSpecificOutput"]["additionalContext"]
        # journey-nudges Phase 7: the glyph rail's single green "current stage"
        # accent is retired along with the glyph geometry — the word-list + Next
        # line paint via the same theme-adaptive palette every other band uses
        # (undimmed body text for the free-text Next clause), not a hardcoded green.
        self.assertIn("\x1b[22m", sysmsg)   # the Next clause is painted, not raw plain
        # leading blank separates the surface from Claude Code's hook-message
        # wrapper. The paint path colors via the gate, so recompute with it to
        # match exactly — a post-hoc re-select is safe here (same fingerprint,
        # well under the anti-nag session cap), matching the CommandPaintTests
        # golden-recompute pattern.
        candidate = sfx._select_inline_nudge(
            self.STATE, Path.cwd().resolve(), None, session_id="s1")
        self.assertEqual(sysmsg, "\n" + "\n".join(sfx._render_nudge_inline(
            self.STATE, candidate, color=sfx._banner_color_enabled())))
        stripped = strip_ansi(sysmsg)
        self.assertIn("sfdx project: acme-crm", stripped)
        self.assertIn("org: acme-dev ✓", stripped)
        self.assertTrue(all(sfx._is_width_exempt(l) or len(l) <= 80 for l in stripped.splitlines()))
        # Model note is ANSI-free, names the stage, and forbids reproduction — it
        # must NOT hand the model the nudge ASCII to parrot.
        self.assertNotIn("\x1b", note)
        self.assertIn("Build", note)
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)add only your")
        self.assertNotIn("●", note)   # the glyph rail is not in the model note

    def test_non_orientation_prompt_is_silent_continue(self):
        for prompt in ("where is the Account class?", "deploy to prod",
                       "which file holds the flows?", "add the apex skill", ""):
            with self.subTest(prompt=prompt):
                code, result = self.capture(prompt)
                self.assertEqual((code, result), (0, {"continue": True}))

    def test_nudge_painting_branches_record_the_per_turn_dedup_flag(self):
        # Every nudge branch atomically claims its fallback prompt namespace. Each
        # direct UserPromptSubmit call rotates that old-host token; silent turns do not claim.
        self.capture("where am i?")                                 # in-project orientation nudge
        self.assertTrue(sfx._nudge_painted_this_turn("s1"), "orientation nudge branch")
        self.capture_status("what's the status of the project")     # status bands + nudge
        self.assertTrue(sfx._nudge_painted_this_turn("s1"), "status branch")
        self.capture("add a field to the Account object")           # entered => silent, no nudge
        self.assertFalse(sfx._nudge_painted_this_turn("s1"), "silent turn must not set the flag")

    def test_orientation_paint_records_the_signature_for_the_wayfinder(self):
        # The reprint-on-change gate's other half: an orientation paint records WHAT
        # candidate it showed (bookkeeping only — this branch is the unmigrated bare
        # nudge, so nothing was actually shown as a Next line), so a same-turn connect
        # (the wayfinder) can tell the nudge did not change and skip a duplicate.
        # Companion to the per-turn flag test above.
        sfx._session_marker("s1", "nudgesig").unlink(missing_ok=True)
        self.capture("where am i?")
        expected_candidate = sfx._select_inline_nudge(
            self.STATE, Path.cwd().resolve(), None, session_id="s1",
        )
        self.assertEqual(
            sfx._last_nudge_signature("s1"), sfx._nudge_signature(expected_candidate),
        )

    def test_lever_c_dedupes_on_a_regex_hit_and_paints_on_a_regex_miss(self):
        # UserPromptSubmit and PostToolUse compose through the same fallback prompt
        # namespace on an old-host payload with no native prompt_id.

        def run_journey_paint():
            payload = io.StringIO(json.dumps(
                {"tool_input": {"command": "sf-context discover journey"}, "session_id": "s1"}))
            out = io.StringIO()
            with mock.patch.object(sfx, "_journey_state", return_value=self.STATE), \
                    mock.patch.object(sfx.sys, "stdin", payload), \
                    mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
                sfx.cmd_journey_paint()
            return json.loads(out.getvalue())

        # (a) regex HIT: the UserPromptSubmit paint sets the flag; journey-paint dedupes.
        self.capture("where am i?")
        self.assertTrue(sfx._nudge_painted_this_turn("s1"))
        self.assertEqual(run_journey_paint(), {"continue": True})   # deduped — no second nudge

        # (b) regex MISS (the Lever-C win): a phrase _is_orientation_question rejects leaves
        # the flag unset (the UserPromptSubmit hook stays silent), so journey-paint paints.
        self.assertFalse(sfx._is_orientation_question("what's the state of things"))
        _, ups = self.capture("what's the state of things")
        self.assertEqual(ups, {"continue": True})
        self.assertFalse(sfx._nudge_painted_this_turn("s1"))
        self.assertIn("systemMessage", run_journey_paint())

    def test_explicit_discovery_command_forms_stay_silent_on_submit_path(self):
        # A typed `/discover journey`/`where` paints its full ranked hints list on the
        # UserPromptExpansion path (cmd_command_paint, covered by CommandPaintTests).
        # The ambient UserPromptSubmit path must therefore stay SILENT for the command
        # form — otherwise it double-paints a single nudge on top of the command's hints.
        for prompt in ("/discover journey", "/salesforce-development:discover where",
                       "discover journey"):
            with self.subTest(prompt=prompt):
                code, result = self.capture(prompt)
                self.assertEqual((code, result), (0, {"continue": True}))

    def test_journey_product_term_does_not_paint_end_to_end(self):
        # Regression for the confirmed over-fire: a Journey Builder / customer-journey
        # task prompt must be a silent continue, not an unasked-for painted nudge.
        for prompt in ("build a customer journey in Marketing Cloud",
                       "where is the journey builder flow?"):
            with self.subTest(prompt=prompt):
                _, result = self.capture(prompt)
                self.assertEqual(result, {"continue": True})

    def test_orientation_is_plain_under_no_color(self):
        _, result = self.capture("where am i?", env={"NO_COLOR": "1"})
        self.assertNotIn("\x1b", result["systemMessage"])
        self.assertNotIn("\x1b", result["hookSpecificOutput"]["additionalContext"])

    def test_malformed_stdin_and_render_crash_fail_open(self):
        # Malformed payload → continue.
        payload = io.StringIO("not json")
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        self.assertEqual((code, json.loads(out.getvalue())), (0, {"continue": True}))
        # A crash while rendering an orientation prompt → continue (never disrupts).
        payload2 = io.StringIO(json.dumps({"prompt": "where am i"}))
        out2 = io.StringIO()
        with mock.patch.object(sfx, "_journey_state", side_effect=RuntimeError("boom")), \
                mock.patch.object(sfx.sys, "stdin", payload2), redirect_stdout(out2):
            code2 = sfx.cmd_orientation_paint()
        self.assertEqual((code2, json.loads(out2.getvalue())), (0, {"continue": True}))

    def test_paint_stays_within_eighty_on_maximal_untrusted_names(self):
        hostile = {**self.STATE, "context": {
            "project": "Z" * 300, "orgAlias": "A" * 300,
            "orgStatus": "reachable", "sourceTracking": "unknown"}}
        payload = io.StringIO(json.dumps({"prompt": "where am i"}))
        out = io.StringIO()
        with mock.patch.object(sfx, "_journey_state", return_value=hostile), \
                mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            sfx.cmd_orientation_paint()
        stripped = strip_ansi(json.loads(out.getvalue())["systemMessage"])
        self.assertEqual([l for l in stripped.splitlines() if len(l) > 80 and not sfx._is_width_exempt(l)], [])

    def test_orientation_paint_note_is_compact_facts_not_a_rendering_handbook(self):
        _, result = self.capture("where am i?")
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not reproduce")
        for fact in ("current stage: Project", "next stage: Build", "reached:",
                     "no evidence:", "recent events:", "next action:"):
            self.assertIn(fact, note)
        self.assertNotIn("MICRO-TIER RENDERING CONTRACT", note)
        self.assertNotIn("Pick ONE vehicle", note)
        self.assertNotIn("█", note)
        self.assertNotIn("●", note)
        self.assertNotIn("◉", note)
        self.assertNotIn("○", note)
        self.assertNotIn("\x1b", note)
        self.assertLessEqual(len(note), 1500)
        self.assertTrue(all(len(line) <= 120 for line in note.splitlines()), note)

    def test_status_paint_note_has_the_same_compact_fact_budget(self):
        note = sfx._status_paint_note(self.STATE)
        for fact in ("current stage: Project", "next stage: Build", "reached:",
                     "no evidence:", "recent events:", "next action:"):
            self.assertIn(fact, note)
        for decorative in ("█", "●", "◉", "○", "MICRO-TIER RENDERING CONTRACT"):
            self.assertNotIn(decorative, note)
        self.assertLessEqual(len(note), 1500)
        self.assertTrue(all(len(line) <= 120 for line in note.splitlines()), note)

    def test_attempted_deploy_surfaces_honestly_in_the_micro_facts_end_to_end(self):
        # A recorded FAILED deploy in this project makes a cursor-Deploy micro block
        # read `attempted` with the failure event on record — the honest "not
        # deployed" signal — while the block invents no error text or count (none is
        # persisted). The macro nudge on systemMessage is unaffected.
        Path(".sf").mkdir(exist_ok=True)
        Path(".sf/phase-history.jsonl").write_text(
            json.dumps({"type": "deploy", "stage": "Deploy", "outcome": "failed",
                        "source": "cmd_post_deploy_failure",
                        "ts": "2026-08-03T00:00:00Z"}) + "\n", encoding="utf-8")
        deploy_state = {**self.STATE, "currentStage": "Deploy",
                        "stages": [{"name": n, "status": s} for n, s in [
                            ("Setup", "complete"), ("Connect", "complete"),
                            ("Build", "complete"), ("Test", "complete"),
                            ("Deploy", "current"), ("Observe", "future")]]}
        payload = io.StringIO(json.dumps({"prompt": "where am i?", "session_id": "s1"}))
        out = io.StringIO()
        with mock.patch.object(sfx, "_journey_state", return_value=deploy_state), \
                mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            sfx.cmd_orientation_paint()
        note = json.loads(out.getvalue())["hookSpecificOutput"]["additionalContext"]
        # The rail's ◉ sits on the frontier (latest reached = Test); the failed-deploy
        # cursor is the forward gap, so it reads as "next stage", not "current stage".
        self.assertIn("current stage: Test", note)
        self.assertIn("next stage: Deploy", note)
        self.assertIn("substate: attempted", note)
        self.assertIn("outcome=failed", note)
        # the deterministic block portion never fabricates error text (unlike the spike fixture)
        block_part = note.split("MICRO-TIER RENDERING CONTRACT")[0]
        self.assertNotIn("error", block_part.lower())


class MicroTierTests(unittest.TestCase):
    """Decision-A HYBRID micro tier: the hook emits a deterministic journey-context
    fact block + rendering contract on the model-only channel; the model renders the
    tier. The block may carry ONLY fields a writer persists to phase-history.jsonl
    (type/outcome/source) — never the spike fixture's invented error text/counts — so
    the north star holds by construction."""

    @staticmethod
    def _state(cursor):
        return {
            "stages": [{"name": n, "status": ("current" if n == cursor else "future")}
                       for n in sfx.JOURNEY_STAGES],
            "currentStage": cursor,
            "context": {},
        }

    def test_substate_attempted_when_a_failed_event_is_on_record(self):
        self.assertEqual(
            sfx._current_stage_substate([{"stage": "Deploy", "outcome": "failed"}]),
            "attempted")

    def test_substate_working_on_nonfailed_activity(self):
        # A present/observe-skill dispatch is activity, not a failure -> working.
        self.assertEqual(
            sfx._current_stage_substate([{"stage": "Observe", "outcome": "present"}]),
            "working")

    def test_substate_entered_when_nothing_recorded(self):
        self.assertEqual(sfx._current_stage_substate([]), "entered")

    def test_facts_filter_to_cursor_stage_and_reject_unknown_record_fields(self):
        # History spans stages and carries one hostile extra-key record. The parser
        # rejects that entire row; only the valid cursor-stage event reaches context.
        history = [
            {"stage": "Test", "outcome": "passed", "type": "test-run", "source": "cmd_post_test_run"},
            {"stage": "Deploy", "outcome": "failed", "type": "deploy",
             "source": "cmd_post_deploy_failure", "errors": ["invented"], "error_count": 2},
            {"stage": "Deploy", "outcome": "failed", "type": "deploy",
             "source": "cmd_post_deploy_failure"},
        ]
        facts = sfx._journey_micro_facts(self._state("Deploy"), history=history)
        self.assertEqual(facts["cursor"], "Deploy")
        self.assertEqual(facts["substate"], "attempted")
        self.assertEqual(len(facts["events"]), 1)                    # cursor stage only
        self.assertEqual(set(facts["events"][0]), {"type", "outcome", "source"})
        self.assertEqual(facts["events"][0]["outcome"], "failed")
        # journey-nudges Phase 5: no candidate was passed, so this degrades to the
        # neutral "nothing selected" text rather than a retired per-stage lookup.
        self.assertEqual(facts["likely_next"], "no outstanding next step")

    def test_events_are_capped(self):
        history = [{"stage": "Observe", "outcome": "present", "type": "observe-skill", "source": "s"}
                   for _ in range(sfx._MICRO_EVENT_CAP + 4)]
        facts = sfx._journey_micro_facts(self._state("Observe"), history=history)
        self.assertEqual(len(facts["events"]), sfx._MICRO_EVENT_CAP)

    def test_context_block_is_plain_names_the_facts_and_invents_no_errors(self):
        block = sfx._render_journey_context_block(sfx._journey_micro_facts(
            self._state("Deploy"),
            history=[{"stage": "Deploy", "outcome": "failed", "type": "deploy",
                      "source": "cmd_post_deploy_failure"}]))
        self.assertNotIn("\x1b", block)                              # plain
        self.assertNotIn("●", block)                                 # no macro glyph rail
        self.assertIn("current stage: Deploy", block)
        self.assertIn("substate: attempted", block)
        self.assertIn("outcome=failed", block)
        self.assertNotIn("error", block.lower())

    def test_block_states_none_when_no_events(self):
        block = sfx._render_journey_context_block(
            sfx._journey_micro_facts(self._state("Setup"), history=[]))
        self.assertIn("substate: entered", block)
        self.assertIn("events on record for this stage: none", block)

    def test_micro_tier_note_is_compact_facts_only(self):
        note = sfx._micro_tier_note(self._state("Deploy"))
        self.assertNotIn("\x1b", note)
        self.assertNotIn("●", note)
        self.assertNotIn("○", note)
        # This fixture reaches nothing, so Deploy is the cursor (forward gap): it reads
        # as "next stage"; "current stage" is the (empty) frontier, not the cursor.
        self.assertIn("next stage: Deploy", note)
        self.assertIn("recent events", note)
        self.assertIn("next action:", note)
        self.assertNotIn("MICRO-TIER RENDERING CONTRACT", note)
        self.assertNotIn("you-are-here card", note)
        self.assertLessEqual(len(note), 1500)

    def test_block_is_byte_reproducible(self):
        history = [{"stage": "Deploy", "outcome": "failed", "type": "deploy", "source": "x"}]
        render = lambda: sfx._render_journey_context_block(
            sfx._journey_micro_facts(self._state("Deploy"), history=history))
        self.assertEqual(render(), render())

    def test_facts_default_to_the_durable_read_when_no_history_injected(self):
        # With no history argument the facts use the canonical parser result.
        empty = sfx.PhaseHistoryResult(accepted=0, rejected=0, truncated=False, records=[])
        with mock.patch.object(sfx, "_load_phase_history_result", return_value=empty):
            facts = sfx._journey_micro_facts(self._state("Build"))
        self.assertEqual(facts["substate"], "entered")
        self.assertEqual(facts["events"], [])


class GettingStartedWelcomeTests(unittest.TestCase):
    """Side A of the paint hook: OUTSIDE a Salesforce project, a prompt that names
    Salesforce or CRM (the product category) emits a MODEL-FACING-ONLY note (no
    visible paint — entered-project-splash plan, Change 2), once per session. The
    plugin is global, so orientation phrasing alone must NOT trip this in a random
    dir — only an explicit Salesforce/CRM product cue does."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = Path.cwd()
        os.chdir(self.tmp.name)   # NO sfdx-project.json — this is the outside case
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        self._orig_runtime_dir = sfx._PROMPT_RUNTIME_DIR
        self._orig_plugin_proposal_dir = sfx._PLUGIN_PROPOSAL_DIR
        self._orig_plugin_flow_dir = sfx._PLUGIN_FLOW_DIR
        sfx._WELCOME_MARKER_DIR = Path(self.tmp.name)  # isolate the session marker
        # The welcome bridge (option B) reuses the in-project catalog scorer, which
        # persists a proposal ledger + decision flow keyed by session id. Redirect
        # those runtime dirs into the temp dir so a bridged rec never leaks state
        # (for the fixed "s1" id) between tests.
        sfx._PROMPT_RUNTIME_DIR = Path(self.tmp.name) / "runtime"
        sfx._PLUGIN_PROPOSAL_DIR = sfx._PROMPT_RUNTIME_DIR / "plugin-proposals"
        sfx._PLUGIN_FLOW_DIR = sfx._PROMPT_RUNTIME_DIR / "plugin-flows"
        # Pin the enabled-plugin set to a true Side-A newcomer (only the base
        # plugin installed). Otherwise these chrome tests are host-coupled: on a
        # machine where salesforce-test-drive happens to be installed, the Shape-2
        # welcome pointer fires and folds its block into the getting-started
        # welcome, floating the assertions below. A newcomer has no sibling
        # plugins, so the Side-A pointer returns None here — and experience-cms
        # (the bridge tests) stays uninstalled and therefore still recommendable.
        self._enabled_patch = mock.patch.object(
            sfx, "_enabled_plugin_names", return_value={"salesforce-development"})
        self._enabled_patch.start()
        self.addCleanup(self._enabled_patch.stop)

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        sfx._PROMPT_RUNTIME_DIR = self._orig_runtime_dir
        sfx._PLUGIN_PROPOSAL_DIR = self._orig_plugin_proposal_dir
        sfx._PLUGIN_FLOW_DIR = self._orig_plugin_flow_dir
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def capture(self, prompt, session_id="s1"):
        payload = io.StringIO(json.dumps({"prompt": prompt, "session_id": session_id}))
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        return code, json.loads(out.getvalue())

    def test_no_out_of_project_surface_flips_the_welcome_flag(self):
        # Invariant (owner directive): NOTHING in the out-of-project experience may
        # record the `welcome` splash flag — only a successful `sf project generate`
        # (cmd_scaffold_paint) flips it. If any Side-A prompt surface burned `welcome`
        # it would pre-suppress the scaffold splash, the one visible surface meant to
        # greet a freshly created project. Every Side-A handler records its OWN trip
        # marker (modelnote / create_flow_shown / nudge_shown) instead — never welcome.
        sid = "s1"
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None):
            # A bare Salesforce mention trips the session (records modelnote) but must
            # NOT record welcome — it is model-facing-only, nothing was painted.
            self.capture("let's build something on salesforce", session_id=sid)
            self.assertTrue(sfx._model_noted_this_session(sid))    # tripped
            self.assertFalse(sfx._welcomed_this_session(sid))      # but never welcomed
            # With the session tripped, every other Side-A intent must also leave
            # welcome unset (create-flow, orientation, overview, connect, environment).
            for prompt in (
                "create a new salesforce project",
                "where am I",
                "what can I do here?",
                "connect an org",
                "set up my environment",
            ):
                self.capture(prompt, session_id=sid)
                self.assertFalse(
                    sfx._welcomed_this_session(sid),
                    f"out-of-project prompt {prompt!r} must not flip the welcome flag",
                )

    def test_salesforce_mention_emits_model_facing_note_only(self):
        # Change 2 (entered-project-splash plan): a Salesforce mention outside a
        # project no longer paints ANY visible chrome — no banner, no rail, no org/
        # project bands. It emits a MODEL-FACING-ONLY note steering the model to offer
        # the discover-overview command or project creation, and explicitly telling it
        # not to paint a banner or welcome surface itself. Pin _configured_target_alias
        # to None (a true newcomer) — irrelevant to the (now org-agnostic) note, but
        # keeps this test independent of the real ~/.sf state.
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None):
            _, result = self.capture("I want to build something on Salesforce")
        self.assertNotIn("systemMessage", result)                # no visible paint at all
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not (?:reproduce|paint)")
        self.assertRegex(note, r"(?i)discover overview")
        self.assertRegex(note, r"(?i)create a new salesforce dx project")
        # The getting-started entry is the more common "build something" front door and
        # ALSO leads to a scaffold — so it must carry the same template-choice guardrail
        # as the create-flow note: route the scaffold through dx-project-create, never
        # assume a template, and don't collapse a UI ask to LWC (Image #5 regression).
        self.assertIn("dx-project-create", note)
        self.assertRegex(note, r"(?i)template is the user's explicit choice|never assume")
        self.assertRegex(note, r"(?i)react")
        self.assertRegex(note, r"(?i)collapse .*(?:to )?LWC|LWC.*default")

    def test_welcome_never_consults_readiness_or_runs_a_scan(self):
        # The hard D6 guarantee still holds post-demotion: the model-facing-only note
        # must never invoke the ~9s check-tools scan (I4) and must not read the
        # readiness signal — it hands off to the model instead of probing anything.
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None), \
                mock.patch.object(sfx, "cmd_check_tools") as scan, \
                mock.patch.object(sfx, "_welcome_readiness") as readiness:
            _, result = self.capture("help me build something on Salesforce")
        scan.assert_not_called()          # the ~9s scan never runs on the greeting (I4)
        readiness.assert_not_called()     # the note never reads readiness at all
        self.assertNotIn("systemMessage", result)                # model-facing only, no paint
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not (?:reproduce|paint)")

    def test_welcome_paints_only_once_per_session(self):
        self.capture("I want to build on Salesforce", session_id="s1")
        _, again = self.capture("help me build a Salesforce app", session_id="s1")
        self.assertEqual(again, {"continue": True})

    def test_out_of_project_connect_intent_when_tripped_hands_off_the_flow(self):
        # Side A (D9/D10): once the session is tripped (welcomed), a connect-org intent
        # outside a project hands the model the cheap-check + ternary note — model-facing
        # only, no paint. This is the core newcomer path (they said "build on Salesforce"
        # first). capture() clears the env, so `sf` is absent → the setup route.
        sfx._record_model_noted("s1")
        _, result = self.capture("connect an org")
        self.assertNotIn("systemMessage", result)                # model-facing only, no paint
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("platform-environment-validate", note)     # sf absent (cleared env) → setup
        self.assertRegex(note, r"(?i)do not attempt a login")

    def test_out_of_project_connect_intent_untripped_stays_silent(self):
        # The Side A guard: untripped (no welcome yet), a bare "connect an org" in a
        # random dir is not a Salesforce cue, so it stays silent (signal, not noise) —
        # the model handles it, and the plugin never runs the login regardless.
        _, result = self.capture("connect an org")
        self.assertEqual(result, {"continue": True})

    def test_create_intent_when_tripped_drives_scaffold_with_light_catalog_nudge(self):
        # D11/Q4=c (revised 2026-08-04): the user asked to CREATE a project, so the OUTCOME
        # is a scaffolded project — the hook does NOT paint the capability catalog here (that
        # read as a non-sequitur to a directive "set me up a new project"). It hands the model
        # the create-flow note (model-facing ONLY, no visible paint): env-verify → pick a
        # direction → scaffold, plus ONE light nudge that the catalog is browsable. A second
        # create-intent does NOT re-fire (once per session = signal, not noise).
        sfx._record_model_noted("s1")
        with mock.patch.object(sfx, "_render_overview_paint") as rp:
            _, first = self.capture("create a Salesforce project")
            _, second = self.capture("let's scaffold a new project")
        rp.assert_not_called()                                    # catalog is never painted here
        self.assertNotIn("systemMessage", first)                  # model-facing only — no paint
        note = first["hookSpecificOutput"]["additionalContext"]
        self.assertIn("platform-environment-validate", note)      # verify env before scaffolding
        self.assertRegex(note, r"(?i)direction")                  # pick a direction to build
        self.assertRegex(note, r"(?i)scaffold")                   # the outcome is a scaffolded project
        self.assertIn("what can I do here?", note)                # the one light catalog nudge
        # Template must be an EXPLICIT choice, not inferred from the high-level direction:
        # the note routes the scaffold through dx-project-create (which owns the template
        # picker) and forbids silently defaulting to standard. Regression for the reported
        # miss: picking "A UI (LWC / pages)" got mapped to `standard` with no template ask.
        self.assertIn("dx-project-create", note)                  # scaffold via the skill that asks
        self.assertRegex(note, r"(?i)template")                   # the template decision is called out
        self.assertRegex(note, r"(?i)never default to standard")  # no silent standard fallback
        # A UI direction must NOT collapse to LWC — the note names React/Angular as
        # first-class UI options so the model doesn't narrow "a UI" to Lightning.
        # Regression for the reported miss: picking "UI (LWC / Lightning pages)" jumped
        # straight to LWC + a standard project with no framework choice.
        self.assertRegex(note, r"(?i)react")                      # React/Angular are UI options too
        self.assertRegex(note, r"(?i)not\b.*\bLWC|LWC\b.*default") # don't assume LWC by default
        self.assertTrue(sfx._create_flow_shown_this_session("s1"))
        self.assertEqual(second, {"continue": True})              # once only — no re-fire

    def test_create_flow_hot_path_checks_marker_before_lock(self):
        sfx._record_model_noted("s1")
        sfx._record_create_flow_shown("s1")
        with mock.patch.object(sfx, "_acquire_create_flow_lock", return_value=None) as acquire:
            _, result = self.capture("create a Salesforce project")
        self.assertEqual(result, {"continue": True})
        acquire.assert_not_called()

    def test_concurrent_create_flow_contenders_emit_once_and_mark_once(self):
        # Both real hook processes reach a release barrier before classification. The
        # delayed emit then forces an unlocked check→emit→record implementation to
        # overlap: both contenders would observe the marker absent and both emit.
        gate = Path(self.tmp.name) / "release-create-flow"
        script = (
            "import pathlib,runpy,sys,time; "
            "ns=runpy.run_path(sys.argv[1]); g=ns['cmd_orientation_paint'].__globals__; "
            "g['_WELCOME_MARKER_DIR']=pathlib.Path(sys.argv[2]); "
            "g['_record_model_noted']('s1'); original=g['emit']; "
            "pathlib.Path(sys.argv[3]).write_text('ready'); gate=pathlib.Path(sys.argv[4]); "
            "deadline=time.monotonic()+5; "
            "exec('while not gate.exists() and time.monotonic() < deadline:\\n time.sleep(.01)'); "
            "g['emit']=lambda *a,**k:(time.sleep(0.5),original(*a,**k))[-1]; "
            "g['cmd_orientation_paint'](payload={'prompt':'create a Salesforce project',"
            "'session_id':'s1'}) if gate.exists() else sys.exit(4)"
        )
        workers = []
        for index in range(2):
            ready = Path(self.tmp.name) / f"create-worker-{index}.ready"
            workers.append(subprocess.Popen(
                [sys.executable, "-c", script, os.fspath(SF_CONTEXT_PATH),
                 os.fspath(sfx._WELCOME_MARKER_DIR), os.fspath(ready), os.fspath(gate)],
                cwd=self.tmp.name,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ))
        deadline = time.monotonic() + 5
        while (len(list(Path(self.tmp.name).glob("create-worker-*.ready"))) < 2
               and time.monotonic() < deadline):
            time.sleep(0.01)
        self.assertEqual(len(list(Path(self.tmp.name).glob("create-worker-*.ready"))), 2)
        gate.write_text("go", encoding="utf-8")
        results = [worker.communicate(timeout=10) for worker in workers]
        self.assertEqual([worker.returncode for worker in workers], [0, 0], results)
        payloads = [json.loads(stdout) for stdout, _stderr in results]
        emitted = [
            result for result in payloads
            if result.get("hookSpecificOutput", {}).get("additionalContext")
        ]
        self.assertEqual(len(emitted), 1, results)
        self.assertTrue(sfx._create_flow_shown_this_session("s1"))
        self.assertEqual(
            len(list(Path(self.tmp.name).glob("createflow-[0-9a-f]*"))), 1,
            "one durable shown marker is committed",
        )

    def test_create_flow_retries_after_emit_failure(self):
        sfx._record_model_noted("s1")
        with mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, failed = self.capture("create a Salesforce project")
        self.assertEqual(failed, {"continue": True})
        self.assertFalse(sfx._create_flow_shown_this_session("s1"))

        _, retry = self.capture("create a Salesforce project")
        self.assertIn("additionalContext", retry["hookSpecificOutput"])
        self.assertTrue(sfx._create_flow_shown_this_session("s1"))

    def test_create_intent_untripped_stays_silent(self):
        # Untripped, a bare "scaffold a new project" in a random dir is not a Salesforce
        # cue (no mention), so it stays silent — no create-flow note is emitted.
        _, result = self.capture("scaffold a new project")
        self.assertEqual(result, {"continue": True})

    def test_build_stage_create_does_not_trigger_discovery_on_create(self):
        # Precision: "create a custom object" is Build-stage work inside a project, not
        # a project-CREATION intent, so it must NOT fire the create-flow note even when
        # tripped (and it has no Salesforce mention, so it stays silent).
        sfx._record_model_noted("s1")
        _, result = self.capture("create a custom object")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._create_flow_shown_this_session("s1"))

    def test_create_intent_recognizes_set_up_phrasings(self):
        # "set up a project" is the most common way people phrase scaffolding one, so it
        # must trip discovery-on-create — including "setup" (no space) and "setting up".
        # Precision holds: "project" must still sit nearby, so setup phrasings that are
        # NOT about a project (environment, pipeline) stay silent.
        for prompt in ("lets setup a project", "lets set up a project",
                       "set up a Salesforce project", "setting up a new project"):
            self.assertTrue(sfx._is_create_project_intent(prompt), prompt)
        for prompt in ("set up my environment", "set up the deploy pipeline for this service"):
            self.assertFalse(sfx._is_create_project_intent(prompt), prompt)

    def test_create_intent_recognizes_both_scaffold_command_forms(self):
        # The typed scaffold command trips create-intent whether it's the deprecated
        # `sf project generate` or the non-deprecated `sf template generate project`.
        for prompt in ("sf project generate -n acme", "sfdx project create -n acme",
                       "sf template generate project -t standard -n acme"):
            self.assertTrue(sfx._is_create_project_intent(prompt), prompt)
        # A different `template generate` subcommand is not project scaffolding.
        self.assertFalse(sfx._is_create_project_intent("sf template generate apex-class -n Foo"))

    def test_environment_intent_matrix(self):
        # The environment check is a stage-independent capability (D5) with its own direct
        # trigger — distinct from connect and create, which merely CALL it when applicable.
        for prompt in ("set up my environment", "check my environment", "verify my toolchain",
                       "am I set up", "is my environment ready", "fix my tooling",
                       "get my dev environment ready"):
            self.assertTrue(sfx._is_environment_intent(prompt), prompt)
        for prompt in ("set up a project", "connect an org", "create a custom object",
                       "what can I do here?", "build me an app"):
            self.assertFalse(sfx._is_environment_intent(prompt), prompt)

    def test_environment_intent_when_tripped_routes_to_the_check(self):
        # Tripped (welcomed) Side A: "set up my environment" hands the model a note steering
        # to the on-demand readiness check — the ~9s scan never runs in the hook (I4), and
        # nothing is painted (model-facing only).
        sfx._record_model_noted("s1")
        with mock.patch.object(sfx, "cmd_check_tools") as scan:
            _, result = self.capture("set up my environment")
        scan.assert_not_called()                        # I4: never scans in the hook
        self.assertNotIn("systemMessage", result)       # model-facing only, no paint
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("platform-environment-validate", note)
        self.assertIn("/salesforce-development:setup", note)

    def test_environment_intent_untripped_stays_silent(self):
        # Untripped Side A: "set up my environment" alone is not a Salesforce cue (the
        # plugin is global), so it stays silent until the session is welcomed.
        _, result = self.capture("set up my environment")
        self.assertEqual(result, {"continue": True})

    def test_environment_intent_in_project_routes_to_the_check(self):
        # Side B (in a project): being in a project IS the signal, so no welcomed gate —
        # "check my environment" routes straight to the stage-independent on-demand check.
        Path("sfdx-project.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(sfx, "cmd_check_tools") as scan:
            _, result = self.capture("check my environment", session_id="sB")
        scan.assert_not_called()
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("platform-environment-validate", note)

    def test_orientation_phrasing_without_salesforce_stays_silent_outside(self):
        # "where am i?" in a random directory must NOT paint — that's the Side A guard.
        # Untripped (no prior welcome this session), so orientation phrasing alone is
        # not a Salesforce cue. The tripped counterpart paints (test below).
        for prompt in ("where am i?", "what can I do here", "what should I do next"):
            with self.subTest(prompt=prompt):
                _, result = self.capture(prompt)
                self.assertEqual(result, {"continue": True})

    def test_tripped_out_of_project_orientation_ask_paints_the_nudge(self):
        # The other half of the Side A guard: once the plugin has been tripped this
        # session (welcomed), an orientation question DOES paint the Tier-1 position
        # nudge — the same discipline as the overview ask. The nudge rides the visible
        # channel, and the model gets the do-not-reproduce note so it never re-runs
        # `discover journey` or reprints the nudge. Without this branch the model
        # serviced "where am I" itself and double-printed a colorless nudge (the bug).
        sfx._record_model_noted("s1")
        # The natural out-of-project orientation state after the redesign: an all-○
        # teaching map ("here's the whole path; you're at the start"), nothing earned
        # yet. The state still carries currentStage=Connect for the model, but with no
        # reached stage the visible nudge has no accent — it is entirely plain ○.
        state = {
            "stages": [{"name": n, "status": s} for n, s in [
                ("Connect", "current"), ("Project", "future"), ("Build", "future"),
                ("Test", "future"), ("Deploy", "future"), ("Observe", "future")]],
            "currentStage": "Connect",
            "context": {},
        }
        payload = io.StringIO(json.dumps({"prompt": "where am i?", "session_id": "s1"}))
        out = io.StringIO()
        with mock.patch.object(sfx, "_journey_state", return_value=state), \
                mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        result = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        # journey-nudges Phase 7: the glyph rail is retired — this surface now
        # paints the word-list + single ladder-winning nudge. Recompute the same
        # candidate the code path resolves (session_id="s1", root=cwd) to build
        # the golden; a post-hoc re-select is safe (same fingerprint, well under
        # the anti-nag session cap).
        candidate = sfx._select_inline_nudge(
            state, Path.cwd().resolve(), None, session_id="s1")
        self.assertEqual(result["systemMessage"],
                         "\n" + "\n".join(sfx._render_nudge_inline(
                             state, candidate, color=sfx._banner_color_enabled())))
        # Nothing is reached in this no-evidence state, so there is no word-list
        # line and no green accent — the glyph rail's cursor-accent concept never
        # carries over to the nudge renderer either way.
        self.assertNotIn("\x1b[32m", result["systemMessage"])
        self.assertNotIn("create a Salesforce project", result["systemMessage"])  # NOT the welcome
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                              # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)do not run the journey command")

    def test_locator_question_mentioning_salesforce_stays_silent(self):
        _, result = self.capture("where is the salesforce config file?")
        self.assertEqual(result, {"continue": True})

    def test_crm_mention_emits_model_facing_note_only(self):
        # The Side-A cue is the product CATEGORY, not just the vendor: a newcomer not yet
        # sold on Salesforce ("I want to build a CRM") names the category, and CRM is
        # Salesforce's space, so out of a project a CRM mention reaches the same
        # model-facing-only note a "Salesforce" mention does. Lean assertion — the
        # salesforce test above pins the note's full content; here we only prove the
        # cue reaches it (no paint, note present).
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None):
            _, result = self.capture("I want to build a CRM")
        self.assertNotIn("systemMessage", result)
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not (?:reproduce|paint)")

    def test_getting_started_intent_cue_set_is_salesforce_or_crm(self):
        # The trigger predicate directly: the minimal cue set is {salesforce, crm} (plural
        # tolerated), word-boundary matched, with the locator exclusion still winning. A
        # prompt naming neither — the unrelated-work case the global-plugin boundary exists
        # to protect ("my mobile game") — stays False so the welcome never intrudes.
        for prompt in ("I want to build something on Salesforce", "I want to build a CRM",
                       "which CRMs should I compare?"):
            with self.subTest(cue=prompt):
                self.assertTrue(sfx._is_getting_started_intent(prompt))
        for prompt in ("where do I start with my mobile game?", "help me build a mobile game",
                       "where is the crm config file?", "where is the salesforce config file?",
                       ""):
            with self.subTest(non_cue=prompt):
                self.assertFalse(sfx._is_getting_started_intent(prompt))

    def test_tripped_out_of_project_overview_ask_paints_the_block(self):
        # Rule (c): outside a project a capability question ("what can I do here?")
        # paints the Tier-1 overview — but ONLY once the plugin has already been
        # tripped this session (the welcome/logo has shown, i.e. welcomed). Here it
        # has, so the block paints directly on the visible channel and the model gets
        # the do-not-reproduce note. It is disjoint from the getting-started intent, so
        # the welcome is NOT re-drawn (its "create a Salesforce project" CTA is absent).
        sfx._record_model_noted("s1")
        block = "Salesforce Headless 360 · what you can do here\n(fixed test block)"
        with mock.patch.object(sfx, "_render_overview_paint", return_value=block) as rp:
            _, result = self.capture("what can I do here?")
        rp.assert_called_once()
        self.assertEqual(result["systemMessage"], "\n" + block)     # painted directly
        self.assertNotIn("create a Salesforce project", result["systemMessage"])  # NOT the welcome
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                              # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)overview")

    def test_untripped_out_of_project_overview_ask_never_builds_the_block(self):
        # Rule (c), the other half: without a prior trip this session, a bare "what
        # can I do here?" in a random dir is not itself a Salesforce cue (it never
        # matches the getting-started intent), so we stay silent AND never even build
        # the overview block — the model falls back to routing to the overview command.
        with mock.patch.object(sfx, "_render_overview_paint") as rp:
            _, result = self.capture("what can I do here?")
        self.assertEqual(result, {"continue": True})
        rp.assert_not_called()

    def test_tripped_out_of_project_overview_ask_fails_open_on_render_error(self):
        # Fail-open on the tripped Side-A path: the trip gate opens and the helper is
        # called, but a render failure (None) must fall through to a silent continue,
        # not a paint — the model then falls back to the overview command's stdout.
        sfx._record_model_noted("s1")
        with mock.patch.object(sfx, "_render_overview_paint", return_value=None) as rp:
            _, result = self.capture("what are my options")
        rp.assert_called_once()
        self.assertEqual(result, {"continue": True})

    def test_untripped_salesforce_naming_overview_ask_still_gets_the_note(self):
        # Regression guard (the intents OVERLAP): an overview ask that ALSO names
        # Salesforce — "what can I do here with Salesforce?" — matches BOTH the
        # overview and the getting-started intent. Untripped, that naming IS the trip,
        # so the prompt must reach the model-facing-only NOTE, not be swallowed
        # silently by the trip-gated overview branch, and the overview block must NOT
        # be built. (The overview paints only on a LATER ask, once this note marks the
        # session welcomed.)
        with mock.patch.object(sfx, "_render_overview_paint") as rp, \
                mock.patch.object(sfx, "_welcome_readiness", return_value="ready"):
            _, result = self.capture("what can I do here with Salesforce?")
        self.assertNotIn("systemMessage", result)                   # the note, not silence — no paint
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not (?:reproduce|paint)")
        rp.assert_not_called()                                      # overview never built
        self.assertTrue(sfx._model_noted_this_session("s1"))           # the trip is recorded
        # ...on the model-note marker ONLY. It must NOT set the visible-paint
        # `welcome` marker, or a benign mention would silently suppress the later
        # scaffold paint (the reported live miss). The two markers are disjoint.
        self.assertFalse(sfx._welcomed_this_session("s1"))


class DeployHookSelfGateTests(unittest.TestCase):
    """verify-org and post-deploy self-gate on the executed command. Some Claude
    Code builds ignore the plugin.json `if:` matcher and fire every Bash hook on
    every command, so the scripts gate themselves. verify-org fails CLOSED, so
    without the gate it would DENY an unrelated `cd`/`ls` whenever no org is set."""

    def run_hook(self, fn, command):
        payload = io.StringIO(json.dumps({"tool_input": {"command": command}}))
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            code = fn()
        return code, json.loads(out.getvalue())

    def test_verify_org_allows_non_deploy_before_any_cli_work(self):
        # The critical fix: an ordinary command is allowed without even resolving
        # the CLI — so a no-org project can still run `cd`/`ls`/`grep`.
        for cmd in ("cd /tmp && ls", "grep -r foo .", "sf org list", ""):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "resolve_executable") as rex, \
                        mock.patch.object(sfx, "get_target_org_detailed") as gto:
                    code, result = self.run_hook(sfx.cmd_verify_org, cmd)
                self.assertEqual((code, result), (0, {"continue": True}))
                rex.assert_not_called()
                gto.assert_not_called()

    def test_verify_org_still_denies_a_deploy_with_no_org(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("", "")):
            _, result = self.run_hook(sfx.cmd_verify_org, "sf project deploy start -o x")
        self.assertEqual(result.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_verify_org_allows_a_deploy_or_delete_with_reachable_org(self):
        for cmd in ("sf project deploy start -o acme", "sf project delete source -o acme"):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                        mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme", "")), \
                        mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme"}):
                    _, result = self.run_hook(sfx.cmd_verify_org, cmd)
                self.assertEqual(result, {"continue": True})

    def test_verify_org_honors_an_explicit_target_org_flag(self):
        # An explicit --target-org / -o on the deploy segment IS the target: the
        # gate must verify THAT org and never consult (or require) the default org.
        # The sibling bash gate (sf-deploy-gate) already reads the flag; this keeps
        # the two gates consistent for the home-directory / multi-org workflow.
        for cmd in (
            "sf project deploy start -o acme --source-dir force-app",
            "sf project deploy start --target-org acme --source-dir force-app",
            "sf project deploy start --target-org=acme --source-dir force-app",
            "cd /tmp/proj && sf project deploy start --source-dir force-app -o acme --json | jq .",
            "sf project delete source --metadata Flow:X --target-org acme --no-prompt",
        ):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                        mock.patch.object(sfx, "get_target_org_detailed", return_value=("", "")) as gto, \
                        mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme"}) as god:
                    _, result = self.run_hook(sfx.cmd_verify_org, cmd)
                self.assertEqual(result, {"continue": True})
                gto.assert_not_called()
                god.assert_called_once_with("acme")

    def test_verify_org_explicit_flag_still_fails_closed_when_unreachable(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("other", "")), \
                mock.patch.object(sfx, "get_org_display", return_value={}):
            _, result = self.run_hook(sfx.cmd_verify_org, "sf project deploy start -o gone --source-dir x")
        self.assertEqual(result.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_verify_org_flag_on_another_segment_does_not_count(self):
        # `-o` belongs to `sf org display`, not to the deploy — the deploy will run
        # against the DEFAULT org, so the gate must still require one.
        cmd = "sf org display -o acme --json && sf project deploy start --source-dir force-app"
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("", "")) as gto:
            _, result = self.run_hook(sfx.cmd_verify_org, cmd)
        self.assertEqual(result.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        gto.assert_called_once()

    def test_verify_org_mixed_segments_require_the_default_org(self):
        # Two deploys, one explicit and one not: the bare one uses the default org,
        # so the default must exist; the explicit one is verified on its own alias.
        cmd = "sf project deploy start -o acme --source-dir a; sf project deploy start --source-dir b"
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("dflt", "")), \
                mock.patch.object(sfx, "get_org_display", return_value={"alias": "x"}) as god:
            _, result = self.run_hook(sfx.cmd_verify_org, cmd)
        self.assertEqual(result, {"continue": True})
        self.assertEqual(sorted(c.args[0] for c in god.call_args_list), ["acme", "dflt"])

    def test_explicit_target_orgs_parser(self):
        f = sfx._explicit_deploy_target_orgs
        self.assertEqual(f("sf project deploy start -o acme --json"), ["acme"])
        self.assertEqual(f("sf project deploy start --target-org=acme"), ["acme"])
        self.assertEqual(f("sf project deploy start --target-org 'my org'"), ["my org"])
        self.assertEqual(f('sf project deploy start --target-org "my org"'), ["my org"])
        # `-o` inside another flag's value or a word is not the flag.
        self.assertEqual(f("sf project deploy start --source-dir foo-o"), [""])
        self.assertEqual(f("sf project deploy start --wait 30"), [""])
        # One entry per deploy/delete segment, in order; `-o` on other segments ignored.
        self.assertEqual(
            f("sf org display -o zz && sf project deploy start -o a; sf project delete source"),
            ["a", ""],
        )
        self.assertEqual(f("ls"), [])

    def test_post_deploy_silent_on_non_deploy_advises_on_deploy(self):
        _, silent = self.run_hook(sfx.cmd_post_deploy, "cd /tmp && grep foo .")
        self.assertEqual(silent, {"continue": True})
        _, advised = self.run_hook(sfx.cmd_post_deploy, "sf project deploy start -o x")
        self.assertIn("Deployment complete",
                      advised.get("hookSpecificOutput", {}).get("additionalContext", ""))

    def test_post_deploy_silent_on_check_only_and_non_mutating_forms(self):
        # A check-only `validate` (and preview/report/cancel) deploys NOTHING, so it
        # must NOT claim "Deployment complete" — that false signal could make the
        # model skip the real deploy after a validate. Only start/quick/resume advise.
        for cmd in ("sf project deploy validate -o x", "sf project deploy preview -o x",
                    "sf project deploy report", "sf project deploy cancel"):
            with self.subTest(cmd=cmd):
                _, result = self.run_hook(sfx.cmd_post_deploy, cmd)
                self.assertEqual(result, {"continue": True})
        # And it stays whitespace-flexible on the forms that DO deploy.
        _, spaced = self.run_hook(sfx.cmd_post_deploy, "sf  project   deploy quick --job-id 0Af")
        self.assertIn("Deployment complete",
                      spaced.get("hookSpecificOutput", {}).get("additionalContext", ""))

    def _run_payload(self, fn, payload):
        """Drive a PostToolUse handler with a full hook payload (incl. tool_response)."""
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", io.StringIO(json.dumps(payload))), \
                redirect_stdout(out):
            code = fn()
        return code, json.loads(out.getvalue())

    def test_post_deploy_ignores_a_dry_run_start_as_non_mutating(self):
        # `sf project deploy start --dry-run` (and --checkonly) VALIDATES without
        # mutating the org — the flag-form of the validate/preview carve-out. It must
        # light neither Deploy nor Test, nor claim "Deployment complete."
        for cmd in (
            "sf project deploy start --dry-run -o x",
            "sf project deploy start --dry-run --test-level RunLocalTests -o x",
            "sf project deploy start --checkonly -o x",
        ):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "_record_attributed_phase_event") as rec, \
                        mock.patch.object(sfx, "_resolve_phase_org_id", return_value=None):
                    _, result = self.run_hook(sfx.cmd_post_deploy, cmd)
                rec.assert_not_called()
                self.assertEqual(result, {"continue": True})

    def test_post_deploy_still_records_a_real_start(self):
        # Guard against over-rejection: a real deploy (no dry-run flag) still records.
        with mock.patch.object(sfx, "_record_attributed_phase_event") as rec, \
                mock.patch.object(sfx, "_resolve_phase_org_id", return_value=None):
            _, result = self.run_hook(sfx.cmd_post_deploy, "sf project deploy start -o x")
        self.assertEqual([call.args[0] for call in rec.call_args_list], ["Deploy"])
        self.assertIn("Deployment complete",
                      result.get("hookSpecificOutput", {}).get("additionalContext", ""))

    def test_post_writers_skip_a_host_reported_failure(self):
        # Some CC builds deliver a FAILED Bash result to PostToolUse instead of the
        # PostToolUseFailure event. A `passed` milestone must never be minted from a
        # run the host reported as failed (exit!=0 / interrupted / error flag).
        writers = (
            (sfx.cmd_post_deploy, "sf project deploy start -o x"),
            (sfx.cmd_post_test_run, "sf apex run test --synchronous -o x"),
            (sfx.cmd_post_observe, "sf apex tail log -o x"),
        )
        for fn, cmd in writers:
            for marker in ({"exitCode": 1}, {"interrupted": True}, {"is_error": True}):
                with self.subTest(fn=fn.__name__, marker=marker):
                    payload = {"tool_input": {"command": cmd}, "tool_response": marker}
                    with mock.patch.object(sfx, "_record_attributed_phase_event") as rec, \
                            mock.patch.object(sfx, "_resolve_phase_org_id", return_value=None):
                        _, result = self._run_payload(fn, payload)
                    rec.assert_not_called()
                    self.assertEqual(result, {"continue": True})

    def test_post_writers_record_on_zero_exit_or_absent_signal(self):
        # The failure guard is conservative: a genuine success (zero exit) or a host
        # that omits tool_response still records — evidence never fails closed.
        for marker in ({"exitCode": 0}, None):
            with self.subTest(marker=marker):
                payload = {"tool_input": {"command": "sf apex tail log -o x"}}
                if marker is not None:
                    payload["tool_response"] = marker
                with mock.patch.object(sfx, "_record_attributed_phase_event") as rec, \
                        mock.patch.object(sfx, "_resolve_phase_org_id", return_value=None):
                    self._run_payload(sfx.cmd_post_observe, payload)
                self.assertEqual([call.args[0] for call in rec.call_args_list], ["Observe"])

    def test_post_test_failure_self_gates_on_command(self):
        # journey-nudges Phase 6 (T7/O3): defense-in-depth, mirrors cmd_post_deploy_failure
        # — an unrelated command must never mint a Test/failed record even though the
        # hook is registered as its own if:-gated PostToolUseFailure entry.
        with mock.patch.object(sfx, "_record_attributed_phase_event") as rec:
            code, result = self.run_hook(sfx.cmd_post_test_failure, "cd /tmp && grep foo .")
        self.assertEqual((code, result), (0, {"continue": True}))
        rec.assert_not_called()
        with mock.patch.object(sfx, "_record_attributed_phase_event") as rec, \
                mock.patch.object(sfx, "_resolve_phase_org_id", return_value=None):
            code, result = self.run_hook(sfx.cmd_post_test_failure, "sf apex run test --synchronous -o x")
        self.assertEqual((code, result), (0, {"continue": True}))
        rec.assert_called_once_with(
            "Test", "failed", source="cmd_post_test_failure", org_id=None, event_type="test-run")

    def test_post_test_failure_ignores_a_non_synchronous_run(self):
        # Only the FINAL synchronous form's exit code reliably reflects the test
        # result — the async default (no --synchronous/-y) never earns evidence.
        with mock.patch.object(sfx, "_record_attributed_phase_event") as rec:
            code, result = self.run_hook(sfx.cmd_post_test_failure, "sf apex run test -o x")
        self.assertEqual((code, result), (0, {"continue": True}))
        rec.assert_not_called()

    def test_post_code_analyzer_self_gates_and_skips_a_host_reported_failure(self):
        # journey-nudges Phase 6 (T6): a Tier-C "ran once" activity write must self-gate
        # on the command AND consult the same conservative failure guard every other
        # PostToolUse success writer uses (a failed run never earns even the mere
        # "activity" signal).
        with mock.patch.object(sfx, "_record_phase_event") as rec:
            code, result = self.run_hook(sfx.cmd_post_code_analyzer, "cd /tmp && ls")
        self.assertEqual((code, result), (0, {"continue": True}))
        rec.assert_not_called()
        for marker in ({"exitCode": 1}, {"interrupted": True}, {"is_error": True}):
            with self.subTest(marker=marker):
                payload = {"tool_input": {"command": "sf code-analyzer run"}, "tool_response": marker}
                with mock.patch.object(sfx, "_record_phase_event") as rec:
                    _, result = self._run_payload(sfx.cmd_post_code_analyzer, payload)
                rec.assert_not_called()
                self.assertEqual(result, {"continue": True})
        with mock.patch.object(sfx, "_record_phase_event") as rec:
            code, result = self.run_hook(sfx.cmd_post_code_analyzer, "sf code-analyzer run")
        self.assertEqual((code, result), (0, {"continue": True}))
        rec.assert_called_once_with(
            "Test", "present", source="cmd_post_code_analyzer", event_type="code-analyzer")


class ReadinessPaintTests(unittest.TestCase):
    """The check-tools readiness banner is a Tier-1 surface: after a check-tools
    scan the PostToolUse Bash hook paints the framed banner on the visible channel
    and hands the model a plain "already shown — add only your read" note. Mirrors
    the overview-paint contract and the wayfinder/post-deploy command self-gate.
    A PostToolUse payload carries only the command (never the scan's stdout), so the
    banner is rendered from the report the scan persisted to .sf/ — cwd-isolated here."""

    def setUp(self):
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    def run_hook(self, command):
        payload = io.StringIO(json.dumps({"tool_input": {"command": command}}))
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            code = sfx.cmd_readiness_paint()
        return code, json.loads(out.getvalue())

    def test_non_scan_command_stays_a_silent_continue_without_rendering(self):
        # The plugin.json hook carries no `if:` (some builds ignore it and fire every
        # Bash hook on every command), so the gate is the command regex — and it must
        # not even read the report for an unrelated command.
        for cmd in ("cd /tmp && ls", "sf project deploy start -o x", "sf-context detect", ""):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "_render_readiness_paint") as rp:
                    code, result = self.run_hook(cmd)
                self.assertEqual((code, result), (0, {"continue": True}))
                rp.assert_not_called()

    def test_check_tools_scan_paints_the_banner_and_hands_a_plain_note(self):
        block = "──── Ready to build on Salesforce? ────\n(fixed test block)"
        with mock.patch.object(sfx, "_render_readiness_paint", return_value=block) as rp:
            code, result = self.run_hook('"${CLAUDE_PLUGIN_ROOT}"/scripts/sf-context check-tools')
        self.assertEqual(code, 0)
        rp.assert_called_once()
        self.assertEqual(result["systemMessage"], "\n" + block)   # painted directly, verbatim
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                            # model note is plain (no ANSI)
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)add only your")
        self.assertRegex(note, r"(?i)readiness")

    def test_scan_with_an_unrenderable_report_falls_back_to_silent(self):
        # Self-gate matches, but the report can't be rendered (no file / empty tools)
        # → _render_readiness_paint returns None → silent continue, model hand-renders.
        with mock.patch.object(sfx, "_render_readiness_paint", return_value=None):
            code, result = self.run_hook("sf-context check-tools")
        self.assertEqual((code, result), (0, {"continue": True}))

    def test_crash_in_the_hook_degrades_to_a_silent_continue(self):
        # Fail open: a crashing PostToolUse hook must never disrupt the turn.
        with mock.patch.object(sfx, "_render_readiness_paint", side_effect=Exception("boom")):
            code, result = self.run_hook("sf-context check-tools")
        self.assertEqual((code, result), (0, {"continue": True}))

    def test_render_readiness_paint_renders_from_the_persisted_report(self):
        # Integration: persist a report (as cmd_check_tools does) then render it back.
        report = {"tools": [
            {"name": "Git", "status": "ok", "version": "git version 2.50.1", "message": "Installed"},
            {"name": "Salesforce MCP (process)", "status": "info", "message": "Confirm with /mcp"},
        ]}
        sfx._record_readiness_report(report)
        with mock.patch.object(sfx, "_banner_color_enabled", return_value=True):
            block = sfx._render_readiness_paint()
        self.assertIsInstance(block, str)
        self.assertIn("Ready to build on Salesforce?", strip_ansi(block))
        self.assertIn("2.50.1", strip_ansi(block))
        # The visible paint path now colors the ✳ New here? footer (brand bright-blue, like
        # the welcome/SessionStart invitation); the TABLE rows stay ANSI-free — status is dots
        # + READY/WARN words, not color (owner direction 2026-08-05).
        self.assertIn(sfx._SGR_BRIGHT_BLUE, block)                # footer ✳ New here? is brand bright-blue
        self.assertNotIn("\x1b[36m", block)                       # …not the cyan link tint
        for line in block.splitlines():
            if any(w in line for w in ("READY", "WARN", "INFO", "BLOCKED")):
                self.assertNotIn("\x1b", line)                    # dots + words are content, not ANSI

    def test_render_readiness_paint_returns_none_when_no_report_or_empty(self):
        self.assertIsNone(sfx._render_readiness_paint())          # no file yet
        sfx._record_readiness_report({"tools": []})
        self.assertIsNone(sfx._render_readiness_paint())          # empty tools
        sfx._record_readiness_report({"nope": 1})
        self.assertIsNone(sfx._render_readiness_paint())          # no tools key


class JourneyPaintTests(unittest.TestCase):
    """Lever C: after the MODEL runs `sf-context discover journey` (because it
    recognized a fuzzy orientation question the UserPromptSubmit regex missed), a
    PostToolUse Bash hook paints the SAME colored nudge on the visible channel and
    hands the model an "already shown — add only your read" note. Self-gates on the
    command like the wayfinder / readiness-paint (no `if:`), de-dupes against the
    same turn's UserPromptSubmit paint via the turn-scoped ledger, requires a session
    id, excludes the --json machine form, and fails open. The ledger lives in .sf/
    (cwd-relative), so the temp cwd isolates it per test."""

    STATE = OrientationPaintTests.STATE

    def setUp(self):
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        # A painting journey-paint records the step-signature (temp-dir marker), so
        # sandbox the marker dir too or it leaks into the real temp dir across tests.
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        self._orig_runtime_dir = sfx._PROMPT_RUNTIME_DIR
        sfx._WELCOME_MARKER_DIR = Path(self._tmp.name)
        sfx._PROMPT_RUNTIME_DIR = Path(self._tmp.name) / "runtime"

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        sfx._PROMPT_RUNTIME_DIR = self._orig_runtime_dir
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    # A realistic (non-production-looking) org_display so `_gather_nudge_inputs`'
    # is_production heuristic doesn't default to "production" purely for lack of
    # evidence — matches the STATE fixture's implied dev-sandbox scenario.
    ORG_DISPLAY = {
        "alias": "acme-dev", "instanceUrl": "https://acme--dev.sandbox.my.salesforce.com/",
        "id": "00D000000000001EAA", "isSandbox": True,
    }

    def run_hook(self, command, session_id="s1", prompt_id="p1"):
        payload = {"tool_input": {"command": command}}
        if session_id is not None:
            payload["session_id"] = session_id
        if prompt_id is not None:
            payload["prompt_id"] = prompt_id
        out = io.StringIO()
        # cmd_journey_paint resolves state via `_journey_state_with_org` (not the
        # thin `_journey_state` wrapper) so it can hand the already-resolved org
        # display to `_select_inline_nudge` without a second probe — patch the
        # richer seam so both the state AND the (root, org_display) tuple it needs
        # are mocked together.
        with mock.patch.object(
            sfx, "_journey_state_with_org",
            return_value=(self.STATE, Path.cwd(), self.ORG_DISPLAY),
        ), \
                mock.patch.object(sfx.sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.dict(os.environ, {}, clear=True), \
                redirect_stdout(out):
            code = sfx.cmd_journey_paint()
        return code, json.loads(out.getvalue())

    def test_non_journey_command_stays_silent_including_the_json_form(self):
        # No `if:` in plugin.json (some builds fire every Bash hook on every command),
        # so the command regex is the gate — and the --json machine form (a read for
        # the model's own reasoning) must NOT paint a nudge.
        for cmd in ("cd /tmp && ls", "sf project deploy start -o x",
                    "sf-context discover where", "sf-context detect", "",
                    '"${CLAUDE_PLUGIN_ROOT}"/scripts/sf-context discover journey --json'):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "_render_nudge_inline") as rj:
                    code, result = self.run_hook(cmd)
                self.assertEqual((code, result), (0, {"continue": True}))
                rj.assert_not_called()

    def test_journey_command_paints_colored_hints_and_hands_a_plain_note(self):
        # journey-nudges Phase 2/8: the glyph rail is gone from this surface — it now
        # paints the single ladder-winning graded nudge (no "Reached:" word-list). The
        # STATE fixture (Connect/Project reached, Build not yet) with no local
        # source on disk (a bare temp dir) makes `build.empty-scaffold` the
        # deterministic winner — a 🚀 Try next momentum nudge.
        code, result = self.run_hook('"${CLAUDE_PLUGIN_ROOT}"/scripts/sf-context discover journey')
        self.assertEqual(code, 0)
        sysmsg = result["systemMessage"]
        self.assertTrue(sysmsg.startswith("\n"))
        visible = strip_ansi(sysmsg)
        self.assertNotIn("Reached:", visible)
        self.assertIn("🚀 Try next: Project has no local source yet.", visible)
        self.assertIn("\x1b[22m", sysmsg)                    # the nudge line is colored (body style)
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                       # model note is plain (no ANSI)
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertNotIn("●", note)                          # never hands the glyph rail to the model
        context = sfx._prompt_context(
            {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)
        self.assertTrue(sfx._nudge_painted_this_turn(context))  # second call de-dupes

    def test_dedupes_when_a_nudge_already_painted_this_turn(self):
        # The UserPromptSubmit orientation paint owns the atomic prompt claim, so a
        # later journey paint cannot emit a second visible nudge.
        context = sfx._prompt_context(
            {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)
        sfx._record_nudge_painted(context)
        with mock.patch.object(sfx, "_render_nudge_inline") as rj:
            code, result = self.run_hook("sf-context discover journey")
        self.assertEqual((code, result), (0, {"continue": True}))
        rj.assert_not_called()

    def test_missing_session_id_stays_silent_rather_than_risk_a_double(self):
        # Without a session id the paint cannot be de-duped against the UserPromptSubmit
        # paint, so it stays silent (the model reproduces the plain nudge — today's
        # behavior) rather than risk painting the nudge twice.
        with mock.patch.object(sfx, "_render_nudge_inline") as rj:
            code, result = self.run_hook("sf-context discover journey", session_id=None)
        self.assertEqual((code, result), (0, {"continue": True}))
        rj.assert_not_called()

    def test_crash_in_the_hook_degrades_to_a_silent_continue(self):
        # Fail open: a crashing PostToolUse hook must never disrupt the turn. (Patch the
        # renderer now in use — journey-nudges Phase 2 — not _journey_state; run_hook
        # already mocks the richer _journey_state_with_org seam.)
        with mock.patch.object(sfx, "_render_nudge_inline", side_effect=Exception("boom")):
            code, result = self.run_hook("sf-context discover journey")
        self.assertEqual((code, result), (0, {"continue": True}))

    def test_independent_skill_and_nudge_markers_preserve_each_other(self):
        context = sfx._prompt_context(
            {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)

        def dispatch_skill(name):
            payload = io.StringIO(json.dumps({
                "session_id": "s1", "prompt_id": "p1", "tool_input": {"skill": name}
            }))
            with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(io.StringIO()):
                sfx.cmd_record_skill_dispatch()

        sfx._record_nudge_painted(context)
        dispatch_skill("platform-apex-generate")
        self.assertTrue(sfx._nudge_painted_this_turn(context))
        self.assertIn("platform-apex-generate", sfx._dispatched_skills(context))


class CommandPaintTests(unittest.TestCase):
    """The UserPromptExpansion seam: a typed `/salesforce-development:discover …`
    slash command reaches the SAME deterministic paints as the natural-language path
    (one surface, two front doors). Claude Code routes a slash command through the
    dedicated UserPromptExpansion event (not UserPromptSubmit), carrying the command
    identity structurally; `cmd_prompt_dispatch` routes that event to
    `cmd_command_paint`, which maps (command_name, command_args) to a PAINT intent by
    EXACT match — painting overview / nudge unconditionally (an explicit solicit
    bypasses the ambient trip-gating that keeps unsolicited nudges quiet) and staying
    silent for every probe / consent / stateful / JSON / foreign mode, mirroring the
    plugin's existing NL paint-vs-note line. Fails open."""

    STATE = OrientationPaintTests.STATE

    # In-project fixtures for the status-surface family: a resolved org + project so the
    # real band renderers paint on fixed facts (no org round-trip, no fs walk).
    STATUS_ORG = {"alias": "acme-dev", "edition": "Developer", "apiVersion": "63.0",
                  "username": "u@acme.dev", "instanceUrl": "https://acme.my.salesforce.com"}
    STATUS_META = {"name": "acme-crm", "source_api": "63.0", "package_dirs": "force-app"}
    STATUS_STATS = {"apex_src": 3, "apex_test": 1, "triggers": 0, "lwc": 2,
                    "aura": 0, "objects": 5, "permsets": 1, "flows": 0}

    def setUp(self):
        # cmd_command_paint should touch none of these, but sandbox cwd + the marker /
        # runtime dirs so the "sets no trip-gating markers" assertion is hermetic and a
        # future regression can't scribble in the real dirs.
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        self._orig_runtime_dir = sfx._PROMPT_RUNTIME_DIR
        sfx._WELCOME_MARKER_DIR = Path(self._tmp.name) / "markers"
        sfx._PROMPT_RUNTIME_DIR = Path(self._tmp.name) / "runtime"

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        sfx._PROMPT_RUNTIME_DIR = self._orig_runtime_dir
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    # The "hints" intent resolves via `_journey_state_with_org` (not the thin
    # `_journey_state` wrapper) so it can hand the already-resolved org display to
    # `_all_journey_hints` without a second probe (journey-nudges Phase 3, same seam
    # `JourneyPaintTests.run_hook` already mocks for `cmd_journey_paint`) — patch the
    # richer seam so both the state AND the (root, org_display) tuple it needs are
    # mocked together, and the render never touches the real machine's org config.
    ORG_DISPLAY = {"alias": "acme-dev", "instanceUrl": "https://acme--dev.sandbox.my.salesforce.com/",
                   "id": "00D000000000001EAA", "isSandbox": True}

    def capture(self, command_args, *, command_name=None,
                expansion_type="slash_command", event="UserPromptExpansion"):
        """Drive the real dispatch entry point with a UserPromptExpansion payload, so
        this also exercises the event routing in cmd_prompt_dispatch, not just the
        handler. Env is cleared (NO_COLOR unset) so the visible-channel color gate is
        on, matching a real painted command."""
        if command_name is None:
            command_name = sfx._DISCOVERY_COMMAND
        payload = {
            "hook_event_name": event,
            "expansion_type": expansion_type,
            "command_name": command_name,
            "command_args": command_args,
            "prompt": ("/%s %s" % (command_name, command_args)).strip(),
        }
        out = io.StringIO()
        with mock.patch.object(
            sfx, "_journey_state_with_org",
            return_value=(self.STATE, Path.cwd(), self.ORG_DISPLAY),
        ), \
                mock.patch.object(sfx.sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.dict(os.environ, {}, clear=True), \
                redirect_stdout(out):
            code = sfx.cmd_prompt_dispatch()
        return code, json.loads(out.getvalue())

    # ---- arg → intent mapping: the exact-match twin classification ----

    def test_paint_args_map_to_their_intent(self):
        # journey-nudges Phase 3: the mode label is "hints" now (the ranked nudge
        # list), not the retired "rail"; "next"/"whats next"/"what's next" are the
        # new primary phrasing, and "where"/"journey" remain resolving synonyms.
        for args, intent in [
            ("overview", "overview"),
            ("OVERVIEW", "overview"),        # case-insensitive
            ("  overview  ", "overview"),    # whitespace-normalized
            ("", "hints"),                   # bare /discover
            ("next", "hints"),
            ("whats next", "hints"),
            ("what's next", "hints"),
            ("WHAT'S NEXT", "hints"),        # case-insensitive
            ("where", "hints"),
            ("journey", "hints"),
            ("WHERE", "hints"),
            (" journey ", "hints"),
        ]:
            with self.subTest(args=args):
                self.assertEqual(sfx._discovery_command_paint_intent(args), intent)

    def test_never_paint_args_map_to_none(self):
        # Probes / consent / stateful / JSON / garbage all fall through to None so the
        # command body drives them — a bug here would auto-fire an org probe or a reset
        # preview. Exact-match discipline: any trailing token defeats a paint, so the
        # bare `journey` nudge never bleeds into `journey inspect` / `journey reset …`.
        for args in ("overview --json", "journey --json", "journey inspect",
                     "journey reset", "journey reset --stage Connect --scope all",
                     "plugins add a payment gateway", "features",
                     "features --target-org acme --refresh", "overview now",
                     "journey status", "where am i", "--json", "wat"):
            with self.subTest(args=args):
                self.assertIsNone(sfx._discovery_command_paint_intent(args))

    # ---- overview paints ----

    def test_overview_command_paints_overview_and_hands_the_do_not_reproduce_note(self):
        code, result = self.capture("overview")
        self.assertEqual(code, 0)
        self.assertEqual(
            result["hookSpecificOutput"]["hookEventName"], "UserPromptExpansion")
        sysmsg = result["systemMessage"]
        self.assertTrue(sysmsg.startswith("\n"))
        self.assertIn("\x1b[", sysmsg)                                # colored (NO_COLOR unset)
        self.assertIn("what you can do here", strip_ansi(sysmsg))     # the overview, not the nudge
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(note, sfx._overview_paint_note())            # overview note, not nudge note
        self.assertNotIn("\x1b", note)                               # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")

    # ---- hints paints ----

    def test_hints_commands_paint_the_colored_ranked_list_and_hand_the_orientation_note(self):
        # journey-nudges Phase 3: the bare/"where"/"journey" command args now paint
        # the ranked `journey hints` list (nudge_rules.all_hints), not the glyph
        # nudge — reusing the SAME `_journey_state_with_org` seam `capture()` mocks
        # (no re-probe). The STATE fixture (project + org, no source yet) has no
        # local source and no git repo, so build.empty-scaffold and project.no-git
        # both fire — assert on that ranked content instead of the retired glyphs.
        for args in ("", "where", "journey"):
            with self.subTest(args=args):
                code, result = self.capture(args)
                self.assertEqual(code, 0)
                self.assertEqual(
                    result["hookSpecificOutput"]["hookEventName"], "UserPromptExpansion")
                sysmsg = result["systemMessage"]
                self.assertTrue(sysmsg.startswith("\n"))
                self.assertIn("\x1b[", sysmsg)                        # colored on the visible channel
                plain = strip_ansi(sysmsg)
                self.assertIn("Hints (ranked):", plain)
                self.assertIn("generate a component", plain)
                self.assertNotIn("what you can do here", plain)      # hints list, not overview
                note = result["hookSpecificOutput"]["additionalContext"]
                # journey-nudges Phase 5: the note's "next action" text now derives
                # from the SAME candidate the hints list is ranked from — no session
                # id in this explicit-command path, matching production.
                candidate = sfx._select_inline_nudge(self.STATE, Path.cwd(), self.ORG_DISPLAY)
                self.assertEqual(note, sfx._orientation_paint_note(self.STATE, candidate=candidate))
                self.assertNotIn("\x1b", note)                        # model note is plain
                self.assertRegex(note, r"(?i)do not reproduce")

    # ---- silent modes: nothing paints, the command body drives ----

    def test_never_paint_commands_stay_silent(self):
        # Only the render-only modes paint; every probe / consent / stateful / JSON mode
        # emits a bare continue and lets the body run. Guard BOTH renderers to prove
        # neither is even reached — the sharpest hazard is auto-firing a probe / reset.
        for args in ("overview --json", "journey --json", "journey inspect",
                     "journey reset --stage Connect", "plugins add a gateway",
                     "features", "features --refresh", "--json", "wat"):
            with self.subTest(args=args):
                with mock.patch.object(sfx, "_render_overview_paint") as ov, \
                        mock.patch.object(sfx, "_render_journey_hints") as rj:
                    code, result = self.capture(args)
                self.assertEqual((code, result), (0, {"continue": True}))
                ov.assert_not_called()
                rj.assert_not_called()

    def test_foreign_command_name_stays_silent(self):
        with mock.patch.object(sfx, "_render_overview_paint") as ov, \
                mock.patch.object(sfx, "_render_journey_hints") as rj:
            code, result = self.capture("overview", command_name="other-plugin:discovery")
        self.assertEqual((code, result), (0, {"continue": True}))
        ov.assert_not_called()
        rj.assert_not_called()

    def test_non_slash_expansion_stays_silent(self):
        # An MCP-prompt expansion is not a slash command — even with a matching name and
        # a paint arg, it must not paint.
        with mock.patch.object(sfx, "_render_overview_paint") as ov, \
                mock.patch.object(sfx, "_render_journey_hints") as rj:
            code, result = self.capture("overview", expansion_type="mcp_prompt")
        self.assertEqual((code, result), (0, {"continue": True}))
        ov.assert_not_called()
        rj.assert_not_called()

    # ---- explicit-solicit bypass + fail-open ----

    def test_command_paints_unconditionally_and_sets_no_trip_gating_markers(self):
        # A typed command is an explicit solicit: it paints every time, with no
        # welcomed/entered markers and no prompt id, and does not dedupe the way an
        # ambient nudge does — two back-to-back overview commands both paint. And it
        # writes none of the ambient trip-gating markers (nothing to gate, nothing to
        # dedupe), so the sandboxed marker / runtime dirs stay empty.
        _, first = self.capture("overview")
        _, second = self.capture("overview")
        self.assertIn("what you can do here", strip_ansi(first["systemMessage"]))
        self.assertIn("what you can do here", strip_ansi(second["systemMessage"]))
        for d in (sfx._WELCOME_MARKER_DIR, sfx._PROMPT_RUNTIME_DIR):
            self.assertFalse(d.exists() and any(d.iterdir()), d)

    def test_overview_command_does_not_arm_the_test_drive_proposal(self):
        # The command path is contractually side-effect-free: unlike the NL overview
        # front door, it must NOT arm the test-drive proposal ledger, so a command
        # bite keeps the ordinary source-preview confirm.
        with mock.patch.object(sfx, "_arm_overview_test_drive_proposal") as armed:
            self.capture("overview")
        armed.assert_not_called()

    def test_render_failure_degrades_to_a_silent_continue(self):
        # Fail open: a crash anywhere in the handler resolves to a bare continue, never
        # a stack trace on the user's command. (_render_overview_paint is itself
        # hardened to never raise, so force the failure to exercise the handler's own
        # outer guard.)
        with mock.patch.object(sfx, "_render_overview_paint", side_effect=Exception("boom")):
            code, result = self.capture("overview")
        self.assertEqual((code, result), (0, {"continue": True}))
        with mock.patch.object(sfx, "_render_journey_hints", side_effect=Exception("boom")):
            code, result = self.capture("where")
        self.assertEqual((code, result), (0, {"continue": True}))

    # ---- dispatch routing + plugin.json wiring ----

    def test_dispatch_routes_by_event(self):
        # UserPromptExpansion → the command handler; anything else → the NL orientation
        # path. Each branch gets its own fresh mocks (so a call in one can't leak into
        # the other's assert_not_called), and the NL context helpers are mocked too so
        # this isolates the routing branch.
        expansion = {"hook_event_name": "UserPromptExpansion",
                     "expansion_type": "slash_command",
                     "command_name": sfx._DISCOVERY_COMMAND, "command_args": "overview"}
        with mock.patch.object(sfx, "cmd_command_paint", return_value=0) as cp, \
                mock.patch.object(sfx, "cmd_orientation_paint", return_value=0) as op, \
                mock.patch.object(sfx.sys, "stdin", io.StringIO(json.dumps(expansion))), \
                redirect_stdout(io.StringIO()):
            sfx.cmd_prompt_dispatch()
        cp.assert_called_once()
        op.assert_not_called()

        submit = {"prompt": "where am i?", "session_id": "s1"}
        with mock.patch.object(sfx, "cmd_command_paint", return_value=0) as cp, \
                mock.patch.object(sfx, "cmd_orientation_paint", return_value=0) as op, \
                mock.patch.object(sfx, "_prompt_context", return_value=None), \
                mock.patch.object(sfx, "_prune_prompt_runtime"), \
                mock.patch.object(sfx.sys, "stdin", io.StringIO(json.dumps(submit))), \
                redirect_stdout(io.StringIO()):
            sfx.cmd_prompt_dispatch()
        op.assert_called_once()
        cp.assert_not_called()

    def test_plugin_json_registers_prompt_dispatch_on_both_front_doors(self):
        # One handler, two front doors: prompt-dispatch is registered on BOTH
        # UserPromptSubmit (prose) and UserPromptExpansion (structured slash command).
        hooks = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["hooks"]
        for event in ("UserPromptSubmit", "UserPromptExpansion"):
            commands = [h["command"] for group in hooks.get(event, [])
                        for h in group.get("hooks", [])]
            self.assertTrue(
                any(c.endswith("sf-context prompt-dispatch") for c in commands),
                "%s must register sf-context prompt-dispatch, got %r" % (event, commands))

    # ---- status-surface family front doors: /status /welcome /org /project ----
    # Each is a render-only twin of an NL / SessionStart surface reached through the
    # SAME UserPromptExpansion seam as /discover. Its painter ALWAYS returns
    # (note, present-surface) — the no-project / no-org forks live in the deterministic
    # layer — so the shrunk command body defers unconditionally to "already shown above".

    def test_status_family_commands_paint_their_surface_and_note(self):
        # In a project with a resolved org: each command lands on the SAME colored
        # surface its NL / SessionStart twin paints and hands the MATCHING plain note.
        # Scope is the discriminator — /status and /welcome carry org + project + nudge,
        # /org carries only the org band, /project only the project band.
        Path("sfdx-project.json").write_text("{}")
        # journey-nudges Phase 5: /status and /welcome now feed the SAME
        # session-id-less candidate `_status_command_paint`/`_welcome_command_paint`
        # resolve into their note (no session_id in scope there either). Resolve it
        # under the SAME project/git mocks the actual command paint runs under below,
        # so both sides read identical facts (real project_stats()/git_status_line()
        # would otherwise disagree with the mocked STATUS_STATS/empty git status).
        with mock.patch.object(sfx, "project_meta", return_value=self.STATUS_META), \
                mock.patch.object(sfx, "project_stats", return_value=self.STATUS_STATS), \
                mock.patch.object(sfx, "git_status_line", return_value=""):
            status_candidate = sfx._select_inline_nudge(
                self.STATE, Path.cwd().resolve(), self.STATUS_ORG,
            )
        status_note = sfx._status_paint_note(self.STATE, candidate=status_candidate)
        cases = [
            # command_name, expected note, present (lowered), absent (lowered).
            # journey-nudges Phase 8: the "reached:" word-list is retired; the nudge
            # line is now the graded band label. This sandbox has Apex source but no
            # tests, so test.apex-no-tests (⚠️ Heads up) is the ladder winner — its
            # band marker stands in for "the nudge line rides this surface."
            ("salesforce-development:status", status_note,
             ("acme-dev", "sfdx project: acme-crm", "⚠️ heads up:"), ("reached:",)),
            ("salesforce-development:welcome", status_note,
             ("acme-dev", "sfdx project: acme-crm", "⚠️ heads up:"), ("reached:",)),
            ("salesforce-development:org", sfx._org_paint_note(),
             ("acme-dev",), ("sfdx project:", "reached:", "⚠️ heads up:")),
            ("salesforce-development:project", sfx._project_paint_note(),
             ("sfdx project: acme-crm",), ("acme-dev", "reached:", "⚠️ heads up:")),
        ]
        for command, note, present, absent in cases:
            with self.subTest(command=command):
                with mock.patch.object(sfx, "_resolve_position_and_org",
                                       return_value=(self.STATE, self.STATUS_ORG)), \
                        mock.patch.object(sfx, "project_meta", return_value=self.STATUS_META), \
                        mock.patch.object(sfx, "project_stats", return_value=self.STATUS_STATS), \
                        mock.patch.object(sfx, "git_status_line", return_value=""), \
                        mock.patch.object(sfx, "_live_mcp_summary", return_value="1 connected"):
                    code, result = self.capture("", command_name=command)
                self.assertEqual(code, 0)
                self.assertEqual(
                    result["hookSpecificOutput"]["hookEventName"], "UserPromptExpansion")
                sysmsg = result["systemMessage"]
                self.assertTrue(sysmsg.startswith("\n"))
                self.assertIn("\x1b[", sysmsg)                    # colored on the visible channel
                plain = strip_ansi(sysmsg).lower()
                for token in present:
                    self.assertIn(token, plain)
                for token in absent:
                    self.assertNotIn(token, plain)
                got_note = result["hookSpecificOutput"]["additionalContext"]
                self.assertEqual(got_note, note)                  # the RIGHT per-command note
                self.assertNotIn("\x1b", got_note)                # model note is plain
                self.assertRegex(got_note, r"(?i)already visible")
                self.assertRegex(got_note, r"(?i)do not reproduce")

    def test_welcome_carries_the_logo_and_status_does_not(self):
        # /welcome is the full session banner WITH the HEADLESS lockup (the SessionStart
        # surface); /status is the same picture WITHOUT it (the lean on-demand readout).
        # Assert the one axis that differs — the logo flag into the shared renderer —
        # rather than matching multi-line ASCII art through the color codes.
        Path("sfdx-project.json").write_text("{}")
        for command, want_logo in [("salesforce-development:welcome", True),
                                   ("salesforce-development:status", False)]:
            with self.subTest(command=command):
                with mock.patch.object(sfx, "_resolve_position_and_org",
                                       return_value=(self.STATE, self.STATUS_ORG)), \
                        mock.patch.object(sfx, "project_meta", return_value=self.STATUS_META), \
                        mock.patch.object(sfx, "project_stats", return_value=self.STATUS_STATS), \
                        mock.patch.object(sfx, "git_status_line", return_value=""), \
                        mock.patch.object(sfx, "_live_mcp_summary", return_value=""), \
                        mock.patch.object(sfx, "render_status_surface",
                                          wraps=sfx.render_status_surface) as rss:
                    code, _ = self.capture("", command_name=command)
                self.assertEqual(code, 0)
                rss.assert_called_once()
                self.assertIs(rss.call_args.kwargs["logo"], want_logo)

    def test_status_family_no_project_degrades_to_a_present_surface(self):
        # No sfdx-project.json (the sandbox default): /status, /welcome, /project each
        # paint the honest "no Salesforce project" surface and hand the no-project note
        # that points at setup — a present, colored surface, never an empty continue,
        # so the body still defers unconditionally.
        for command in ("salesforce-development:status",
                        "salesforce-development:welcome",
                        "salesforce-development:project"):
            with self.subTest(command=command):
                code, result = self.capture("", command_name=command)
                self.assertEqual(code, 0)
                sysmsg = result["systemMessage"]
                self.assertTrue(sysmsg.startswith("\n"))
                self.assertIn("\x1b[", sysmsg)                    # honest surface still paints in color
                self.assertIn("no Salesforce project", strip_ansi(sysmsg))
                self.assertEqual(
                    result["hookSpecificOutput"]["additionalContext"], sfx._no_project_note())

    def test_org_with_no_resolved_org_degrades_through_the_shared_org_lines(self):
        # /org is project-independent (an org can be a global default). With no org
        # resolved it degrades through the SAME honest lines the full status surface
        # uses (`_status_org_group`), skips the MCP probe, and still hands the org note.
        # The degraded line is muted (CC dims it), so this surface is legitimately plain.
        degraded = {"context": {"orgStatus": "not-configured"}}
        with mock.patch.object(sfx, "_resolve_position_and_org",
                               return_value=(degraded, None)), \
                mock.patch.object(sfx, "_live_mcp_summary") as mcp:
            code, result = self.capture("", command_name="salesforce-development:org")
        self.assertEqual(code, 0)
        mcp.assert_not_called()                                   # no org → no wasted MCP round-trip
        self.assertIn("no default set", strip_ansi(result["systemMessage"]))
        self.assertEqual(
            result["hookSpecificOutput"]["additionalContext"], sfx._org_paint_note())

    def test_status_family_stays_silent_for_foreign_name_and_non_slash_expansion(self):
        # Gate discipline for the status family, mirroring the discovery-family guards:
        # a status command_name only paints as a real slash command. A foreign name
        # (unknown → not in the painter table) and a non-slash MCP-prompt expansion both
        # fall through to a bare continue, with no painter reached.
        with mock.patch.object(sfx, "_status_command_paint") as sp, \
                mock.patch.object(sfx, "_org_command_paint") as op, \
                mock.patch.object(sfx, "_project_command_paint") as pp, \
                mock.patch.object(sfx, "_welcome_command_paint") as wp:
            foreign_code, foreign = self.capture("", command_name="other-plugin:status")
            nonslash_code, nonslash = self.capture(
                "", command_name="salesforce-development:status", expansion_type="mcp_prompt")
        self.assertEqual((foreign_code, foreign), (0, {"continue": True}))
        self.assertEqual((nonslash_code, nonslash), (0, {"continue": True}))
        for painter in (sp, op, pp, wp):
            painter.assert_not_called()


class ResolvePositionAndOrgTests(unittest.TestCase):
    """`_resolve_position_and_org` resolves the org ONCE for the status surface and
    fails soft: an unresolvable CLI (or a failed query) yields a Setup/unknown state
    and no org band — never a fabricated 'no org' (W-23466800 / WIN-027)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root.joinpath("sfdx-project.json").write_text("{}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_unresolved_yields_unknown_state_and_no_org_without_querying(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None), \
                mock.patch.object(sfx, "get_target_org_detailed") as gto:
            state, org = sfx._resolve_position_and_org(self.root)
        self.assertIsNone(org)
        self.assertEqual(state["context"]["orgStatus"], "unknown")
        gto.assert_not_called()   # the CLI is gone — never even query for an org

    def test_failed_query_yields_unknown_not_a_fabricated_no_org(self):
        # CLI present but the target-org query failed → "unknown", never the
        # "not-configured" that would advise an `sf org login` that can't succeed.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("", "timeout")):
            state, org = sfx._resolve_position_and_org(self.root)
        self.assertIsNone(org)
        self.assertEqual(state["context"]["orgStatus"], "unknown")

    def test_reachable_org_returns_org_and_advances_the_stage(self):
        org_info = {"alias": "acme-dev", "edition": "Developer Edition (Sandbox)",
                    "apiVersion": "67.0", "instanceUrl": "https://x.my.salesforce.com"}
        # Pin the FRONT signals so the cursor is driven purely by the org + on-disk
        # facts under test (real ~/.sf / ~/.sfdx / PATH must never leak in). Connect
        # lights from a CONFIGURED target — here the resolved target "acme-dev" does
        # that directly; reachability is not what lights it (non-decay).
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "_welcome_readiness", return_value="ready"), \
                mock.patch.object(sfx, "_configured_target_alias", return_value="acme-dev"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("acme-dev", "")), \
                mock.patch.object(sfx, "get_org_list", return_value={}), \
                mock.patch.object(sfx, "get_org_display", return_value={"alias": "acme-dev"}), \
                mock.patch.object(sfx, "resolve_org_info", return_value=org_info), \
                mock.patch.object(sfx, "_has_local_source_artifacts", return_value=False):
            state, org = sfx._resolve_position_and_org(self.root)
        self.assertEqual(org, org_info)
        self.assertEqual(state["context"]["orgStatus"], "reachable")
        self.assertEqual(state["currentStage"], "Build")   # project + org, no source yet


if __name__ == "__main__":
    unittest.main(verbosity=2)

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
CATALOG_PATH = SCRIPTS / "discovery_catalog.py"
PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin/plugin.json"
CATALOG_ARTIFACT = PLUGIN_ROOT / "catalog/discovery.json"
POINTER = 'Ask “what can I do here?” or run /salesforce-development:discovery.'
# The visible SessionStart banner, the degraded banners, AND the readiness footer now
# all close with the shared "✳ New here?" wayfinding footer (_wayfinding_footer, unified
# with platform-environment-validate). DISCOVERY_POINTER (POINTER, above) is the plain
# one-liner that remains on the post-login wayfinder and the model-facing additionalContext
# note. On any visible banner the discovery command token appears exactly once — the
# "single pointer" invariant.
DISCOVERY_CMD = "/salesforce-development:discovery"
INSTALL = "npx skills@1.5.20 add forcedotcom/sf-skills#1.32.0 --skill {name} --agent claude-code --yes"
TAGLINE = "headless Salesforce development, from inside the agent"

catalog = load_module(CATALOG_PATH, "discovery_runtime_catalog")
sfx = load_module(SF_CONTEXT_PATH, "discovery_runtime_context")


class DiscoveryRuntimeTests(unittest.TestCase):
    def run_discovery(self, args, cwd, home, org_presence=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = catalog.run_discovery(
                args, plugin_root=PLUGIN_ROOT, cwd=cwd, home=home, org_presence=org_presence
            )
        return code, out.getvalue(), err.getvalue()

    def overview_sections(self, text: str) -> dict[str, list[str]]:
        """Split the human overview into its two labelled sections of domain rows."""
        sections: dict[str, list[str]] = {}
        heading = None
        for line in text.splitlines():
            if line.startswith(("INSTALLED", "AVAILABLE TO ADD")):
                heading = line.split(" —")[0]
                sections[heading] = []
            elif heading and line.startswith("  "):
                sections[heading].append(line)
        return sections

    def test_overview_human_is_grouped_bounded_and_leak_free(self):
        """The human overview is model-presented catalog content: labels and bounds only.

        The exact-count contract lives on the JSON surface below. The numbers this
        text does state are still asserted here, but derived from the artifact in
        the test — enough to catch a swapped or recomputed count without pinning
        the model-presented wording around it.
        """
        artifact = catalog.load_catalog(PLUGIN_ROOT)
        self.assertNotIn('"description"', json.dumps(artifact))
        # Nothing is installed standalone under a temporary root, so the bundled
        # foundation roster is exactly the installed set for this render.
        installed = [row for row in artifact["skills"] if row["foundationInstalled"]]
        addable = [
            row for row in artifact["skills"]
            if row["publicAvailable"] and not row["foundationInstalled"]
        ]
        with tempfile.TemporaryDirectory() as td:
            code, out, err = self.run_discovery(["overview"], Path(td), Path(td) / "home")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("INSTALLED", out)
        self.assertIn("AVAILABLE TO ADD", out)
        self.assertIn(artifact["publicRelease"]["releaseRef"], out)
        self.assertNotIn("spike", out.lower())
        self.assertNotIn("sf-context", out)
        self.assertLess(len(out.splitlines()), 80)
        self.assertNotIn("\t", out)
        sections = self.overview_sections(out)
        self.assertEqual(sorted(sections), ["AVAILABLE TO ADD", "INSTALLED"])
        headings = {line.split(" —")[0]: line for line in out.splitlines()
                    if line.startswith(("INSTALLED", "AVAILABLE TO ADD"))}
        self.assertIn(str(len(installed)), headings["INSTALLED"])
        self.assertIn(str(len(addable)), headings["AVAILABLE TO ADD"])
        # Each section lists exactly the domains that actually have rows in it, so
        # dropping the empty-group guard cannot pad a section with 0-count domains.
        # Rows render the first-party FRIENDLY label, not the raw prefix; parse the
        # fixed-width label cell (never the example) and rsplit off the count paren
        # so labels that themselves contain " (" (e.g. "Automation (Flow)") survive.
        def row_label(row):
            return row[2:2 + catalog._DOMAIN_CELL].rstrip().rsplit(" (", 1)[0]
        for heading, group in (("INSTALLED", installed), ("AVAILABLE TO ADD", addable)):
            with self.subTest(section=heading):
                expected = sorted({catalog._display(row["domain"])["label"] for row in group})
                self.assertEqual(sorted(row_label(row) for row in sections[heading]), expected)
        # The hero human surface must fit an 80-column terminal without wrapping.
        self.assertEqual([line for line in out.splitlines() if len(line) > 80], [])

    def test_overview_text_matches_the_printed_block_and_the_paint_helper(self):
        # The refactor split _overview_text (a string) out of _print_overview (stdout)
        # and reuses it in render_overview_text (the Tier-1 paint hook). All three must
        # agree byte-for-byte, so the geometry goldens hold on whichever path emits the
        # block — the command's stdout (model-reproduced fallback) or the systemMessage.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cat, rows = catalog._runtime_rows(PLUGIN_ROOT, root, root / "home")
            data = catalog._overview(cat, rows, org_presence="none")
            out = io.StringIO()
            with redirect_stdout(out):
                catalog._print_overview(data)
            printed = out.getvalue()
            text = catalog._overview_text(data)
            self.assertEqual(printed, text + "\n")   # print() adds exactly one trailing \n
            helper = catalog.render_overview_text(
                PLUGIN_ROOT, cwd=root, home=root / "home", org_presence="none")
            self.assertEqual(helper, text)           # the paint hook renders the same block
            self.assertNotIn("\x1b", helper)         # default path is plain — color is opt-in

    def test_overview_color_strips_to_the_plain_block_with_the_expected_hues(self):
        """The colored overview is the plain block plus the mock's vocabulary, and
        nothing else: strip it and you get the byte-identical monochrome block the
        command prints and the model reproduces. Mirrors the rail's color golden — the
        paint hook is the ONLY caller that opts into color (render_overview_text /
        _overview_text default to plain), so the whole golden geometry rides through
        color=True unchanged, and NO_COLOR forces plain even when color is requested."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cat, rows = catalog._runtime_rows(PLUGIN_ROOT, root, root / "home")
            data = catalog._overview(cat, rows, org_presence="none")
        plain = catalog._overview_text(data)
        colored = catalog._overview_text(data, color=True)
        self.assertNotIn("\x1b", plain)                        # default render carries no ANSI
        self.assertEqual(strip_ansi(colored), plain)           # color is purely additive
        # Every color is pulled from the theme — NO hard-coded truecolor (\x1b[38;2;r;g;b)
        # nor the colon-subparameter form, the two encodings CC renders as absolute RGB.
        self.assertNotIn("\x1b[38;2", colored)
        self.assertNotRegex(colored, r"\x1b\[[0-9;]*:")
        # The accents are 16-color palette + attributes, undim-prefixed so they read
        # above the muted baseline: bold title, green INSTALLED, amber ADD, cyan links.
        for code in ("\x1b[1m", "\x1b[32m", "\x1b[33m", "\x1b[36m", "\x1b[22m"):
            self.assertIn(code, colored)
        # Retired: the connect affordance's magenta ▶, the link underline (read as
        # clickable), and any explicit grey — the muted tone is now plain (below).
        self.assertNotIn("\x1b[35m", colored)                  # no magenta ▶
        self.assertNotIn("\x1b[4m", colored)                   # links are cyan, never underlined
        self.assertNotIn("\x1b[90m", colored)                  # no bright-black grey
        # The muted/secondary tone carries NO SGR at all: emitted plain, it inherits
        # CC's systemMessage dimming (the theme's own dimmed foreground — the banner's
        # gray). Fully-muted lines therefore have zero ANSI: the top provenance, and
        # — as of the right-column pass — the Try nudge and the Next command too.
        for prefix in ("Public release", "Try:", "Next:"):
            line = next(l for l in colored.splitlines() if strip_ansi(l).startswith(prefix))
            self.assertNotIn("\x1b", line, prefix)
        # An INSTALLED row carries cyan ONLY on its label; the right-column example is
        # muted (plain), not a cyan link — so the row line has exactly one cyan span.
        row = next(l for l in colored.splitlines() if "build an Agentforce agent" in strip_ansi(l))
        self.assertEqual(row.count("\x1b[36m"), 1)
        # Color is zero-width: the 80-column bound the plain block satisfies still holds.
        self.assertEqual([l for l in strip_ansi(colored).splitlines() if len(l) > 80], [])
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertEqual(catalog._overview_text(data, color=True), plain)

    def test_overview_json_counts_are_exact_and_agree_with_the_domain_rows(self):
        """The JSON overview is the exact-count home; expectations come from the artifact."""
        artifact_counts = catalog.load_catalog(PLUGIN_ROOT)["counts"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, out, err = self.run_discovery(["overview", "--json"], root, root / "home")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        counts = data["counts"]
        self.assertEqual({key: counts[key] for key in artifact_counts}, artifact_counts)
        self.assertEqual(set(counts) - set(artifact_counts), {"installedVisible", "addableVisible"})
        self.assertEqual(counts["installedVisible"], sum(row["installed"] for row in data["domains"]))
        self.assertEqual(counts["addableVisible"], sum(row["addable"] for row in data["domains"]))
        self.assertEqual(counts["visibleUnion"], sum(row["total"] for row in data["domains"]))

    def test_overview_json_carries_release_ref_and_derived_per_domain_examples(self):
        artifact = catalog.load_catalog(PLUGIN_ROOT)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, out, err = self.run_discovery(["overview", "--json"], root, root / "home")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["releaseRef"], artifact["publicRelease"]["releaseRef"])
        for entry in data["domains"]:
            with self.subTest(domain=entry["domain"]):
                # Nothing is installed standalone under the temporary roots, so the
                # bundled foundation roster is exactly the installed set here.
                group = [row for row in artifact["skills"] if row["domain"] == entry["domain"]]
                installed = [row for row in group if row["foundationInstalled"]]
                addable = [row for row in group if row["publicAvailable"] and not row["foundationInstalled"]]
                self.assertEqual(entry["installed"], len(installed))
                self.assertEqual(entry["addable"], len(addable))
                # installedExample prefers the authored curated example, falling back
                # to the first installed skill's live examplePrompt; None when nothing
                # is installed. addableExample stays the first addable's live prompt.
                disp = catalog._display(entry["domain"])
                expected_installed = (
                    (disp.get("installedExample") or installed[0]["examplePrompt"])
                    if installed else None
                )
                self.assertEqual(entry["installedExample"], expected_installed)
                self.assertEqual(
                    entry["addableExample"], addable[0]["examplePrompt"] if addable else None
                )
        self.assertIn(None, [entry["installedExample"] for entry in data["domains"]])
        self.assertIn(None, [entry["addableExample"] for entry in data["domains"]])

    def test_overview_omits_the_connect_affordance_even_when_no_org(self):
        """The connect-an-org affordance was removed (org connection can't yet tailor
        the catalog): even with no org connected, the overview shows no connect lead —
        just the honest full catalog, both labelled sections with exact counts, still
        80-column and leak-free."""
        artifact = catalog.load_catalog(PLUGIN_ROOT)
        installed = [row for row in artifact["skills"] if row["foundationInstalled"]]
        addable = [row for row in artifact["skills"]
                   if row["publicAvailable"] and not row["foundationInstalled"]]
        with tempfile.TemporaryDirectory() as td:
            code, out, err = self.run_discovery(
                ["overview"], Path(td), Path(td) / "home", org_presence="none")
        self.assertEqual((code, err), (0, ""))
        # No connect affordance anywhere: no honesty warning, no pitch, no CTA/command.
        self.assertNotIn("No org connected", out)
        self.assertNotIn("Why connect an org first?", out)
        self.assertNotIn('"connect an org"', out)
        self.assertNotIn("sf org list", out)
        self.assertNotIn("connect an org to see which apply to you", out)
        # The honest full catalog: both sections, exact counts intact.
        sections = self.overview_sections(out)
        self.assertEqual(sorted(sections), ["AVAILABLE TO ADD", "INSTALLED"])
        headings = {line.split(" —")[0]: line for line in out.splitlines()
                    if line.startswith(("INSTALLED", "AVAILABLE TO ADD"))}
        self.assertIn(str(len(installed)), headings["INSTALLED"])
        self.assertIn(str(len(addable)), headings["AVAILABLE TO ADD"])
        # Same hard invariants as the neutral overview: 80-col and leak-free.
        self.assertEqual([line for line in out.splitlines() if len(line) > 80], [])
        self.assertNotIn("sf-context", out)
        self.assertNotIn("spike", out.lower())

    def test_overview_json_carries_org_presence_without_perturbing_counts(self):
        """org-presence is a runtime lead hint on the JSON surface; it must never
        change the exact counts contract."""
        artifact_counts = catalog.load_catalog(PLUGIN_ROOT)["counts"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, out, err = self.run_discovery(
                ["overview", "--json"], root, root / "home", org_presence="none")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["orgPresence"], "none")
        self.assertEqual({key: data["counts"][key] for key in artifact_counts}, artifact_counts)

    def test_overview_is_org_neutral_across_every_presence(self):
        """The overview no longer varies on org presence: none, connected, unknown,
        and the default (org-presence unresolved) all render the same neutral block —
        no connect lead, the neutral INSTALLED heading, and both sections."""
        for presence in ("none", "connected", "unknown", None):
            with self.subTest(presence=presence):
                with tempfile.TemporaryDirectory() as td:
                    code, out, err = self.run_discovery(
                        ["overview"], Path(td), Path(td) / "home", org_presence=presence)
                self.assertEqual((code, err), (0, ""))
                self.assertNotIn("No org connected", out)
                self.assertNotIn("Why connect an org first?", out)
                self.assertNotIn('"connect an org"', out)
                self.assertIn("ready in this session", out)   # neutral INSTALLED heading
                self.assertIn("INSTALLED", out)
                self.assertIn("AVAILABLE TO ADD", out)

    def test_overview_human_renders_friendly_labels_and_taglines_not_raw_prefixes(self):
        """The two-tier block presents first-party display copy: friendly labels on
        both sections, taglines on AVAILABLE-TO-ADD rows, and a concrete example on
        INSTALLED rows — never the raw domain prefix, still within 80 columns."""
        with tempfile.TemporaryDirectory() as td:
            code, out, err = self.run_discovery(["overview"], Path(td), Path(td) / "home")
        self.assertEqual((code, err), (0, ""))
        # A sampling of friendly labels (including ones the raw prefix would mangle).
        for label in ("Platform Core", "Data Cloud (Data 360)", "OmniStudio", "Diagrams"):
            self.assertIn(label, out)
        # A tagline (drives an AVAILABLE-TO-ADD row) and an installed example.
        self.assertIn("OmniScripts, FlexCards, Integration Procedures.", out)
        self.assertIn("write an AccountService class", out)
        # Raw prefixes must never surface as a row label ("<prefix> (N)").
        for raw in ("data360", "design-systems", "omnistudio", "external", "platform"):
            self.assertNotIn(f"{raw} (", out)
        self.assertEqual([line for line in out.splitlines() if len(line) > 80], [])

    def test_overview_rows_stay_bounded_for_wide_unicode_cells(self):
        data = {
            "counts": {"public": 1, "foundation": 1, "overlap": 0, "visibleUnion": 1,
                       "installedVisible": 1, "addableVisible": 1},
            "releaseRef": "0.0.0",
            "availability": None,
            "domains": [{
                "domain": "platform", "label": "界" * 20,
                "installed": 1, "addable": 1,
                "installedExample": "界" * 48, "tagline": "界" * 48,
            }],
        }
        block = catalog._overview_text(data)
        self.assertTrue(all(
            catalog._terminal_cell_width(line) <= 80 for line in block.splitlines()
        ), block)

    def test_overview_rows_stay_bounded_when_a_catalog_prompt_is_overlong(self):
        """No live prompt is long enough to clamp, so drive the clamp with a synthetic one."""
        overlong = "Ask the platform to generate something " * 8
        data = {
            "counts": {
                "public": 1, "foundation": 1, "overlap": 0, "visibleUnion": 1,
                "installedVisible": 1, "addableVisible": 1,
            },
            "releaseRef": "0.0.0",
            # The INSTALLED cell is the (overlong) installedExample; the AVAILABLE
            # cell is the (overlong) tagline. Both must clamp to the example cell.
            "domains": [{
                "domain": "platform", "label": "Platform Core",
                "installed": 1, "addable": 1,
                "installedExample": overlong, "tagline": overlong,
            }],
        }
        out = io.StringIO()
        with redirect_stdout(out):
            catalog._print_overview(data)
        width = 2 + catalog._DOMAIN_CELL + 1 + catalog._EXAMPLE_CELL
        rows = [line for line in out.getvalue().splitlines() if line.startswith("  ")]
        self.assertEqual(len(rows), 2)
        for row in rows:
            with self.subTest(row=row):
                self.assertTrue(row.endswith("…"), row)
                self.assertLessEqual(len(row), width)
        self.assertNotIn(overlong, out.getvalue())

    def test_access_state_classifies_the_tristate_by_shape_not_truthiness(self):
        # [] and None are both falsy: classify by isinstance, never truthiness. A
        # truthiness collapse would fold "applies to any org" into "undeclared" and,
        # worse, read an absent declaration as org-agnostic. Any non-list shape is
        # undeclared — the safe direction, never a positive org-agnostic claim.
        self.assertEqual(catalog._access_state(None), "undeclared")
        self.assertEqual(catalog._access_state([]), "any-org")
        self.assertEqual(
            catalog._access_state([{"type": "license", "value": "X"}]), "conditional"
        )
        self.assertEqual(catalog._access_state("license"), "undeclared")

    def test_overview_availability_partition_matches_the_offline_catalog(self):
        """The JSON availability partition is derived offline from each skill's own
        accessCheck (public-preferred), sums to visibleUnion, and is basis-tagged."""
        artifact = catalog.load_catalog(PLUGIN_ROOT)
        expected = {"any-org": 0, "conditional": 0, "undeclared": 0}
        for row in artifact["skills"]:
            expected[catalog._access_state(catalog._selected_access_check(row))] += 1
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, out, err = self.run_discovery(["overview", "--json"], root, root / "home")
        self.assertEqual((code, err), (0, ""))
        availability = json.loads(out)["availability"]
        self.assertEqual(availability["basis"], "declared-offline")
        self.assertEqual(availability["anyOrg"], expected["any-org"])
        self.assertEqual(availability["conditional"], expected["conditional"])
        self.assertEqual(availability["undeclared"], expected["undeclared"])
        self.assertEqual(
            availability["anyOrg"] + availability["conditional"] + availability["undeclared"],
            artifact["counts"]["visibleUnion"],
        )
        self.assertEqual(availability["total"], artifact["counts"]["visibleUnion"])
        # A truthiness-based classifier would misfile the [] any-org skills; the
        # real catalog carries at least one declared gate, so the partition is not
        # trivially all-undeclared.
        self.assertGreaterEqual(availability["conditional"] + availability["anyOrg"], 1)

    def test_overview_availability_is_org_independent(self):
        """Availability is what each skill declares offline, never a probe of the
        connected org — so it renders identically for every org-presence state."""
        partitions = {}
        for presence in ("connected", "none", "unknown"):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                _, out, err = self.run_discovery(
                    ["overview", "--json"], root, root / "home", org_presence=presence)
            self.assertEqual(err, "")
            partitions[presence] = json.loads(out)["availability"]
        self.assertEqual(partitions["connected"], partitions["none"])
        self.assertEqual(partitions["connected"], partitions["unknown"])

    def test_overview_human_shows_declared_availability_with_the_unknown_disclaimer(self):
        """The real catalog declares posture on at least one skill today, so the
        offline availability block renders — and while any skill is still
        undeclared the 'not yet declared means unknown' disclaimer rides with it."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, out, err = self.run_discovery(["overview"], root, root / "home")
        self.assertEqual(err, "")
        self.assertIn("Declared availability (offline — not an org check)", out)
        self.assertIn("conditional", out)
        self.assertIn("not yet declared", out)
        self.assertIn('never read it as "applies to any org."', out)
        self.assertEqual([line for line in out.splitlines() if len(line) > 80], [])

    def test_overview_hides_declared_availability_until_a_skill_declares_posture(self):
        """Pre-backfill every skill is undeclared and a '0 · 0 · N' line is noise, so
        the printed block is gated on a real signal (anyOrg+conditional>0). The JSON
        key is still always present (asserted in the partition test above)."""
        base = {
            "counts": {"public": 1, "foundation": 0, "overlap": 0, "visibleUnion": 1,
                       "installedVisible": 0, "addableVisible": 1},
            "releaseRef": "0.0.0",
            "domains": [],
        }
        all_undeclared = {**base, "availability": {
            "basis": "declared-offline", "anyOrg": 0, "conditional": 0,
            "undeclared": 1, "total": 1}}
        out = io.StringIO()
        with redirect_stdout(out):
            catalog._print_overview(all_undeclared)
        self.assertNotIn("Declared availability", out.getvalue())
        with_signal = {**base, "availability": {
            "basis": "declared-offline", "anyOrg": 2, "conditional": 0,
            "undeclared": 1, "total": 3}}
        out = io.StringIO()
        with redirect_stdout(out):
            catalog._print_overview(with_signal)
        self.assertIn("Declared availability", out.getvalue())
        self.assertIn("2 apply to any org", out.getvalue())
        self.assertIn("not yet declared", out.getvalue())

    def test_domain_human_keeps_every_row_and_footers_only_the_first_capability(self):
        """Domain rows stay complete while wrapping; footer names only the first capability."""
        by_domain: dict[str, list[str]] = {}
        for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]:
            by_domain.setdefault(row["domain"], []).append(row["name"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for domain, names in by_domain.items():
                with self.subTest(domain=domain):
                    code, out, err = self.run_discovery(["domain", domain], root, root / "home")
                    self.assertEqual((code, err), (0, ""))
                    for name in names:
                        self.assertIn(f"- {name} [", out)
                    self.assertIn(
                        f"Next: /salesforce-development:discovery skill {min(names)}",
                        " ".join(out.split()),
                    )
                    self.assertTrue(all(
                        catalog._terminal_cell_width(line) <= 80
                        for line in out.splitlines()
                    ))
                    self.assertNotIn("sf-context", out)
                    self.assertNotIn("Try:", out)
                    self.assertNotIn("npx skills", out)

    def test_json_modes_and_available_skill_instruction(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, overview, _ = self.run_discovery(["--json"], root, root / "home")
            overview_data = json.loads(overview)
            self.assertEqual(code, 0)
            self.assertEqual(overview_data["mode"], "overview")
            domain = overview_data["domains"][0]["domain"]
            code, domain_out, _ = self.run_discovery(["domain", domain, "--json"], root, root / "home")
            domain_data = json.loads(domain_out)
            self.assertEqual(code, 0)
            self.assertEqual(domain_data["mode"], "domain")
            self.assertTrue(domain_data["skills"])
            available = next(
                row for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]
                if not row["foundationInstalled"] and row["publicAvailable"]
            )
            code, detail_out, _ = self.run_discovery(["skill", available["name"], "--json"], root, root / "home")
            detail = json.loads(detail_out)
            self.assertEqual(code, 0)
            self.assertEqual(detail["status"], "available")
            self.assertEqual(detail["installInstruction"], INSTALL.format(name=available["name"]))
            self.assertIn("fresh Claude session", detail["sessionRequirement"])
            code, index_out, _ = self.run_discovery(["index"], root, root / "home")
            self.assertEqual(code, 0)
            index_lines = index_out.strip().splitlines()
            self.assertEqual(sum(not line.startswith("  ") for line in index_lines), 113)
            self.assertTrue(all(catalog._terminal_cell_width(line) <= 80 for line in index_lines))

    def test_valid_standalone_directory_symlink_counts_as_installed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cwd, home = root / "project", root / "home"
            available_name = next(
                row["name"] for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]
                if not row["foundationInstalled"] and row["publicAvailable"]
            )
            source = root / available_name
            source.mkdir(parents=True)
            source.joinpath("SKILL.md").write_text(
                f'---\nname: {available_name}\ndescription: "Use this standalone skill for capability testing."\n---\n',
                encoding="utf-8",
            )
            project_skills = cwd / ".claude/skills"
            project_skills.mkdir(parents=True)
            project_skills.joinpath(available_name).symlink_to(source, target_is_directory=True)
            code, out, _ = self.run_discovery(["skill", available_name, "--json"], cwd, home)
        self.assertEqual(code, 0)
        detail = json.loads(out)
        self.assertEqual(detail["status"], "installed")
        self.assertEqual(detail["provenance"]["state"], "modified")
        self.assertEqual(detail["provenance"]["observations"], [])

    def test_invalid_same_name_entries_do_not_install_or_suppress_public_add(self):
        available_name = next(
            row["name"] for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]
            if not row["foundationInstalled"] and row["publicAvailable"]
        )
        for kind in ("malformed", "file", "dangling"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                cwd, home = root / "project", root / "home"
                target = cwd / ".claude/skills" / available_name
                target.parent.mkdir(parents=True)
                if kind == "malformed":
                    target.mkdir()
                    target.joinpath("SKILL.md").write_text("not frontmatter", encoding="utf-8")
                elif kind == "file":
                    target.write_text("not a directory", encoding="utf-8")
                else:
                    target.symlink_to(root / "missing", target_is_directory=True)
                code, out, err = self.run_discovery(["skill", available_name, "--json"], cwd, home)
                detail = json.loads(out)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(detail["status"], "available")
                self.assertEqual(detail["installInstruction"], INSTALL.format(name=available_name))
                self.assertEqual(detail["provenance"]["records"], [])
                self.assertEqual(detail["provenance"]["state"], "unknown")
                self.assertEqual(detail["provenance"]["observations"][0]["state"], "invalid")

    def test_unreadable_same_name_directory_is_unknown_and_not_installed(self):
        available_name = next(
            row["name"] for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]
            if not row["foundationInstalled"] and row["publicAvailable"]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "project/.claude/skills" / available_name
            target.mkdir(parents=True)
            target.joinpath("SKILL.md").write_text(
                f'---\nname: {available_name}\ndescription: "Use this fixture to test unreadable installed observations safely."\n---\n',
                encoding="utf-8",
            )
            with mock.patch.object(catalog.registry, "inspect_skill_tree", side_effect=OSError("denied")):
                code, out, err = self.run_discovery(
                    ["skill", available_name, "--json"], root / "project", root / "home"
                )
        detail = json.loads(out)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(detail["status"], "available")
        self.assertEqual(detail["provenance"]["state"], "unknown")
        self.assertEqual(detail["provenance"]["observations"][0]["state"], "unknown")

    def test_tree_hash_provenance_public_exact_modified_unknown_and_conflict(self):
        baseline = catalog.load_catalog(PLUGIN_ROOT)
        source_row = next(
            row for row in baseline["skills"]
            if row["publicAvailable"] and not row["foundationInstalled"]
        )
        name = source_row["name"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "plugin"
            artifact = plugin / catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            installed = root / "project/.claude/skills" / name
            installed.mkdir(parents=True)
            skill_text = (
                f'---\nname: {name}\n'
                'description: "Use this exact public fixture to test installed provenance safely."\n'
                '---\nbody\n'
            )
            (installed / "SKILL.md").write_text(skill_text, encoding="utf-8")
            altered = copy.deepcopy(baseline)
            row = next(item for item in altered["skills"] if item["name"] == name)
            row["variants"]["public"]["treeSha256"] = catalog.registry.canonical_tree_sha256(installed)
            row["variants"]["public"]["skillMdSha256"] = catalog.registry.sha256_file(installed / "SKILL.md")
            artifact.write_text(json.dumps(altered), encoding="utf-8")

            code, out, err = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            self.assertEqual((code, err), (0, ""))
            exact = json.loads(out)
            self.assertEqual(exact["provenance"]["state"], "public-exact")
            self.assertEqual(
                exact["description"],
                "Use this exact public fixture to test installed provenance safely.",
            )

            (installed / "extra.txt").write_text("modified", encoding="utf-8")
            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            modified = json.loads(out)
            self.assertEqual(modified["provenance"]["state"], "modified")
            self.assertNotIn("description", modified)

            user_copy = root / "home/.claude/skills" / name
            user_copy.mkdir(parents=True)
            (user_copy / "SKILL.md").write_text(skill_text, encoding="utf-8")
            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            self.assertEqual(json.loads(out)["provenance"]["state"], "conflict")

            (installed / "SKILL.md").write_text("malformed", encoding="utf-8")
            user_copy.joinpath("SKILL.md").write_text("malformed", encoding="utf-8")
            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            unknown = json.loads(out)
            self.assertEqual(unknown["provenance"]["state"], "unknown")
            self.assertEqual(unknown["status"], "available")
            self.assertEqual(len(unknown["provenance"]["observations"]), 2)

    def test_raced_scan_is_rejected_as_invalid_not_classified_exact(self):
        # A scan the tree changed *during* (stable=False) is failed closed: even when
        # its torn hash still matches the trusted variant, it is NEVER classified
        # installed/exact — it is retained as an invalid observation, matching the
        # build-time canonical_tree_sha256 gate. Supersedes the earlier "preserve
        # classification but omit description" behavior (Prizm A9).
        baseline = catalog.load_catalog(PLUGIN_ROOT)
        source_row = next(
            row for row in baseline["skills"]
            if row["publicAvailable"] and not row["foundationInstalled"]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "plugin"
            artifact = plugin / catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(baseline), encoding="utf-8")
            installed = root / "project/.claude/skills" / source_row["name"]
            installed.mkdir(parents=True)
            expected = source_row["variants"]["public"]["treeSha256"]
            with mock.patch.object(
                catalog.registry,
                "inspect_skill_tree",
                return_value={"treeSha256": expected, "skillMdBytes": None, "stable": False},
            ):
                _, out, _ = self.run_discovery_with_plugin(
                    ["skill", source_row["name"], "--json"],
                    plugin,
                    root / "project",
                    root / "home",
                )
        detail = json.loads(out)
        self.assertEqual(detail["status"], "available")
        self.assertEqual(detail["provenance"]["state"], "unknown")
        self.assertEqual(detail["provenance"]["records"], [])
        self.assertEqual(detail["provenance"]["observations"][0]["state"], "invalid")
        self.assertNotIn("description", detail)
        self.assertIn("catalogMetadataNotice", detail)

    def test_raced_bundled_foundation_scan_is_rejected_not_classified_exact(self):
        # The bundled-foundation path fails closed too: an unstable scan of the plugin's
        # own skill tree is an invalid observation, never a raced foundation-exact.
        baseline = catalog.load_catalog(PLUGIN_ROOT)
        foundation_row = next(row for row in baseline["skills"] if row["foundationInstalled"])
        name = foundation_row["name"]
        expected = foundation_row["variants"]["foundation"]["treeSha256"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "plugin"
            artifact = plugin / catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(baseline), encoding="utf-8")
            bundled = plugin / "skills" / name
            bundled.parent.mkdir(parents=True)
            shutil.copytree(PLUGIN_ROOT / "skills" / name, bundled)
            with mock.patch.object(
                catalog.registry,
                "inspect_skill_tree",
                return_value={"treeSha256": expected, "skillMdBytes": None, "stable": False},
            ):
                _, out, _ = self.run_discovery_with_plugin(
                    ["skill", name, "--json"], plugin, root / "project", root / "home"
                )
        detail = json.loads(out)
        self.assertEqual(detail["status"], "available")
        self.assertEqual(detail["provenance"]["state"], "unknown")
        self.assertEqual(detail["provenance"]["records"], [])
        self.assertEqual(detail["provenance"]["observations"][0]["state"], "invalid")
        self.assertNotIn("description", detail)

    def test_unsafe_same_name_observation_suppresses_other_exact_description(self):
        baseline = catalog.load_catalog(PLUGIN_ROOT)
        source_row = next(
            row for row in baseline["skills"]
            if row["publicAvailable"] and not row["foundationInstalled"]
        )
        name = source_row["name"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "plugin"
            artifact = plugin / catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            exact = root / "home/.claude/skills" / name
            exact.mkdir(parents=True)
            skill_text = (
                f'---\nname: {name}\n'
                'description: "Use this exact public fixture without trusting an unsafe peer."\n'
                '---\nbody\n'
            )
            (exact / "SKILL.md").write_text(skill_text, encoding="utf-8")
            altered = copy.deepcopy(baseline)
            row = next(item for item in altered["skills"] if item["name"] == name)
            row["variants"]["public"]["treeSha256"] = catalog.registry.canonical_tree_sha256(exact)
            row["variants"]["public"]["skillMdSha256"] = catalog.registry.sha256_file(exact / "SKILL.md")
            artifact.write_text(json.dumps(altered), encoding="utf-8")
            unsafe = root / "project/.claude/skills" / name
            unsafe.parent.mkdir(parents=True)
            unsafe.symlink_to(root / "missing", target_is_directory=True)
            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
        detail = json.loads(out)
        self.assertEqual(detail["status"], "installed")
        self.assertEqual(detail["provenance"]["state"], "conflict")
        self.assertNotIn("description", detail)
        self.assertIn("catalogMetadataNotice", detail)
        self.assertEqual(detail["provenance"]["observations"][0]["state"], "invalid")

    def test_bundled_foundation_is_hashed_at_runtime_and_symlink_is_unknown(self):
        baseline = catalog.load_catalog(PLUGIN_ROOT)
        foundation_row = next(row for row in baseline["skills"] if row["foundationInstalled"])
        name = foundation_row["name"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "plugin"
            artifact = plugin / catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(baseline), encoding="utf-8")
            bundled = plugin / "skills" / name
            bundled.parent.mkdir(parents=True)
            shutil.copytree(PLUGIN_ROOT / "skills" / name, bundled)

            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            exact = json.loads(out)
            self.assertEqual(exact["provenance"]["state"], "foundation-exact")
            self.assertEqual(exact["status"], "installed")

            bundled.joinpath("runtime-mutation.txt").write_text("changed", encoding="utf-8")
            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            modified = json.loads(out)
            self.assertEqual(modified["provenance"]["state"], "modified")
            self.assertNotIn("description", modified)

            shutil.rmtree(bundled)
            external = root / "external"
            shutil.copytree(PLUGIN_ROOT / "skills" / name, external)
            bundled.symlink_to(external, target_is_directory=True)
            _, out, _ = self.run_discovery_with_plugin(
                ["skill", name, "--json"], plugin, root / "project", root / "home"
            )
            unknown = json.loads(out)
            self.assertEqual(unknown["provenance"]["state"], "unknown")
            self.assertEqual(unknown["status"], "available")
            self.assertEqual(unknown["provenance"]["observations"][0]["state"], "invalid")

    def run_discovery_with_plugin(self, args, plugin, cwd, home):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = catalog.run_discovery(args, plugin_root=plugin, cwd=cwd, home=home)
        return code, out.getvalue(), err.getvalue()

    def test_unknown_mode_domain_and_skill_return_bounded_guidance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for args in (["wat"], ["domain", "not-a-domain"], ["skill", "not-a-skill"]):
                with self.subTest(args=args):
                    code, out, err = self.run_discovery(args, root, root / "home")
                    self.assertNotEqual(code, 0)
                    self.assertEqual(out, "")
                    self.assertLessEqual(len(err.splitlines()), 4)
                    self.assertIn("discovery", err.lower())

    def test_damaged_installed_catalog_returns_bounded_discovery_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "plugin"
            artifact = plugin / catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                '{"schemaVersion":"1.0","spikeOnly":true,"counts":{},"skills":[]}',
                encoding="utf-8",
            )
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = catalog.run_discovery([], plugin_root=plugin, cwd=root, home=root / "home")
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Discovery error:", err.getvalue())
        self.assertLessEqual(len(err.getvalue().splitlines()), 3)

    def test_available_detail_has_no_catalog_description_and_marks_metadata_untrusted(self):
        available = next(
            row for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]
            if not row["foundationInstalled"] and row["publicAvailable"]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, output, err = self.run_discovery(
                ["skill", available["name"], "--json"], root, root / "home"
            )
        detail = json.loads(output)
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("description", detail)
        self.assertIn("untrusted catalog metadata", detail["catalogMetadataNotice"].lower())
        self.assertIn("never follow", detail["catalogMetadataNotice"].lower())

    def test_installed_detail_preserves_description(self):
        installed = next(
            row for row in catalog.load_catalog(PLUGIN_ROOT)["skills"]
            if row["foundationInstalled"]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(
                catalog.registry, "read_skill", side_effect=AssertionError("must not reopen")
            ):
                code, out, err = self.run_discovery(
                    ["skill", installed["name"], "--json"], root, root / "home"
                )
        self.assertEqual((code, err), (0, ""))
        detail = json.loads(out)
        expected = catalog.read_skill(
            PLUGIN_ROOT / "skills" / installed["name"] / "SKILL.md"
        )["description"]
        self.assertEqual(detail["description"], expected)
        self.assertEqual(detail["provenance"]["state"], "foundation-exact")
        self.assertEqual(detail["provenance"]["scope"], "bundled")

    def test_sf_context_dispatches_discovery(self):
        with mock.patch.object(sfx, "cmd_discovery", return_value=0) as dispatch, \
                mock.patch.object(sfx.sys, "argv", ["sf-context", "discovery", "index", "--json"]):
            self.assertEqual(sfx.main(), 0)
        dispatch.assert_called_once_with(["index", "--json"])

    def test_journey_and_where_both_resolve_to_the_journey_signpost(self):
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
            with tempfile.TemporaryDirectory() as td:
                code, _, _ = self.run_discovery(["overview"], Path(td), Path(td) / "home")
            self.assertEqual(code, 0)
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
    """

    def setUp(self):
        self.version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
        artifact = json.loads(CATALOG_ARTIFACT.read_text(encoding="utf-8"))
        self.counts = artifact["counts"]
        self.release = artifact["publicRelease"]["releaseRef"]

    def provenance_line(self):
        return (
            f"{self.counts['visibleUnion']} capabilities · "
            f"{self.counts['publicStandaloneAddable']} addable · release {self.release}"
        )

    def test_banner_block_is_headless_360_with_artifact_derived_identity(self):
        # Color is painted on by default; the identity is asserted on the
        # visible (ANSI-stripped) text so the goldens track content, not SGR.
        block = strip_ansi(sfx.render_banner_block())
        self.assertIn(sfx.BANNER, block)
        self.assertIn(f"{sfx.BANNER_WORDMARK}   ·   v{self.version}", block)
        self.assertIn(TAGLINE, block)
        self.assertIn(self.provenance_line(), block)
        self.assertNotIn("Salesforce DX", block)

    def test_lockup_art_matches_the_designed_ansi_shadow_geometry(self):
        """The comp's mark is a 6-line, 64-column block wordmark — pin both."""
        art = sfx.BANNER.splitlines()
        self.assertEqual(len(art), 6)
        self.assertEqual({len(line) for line in art}, {64})
        # Block-drawn, not the pure-ASCII Slant mark it replaced. Every cell must
        # come from the single-width block/box set, or the mark stops aligning.
        self.assertEqual(set(sfx.BANNER) - {"\n"}, set(" █╗╔╝╚═║"))

    def test_banner_block_display_width_fits_eighty_columns(self):
        # Width is a display constraint, so measure the visible text — SGR bytes
        # inflate len() well past 80 without adding a single column.
        lines = strip_ansi(sfx.render_banner_block()).splitlines()
        self.assertTrue(all(len(line) <= 80 for line in lines), lines)

    def test_banner_block_is_colored_by_default_and_plain_under_no_color(self):
        # The gate is ON now: the SessionStart banner paints with the theme-adaptive
        # palette (bright-blue lockup, no truecolor), stripping to the plain lockup.
        # NO_COLOR forces it fully plain (and model-reproduced stdout callers pass
        # color=False — see render_banner_message).
        with mock.patch.dict(os.environ, {}, clear=True):
            block = sfx.render_banner_block()
        self.assertIn("\x1b[94m", block)               # bright-blue lockup hue
        self.assertNotIn("\x1b[38;2", block)           # theme-adaptive: no truecolor
        self.assertIn(sfx.BANNER, strip_ansi(block))
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            plain = sfx.render_banner_block()
        self.assertNotIn("\x1b", plain)
        self.assertIn(sfx.BANNER, plain)

    def test_provenance_fails_open_on_missing_and_damaged_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing"
            damaged = Path(td) / "damaged"
            damaged.joinpath(".claude-plugin").mkdir(parents=True)
            damaged.joinpath(".claude-plugin/plugin.json").write_text("{not json", encoding="utf-8")
            damaged.joinpath("catalog").mkdir()
            damaged.joinpath("catalog/discovery.json").write_text(
                '{"counts":{"visibleUnion":"many"},"publicRelease":{}}', encoding="utf-8"
            )
            for root in (missing, damaged):
                with self.subTest(root=root.name):
                    facts = sfx._banner_provenance(root)
                    self.assertEqual(facts["version"], "?")
                    self.assertIsNone(facts["capabilities"])
                    self.assertIsNone(facts["addable"])
                    self.assertIsNone(facts["releaseRef"])
                    block = strip_ansi(sfx.render_banner_block(root))
                    self.assertIn(sfx.BANNER, block)
                    self.assertIn("v?", block)
                    self.assertIn(TAGLINE, block)
                    self.assertNotIn("release", block)

    def test_banner_stays_within_eighty_columns_on_absurd_artifact_values(self):
        """The ≤80 lockup is a contract, so artifact strings it interpolates are bounded."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath(".claude-plugin").mkdir()
            root.joinpath(".claude-plugin/plugin.json").write_text(
                json.dumps({"version": "9." + "9" * 200}), encoding="utf-8"
            )
            root.joinpath("catalog").mkdir()
            root.joinpath("catalog/discovery.json").write_text(
                json.dumps({
                    "counts": {"visibleUnion": 10 ** 40, "publicStandaloneAddable": 10 ** 40},
                    "publicRelease": {"releaseRef": "1." + "2" * 200},
                }),
                encoding="utf-8",
            )
            block = strip_ansi(sfx.render_banner_block(root))
        self.assertTrue(all(len(line) <= 80 for line in block.splitlines()), block)
        self.assertIn(sfx.BANNER, block)

    def test_degraded_banner_carries_the_same_lockup_and_one_pointer(self):
        raw = sfx.render_degraded_banner("No Default Org", ["No target-org is set."])
        degraded = strip_ansi(raw)
        self.assertIn(sfx.BANNER, degraded)
        self.assertIn(TAGLINE, degraded)
        self.assertIn(self.provenance_line(), degraded)
        # Now closes with the shared wayfinding footer (unified with the connected banner),
        # not the lone one-liner pointer; the discovery command token still appears once.
        self.assertIn("You don't memorize commands here.", degraded)
        self.assertEqual(degraded.count("/salesforce-development:discovery"), 1)
        self.assertTrue(all(len(line) <= 80 for line in degraded.splitlines()))


class EnvironmentBandTests(unittest.TestCase):
    """The rule-delimited status bands that replaced the titled boxes below the
    lockup. Every count is derived from the checked artifacts here rather than
    restated as a literal, and the band never fabricates an MCP health check."""

    def setUp(self):
        self.counts = json.loads(CATALOG_ARTIFACT.read_text(encoding="utf-8"))["counts"]
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

    def test_install_summary_counts_are_artifact_derived(self):
        skills = self.counts["foundation"]
        library = self.counts["visibleUnion"]
        commands = len(list((PLUGIN_ROOT / "commands").glob("*.md")))
        agents = len(list((PLUGIN_ROOT / "agents").glob("*.md")))
        servers = len(json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"])
        msg = self.message()
        self.assertIn("✓ Installed salesforce-development", msg)
        self.assertIn(
            f"{skills} skills installed · {library} in library · "
            f"{commands} commands · {agents} agents · {servers} MCP servers", msg)

    def test_install_summary_fails_open_on_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(sfx._install_facets(root), [])
            summary = strip_ansi("\n".join(sfx.render_install_summary(False, root)))
            self.assertIn("✓ Installed salesforce-development", summary)  # names the plugin (pinned fallback)
            self.assertNotRegex(summary, r"\d+\s+skills")  # no fabricated count

    def test_catalog_facts_fail_open_independently(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath(".claude-plugin").mkdir()
            root.joinpath(".claude-plugin/plugin.json").write_text(
                json.dumps({"name": "salesforce-development", "version": "1.9.0"}),
                encoding="utf-8",
            )
            catalog_dir = root / "catalog"
            catalog_dir.mkdir()
            artifact = catalog_dir / "discovery.json"

            artifact.write_text(
                json.dumps({
                    "counts": {"visibleUnion": 114, "foundation": 41},
                    "publicRelease": {"releaseRef": "1.32.0"},
                }),
                encoding="utf-8",
            )
            facts = sfx._banner_provenance(root)
            self.assertIsNone(facts["capabilities"])
            summary = "\n".join(sfx.render_install_summary(False, root, facts=facts))
            self.assertIn("41 skills installed · 114 in library", summary)

            artifact.write_text(
                json.dumps({
                    "counts": {
                        "visibleUnion": 114,
                        "foundation": "many",
                        "publicStandaloneAddable": 73,
                    },
                    "publicRelease": {"releaseRef": "1.32.0"},
                }),
                encoding="utf-8",
            )
            facts = sfx._banner_provenance(root)
            self.assertIsNone(facts["foundation"])
            self.assertIn("114 capabilities · 73 addable · release 1.32.0", sfx.render_banner_block(root, facts=facts))

    def test_install_summary_drops_the_comp_fictions(self):
        msg = self.message()
        self.assertIn("✓ Installed", msg)             # present-state label — true on every session
        self.assertNotIn("reloaded", msg)             # no reload signal exists in the payload
        self.assertNotIn("marketplace", msg.lower())  # not reachable from the plugin-rooted hook

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
        self.assertTrue(all(len(line) <= 80 for line in msg.splitlines()), msg)

    def test_detail_line_omitted_when_org_lacks_instance_and_username(self):
        band = strip_ansi("\n".join(sfx.render_environment_band(
            {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}, "connecting", False)))
        self.assertNotIn("https://", band)
        self.assertNotIn("@", band)

    def test_bands_stay_within_eighty_on_absurd_values(self):
        msg = self.message(alias="Z" * 300, edition="E" * 300,
                           instanceUrl="https://" + "x" * 300, username="u" * 300)
        self.assertTrue(all(len(line) <= 80 for line in msg.splitlines()), msg)

    def test_message_uses_rules_not_boxes(self):
        msg = self.message()
        self.assertIn("─" * 64, msg)
        for box_glyph in ("╭", "╰", "│"):
            self.assertNotIn(box_glyph, msg)

    def test_invitation_is_mindset_line_and_a_single_pointer(self):
        # Counts are not restated in the invitation — the installed count rides in
        # the install summary, the library/addable totals in the provenance line.
        msg = self.message()
        self.assertIn("You don't memorize commands here.", msg)   # the mindset line
        self.assertIn('✳ New here? run /salesforce-development:discovery — or ask "what can I do here?"', msg)
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
        self.assertEqual(strip_ansi(colored), plain)

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
        self.assertNotIn("\x1b[38;2", colored)      # ...with the theme palette, not truecolor
        self.assertEqual(strip_ansi(colored), plain)

    def test_degraded_bands_keep_lockup_pointer_and_use_rules_not_boxes(self):
        for title, body in (("No Default Org", ["No target-org is set."]),
                            ("Org Unreachable", ["Configured org 'x' is unreachable."])):
            with self.subTest(title=title):
                d = strip_ansi(sfx.render_degraded_banner(title, body))
                self.assertIn(sfx.BANNER, d)
                self.assertIn(title, d)
                # Shared wayfinding footer now closes the degraded banner (single pointer).
                self.assertIn("You don't memorize commands here.", d)
                self.assertEqual(d.count("/salesforce-development:discovery"), 1)
                self.assertIn("─" * 64, d)
                for box_glyph in ("╭", "╰", "│"):
                    self.assertNotIn(box_glyph, d)
                self.assertTrue(all(len(line) <= 80 for line in d.splitlines()))

    def test_degraded_banner_clips_an_oversized_title_and_body(self):
        # Callers pass short literal titles today; clip defensively so the ≤80
        # contract holds structurally for the title, not just the body lines.
        d = strip_ansi(sfx.render_degraded_banner("T" * 300, ["b" * 300, "", "short"]))
        self.assertTrue(all(len(line) <= 80 for line in d.splitlines()), d)

    def test_degraded_banner_omits_the_install_summary(self):
        # Leaner degraded path: no install-confirmation line or inventory counts —
        # the provenance line already signals the plugin is live.
        d = strip_ansi(sfx.render_degraded_banner("No Default Org", ["No target-org is set."]))
        self.assertNotIn("✓ Installed", d)
        self.assertNotIn("MCP servers", d)

    def test_project_row_leads_with_the_sfdx_project_label(self):
        # Mirror the org row's leading "org:" label: the project band leads with
        # "sfdx project:" then the name, in the connected banner and (below) the
        # degraded path. Both labels are lowercase with a trailing colon so the two
        # deterministic surfaces (banner + journey rail) read identically.
        msg = self.message()
        self.assertIn("sfdx project: acme-crm", msg)
        self.assertIn("org: acme-dev", msg)

    def test_degraded_banner_carries_the_detected_project_context(self):
        # No org, but a project IS detected — surface where you are: the project
        # band rides below the guidance sharing its divider (one region, three
        # rules), so the no-org session still shows the local code it can act on.
        # This is the user's own project context, distinct from the dropped
        # plugin install summary.
        d = strip_ansi(sfx.render_degraded_banner(
            "No Default Org", ["No target-org is set.", "", "Skills are available for local code generation."],
            project=self.project, stats=self.stats, git_line="4 file(s) changed"))
        self.assertIn("sfdx project: acme-crm", d)        # label precedes project name
        self.assertIn("Apex 12 src / 8 test", d)           # code inventory row
        self.assertIn("4 file(s) changed", d)              # git line
        self.assertEqual(d.splitlines().count("─" * 64), 3)   # shared divider, not doubled
        self.assertNotIn("✓ Installed", d)   # still no install summary

    def test_degraded_banner_with_project_context_stays_within_eighty(self):
        # Project name/dirs/git can be untrusted or long — the band must still
        # clip to the ≤80 contract, not just the guidance lines.
        d = strip_ansi(sfx.render_degraded_banner(
            "T" * 300, ["b" * 300],
            project={"name": "Z" * 300, "source_api": "9" * 300, "package_dirs": "p" * 300},
            stats=self.stats, git_line="g" * 300))
        self.assertTrue(all(len(line) <= 80 for line in d.splitlines()), d)


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

    def test_connected_project_visible_pointer_without_feature_detector(self):
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org), \
                mock.patch.object(sfx, "cmd_features") as feature_detector:
            _, result = self.capture_detect()
        self.assert_visible_pointer(result)
        feature_detector.assert_not_called()

    def test_session_start_seeds_the_rail_signature(self):
        # Decision 2: SessionStart records WHAT rail its banner painted, so a routine
        # connect right after (no step moved) de-dupes in the wayfinder instead of
        # repainting an identical rail. Needs a session id (the marker key) and a
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
            seeded = sfx._last_rail_signature("seed1")
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        self.assertIsNotNone(seeded)                 # a signature was seeded
        self.assertIn("Connect:complete", seeded)    # the org is set, so Connect is lit

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
        for fact in ("salesforce-development", "catalog", "project:", "org:",
                     "current stage:", "reached:", "no evidence:", "next action:",
                     "Skills first", POINTER):
            self.assertIn(fact, context)
        self.assertLessEqual(len(context), 3000)
        self.assertTrue(all(len(line) <= 120 for line in context.splitlines()), context)
        self.assertFalse(any(ord(ch) < 32 and ch not in "\n\t" for ch in context))

    def test_session_start_banner_includes_the_position_rail(self):
        # SessionStart now shows "where you are" (the rail) alongside "what's here"
        # (the bands). The rail is built from the org already resolved for the bands.
        self.make_project()
        p1, p2 = self.normal_patches()
        org = {"orgInfo": {"alias": "fixture", "edition": "Developer", "apiVersion": "65.0"}}
        with p1, p2, mock.patch.object(sfx, "fetch_org_info_via_node", return_value=org):
            _, result = self.capture_detect()
        visible = strip_ansi(result["systemMessage"])
        # Rail labels (front-of-journey redesign: Setup left the rail, Project joined).
        self.assertIn("connect", visible)
        self.assertIn("project", visible)
        self.assertIn("build", visible)
        self.assertIn("likely next", visible)  # rail's next step
        self.assertTrue(all(len(l) <= 80 for l in visible.splitlines()))

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
        """An orientation question must reach the rail, not stop at the banner's facts.

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
        self.assertRegex(rule, r"(?i)never answer those with the journey rail")
        self.assertLessEqual(len(rule.splitlines()), 24)

    def test_orientation_rule_requires_the_rail_and_then_the_model_s_own_read(self):
        """The answer is both halves, in order: deterministic grounding, then relevance.

        The rail alone is consistent but inert; prose alone is relevant but drifts
        run to run and hides the six-stage model. The contract is rail first and
        unmodified, then the model's own short read of what it means here.
        """
        rule = sfx.ORIENTATION_DIRECTIVE
        self.assertRegex(rule, r"(?i)two parts")
        first, second = rule.index("1."), rule.index("2.")
        self.assertLess(first, second)
        self.assertRegex(rule[first:second], r"(?i)unmodified")
        # A tool result can be collapsed or absent from what the user reads, so the
        # rail must be in the reply itself — measured: one run said "that's the
        # position rail" and shipped an answer containing no rail at all.
        self.assertRegex(rule[first:second], r"(?i)in your reply")
        self.assertRegex(rule[second:], r"(?i)never (restate|replace)")
        self.assertRegex(rule[second:], r"(?i)relevance|means for")

    def test_orientation_rule_defers_when_the_rail_is_already_painted(self):
        """The paint hook shows the rail in color; the directive must let the model
        skip reproducing it (else the plain reproduction double-prints the rail)."""
        rule = sfx.ORIENTATION_DIRECTIVE
        self.assertRegex(rule, r"(?i)already\s+displayed the rail")   # may wrap
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
        # SessionStart paints the banner (logo + rail), so it records BOTH markers:
        # `welcomed` (first orientation question won't re-show the logo) and `entered`
        # (first ordinary prompt won't repaint the rail). Isolate markers in the cwd.
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
            self.assertIsNotNone(sfx._last_rail_signature("sess-A"))
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
            self.assertIsNone(sfx._last_rail_signature("emit-failure"))
        finally:
            sfx._WELCOME_MARKER_DIR = orig

    def test_session_start_suppresses_the_duplicate_first_message_rail(self):
        # After SessionStart paints the banner+rail, the first ordinary in-project
        # prompt must NOT repaint the rail as ambient orientation — that duplicate
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
            self.assertEqual(json.loads(out.getvalue()), {"continue": True})   # silent, no duplicate rail
            js.assert_not_called()                                             # and no second org fetch
        finally:
            sfx._WELCOME_MARKER_DIR = orig


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
        # The rail rides with /status too — its labels and next step, fully plain
        # (the current-stage green accent is stripped on this model-reproduced pipe).
        self.assertIn("build", printed)
        self.assertIn("likely next", printed)


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
        # firing every Bash hook on every command). This is the fix for the rail
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
        self.assertTrue(all(len(l) <= 80 for l in msg.splitlines()))

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
        self.assertTrue(all(len(l) <= 80 for l in msg.splitlines()))

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
        self.assertIn("\x1b[32m", visible)   # current stage greened (the one accent)
        stripped = strip_ansi(visible)
        self.assertIn("connected", stripped)              # ◆ connected — <org> · … header
        self.assertIn("acme-dev", stripped)               # which org connected
        self.assertNotIn("sfdx project:", stripped)       # heavy bands trimmed away
        self.assertNotIn("Apex 0", stripped)              # inventory band trimmed away
        self.assertIn("●", stripped)                      # the journey rail glyph row
        self.assertEqual(stripped.count(POINTER), 1)
        self.assertTrue(all(len(l) <= 80 for l in stripped.splitlines()), stripped)
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
        # rail and bands must clip, never soft-wrap out of their ≤80 contract.
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
        self.assertEqual([l for l in stripped.splitlines() if len(l) > 80], [])

    def test_connect_records_the_flag_so_a_same_turn_journey_paint_dedupes(self):
        # When the connect PAINTS the rail (here a fresh session — no prior rail seen,
        # so the step-signature gate treats it as moved), it records the per-turn dedup
        # flag: a same-turn `discovery journey` then de-dupes (at most one rail per turn
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
            self.assertTrue(sfx._rail_painted_this_turn(context))
            # A follow-on journey-paint in the same turn now de-dupes (no second rail).
            jp = io.StringIO(json.dumps({
                "tool_input": {"command": "sf-context discovery journey"},
                "session_id": "s1", "prompt_id": "p1"}))
            jout = io.StringIO()
            with mock.patch.object(sfx, "_journey_state", return_value=OrientationPaintTests.STATE), \
                    mock.patch.object(sfx, "_render_journey_rail") as rj, \
                    mock.patch.object(sfx.sys, "stdin", jp), redirect_stdout(jout):
                sfx.cmd_journey_paint()
            self.assertEqual(json.loads(jout.getvalue()), {"continue": True})
            rj.assert_not_called()
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir

    def test_rail_signature_is_steps_only_ignoring_the_org_context(self):
        # The signature is the SIX steps and nothing else — so a connect that only
        # re-resolves the org (same steps, different header) de-dupes, while a genuine
        # step move does not. Org context in the state must not perturb it.
        steps = [{"name": "Connect", "status": "complete"},
                 {"name": "Build", "status": "current"}]
        a = {"stages": steps, "context": {"orgAlias": "acme-dev", "orgStatus": "reachable"}}
        b = {"stages": [dict(s) for s in steps],
             "context": {"orgAlias": "other-org", "orgStatus": "unreachable"}}
        self.assertEqual(sfx._rail_signature(a), sfx._rail_signature(b))
        moved = {"stages": [{"name": "Connect", "status": "complete"},
                            {"name": "Build", "status": "complete"}]}
        self.assertNotEqual(sfx._rail_signature(a), sfx._rail_signature(moved))

    def test_connect_with_unchanged_steps_shows_header_but_not_a_second_rail(self):
        # The reported bug, wayfinder side: the last rail the user saw had these exact
        # steps, so a connect that re-resolves the same org moves nothing — show the
        # connected-org header (real news), but NOT a duplicate rail.
        self.make_project()
        p1, p2 = self.stat_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            seen = sfx._derive_journey_state(self.cwd.resolve(), has_project=True,
                                             target="acme-dev", target_error=None,
                                             org_display=self.org)
            sfx._record_rail_signature("sess-x", seen)
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
            painted_flag = sfx._rail_painted_this_turn("sess-x")
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("connected", stripped)          # header still shows — the connect is real news
        self.assertIn("acme-dev", stripped)
        self.assertNotIn("●", stripped)                # but no second rail glyph row
        self.assertNotIn("likely next", stripped)      # nor the rail's next-step line
        self.assertEqual(stripped.count(POINTER), 1)    # the pointer still closes it
        # A suppressed rail must not consume the turn's single-rail budget, so a later
        # solicited "where am I" this turn could still paint.
        self.assertFalse(painted_flag)

    def test_connect_that_lights_a_step_reprints_the_rail(self):
        # The reprint-on-change half: when the connect genuinely moves a step (here the
        # last rail the user saw had Connect NOT yet lit), the rail reprints and the
        # signature advances.
        self.make_project()
        p1, p2 = self.stat_patches()
        orig_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = self.cwd
        try:
            stale = {"stages": [{"name": n, "status": "future"} for n in (
                "Connect", "Project", "Build", "Test", "Deploy", "Observe")]}
            sfx._record_rail_signature("sess-y", stale)
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
            recorded = sfx._last_rail_signature("sess-y")
            context = sfx._prompt_context(
                {"session_id": "sess-y", "prompt_id": "p1"}, rotate_fallback=False)
            painted_flag = sfx._rail_painted_this_turn(context)
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("●", stripped)                              # the rail reprinted
        self.assertIn("connected", stripped)
        self.assertNotEqual(recorded, sfx._rail_signature(stale))  # signature advanced off the stale one
        self.assertTrue(painted_flag)                              # counted as a paint (dedupes a follow-on)

    def test_orientation_then_same_state_connect_paints_the_rail_once(self):
        # End-to-end regression for the reported bug: `/cd` into a project, ask
        # "what's next" (rail on UserPromptSubmit), then the model sets the SAME target
        # org (wayfinder on PostToolUse). Feature B painted the rail BOTH times; the
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
            rail1 = strip_ansi(json.loads(ups_out.getvalue())["systemMessage"])

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
            rail2 = strip_ansi(json.loads(wf_out.getvalue())["systemMessage"])
        finally:
            sfx._WELCOME_MARKER_DIR = orig_dir
        self.assertIn("●", rail1)          # rail #1 painted (the solicited orientation)
        self.assertIn("connected", rail2)  # the connect still confirms the org
        self.assertNotIn("●", rail2)       # but there is no second rail


class OrientationPaintTests(unittest.TestCase):
    """The UserPromptSubmit paint hook: on an orientation question the journey rail
    rides the color-carrying systemMessage channel (the one pipe that can, like the
    banner), and the model gets a plain note saying the rail is already shown so it
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
        # These tests exercise Side B's steady state — the in-project rail. Run from
        # inside a project, and mark the logo already shown this session (session
        # "s1", the id capture() uses) so the hook paints the rail, not the
        # once-per-scenario welcome. The first-time welcome has its own test.
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = Path.cwd()
        os.chdir(self.tmp.name)
        Path("sfdx-project.json").write_text("{}")
        # Session markers live in the temp dir (not cwd), so isolate + clean them.
        # Steady state: logo already shown AND the project already "entered", so
        # orientation questions paint the rail and other prompts stay silent. The
        # first-message (entered) nudge has its own test.
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        self._orig_runtime_dir = sfx._PROMPT_RUNTIME_DIR
        sfx._WELCOME_MARKER_DIR = Path(self.tmp.name)
        sfx._PROMPT_RUNTIME_DIR = Path(self.tmp.name) / "runtime"
        sfx._record_welcomed("s1")
        sfx._record_entered("s1")

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        sfx._PROMPT_RUNTIME_DIR = self._orig_runtime_dir
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_first_in_project_orientation_shows_the_logo_once(self):
        sfx._session_marker("s1", "welcome").unlink(missing_ok=True)   # scenario's first orientation
        # The first-surface welcome now paints the full banner chrome, resolving the
        # org via _resolve_position_and_org for its org band — so mock that alongside
        # _journey_state (the bare-rail second turn still reads _journey_state).
        org = {"alias": "acme-dev", "edition": "Developer Edition (Sandbox)",
               "apiVersion": "67.0", "instanceUrl": "https://x.my.salesforce.com",
               "username": "u@example.com"}
        with mock.patch.object(sfx, "_journey_state", return_value=self.STATE), \
                mock.patch.object(sfx, "_resolve_position_and_org", return_value=(self.STATE, org)):
            _, first = self.capture("where am i?")
            _, second = self.capture("where am i?")
        # The lockup is colored on the systemMessage channel, so match the stripped form.
        self.assertIn(sfx.BANNER, strip_ansi(first["systemMessage"]))       # logo carried once
        self.assertNotIn(sfx.BANNER, strip_ansi(second["systemMessage"]))   # rail only thereafter
        self.assertIn("build", second["systemMessage"])         # still the rail

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

    def test_status_question_paints_org_and_project_bands_plus_rail(self):
        code, result = self.capture_status("what's the status of the project")
        self.assertEqual(code, 0)
        sysmsg = result["systemMessage"]
        stripped = strip_ansi(sysmsg)
        self.assertIn("org: acme-dev", stripped)             # the org band
        self.assertIn("sfdx project: acme-crm", stripped)    # the project band
        self.assertIn("build", stripped)                     # the rail labels
        self.assertIn("likely next", stripped)               # the rail's next step
        self.assertIn("\x1b[32m", sysmsg)        # current stage greened (systemMessage keeps it)
        self.assertTrue(all(len(l) <= 80 for l in stripped.splitlines()))
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                       # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)status")
        self.assertNotIn("●", note)                          # never hands the glyph rail to the model

    def test_status_question_with_no_reachable_org_degrades_but_still_paints(self):
        code, result = self.capture_status("status", org=None)
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("sfdx project: acme-crm", stripped)    # project band still shows
        self.assertIn("build", stripped)                     # rail still shows
        self.assertNotIn("org: acme-dev", stripped)          # no fabricated connected org
        self.assertTrue(all(len(l) <= 80 for l in stripped.splitlines()))

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

    def test_positional_question_paints_rail_only_not_the_bands(self):
        # "what's next" is positional — the rail (with its one-line context row),
        # never the rule-framed org/project bands. The rail's context row does state
        # the project/org, so the band-only markers are the discriminator: the MCP
        # line and the Apex-inventory counts appear only when the status bands paint.
        _, result = self.capture("what's next")
        stripped = strip_ansi(result["systemMessage"])
        self.assertIn("build", stripped)                     # the rail
        self.assertNotIn("MCP:", stripped)                   # NOT the org band
        self.assertNotIn("Apex ", stripped)                  # NOT the project inventory band

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

    def test_first_in_project_message_paints_the_rail_once_as_ambient(self):
        # First non-orientation, non-connect message after entering the project →
        # the position rail paints once, as AMBIENT orientation (the note tells the
        # model to proceed with the request, not to orient). Silent on the next.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        _, first = self.capture("create a custom object")
        _, second = self.capture("add a field to it")
        self.assertIn("build", first["systemMessage"])             # the rail is shown
        note = first["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)ambient")
        self.assertRegex(note, r"(?i)proceed with")
        self.assertEqual(second, {"continue": True})               # once only

    def test_connect_intent_with_sf_absent_routes_to_setup_and_never_logs_in(self):
        # D9: on connect intent the plugin does the cheap `sf`-on-PATH check FIRST.
        # capture() clears the env, so `sf` is not resolvable → the note routes to
        # environment setup and explicitly does NOT attempt an interactive login (the
        # plugin never runs `sf org login`). It marks entered (so the ambient rail
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
        # it. The ambient rail steps aside (entered is marked) and is NOT drawn here.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        block = "Salesforce Headless 360 · what you can do here\n(fixed test block)"
        with mock.patch.object(sfx, "_render_overview_paint", return_value=block) as rp:
            _, result = self.capture("what can I do here?")
        rp.assert_called_once()
        self.assertEqual(result["systemMessage"], "\n" + block)   # painted directly, verbatim
        self.assertNotIn("build", result["systemMessage"])        # the overview, NOT the rail
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                            # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)add only your")
        self.assertRegex(note, r"(?i)overview")
        self.assertTrue(sfx._entered_this_session("s1"))

    def test_failed_overview_render_leaves_entered_absent_and_ambient_retries(self):
        # A failed overview paint did not show the suppressing surface. Keep `entered`
        # absent so the next ordinary prompt can still deliver the ambient rail.
        sfx._session_marker("s1", "entered").unlink(missing_ok=True)
        with mock.patch.object(sfx, "_render_overview_paint", return_value=None):
            _, failed = self.capture("what are my options")
        self.assertEqual(failed, {"continue": True})
        self.assertFalse(sfx._entered_this_session("s1"))

        _, retry = self.capture("add a field to Account")
        self.assertIn("build", retry["systemMessage"])
        self.assertTrue(sfx._entered_this_session("s1"))

    def test_status_render_failure_leaves_shown_state_absent(self):
        for kind in ("welcome", "entered", "railsig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(
            sfx, "render_status_surface", side_effect=RuntimeError("render failed")
        ):
            _, result = self.capture_status("status")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_rail_signature("s1"))
        self.assertFalse(sfx._rail_painted_this_turn("s1"))

    def _clear_shown_state(self):
        for kind in ("welcome", "entered", "railsig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)

    def _assert_no_shown_state(self):
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_rail_signature("s1"))

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
        self.assertIsNotNone(sfx._last_rail_signature("s1"))

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
        self.assertIsNone(sfx._last_rail_signature("s1"))

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
        self.assertIsNone(sfx._last_rail_signature("s1"))

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
        self.assertIsNone(sfx._last_rail_signature("s1"))

    def test_orientation_state_failure_leaves_shown_state_absent(self):
        for kind in ("welcome", "entered", "railsig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(
            sfx, "_resolve_position_and_org", side_effect=RuntimeError("state failed")
        ):
            _, result = self.capture("where am I?")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_rail_signature("s1"))
        self.assertFalse(sfx._rail_painted_this_turn("s1"))

    def test_orientation_emit_failure_keeps_claim_but_commits_no_shown_state(self):
        # The at-most-once claim intentionally stays before emit. An emit failure may
        # consume that prompt's rail, but it must not commit session shown-state.
        for kind in ("welcome", "entered", "railsig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(sfx, "emit", side_effect=RuntimeError("emit failed")):
            _, result = self.capture("where am I?")
        self.assertEqual(result, {"continue": True})
        self.assertTrue(sfx._rail_painted_this_turn("s1"))
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_rail_signature("s1"))

    def test_prompt_claim_loss_commits_no_shown_state_or_signature(self):
        for kind in ("welcome", "entered", "railsig"):
            sfx._session_marker("s1", kind).unlink(missing_ok=True)
        with mock.patch.object(sfx, "_claim_prompt_rail", return_value=False):
            _, result = self.capture("where am I?")
        self.assertEqual(result, {"continue": True})
        self.assertFalse(sfx._welcomed_this_session("s1"))
        self.assertFalse(sfx._entered_this_session("s1"))
        self.assertIsNone(sfx._last_rail_signature("s1"))

    def test_successful_orientation_orders_claim_emit_then_shown_state(self):
        for kind in ("welcome", "entered", "railsig"):
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
                    sfx, "_claim_prompt_rail",
                    side_effect=lambda _context: events.append("claim") or True), \
                mock.patch.object(sfx, "emit", side_effect=successful_emit), \
                mock.patch.object(
                    sfx, "_record_entered", side_effect=lambda _sid: events.append("entered")), \
                mock.patch.object(
                    sfx, "_record_welcomed", side_effect=lambda _sid: events.append("welcomed")), \
                mock.patch.object(
                    sfx, "_record_rail_signature",
                    side_effect=lambda _sid, _state: events.append("signature")):
            self.capture("where am I?")
        self.assertEqual(events, [
            "gather", "render", "claim", "emit", "entered", "welcomed", "signature",
        ])

    def test_render_overview_paint_renders_a_bounded_colored_block_from_the_real_catalog(self):
        # Integration: the paint helper loads the checked-in catalog and returns the
        # visible-channel block — colored with the overview palette (this is the paint
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
        self.assertEqual([l for l in plain.splitlines() if len(l) > 80], [])

    def test_render_overview_paint_returns_none_on_any_render_failure(self):
        # Fail open: any catalog-render error resolves to None so the hook stays a
        # silent continue — never a stack trace on the user's prompt. Inject the
        # renderer through sys.modules so the test covers both normal and fallback
        # import environments without depending on sys.path.
        failing_catalog = types.ModuleType("discovery_catalog")
        failing_catalog.render_overview_text = mock.Mock(side_effect=Exception("boom"))
        with mock.patch.dict("sys.modules", {"discovery_catalog": failing_catalog}):
            self.assertIsNone(sfx._render_overview_paint(Path(self.tmp.name)))

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
                    "/discovery journey", "discovery where",
                    # Fuzzy-tail orientation phrasings (Lever A): still first-person and
                    # about the user's OWN position/progress, so they earn the rail.
                    "catch me up", "remind me where I left off",
                    "remind me what I was doing", "how far along am I",
                    "am I making progress", "am I making any progress",
                    "what have I done so far", "what have we accomplished",
                    "what have we gotten done so far", "what should I be working on",
                    "how's my project going", "how is my project coming along"):
            self.assertTrue(sfx._is_orientation_question(hit), hit)
        # Bare Salesforce product nouns must NOT paint the rail: "journey" is
        # Marketing Cloud Journey Builder, "stage" is Opportunity Stage. Anchoring
        # to first-person orientation phrasing keeps these ordinary tasks quiet.
        for miss in ("where is the Account class?", "which directory holds the flows",
                     "add the apex skill", "deploy to prod", "", "x" * 3000,
                     # capability-catalog question -> discovery overview, NOT the rail
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

    def test_orientation_prompt_paints_colored_rail_on_systemmessage(self):
        code, result = self.capture("where am i?")
        self.assertEqual(code, 0)
        sysmsg = result["systemMessage"]
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("\x1b[32m", sysmsg)   # current stage greened (the one accent)
        # leading blank separates the rail from Claude Code's hook-message wrapper.
        # The paint path colors via the gate, so recompute with it to match exactly.
        self.assertEqual(sysmsg, "\n" + sfx._render_journey_rail(self.STATE, color=sfx._banner_color_enabled()))
        stripped = strip_ansi(sysmsg)
        self.assertIn("sfdx project: acme-crm", stripped)
        self.assertIn("org: acme-dev ✓", stripped)
        self.assertTrue(all(len(l) <= 80 for l in stripped.splitlines()))
        # Model note is ANSI-free, names the stage, and forbids reproduction — it
        # must NOT hand the model the rail ASCII to parrot.
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

    def test_rail_painting_branches_record_the_per_turn_dedup_flag(self):
        # Every rail branch atomically claims its fallback prompt namespace. Each
        # direct UserPromptSubmit call rotates that old-host token; silent turns do not claim.
        self.capture("where am i?")                                 # in-project orientation rail
        self.assertTrue(sfx._rail_painted_this_turn("s1"), "orientation rail branch")
        self.capture_status("what's the status of the project")     # status bands + rail
        self.assertTrue(sfx._rail_painted_this_turn("s1"), "status branch")
        self.capture("add a field to the Account object")           # entered => silent, no rail
        self.assertFalse(sfx._rail_painted_this_turn("s1"), "silent turn must not set the flag")

    def test_orientation_paint_records_the_step_signature_for_the_wayfinder(self):
        # The reprint-on-change gate's other half: an orientation paint records WHAT it
        # showed, so a same-turn connect (the wayfinder) can tell the rail did not move
        # and skip a duplicate. Companion to the per-turn flag test above.
        sfx._session_marker("s1", "railsig").unlink(missing_ok=True)
        self.capture("where am i?")
        self.assertEqual(sfx._last_rail_signature("s1"), sfx._rail_signature(self.STATE))

    def test_lever_c_dedupes_on_a_regex_hit_and_paints_on_a_regex_miss(self):
        # UserPromptSubmit and PostToolUse compose through the same fallback prompt
        # namespace on an old-host payload with no native prompt_id.

        def run_journey_paint():
            payload = io.StringIO(json.dumps(
                {"tool_input": {"command": "sf-context discovery journey"}, "session_id": "s1"}))
            out = io.StringIO()
            with mock.patch.object(sfx, "_journey_state", return_value=self.STATE), \
                    mock.patch.object(sfx.sys, "stdin", payload), \
                    mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
                sfx.cmd_journey_paint()
            return json.loads(out.getvalue())

        # (a) regex HIT: the UserPromptSubmit paint sets the flag; journey-paint dedupes.
        self.capture("where am i?")
        self.assertTrue(sfx._rail_painted_this_turn("s1"))
        self.assertEqual(run_journey_paint(), {"continue": True})   # deduped — no second rail

        # (b) regex MISS (the Lever-C win): a phrase _is_orientation_question rejects leaves
        # the flag unset (the UserPromptSubmit hook stays silent), so journey-paint paints.
        self.assertFalse(sfx._is_orientation_question("what's the state of things"))
        _, ups = self.capture("what's the state of things")
        self.assertEqual(ups, {"continue": True})
        self.assertFalse(sfx._rail_painted_this_turn("s1"))
        self.assertIn("systemMessage", run_journey_paint())

    def test_explicit_discovery_command_forms_all_paint(self):
        for prompt in ("/discovery journey", "/salesforce-development:discovery where",
                       "discovery journey"):
            with self.subTest(prompt=prompt):
                _, result = self.capture(prompt)
                self.assertIn("systemMessage", result)

    def test_journey_product_term_does_not_paint_end_to_end(self):
        # Regression for the confirmed over-fire: a Journey Builder / customer-journey
        # task prompt must be a silent continue, not an unasked-for painted rail.
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
        self.assertEqual([l for l in stripped.splitlines() if len(l) > 80], [])

    def test_orientation_paint_note_is_compact_facts_not_a_rendering_handbook(self):
        _, result = self.capture("where am i?")
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not reproduce")
        for fact in ("current stage: Build", "reached:", "no evidence:",
                     "recent events:", "next action:"):
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
        for fact in ("current stage: Build", "reached:", "no evidence:",
                     "recent events:", "next action:"):
            self.assertIn(fact, note)
        for decorative in ("█", "●", "◉", "○", "MICRO-TIER RENDERING CONTRACT"):
            self.assertNotIn(decorative, note)
        self.assertLessEqual(len(note), 1500)
        self.assertTrue(all(len(line) <= 120 for line in note.splitlines()), note)

    def test_attempted_deploy_surfaces_honestly_in_the_micro_facts_end_to_end(self):
        # A recorded FAILED deploy in this project makes a cursor-Deploy micro block
        # read `attempted` with the failure event on record — the honest "not
        # deployed" signal — while the block invents no error text or count (none is
        # persisted). The macro rail on systemMessage is unaffected.
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
        self.assertIn("current stage: Deploy", note)
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
        self.assertEqual(facts["likely_next"], sfx.NEXT_ACTION["Deploy"].strip())

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
        self.assertIn("current stage: Deploy", note)
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
    """Side A of the paint hook: OUTSIDE a Salesforce project, a prompt that mentions
    Salesforce surfaces the unstyled getting-started welcome, once per session. The
    plugin is global, so orientation phrasing alone must NOT paint in a random dir —
    only an explicit Salesforce mention does."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = Path.cwd()
        os.chdir(self.tmp.name)   # NO sfdx-project.json — this is the outside case
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        sfx._WELCOME_MARKER_DIR = Path(self.tmp.name)  # isolate the session marker

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def capture(self, prompt, session_id="s1"):
        payload = io.StringIO(json.dumps({"prompt": prompt, "session_id": session_id}))
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), \
                mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            code = sfx.cmd_orientation_paint()
        return code, json.loads(out.getvalue())

    def test_salesforce_mention_paints_the_readiness_agnostic_welcome(self):
        # D6 + presentation parity (owner direction 2026-08-05): a Salesforce mention
        # outside a project surfaces the welcome SURFACE, which now paints the SAME chrome
        # as the SessionStart banner — the colored HEADLESS lockup, the install summary,
        # the org + project bands, the position rail, and the shared wayfinding footer —
        # plus connect + create offered as PEERS and a single awareness heads-up, with NO
        # environment check behind it. Pin _configured_target_alias to None (a true
        # newcomer with no target org) so the rail state is deterministic (capture()
        # clears the env, so the target-org read would otherwise hit the real ~/.sf and
        # float the cursor between Connect and Project; a cleared PATH also means the
        # welcome's org probe no-ops, so the org band shows the empty "none connected").
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None):
            _, result = self.capture("I want to build something on Salesforce")
        sysmsg = result["systemMessage"]
        visible = strip_ansi(sysmsg)
        # The banner chrome the welcome now shares (the four presentation-layer elements).
        self.assertIn(sfx.BANNER, visible)                      # the colored HEADLESS lockup
        self.assertIn("✓ Installed salesforce-development", visible)   # the install summary
        self.assertIn("skills installed", visible)
        self.assertIn("org: ", visible)                         # the org band (empty here)
        self.assertIn("sfdx project: (none detected)", visible)  # the one-line project band
        self.assertIn("You don't memorize commands here.", visible)   # the wayfinding footer
        self.assertIn("✳ New here?", visible)
        self.assertIn('"what can I do here?"', sysmsg)          # discovery peer CTA (leads)
        self.assertIn('"connect an org"', sysmsg)               # peer CTA
        self.assertIn("create a Salesforce project", sysmsg)    # peer CTA
        self.assertIn("environment set up", sysmsg)             # the single awareness heads-up
        self.assertIn("\x1b[32m", sysmsg)          # current stage greened (the one accent)
        self.assertNotIn("you are here", sysmsg)                # marker stays gone
        self.assertNotIn("set up my environment", sysmsg)       # the OLD readiness lead is gone
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not reproduce")
        # A pinned surface: every painted line holds inside 80 columns.
        self.assertEqual([l for l in visible.splitlines() if len(l) > 80], [])

    def test_getting_started_welcome_paints_the_all_circle_teaching_map(self):
        # D8: out of a project with no org, the welcome paints the rail as a TEACHING
        # MAP — the whole path with nothing earned yet (cursor ◉ at Connect, the other
        # five stages ○, no ● anywhere). Seeing it born empty and light up teaches the
        # shape better than having it appear mid-journey. This is the pre-project
        # orientation moment the all-○ rule (D8) exists for.
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None):
            _, result = self.capture("I want to build on Salesforce")
        visible = strip_ansi(result["systemMessage"])
        # The signpost row carries the journey glyphs; the org + project band rules are
        # long dash runs too now, so match the glyph row by its glyphs, not by dashes.
        glyph_row = next(l for l in visible.splitlines() if any(g in l for g in ("◉", "●", "○")))
        self.assertNotIn("●", glyph_row)                 # nothing reached yet — a map, not progress
        self.assertEqual(glyph_row.count("◉"), 1)        # exactly one cursor, at the start
        self.assertEqual(glyph_row.count("○"), 5)        # the whole path ahead is shown
        self.assertIn("connect", visible)                # first stage
        self.assertIn("observe", visible)                # …through the last

    def test_welcome_never_consults_readiness_or_runs_a_scan(self):
        # The hard D6 guarantee: painting the welcome must never invoke the ~9s
        # check-tools scan (I4) and — since readiness left the front stages — must not
        # even read the readiness signal. The model note steers the model away from
        # running a check or pushing project creation as a prerequisite.
        with mock.patch.object(sfx, "_configured_target_alias", return_value=None), \
                mock.patch.object(sfx, "cmd_check_tools") as scan, \
                mock.patch.object(sfx, "_welcome_readiness") as readiness:
            _, result = self.capture("help me build something on Salesforce")
        scan.assert_not_called()          # the ~9s scan never runs on the greeting (I4)
        readiness.assert_not_called()     # D6: the welcome no longer reads readiness at all
        sysmsg = result["systemMessage"]
        self.assertIn(sfx.BANNER, strip_ansi(sysmsg))           # colored lockup → match stripped
        self.assertIn("create a Salesforce project", sysmsg)    # still offers create, ungated
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)do not run an environment")
        self.assertNotIn("platform-environment-validate", note)  # no check nag anymore

    def test_returning_dev_welcome_reflects_the_org_and_pivots_to_project(self):
        # D6 refinement: a configured target org (a returning developer — Connect ●, the
        # cursor at Project) is legitimate. The welcome must SHOW they are connected and
        # pivot to setting up a project + discovery, NOT re-offer "connect an org" or name
        # the environment tax (they have the CLI — that is how an org got targeted).
        with mock.patch.object(sfx, "_configured_target_alias", return_value="acme-dev"):
            _, result = self.capture("lets build something on salesforce")
        visible = strip_ansi(result["systemMessage"])
        # capture() clears PATH, so the welcome's org probe no-ops and the org band shows
        # the subprocess-free `org: <alias>` line (the full block is covered by
        # test_returning_dev_welcome_shows_full_org_block_when_probed).
        self.assertIn("org: acme-dev", visible)                 # the org is shown…
        self.assertNotIn("org: unknown", visible)               # …not a bare "unknown"
        self.assertIn("already have a target org", visible)
        self.assertIn("create a Salesforce project", visible)   # pivot to project
        self.assertIn('"what can I do here?"', visible)         # …and discovery
        self.assertNotIn('"connect an org"', visible)           # no connect CTA for a returning dev
        self.assertNotIn("environment set up", visible)         # and no env heads-up
        # Match the glyph row by its glyphs (the band rules are long dash runs too now).
        glyph_row = next(l for l in visible.splitlines() if any(g in l for g in ("◉", "●", "○")))
        self.assertEqual(glyph_row.count("●"), 1)               # Connect earned
        self.assertEqual(glyph_row.count("◉"), 1)               # cursor at Project
        self.assertEqual(glyph_row.count("○"), 4)
        self.assertEqual([l for l in visible.splitlines() if len(l) > 80], [])  # still ≤80
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertRegex(note, r"(?i)already have a target org")  # steer to project, not connect
        self.assertNotIn("platform-environment-validate", note)  # no check nag

    def test_returning_dev_welcome_shows_full_org_block_when_probed(self):
        # Presentation parity (owner direction 2026-08-05): when a target org is
        # configured, the welcome resolves it (via _resolve_welcome_org) and paints the
        # SAME full org band as the SessionStart banner — edition · API · username ·
        # instance · MCP — not just the bare alias. The probe is gated (configured only),
        # once-per-session, and fails soft to the alias line; mock it here to exercise the
        # full-block path deterministically without an `sf` subprocess.
        org = {"alias": "acme-dev", "edition": "Developer Edition (Sandbox)",
               "apiVersion": "67.0", "username": "dev@acme.example.com",
               "instanceUrl": "https://acme.my.salesforce.com"}
        with mock.patch.object(sfx, "_configured_target_alias", return_value="acme-dev"), \
                mock.patch.object(sfx, "_resolve_welcome_org", return_value=org):
            _, result = self.capture("lets build something on salesforce")
        visible = strip_ansi(result["systemMessage"])
        self.assertIn("org: acme-dev ✓ · Developer Edition (Sandbox) · API 67.0", visible)
        self.assertIn("dev@acme.example.com", visible)          # the username · instance detail line
        self.assertIn("MCP:", visible)                          # the MCP line, like the banner
        self.assertIn("sfdx project: (none detected)", visible)  # still no project
        self.assertIn("You don't memorize commands here.", visible)  # …and the shared footer
        self.assertEqual([l for l in visible.splitlines() if len(l) > 80], [])  # ≤80 holds

    def test_welcome_paints_only_once_per_session(self):
        self.capture("I want to build on Salesforce", session_id="s1")
        _, again = self.capture("help me build a Salesforce app", session_id="s1")
        self.assertEqual(again, {"continue": True})

    def test_out_of_project_connect_intent_when_tripped_hands_off_the_flow(self):
        # Side A (D9/D10): once the session is tripped (welcomed), a connect-org intent
        # outside a project hands the model the cheap-check + ternary note — model-facing
        # only, no paint. This is the core newcomer path (they said "build on Salesforce"
        # first). capture() clears the env, so `sf` is absent → the setup route.
        sfx._record_welcomed("s1")
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
        sfx._record_welcomed("s1")
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
        self.assertTrue(sfx._create_flow_shown_this_session("s1"))
        self.assertEqual(second, {"continue": True})              # once only — no re-fire

    def test_create_flow_hot_path_checks_marker_before_lock(self):
        sfx._record_welcomed("s1")
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
            "g['_record_welcomed']('s1'); original=g['emit']; "
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
        sfx._record_welcomed("s1")
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
        sfx._record_welcomed("s1")
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
        sfx._record_welcomed("s1")
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

    def test_tripped_out_of_project_orientation_ask_paints_the_rail(self):
        # The other half of the Side A guard: once the plugin has been tripped this
        # session (welcomed), an orientation question DOES paint the Tier-1 position
        # rail — the same discipline as the overview ask. The rail rides the visible
        # channel with its greened cursor, and the model gets the do-not-reproduce
        # note so it never re-runs `discovery journey` or reprints the rail. Without
        # this branch the model serviced "where am I" itself and double-printed a
        # colorless rail (the reported bug).
        sfx._record_welcomed("s1")
        # The natural out-of-project orientation state after the redesign: an all-○
        # teaching map with the cursor at Connect (D8 — "here's the whole path; you're
        # at the start"), nothing earned yet.
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
        self.assertEqual(result["systemMessage"],
                         "\n" + sfx._render_journey_rail(state, color=sfx._banner_color_enabled()))
        self.assertIn("\x1b[32m", result["systemMessage"])          # greened cursor survives
        self.assertNotIn("create a Salesforce project", result["systemMessage"])  # NOT the welcome
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                              # model note is plain
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertRegex(note, r"(?i)do not run the journey command")

    def test_locator_question_mentioning_salesforce_stays_silent(self):
        _, result = self.capture("where is the salesforce config file?")
        self.assertEqual(result, {"continue": True})

    def test_tripped_out_of_project_overview_ask_paints_the_block(self):
        # Rule (c): outside a project a capability question ("what can I do here?")
        # paints the Tier-1 overview — but ONLY once the plugin has already been
        # tripped this session (the welcome/logo has shown, i.e. welcomed). Here it
        # has, so the block paints directly on the visible channel and the model gets
        # the do-not-reproduce note. It is disjoint from the getting-started intent, so
        # the welcome is NOT re-drawn (its "create a Salesforce project" CTA is absent).
        sfx._record_welcomed("s1")
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
        sfx._record_welcomed("s1")
        with mock.patch.object(sfx, "_render_overview_paint", return_value=None) as rp:
            _, result = self.capture("what are my options")
        rp.assert_called_once()
        self.assertEqual(result, {"continue": True})

    def test_untripped_salesforce_naming_overview_ask_still_gets_the_welcome(self):
        # Regression guard (the intents OVERLAP): an overview ask that ALSO names
        # Salesforce — "what can I do here with Salesforce?" — matches BOTH the
        # overview and the getting-started intent. Untripped, that naming IS the trip,
        # so the prompt must reach the WELCOME, not be swallowed silently by the
        # trip-gated overview branch, and the overview block must NOT be built. (The
        # overview paints only on a LATER ask, once this welcome marks the session
        # welcomed.)
        with mock.patch.object(sfx, "_render_overview_paint") as rp, \
                mock.patch.object(sfx, "_welcome_readiness", return_value="ready"):
            _, result = self.capture("what can I do here with Salesforce?")
        self.assertIn(sfx.BANNER, strip_ansi(result["systemMessage"]))  # the welcome, not silence
        self.assertIn("create a Salesforce project", result["systemMessage"])
        rp.assert_not_called()                                      # overview never built
        self.assertTrue(sfx._welcomed_this_session("s1"))           # the trip is recorded


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
        # The visible paint path now colors the ✳ New here? footer (a cyan link, like the
        # welcome/SessionStart invitation); the TABLE rows stay ANSI-free — status is dots
        # + READY/WARN words, not color (owner direction 2026-08-05).
        self.assertIn("\x1b[36m", block)                          # footer ✳ New here? is a cyan link
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
    """Lever C: after the MODEL runs `sf-context discovery journey` (because it
    recognized a fuzzy orientation question the UserPromptSubmit regex missed), a
    PostToolUse Bash hook paints the SAME colored rail on the visible channel and
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

    def run_hook(self, command, session_id="s1", prompt_id="p1"):
        payload = {"tool_input": {"command": command}}
        if session_id is not None:
            payload["session_id"] = session_id
        if prompt_id is not None:
            payload["prompt_id"] = prompt_id
        out = io.StringIO()
        with mock.patch.object(sfx, "_journey_state", return_value=self.STATE), \
                mock.patch.object(sfx.sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.dict(os.environ, {}, clear=True), \
                redirect_stdout(out):
            code = sfx.cmd_journey_paint()
        return code, json.loads(out.getvalue())

    def test_non_journey_command_stays_silent_including_the_json_form(self):
        # No `if:` in plugin.json (some builds fire every Bash hook on every command),
        # so the command regex is the gate — and the --json machine form (a read for
        # the model's own reasoning) must NOT paint a rail.
        for cmd in ("cd /tmp && ls", "sf project deploy start -o x",
                    "sf-context discovery where", "sf-context detect", "",
                    '"${CLAUDE_PLUGIN_ROOT}"/scripts/sf-context discovery journey --json'):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "_render_journey_rail") as rj:
                    code, result = self.run_hook(cmd)
                self.assertEqual((code, result), (0, {"continue": True}))
                rj.assert_not_called()

    def test_journey_command_paints_colored_rail_and_hands_a_plain_note(self):
        code, result = self.run_hook('"${CLAUDE_PLUGIN_ROOT}"/scripts/sf-context discovery journey')
        self.assertEqual(code, 0)
        sysmsg = result["systemMessage"]
        self.assertTrue(sysmsg.startswith("\n"))
        self.assertIn("\x1b[32m", sysmsg)                    # colored on the visible channel
        self.assertIn("build", sysmsg)                       # the rail is there (cursor stage)
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("\x1b", note)                       # model note is plain (no ANSI)
        self.assertRegex(note, r"(?i)do not reproduce")
        self.assertNotIn("●", note)                          # never hands the glyph rail to the model
        context = sfx._prompt_context(
            {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)
        self.assertTrue(sfx._rail_painted_this_turn(context))  # second call de-dupes

    def test_dedupes_when_a_rail_already_painted_this_turn(self):
        # The UserPromptSubmit orientation paint owns the atomic prompt claim, so a
        # later journey paint cannot emit a second visible rail.
        context = sfx._prompt_context(
            {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)
        sfx._record_rail_painted(context)
        with mock.patch.object(sfx, "_render_journey_rail") as rj:
            code, result = self.run_hook("sf-context discovery journey")
        self.assertEqual((code, result), (0, {"continue": True}))
        rj.assert_not_called()

    def test_missing_session_id_stays_silent_rather_than_risk_a_double(self):
        # Without a session id the paint cannot be de-duped against the UserPromptSubmit
        # paint, so it stays silent (the model reproduces the plain rail — today's
        # behavior) rather than risk painting the rail twice.
        with mock.patch.object(sfx, "_render_journey_rail") as rj:
            code, result = self.run_hook("sf-context discovery journey", session_id=None)
        self.assertEqual((code, result), (0, {"continue": True}))
        rj.assert_not_called()

    def test_crash_in_the_hook_degrades_to_a_silent_continue(self):
        # Fail open: a crashing PostToolUse hook must never disrupt the turn. (Patch the
        # renderer, not _journey_state — run_hook already mocks the latter.)
        with mock.patch.object(sfx, "_render_journey_rail", side_effect=Exception("boom")):
            code, result = self.run_hook("sf-context discovery journey")
        self.assertEqual((code, result), (0, {"continue": True}))

    def test_independent_skill_and_rail_markers_preserve_each_other(self):
        context = sfx._prompt_context(
            {"session_id": "s1", "prompt_id": "p1"}, rotate_fallback=False)

        def dispatch_skill(name):
            payload = io.StringIO(json.dumps({
                "session_id": "s1", "prompt_id": "p1", "tool_input": {"skill": name}
            }))
            with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(io.StringIO()):
                sfx.cmd_record_skill_dispatch()

        sfx._record_rail_painted(context)
        dispatch_skill("platform-apex-generate")
        self.assertTrue(sfx._rail_painted_this_turn(context))
        self.assertIn("platform-apex-generate", sfx._dispatched_skills(context))


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

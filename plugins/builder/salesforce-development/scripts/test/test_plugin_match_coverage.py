#!/usr/bin/env python3
"""Contract tests for per-plugin matching coverage (plugin_match_coverage.py).

This is the gate the Slack ask needs: it iterates the *catalog itself*, so a new
plugin cannot ship without matching coverage. Add a plugin whose own example
prompts don't route back to it and this test goes red — no opt-in, no wiring,
because the corpus is enumerated from ``catalog/plugins.json`` at test time.

Three things are proven here:

  1. Real catalog is clean -- every candidate plugin's own example prompts reach
     that plugin at ``high`` on the discovery path (the hard invariant), and the
     data-driven per-plugin subtests localize any regression to one plugin.
  2. The harness is NON-VACUOUS -- synthetic catalogs with a mispointed plugin,
     a prompt-less plugin, or an empty corpus are all reported as NOT clean.
     Without these, "all covered" could be trivially, silently true.
  3. Anti-drift -- the foundation plugin excluded from coverage is the same name
     the runtime (``_plugin_display_name`` in sf_context.py) excludes, and it is
     really present in the catalog (so the exclusion is doing work, not masking
     a typo).

Runs under ``npm run test:gates`` via the auto-glob of ``test_*.py`` -- no
wiring edit needed.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
MODULE_PATH = SCRIPTS / "plugin_match_coverage.py"
CATALOG_MODULE_PATH = SCRIPTS / "plugin_catalog.py"
CONTEXT_MODULE_PATH = SCRIPTS / "sf_context.py"
PLUGIN_ROOT = SCRIPTS.parent
ARTIFACT = PLUGIN_ROOT / "catalog" / "plugins.json"


def _real_catalog():
    """Fresh deep copy of the checked-in catalog per call.

    Synthetic corpora are built by *mutating a real-sized catalog* rather than
    hand-rolling a 1-2 plugin one. This matters: BM25 IDF depends on corpus
    size -- in a tiny corpus every term appears in "most" documents, its IDF
    collapses toward zero, and nothing can reach the HIGH band. Mutating the
    real ~15-plugin catalog keeps IDF (and therefore the HIGH threshold)
    realistic, so these tests exercise the same regime the runtime does.
    """
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _find(catalog, name):
    for p in catalog["plugins"]:
        if p["name"] == name:
            return p
    raise AssertionError(f"{name} not in catalog (fixture drifted)")


def _pc(report, name):
    for pc in report.plugins:
        if pc.name == name:
            return pc
    raise AssertionError(f"{name} not in coverage report")


class RealCatalogCoverageTests(unittest.TestCase):
    """The catalog on disk must satisfy the hard discovery invariant."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_match_coverage_under_test")
        cls.catalog = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        cls.report = cls.mod.compute_coverage(cls.catalog)

    def test_real_catalog_is_discovery_clean(self):
        # The whole-catalog gate: every candidate plugin's own example prompts
        # route to it at high on the discovery path. This is what `--check`
        # asserts, and what turns red when a new plugin lacks working matching.
        self.assertTrue(
            self.report.is_clean,
            msg="discovery coverage regressed:\n" + self.mod.format_report(self.report),
        )

    def test_every_candidate_plugin_is_covered_individually(self):
        # Data-driven: one subtest per catalog plugin, so a regression names the
        # exact plugin (and the exact prompt) rather than a single opaque failure.
        # Iterates the catalog itself -> a newly added plugin is covered here the
        # moment it lands, with no edit to this test.
        self.assertGreater(len(self.report.plugins), 0, "no candidate plugins measured")
        for pc in self.report.plugins:
            with self.subTest(plugin=pc.name):
                self.assertGreater(
                    len(pc.prompts), 0,
                    f"{pc.name}: declares no examplePrompts -> cannot demonstrate matching",
                )
                failures = [
                    f"{p.prompt!r}"
                    + (f" (other high: {', '.join(p.discovery_other_highs)})" if p.discovery_other_highs else "")
                    for p in pc.discovery_failures
                ]
                self.assertEqual(
                    failures, [],
                    f"{pc.name}: these own example prompts do not route to it at high on the "
                    f"discovery path: {failures}",
                )

    def test_coverage_matches_declared_example_prompts(self):
        # The measured prompt count per plugin equals what the catalog declares,
        # so coverage cannot be inflated or silently truncated.
        by_name = {p["name"]: p for p in self.catalog["plugins"]}
        for pc in self.report.plugins:
            declared = by_name[pc.name]["match"].get("examplePrompts", [])
            self.assertEqual(
                len(pc.prompts), len(declared),
                f"{pc.name}: measured {len(pc.prompts)} prompts, catalog declares {len(declared)}",
            )

    def test_json_snapshot_is_consistent_with_report(self):
        snap = self.mod.report_to_dict(self.report)
        self.assertEqual(snap["summary"]["candidatePlugins"], len(self.report.plugins))
        self.assertEqual(snap["summary"]["clean"], self.report.is_clean)
        self.assertEqual(
            snap["summary"]["totalExamplePrompts"], self.report.total_prompts
        )
        # The foundation axis and the combined --check verdict are surfaced in the
        # snapshot too, so a consumer reading the JSON can't disagree with the CLI
        # exit code (the reporting gap the review flagged).
        self.assertEqual(snap["summary"]["foundationPresent"], self.report.foundation_present)
        self.assertEqual(
            snap["summary"]["checkWouldPass"],
            self.report.is_clean and not self.report.foundation_missing_from_catalog,
        )
        # Every plugin marked covered must carry no discovery failures in the snapshot.
        for row in snap["plugins"]:
            if row["discoveryCovered"]:
                self.assertEqual(row["discoveryFailures"], [], row["name"])


class FoundationExclusionTests(unittest.TestCase):
    """The excluded plugin must be the real, running one -- not a typo."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_match_coverage_fx")
        cls.catalog = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_foundation_is_present_in_catalog(self):
        names = {p["name"] for p in self.catalog["plugins"]}
        self.assertIn(
            self.mod.FOUNDATION_PLUGIN, names,
            "the foundation plugin name is not in the catalog -- exclusion would be a no-op "
            "(likely a rename/typo)",
        )

    def test_foundation_is_excluded_from_coverage(self):
        report = self.mod.compute_coverage(self.catalog)
        covered_names = {pc.name for pc in report.plugins}
        self.assertNotIn(self.mod.FOUNDATION_PLUGIN, covered_names)

    def test_foundation_name_matches_runtime_display_name(self):
        # Anti-drift with the runtime: sf_context.py excludes the plugin that is
        # currently running via _plugin_display_name(), whose plugin.json "name"
        # is the same value we hard-exclude here. If someone renames the
        # foundation plugin, this catches the coverage module drifting from it.
        # The plugin's own manifest is the source of truth for its runtime name.
        plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        manifest_name = json.loads(plugin_json.read_text(encoding="utf-8")).get("name")
        self.assertEqual(
            manifest_name, self.mod.FOUNDATION_PLUGIN,
            "foundation plugin.json name drifted from FOUNDATION_PLUGIN",
        )

    def test_runtime_excludes_the_foundation_via_its_display_name(self):
        # Behavioral anti-drift (replaces a bare grep for "_plugin_display_name",
        # which stayed green even if the exclusion were refactored to a hardcoded
        # literal -- the exact regression it named). Drive the real runtime
        # matcher on one of the foundation's OWN example prompts and prove:
        #   (a) with the real display name, the foundation is excluded from the
        #       candidates (the runtime never recommends the running plugin), and
        #   (b) if _plugin_display_name drifts off the foundation name, the
        #       foundation LEAKS back into the candidates.
        # (b) is what makes (a) load-bearing: it proves the exclusion is keyed on
        # the display name, not incidentally absent for some other reason.
        ctx = load_module(CONTEXT_MODULE_PATH, "sf_context_under_test_drift")
        # Hermetic: fail-open enabled set (treat all as uninstalled) and a pinned
        # sensitivity, so neither the runner's settings.json nor any ~/.sf override
        # can perturb the corpus. Empty session_id keeps it side-effect-free (no
        # marker write, no telemetry).
        ctx._enabled_plugin_names = lambda: None
        ctx._plugin_match_sensitivity = lambda: "standard"
        prompt = "deploy my metadata"  # a foundation examplePrompt

        real = {r["name"] for r in ctx._plugin_catalog_match(prompt, "", "discovery-command")}
        self.assertNotIn(
            self.mod.FOUNDATION_PLUGIN, real,
            "runtime must exclude the running (foundation) plugin from its own recommendations",
        )

        ctx._plugin_display_name = lambda *a, **k: "renamed-foundation-that-no-longer-matches"
        drifted = {r["name"] for r in ctx._plugin_catalog_match(prompt, "", "discovery-command")}
        self.assertIn(
            self.mod.FOUNDATION_PLUGIN, drifted,
            "exclusion is not keyed on _plugin_display_name -- drifting it did not leak the "
            "foundation back in, so this guard would not catch a real rename",
        )


class NonVacuousHarnessTests(unittest.TestCase):
    """Synthetic corpora that MUST be reported as not-clean.

    If any of these pass as clean, the real-catalog assertions above are
    meaningless -- so these are the load-bearing tests of the whole file.
    """

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_match_coverage_nv")

    def test_baseline_real_catalog_is_clean(self):
        # Positive control: the unmutated real catalog is clean. Every negative
        # test below starts from this same corpus and mutates ONE plugin, so any
        # resulting failure is attributable to that mutation, not to a degenerate
        # corpus. If this control ever fails, the negatives prove nothing.
        report = self.mod.compute_coverage(_real_catalog())
        self.assertTrue(report.is_clean, msg=self.mod.format_report(report))

    def test_too_generic_prompt_is_flagged(self):
        # Replace a real plugin's example prompts with one built entirely from
        # generic / stoplisted words ("build", "create", "app", "salesforce",
        # ...). The scorer drops those terms, so the query is empty and the
        # plugin's own prompt routes NOWHERE -> uncovered -> not clean. This is
        # the realistic contributor mistake: an example prompt too vague to
        # discriminate. (A prompt that names another domain can't be staged as a
        # negative here, because example prompts are folded into the plugin's own
        # searchable document -- so it would always self-match.)
        catalog = _real_catalog()
        _find(catalog, "commerce-b2b")["match"]["examplePrompts"] = [
            "build create generate an app in salesforce"
        ]
        report = self.mod.compute_coverage(catalog)
        self.assertFalse(report.is_clean)
        self.assertIn(
            "commerce-b2b", {pc.name for pc in report.discovery_failing_plugins}
        )

    def test_promptless_plugin_is_flagged(self):
        # Strip a real plugin's example prompts entirely. A plugin that declares
        # NO prompts cannot demonstrate matching, so it must count as uncovered
        # -- this stops a contributor from "passing" by omitting examplePrompts.
        catalog = _real_catalog()
        _find(catalog, "integration")["match"]["examplePrompts"] = []
        report = self.mod.compute_coverage(catalog)
        self.assertFalse(report.is_clean)
        self.assertIn(
            "integration", {pc.name for pc in report.discovery_failing_plugins}
        )

    def test_empty_corpus_is_not_clean(self):
        # No candidate plugins at all is not a vacuous pass.
        report = self.mod.compute_coverage({"plugins": []})
        self.assertFalse(report.is_clean)
        self.assertEqual(len(report.plugins), 0)

    def test_foundation_only_corpus_is_not_clean(self):
        # A catalog containing nothing but the foundation has zero candidates,
        # which is not a vacuous "all covered" pass either.
        catalog = {"plugins": [_find(_real_catalog(), self.mod.FOUNDATION_PLUGIN)]}
        report = self.mod.compute_coverage(catalog)
        self.assertFalse(report.is_clean)
        self.assertEqual(len(report.plugins), 0)

    def test_foundation_is_never_a_candidate_even_if_broken(self):
        # Break the foundation's own matching (in the real corpus) and confirm it
        # is still not a candidate and does not fail the gate -- the runtime never
        # recommends the running plugin to itself.
        catalog = _real_catalog()
        _find(catalog, self.mod.FOUNDATION_PLUGIN)["match"]["examplePrompts"] = [
            "something totally unrelated to any foundation keyword"
        ]
        report = self.mod.compute_coverage(catalog)
        self.assertNotIn(
            self.mod.FOUNDATION_PLUGIN, {pc.name for pc in report.plugins}
        )
        self.assertTrue(report.is_clean, msg=self.mod.format_report(report))


class CheckExitCodeTests(unittest.TestCase):
    """``--check`` (the contributor-facing CLI gate) must fail closed on a
    discovery regression and on a missing foundation -- so it can never report
    green while ``npm run test:gates`` (the unittest) reports red on the same
    catalog state."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_match_coverage_check")

    def test_check_passes_on_the_real_catalog(self):
        # End-to-end through main: the checked-in catalog clears --check.
        self.assertEqual(self.mod.main(["--check"]), 0)

    def test_check_fails_closed_on_a_discovery_regression(self):
        # The other --check failure mode still holds: a plugin whose own prompt
        # no longer routes to it fails the gate.
        catalog = _real_catalog()
        _find(catalog, "commerce-b2b")["match"]["examplePrompts"] = [
            "build create generate an app in salesforce"
        ]
        broken_report = self.mod.compute_coverage(catalog)
        original = self.mod._load_report
        self.mod._load_report = lambda: broken_report
        try:
            self.assertEqual(self.mod.main(["--check"]), 1)
        finally:
            self.mod._load_report = original

    def test_foundation_present_flag_tracks_the_catalog(self):
        # Real catalog contains the foundation -> present True, missing False.
        real = self.mod.compute_coverage(_real_catalog())
        self.assertTrue(real.foundation_present)
        self.assertFalse(real.foundation_missing_from_catalog)
        # Drop the foundation entry -> the exclusion becomes a no-op. is_clean can
        # still be True (remaining candidates route), so this is a SEPARATE axis --
        # exactly why --check must gate on it too.
        catalog = _real_catalog()
        catalog["plugins"] = [
            p for p in catalog["plugins"] if p["name"] != self.mod.FOUNDATION_PLUGIN
        ]
        report = self.mod.compute_coverage(catalog)
        self.assertFalse(report.foundation_present)
        self.assertTrue(report.foundation_missing_from_catalog)

    def test_check_fails_closed_when_foundation_missing_from_catalog(self):
        # main([--check]) must exit 1 when the foundation is absent from the
        # catalog, mirroring test_foundation_is_present_in_catalog -- even though
        # the remaining candidates route cleanly (is_clean True).
        catalog = _real_catalog()
        catalog["plugins"] = [
            p for p in catalog["plugins"] if p["name"] != self.mod.FOUNDATION_PLUGIN
        ]
        report = self.mod.compute_coverage(catalog)
        self.assertTrue(report.is_clean)
        original = self.mod._load_report
        self.mod._load_report = lambda: report
        try:
            self.assertEqual(self.mod.main(["--check"]), 1)
        finally:
            self.mod._load_report = original


class ProactiveGapReportingTests(unittest.TestCase):
    """The soft (anchor-gated) signal is reported but must not fail the gate."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_match_coverage_pg")

    def test_anchorless_prompt_is_a_proactive_gap_not_a_failure(self):
        # Give a real plugin an example prompt that names NONE of its anchor
        # terms. On discovery (anchor-ungated) it still matches its keywords ->
        # covered/clean. On the proactive (anchor-gated) path it is dropped ->
        # reported as a gap. Proves gaps are advisory, and exercises the same
        # mechanism as the real experience-lwc gap without pinning that specific
        # plugin's (fixable) anchor list.
        catalog = _real_catalog()
        victim = _find(catalog, "platform-observability")
        # Names observability keywords (so discovery still routes to it) but not
        # its anchor terms (tracing/enableplatformtracing/...).
        victim["match"]["examplePrompts"] = [
            "set up distributed request spans and latency metrics for my logs"
        ]
        report = self.mod.compute_coverage(catalog)
        obs = _pc(report, "platform-observability")
        self.assertTrue(
            obs.discovery_covered,
            "anchorless prompt must still clear the hard discovery gate:\n"
            + self.mod.format_report(report),
        )
        self.assertTrue(
            obs.proactive_gaps,
            "expected the anchorless prompt to be reported as a proactive gap",
        )

    def test_proactive_gaps_never_fail_the_hard_gate(self):
        # Invariant (not a bug-pin): whatever proactive gaps the real catalog
        # has, the corpus is still discovery-clean. Anchor gating is a
        # proactive-only tradeoff and must never turn the build red on its own.
        report = self.mod.compute_coverage(_real_catalog())
        for pc in report.proactive_gap_plugins:
            self.assertTrue(
                pc.discovery_covered,
                f"{pc.name} has proactive gaps but also failed the hard discovery gate",
            )
        self.assertTrue(report.is_clean)


class MatchTextSkillDriftTests(unittest.TestCase):
    """The advisory drift check: does a plugin's curated match text still cover
    the skills it ships? Matching scores marketplace text only, so a skill edit
    can never change a score -- but the text can silently fall out of sync. This
    is advisory (never part of ``is_clean`` / ``--check``), but the real-repo
    case below is asserted as a regression gate: shipped skills must stay
    represented in match text."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_match_coverage_drift")

    def _local_plugin(self, root, skills):
        """Materialize a local plugin dir with the given {dir_name: description}
        skills and return (plugin_dict, repo_root)."""
        pdir = root / "plugins/builder/demo"
        for dir_name, description in skills.items():
            sk = pdir / "skills" / dir_name
            sk.mkdir(parents=True)
            (sk / "SKILL.md").write_text(
                f'---\nname: {dir_name}\ndescription: "{description}"\n---\nbody\n',
                encoding="utf-8",
            )
        plugin = {
            "name": "demo",
            "source": "./plugins/builder/demo",
            "match": {
                "description": "build widget layouts",
                "keywords": ["widget", "layout"],
                "examplePrompts": ["make me a widget"],
            },
        }
        return plugin, root

    def test_unrepresented_skill_is_flagged_and_represented_one_is_not(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, root = self._local_plugin(Path(td), {
                "demo-widget-generate": "generate a widget layout",
                "demo-quantum-teleport-orchestrate": "orchestrate quantum teleportation entanglement",
            })
            drift = self.mod._drift_for_plugin(plugin, root)
        self.assertTrue(drift.is_local)
        self.assertEqual(drift.skill_count, 2)
        # The widget skill's vocab is in the match text; the quantum one's is not.
        self.assertEqual(drift.unrepresented, ("demo-quantum-teleport-orchestrate",))

    def _plugin_with_skills(self, root, name, match, skills):
        """Materialize a local plugin whose match text is given verbatim (so a
        test controls exactly which tokens land in the match vocab) and return
        (plugin_dict, repo_root). Unlike ``_local_plugin`` this does NOT hard-code
        the match text -- the drift regression tests below turn on whether the
        plugin's *name* token is present in that text."""
        source = f"./plugins/builder/{name}"
        pdir = root / source.lstrip("./")
        for dir_name, description in skills.items():
            sk = pdir / "skills" / dir_name
            sk.mkdir(parents=True)
            (sk / "SKILL.md").write_text(
                f'---\nname: {dir_name}\ndescription: "{description}"\n---\nbody\n',
                encoding="utf-8",
            )
        return {"name": name, "source": source, "match": match}, root

    def test_skill_reachable_via_a_name_token_in_match_text_is_not_flagged(self):
        # Regression (false-positive fix): a plugin's name token is NOT reliably
        # absent from its match text -- here "lwc" IS in the match text. A skill
        # reachable through that shared token (the scorer would route a user to
        # the plugin on it) must count as represented. The old code subtracted
        # name tokens before the intersection, so it dropped "lwc" and wrongly
        # flagged this skill; the fix keeps it.
        with tempfile.TemporaryDirectory() as td:
            plugin, root = self._plugin_with_skills(
                Path(td),
                "experience-lwc",
                {
                    "description": "build lightning web components and lwc bundles",
                    "keywords": ["lwc", "component"],
                    "examplePrompts": ["make an lwc"],
                },
                {"lwc-teleport": "teleport"},
            )
            drift = self.mod._drift_for_plugin(plugin, root)
        self.assertEqual(
            drift.unrepresented, (),
            "a skill reachable via a name token that IS in the match text must not be flagged",
        )

    def test_skill_whose_only_token_is_a_name_token_absent_from_match_text_is_flagged(self):
        # Regression (false-negative fix, the dangerous one): mirrors the real
        # dx-org-lifecycle shape, whose match text carries neither "dx" nor "org".
        # A shipped skill whose only distinctive token is "org" is genuinely
        # unreachable by the scorer, so it MUST be flagged. The old code subtracted
        # name tokens ({dx,org,lifecycle}), emptied the skill's vocab, and silently
        # reported it clean -- exactly the drift the check exists to catch.
        with tempfile.TemporaryDirectory() as td:
            plugin, root = self._plugin_with_skills(
                Path(td),
                "dx-org-lifecycle",
                {
                    "description": "manage scratch and sandbox lifecycles",
                    "keywords": ["scratch", "sandbox"],
                    "examplePrompts": ["create a scratch environment"],
                },
                {"org": "org"},
            )
            # Guard the premise: "org" really is absent from the match vocab, so
            # the flag below is a true unreachability, not a fixture accident.
            self.assertNotIn("org", set(self.mod.catalog_mod._plugin_document_tokens(plugin)))
            drift = self.mod._drift_for_plugin(plugin, root)
        self.assertEqual(drift.unrepresented, ("org",))

    def test_external_plugin_is_skipped_never_a_false_warning(self):
        ext = {
            "name": "ext",
            "source": {"source": "url", "url": "https://example/x.git"},
            "match": {"description": "d", "keywords": ["k"], "examplePrompts": ["p"]},
        }
        drift = self.mod._drift_for_plugin(ext, Path("/nonexistent"))
        self.assertFalse(drift.is_local)
        self.assertEqual(drift.unrepresented, ())
        self.assertIn("external", drift.note)

    def test_local_plugin_without_skills_dir_is_local_not_external(self):
        # A LOCAL plugin (string source) that ships no skills/ dir must be
        # classified local-with-no-skills, NOT mislabeled as an external skip.
        # This is the salesforce-test-drive shape in the real catalog.
        plugin = {
            "name": "toolkit",
            "source": "./plugins/builder/toolkit",  # exists on disk, but has no skills/
            "match": {"description": "d", "keywords": ["k"], "examplePrompts": ["p"]},
        }
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "plugins/builder/toolkit").mkdir(parents=True)
            drift = self.mod._drift_for_plugin(plugin, Path(td))
        self.assertTrue(drift.is_local)
        self.assertEqual(drift.skill_count, 0)
        self.assertEqual(drift.unrepresented, ())
        self.assertIn("no skills", drift.note)

    def test_real_repo_local_plugins_have_no_drift(self):
        # Regression gate (advisory feature, but this case is asserted): every
        # shipped local plugin's skills are currently represented in its curated
        # match text. If this fails, either a skill was added without advertising
        # it or match text was pruned too far. The foundation plugin is excluded
        # (compute_drift mirrors compute_coverage's corpus).
        catalog = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        repo_root = self.mod.catalog_mod._repo_root(PLUGIN_ROOT)
        drift = self.mod.compute_drift(catalog, repo_root)
        offenders = {row.name: list(row.unrepresented) for row in drift if row.unrepresented}
        self.assertEqual(offenders, {}, f"unrepresented skills: {offenders}")

    def test_foundation_is_excluded_from_drift(self):
        catalog = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        repo_root = self.mod.catalog_mod._repo_root(PLUGIN_ROOT)
        names = {row.name for row in self.mod.compute_drift(catalog, repo_root)}
        self.assertNotIn(self.mod.FOUNDATION_PLUGIN, names)

    def test_json_snapshot_carries_drift_block_when_supplied(self):
        catalog = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        repo_root = self.mod.catalog_mod._repo_root(PLUGIN_ROOT)
        report = self.mod.compute_coverage(catalog)
        drift = self.mod.compute_drift(catalog, repo_root)
        snap = self.mod.report_to_dict(report, drift)
        self.assertIn("drift", snap)
        self.assertEqual(len(snap["drift"]["plugins"]), len(drift))
        # Advisory: drift never leaks into the clean verdict.
        self.assertNotIn("drift", snap["summary"])
        # And when drift is omitted, no block is emitted at all.
        self.assertNotIn("drift", self.mod.report_to_dict(report))


if __name__ == "__main__":
    unittest.main(verbosity=2)

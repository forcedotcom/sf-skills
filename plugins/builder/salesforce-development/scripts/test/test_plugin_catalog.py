#!/usr/bin/env python3
"""Offline contract tests for the generated plugin-discovery catalog and its
prompt-matching scorer."""
from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
MODULE_PATH = SCRIPTS / "plugin_catalog.py"
REPO_ROOT = SCRIPTS.parents[3]
PLUGIN_ROOT = SCRIPTS.parent


class PluginCatalogGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_catalog_under_test")

    def test_checked_in_artifact_is_current_and_has_no_paths(self):
        artifact = PLUGIN_ROOT / "catalog/plugins.json"
        expected = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        actual = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertTrue(self.mod.check(REPO_ROOT, PLUGIN_ROOT))
        blob = artifact.read_text(encoding="utf-8")
        self.assertNotIn(str(REPO_ROOT), blob)
        self.assertNotIn(str(Path.home()), blob)

    def test_check_rejects_a_stale_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            stale = Path(td) / "plugins.json"
            stale.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "stale"):
                self.mod.check(REPO_ROOT, PLUGIN_ROOT, stale)

    def test_real_catalog_shape_is_single_source_and_flattened(self):
        data = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        self.assertEqual(data["schemaVersion"], "1.0")
        self.assertEqual(
            set(data["generatedFrom"]), {"marketplace", "marketplaceSha256"}
        )
        self.assertEqual(
            data["generatedFrom"]["marketplace"], ".claude-plugin/marketplace.json"
        )
        self.assertRegex(data["generatedFrom"]["marketplaceSha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn("counts", data)
        names = [row["name"] for row in data["plugins"]]
        self.assertEqual(names, sorted(names))
        required_match_keys = {"description", "keywords", "examplePrompts"}
        for row in data["plugins"]:
            self.assertEqual(set(row), {"name", "source", "match"})
            self.assertTrue(required_match_keys <= set(row["match"]) <= required_match_keys | {"anchorTerms"})
            # No pin/origin/marketplace/trust survive into the flattened row.
            self.assertNotIn("pin", row)
            self.assertNotIn("origin", row)
            self.assertNotIn("trust", row)

    def test_local_plugin_source_is_the_verbatim_relative_path_string(self):
        data = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        local_row = next(row for row in data["plugins"] if row["name"] == "salesforce-development")
        self.assertEqual(local_row["source"], "./plugins/builder/salesforce-development")

    def test_external_plugin_source_is_the_verbatim_source_object(self):
        data = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        external_row = next(row for row in data["plugins"] if row["name"] == "agentforce-adlc")
        self.assertIsInstance(external_row["source"], dict)
        self.assertEqual(external_row["source"].get("source"), "url")
        self.assertEqual(
            external_row["source"].get("url"),
            "https://github.com/SalesforceAIResearch/agentforce-adlc.git",
        )
        self.assertEqual(external_row["source"].get("ref"), "main")

    def test_match_text_is_verbatim_from_the_marketplace(self):
        marketplace = json.loads(
            (REPO_ROOT / self.mod.MARKETPLACE_RELATIVE).read_text(encoding="utf-8")
        )
        by_name = {row["name"]: row for row in marketplace["plugins"]}
        data = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        for row in data["plugins"]:
            source_entry = by_name[row["name"]]
            self.assertEqual(row["match"]["description"], source_entry["description"])
            self.assertEqual(row["match"]["keywords"], list(source_entry["keywords"]))
            self.assertEqual(
                row["match"]["examplePrompts"],
                list(source_entry["metadata"]["match"]["examplePrompts"]),
            )

    def test_runtime_load_strictly_rejects_malformed_artifacts(self):
        baseline = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        str_index = next(i for i, row in enumerate(baseline["plugins"]) if isinstance(row["source"], str))
        dict_index = next(i for i, row in enumerate(baseline["plugins"]) if isinstance(row["source"], dict))

        def mutate(label, change):
            data = copy.deepcopy(baseline)
            change(data)
            return label, data

        cases = [
            mutate("extra top key", lambda d: d.update(extra=True)),
            mutate("bad schema version", lambda d: d.update(schemaVersion="2.0")),
            mutate("missing generatedFrom key", lambda d: d["generatedFrom"].pop("marketplaceSha256")),
            mutate("wrong marketplace path", lambda d: d["generatedFrom"].update(marketplace="other.json")),
            mutate("bad marketplace sha", lambda d: d["generatedFrom"].update(marketplaceSha256="bad")),
            mutate("duplicate name", lambda d: d["plugins"].append(copy.deepcopy(d["plugins"][0]))),
            mutate("unsorted names", lambda d: d["plugins"].reverse()),
            mutate("extra plugin key", lambda d: d["plugins"][str_index].update(origin="local")),
            mutate("empty string source", lambda d: d["plugins"][str_index].update(source="")),
            mutate("non-string/non-object source", lambda d: d["plugins"][str_index].update(source=123)),
            mutate("empty object source", lambda d: d["plugins"][dict_index].update(source={})),
            mutate("bad match keys", lambda d: d["plugins"][str_index]["match"].pop("keywords")),
            mutate("empty keywords", lambda d: d["plugins"][str_index]["match"].update(keywords=[])),
            mutate("duplicate keywords", lambda d: d["plugins"][str_index]["match"].update(keywords=["a", "a"])),
            mutate("empty examplePrompts", lambda d: d["plugins"][str_index]["match"].update(examplePrompts=[])),
        ]
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td)
            artifact = plugin / self.mod.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            for label, data in cases:
                with self.subTest(label=label):
                    artifact.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(self.mod.PluginCatalogError):
                        self.mod.load_catalog(plugin)


class InternalPluginHoldsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_catalog_under_test_holds")

    def test_empty_inline_list(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yml"
            config.write_text("internalPlugins: []\n", encoding="utf-8")
            self.assertEqual(self.mod.read_internal_plugin_holds(config), set())

    def test_block_list(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yml"
            config.write_text("internalPlugins:\n  - some-plugin\n  - other-plugin\n", encoding="utf-8")
            self.assertEqual(
                self.mod.read_internal_plugin_holds(config), {"some-plugin", "other-plugin"}
            )

    def test_missing_key_raises(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yml"
            config.write_text("internal: []\n", encoding="utf-8")
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "missing internalPlugins"):
                self.mod.read_internal_plugin_holds(config)

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yml"
            config.write_text('internalPlugins: ["Not_Valid"]\n', encoding="utf-8")
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "invalid internalPlugins"):
                self.mod.read_internal_plugin_holds(config)

    def test_real_config_yml_has_empty_internal_plugins(self):
        self.assertEqual(self.mod.read_internal_plugin_holds(REPO_ROOT / "config.yml"), set())


class BuildCatalogTests(unittest.TestCase):
    """Synthetic, tiny marketplaces — the real salesforce-development marketplace
    is exercised by the checked-in artifact tests above, not here."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_catalog_under_test_build")

    def _write_repo(self, repo_root: Path, entries: list, held: list) -> None:
        (repo_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        (repo_root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "test-marketplace", "plugins": entries}), encoding="utf-8"
        )
        body = (
            "internalPlugins:\n" + "".join(f"  - {name}\n" for name in held)
            if held else "internalPlugins: []\n"
        )
        (repo_root / "config.yml").write_text(body, encoding="utf-8")

    def _entry(self, name, source, description, keywords, example_prompts):
        return {
            "name": name,
            "source": source,
            "description": description,
            "keywords": keywords,
            "metadata": {"match": {"examplePrompts": example_prompts}},
        }

    def test_opted_in_local_plugin_is_emitted_flattened(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_repo(repo_root, [
                self._entry(
                    "sample-plugin", "./plugins/sample-plugin",
                    "A sample plugin for testing purposes.", ["sample"], ["test the sample plugin"],
                ),
            ], held=[])
            data = self.mod.build_catalog(repo_root, repo_root)
            self.assertEqual(len(data["plugins"]), 1)
            row = data["plugins"][0]
            self.assertEqual(set(row), {"name", "source", "match"})
            self.assertEqual(row["name"], "sample-plugin")
            self.assertEqual(row["source"], "./plugins/sample-plugin")
            self.assertEqual(row["match"]["keywords"], ["sample"])
            self.assertEqual(row["match"]["examplePrompts"], ["test the sample plugin"])

    def test_external_source_object_round_trips_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            source = {"source": "github", "repo": "acme/widget", "ref": "v1.2.3"}
            self._write_repo(repo_root, [
                self._entry(
                    "widget", copy.deepcopy(source),
                    "A widget plugin.", ["widget"], ["make a widget"],
                ),
            ], held=[])
            data = self.mod.build_catalog(repo_root, repo_root)
            self.assertEqual(data["plugins"][0]["source"], source)

    def test_held_plugin_is_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_repo(repo_root, [
                self._entry(
                    "held-plugin", "./plugins/held-plugin",
                    "A held plugin.", ["held"], ["use the held plugin"],
                ),
            ], held=["held-plugin"])
            data = self.mod.build_catalog(repo_root, repo_root)
            self.assertEqual(data["plugins"], [])

    def test_entry_without_keywords_is_not_a_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            # No keywords => not opted in => silently skipped (never raises for
            # missing examplePrompts, since it is not a candidate at all).
            self._write_repo(repo_root, [
                {"name": "no-keywords", "source": "./plugins/no-keywords",
                 "description": "A plugin that never opts in."},
            ], held=[])
            data = self.mod.build_catalog(repo_root, repo_root)
            self.assertEqual(data["plugins"], [])

    def test_empty_keywords_array_is_not_a_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_repo(repo_root, [
                {"name": "empty-keywords", "source": "./plugins/empty-keywords",
                 "description": "A plugin with an empty keywords array.", "keywords": []},
            ], held=[])
            data = self.mod.build_catalog(repo_root, repo_root)
            self.assertEqual(data["plugins"], [])

    def test_keywords_without_example_prompts_raises(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_repo(repo_root, [
                {"name": "sample-plugin", "source": "./plugins/sample-plugin",
                 "description": "A plugin that opts in but forgot example prompts.",
                 "keywords": ["sample"]},
            ], held=[])
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "examplePrompts"):
                self.mod.build_catalog(repo_root, repo_root)

    def test_opted_in_plugin_missing_source_raises(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_repo(repo_root, [
                {"name": "sample-plugin", "description": "A plugin with no source.",
                 "keywords": ["sample"],
                 "metadata": {"match": {"examplePrompts": ["do the thing"]}}},
            ], held=[])
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "source"):
                self.mod.build_catalog(repo_root, repo_root)


class HeldPluginDescriptionsTests(unittest.TestCase):
    """`held_plugin_descriptions` -- the release leak-scanner's protected-set
    source (`verify-public-plugin-release.py`), covered independently of the
    scan loop it feeds."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_catalog_under_test_held_descriptions")

    def _write_config(self, repo_root: Path, held: list) -> None:
        body = (
            "internalPlugins:\n" + "".join(f"  - {name}\n" for name in held)
            if held else "internalPlugins: []\n"
        )
        (repo_root / "config.yml").write_text(body, encoding="utf-8")

    def _write_marketplace(self, repo_root: Path, entries: list) -> None:
        (repo_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        (repo_root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "test-marketplace", "plugins": entries}), encoding="utf-8"
        )

    def test_no_holds_returns_empty_without_reading_the_marketplace(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_config(repo_root, [])
            # Deliberately no marketplace.json written -- an empty holds list must
            # short-circuit before the marketplace is read.
            self.assertEqual(self.mod.held_plugin_descriptions(repo_root, repo_root), {})

    def test_held_plugin_description_is_returned_visible_one_is_not(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_config(repo_root, ["held-plugin"])
            self._write_marketplace(repo_root, [
                {"name": "held-plugin", "source": "./plugins/held-plugin",
                 "description": "A held plugin description."},
                {"name": "visible-plugin", "source": "./plugins/visible-plugin",
                 "description": "A visible plugin description."},
            ])
            result = self.mod.held_plugin_descriptions(repo_root, repo_root)
            self.assertEqual(result, {"held-plugin": "A held plugin description."})

    def test_held_external_plugin_description_is_returned(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_config(repo_root, ["held-external"])
            self._write_marketplace(repo_root, [
                {"name": "held-external",
                 "source": {"source": "github", "repo": "acme/held", "ref": "v1"},
                 "description": "A held external plugin description."},
            ])
            result = self.mod.held_plugin_descriptions(repo_root, repo_root)
            self.assertEqual(result, {"held-external": "A held external plugin description."})

    def test_malformed_marketplace_raises(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self._write_config(repo_root, ["held-plugin"])
            (repo_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
            (repo_root / ".claude-plugin" / "marketplace.json").write_text("not json", encoding="utf-8")
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "cannot load marketplace manifest"):
                self.mod.held_plugin_descriptions(repo_root, repo_root)

    def test_real_repo_currently_has_no_held_plugins(self):
        self.assertEqual(self.mod.held_plugin_descriptions(REPO_ROOT, PLUGIN_ROOT), {})


class ScorePromptAgainstCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(MODULE_PATH, "plugin_catalog_under_test_score")

    def _plugin(self, name, description, keywords, example_prompts, source="./x", anchor_terms=None):
        match = {"description": description, "keywords": keywords, "examplePrompts": example_prompts}
        if anchor_terms:
            match["anchorTerms"] = anchor_terms
        return {"name": name, "source": source, "match": match}

    def test_anchor_terms_require_at_least_one_to_be_present_in_the_prompt(self):
        gated = self._plugin(
            "devops-plugin",
            "Operate DevOps Center pipelines and configure their automated testing.",
            ["devops center", "test pipeline"],
            ["configure a DevOps Center test pipeline"],
            anchor_terms=["devops"],
        )
        unrelated = self._plugin(
            "agent-plugin",
            "Author, scaffold, and test Agentforce agent files for employee agents.",
            ["agentforce", "agent", "employee agent"],
            ["author and test an employee agent"],
        )
        catalog_data = {"plugins": [gated, unrelated]}

        # "test" alone, with no "devops" anchor present, must not surface the
        # anchor-gated plugin even though the bare term would otherwise clear
        # the score threshold.
        matches = self.mod.score_prompt_against_catalog(
            "author and test a new Agentforce .agent file for an employee agent", catalog_data
        )
        self.assertNotIn("devops-plugin", {match.plugin["name"] for match in matches})

        # The same plugin still matches once its own anchor term is present.
        matches = self.mod.score_prompt_against_catalog(
            "configure a DevOps Center test pipeline", catalog_data
        )
        self.assertIn("devops-plugin", {match.plugin["name"] for match in matches})

    def test_require_anchor_terms_false_restores_plain_high_and_medium_recall(self):
        # Surfaces that pass require_anchor_terms=False (explicit discovery, the
        # reactive bypass gate) must see a plugin the default-True gate excludes
        # for matching only on a generic word ("install") shared with the corpus,
        # not its own anchor term ("lifecycle") -- mirrors the real "install
        # agentforce-adlc plugin" false positive this gate was built to close.
        gated = self._plugin(
            "orglife-plugin",
            "Configure package post install scripts and post install hooks for "
            "org lifecycle automation.",
            ["post install", "org lifecycle"],
            ["configure a post install hook for org lifecycle automation"],
            anchor_terms=["lifecycle"],
        )
        unrelated = self._plugin(
            "agent-plugin",
            "Author, scaffold, and deploy Agentforce agent files for service agents.",
            ["agentforce", "agent", "service agent"],
            ["build me a service agent", "create an employee agent"],
        )
        catalog_data = {"plugins": [gated, unrelated]}
        prompt = "install this agentforce adlc plugin"

        gated_matches = self.mod.score_prompt_against_catalog(prompt, catalog_data)
        self.assertNotIn("orglife-plugin", {match.plugin["name"] for match in gated_matches})

        ungated_matches = self.mod.score_prompt_against_catalog(
            prompt, catalog_data, require_anchor_terms=False
        )
        self.assertIn("orglife-plugin", {match.plugin["name"] for match in ungated_matches})

    def test_high_confidence_threshold_override_moves_the_band_boundary(self):
        plugin = self._plugin(
            "flow-plugin",
            "Build and automate record-triggered Salesforce Flows for approvals.",
            ["flow", "automation", "record-triggered", "approvals"],
            ["build a flow", "automate an approval process"],
        )
        catalog_data = {"plugins": [plugin]}
        prompt = "build and automate a record-triggered flow for approvals"
        baseline = self.mod.score_prompt_against_catalog(prompt, catalog_data)
        self.assertEqual(len(baseline), 1)
        score = baseline[0].score

        # A threshold above the actual score demotes high -> medium; a threshold
        # at or below it keeps/promotes the match to high. The override must be
        # the only thing that changed the band -- same prompt, same catalog.
        demoted = self.mod.score_prompt_against_catalog(
            prompt, catalog_data, high_confidence_threshold=score + 1.0
        )
        self.assertEqual(demoted[0].band, "medium")
        promoted = self.mod.score_prompt_against_catalog(
            prompt, catalog_data, high_confidence_threshold=score
        )
        self.assertEqual(promoted[0].band, "high")

    def test_two_distinct_plugins_both_clear_the_bar_and_neither_is_suppressed(self):
        flow_plugin = self._plugin(
            "flow-plugin",
            "Build and automate record-triggered and scheduled Salesforce Flows.",
            ["flow", "automation", "record-triggered"],
            ["build a flow", "automate a record-triggered process"],
        )
        agent_plugin = self._plugin(
            "agent-plugin",
            "Author, scaffold, and deploy Agentforce agent files for service agents.",
            ["agentforce", "agent", "service agent"],
            ["build me a service agent", "create an employee agent"],
            source={"source": "github", "repo": "acme/agent", "ref": "v1"},
        )
        catalog_data = {"plugins": [flow_plugin, agent_plugin]}
        matches = self.mod.score_prompt_against_catalog(
            "I want to build a flow and also build me a service agent", catalog_data
        )
        names = {match.plugin["name"] for match in matches}
        self.assertEqual(names, {"flow-plugin", "agent-plugin"})

    def test_near_duplicate_plugins_collapse_to_the_higher_scoring_one(self):
        primary = self._plugin(
            "flow-plugin-primary",
            "Build and automate record-triggered Salesforce Flows for approvals.",
            ["flow", "automation", "record-triggered", "approvals"],
            ["build a flow", "automate an approval process"],
        )
        near_duplicate = self._plugin(
            "flow-plugin-duplicate",
            "Build and automate record-triggered Salesforce Flows for approvals.",
            ["flow", "automation", "record-triggered", "approvals"],
            ["build a flow", "automate an approval process"],
        )
        catalog_data = {"plugins": [primary, near_duplicate]}
        matches = self.mod.score_prompt_against_catalog(
            "build and automate a record-triggered flow for approvals", catalog_data
        )
        self.assertEqual(len(matches), 1)
        self.assertIn(matches[0].plugin["name"], {"flow-plugin-primary", "flow-plugin-duplicate"})

    def test_generic_non_salesforce_prompt_yields_an_empty_list(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)
        matches = self.mod.score_prompt_against_catalog(
            "what's the weather like today in san francisco", data
        )
        self.assertEqual(matches, [])

    def test_generic_follow_up_words_do_not_become_product_evidence(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)
        matches = self.mod.score_prompt_against_catalog("add a field to it", data)
        self.assertFalse(any(match.band == "high" for match in matches))
        self.assertTrue(all(
            match.matched_terms.isdisjoint({"add", "app", "to", "it"})
            for match in matches
        ))

    def test_real_tranche_prompts_have_one_high_confidence_product_route(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)
        # The real runtime (_plugin_catalog_match in sf_context.py) excludes the
        # foundation plugin itself from the scoreable corpus before matching -- it
        # is always already active, never a recommendation candidate. Mirror that
        # exclusion here so this test reflects the actual recommendation surface.
        data = {
            **data,
            "plugins": [p for p in data["plugins"] if p["name"] != "salesforce-development"],
        }
        cases = [
            (
                "configure post-copy steps for my Salesforce sandbox refresh",
                "dx-org-lifecycle",
            ),
            ("create a Salesforce trial org for this demo", "dx-org-lifecycle"),
            ("switch my default Salesforce org", "dx-org-lifecycle"),
            (
                "inspect Dev Hub status and show my scratch allocation",
                "dx-org-lifecycle",
            ),
            ("configure a DevOps Center test pipeline", "dx-devops"),
            (
                "run the test suite for this DevOps Center pipeline stage",
                "dx-devops",
            ),
            (
                "analyze why my DevOps Center pipeline tests failed",
                "dx-devops",
            ),
            (
                "search Salesforce Archive for archived Account records",
                "platform-trust-security",
            ),
            (
                "replace OOTB B2B Commerce definitions with mapped site equivalents",
                "commerce-b2b",
            ),
            (
                "use lightning/mobileCapabilities to add native barcode scanner support",
                "mobile-development",
            ),
            (
                "build a Salesforce iOS app with Mobile SDK",
                "mobile-development",
            ),
            (
                "add MobileSync and SmartStore offline storage to my mobile app",
                "mobile-development",
            ),
            (
                "turn on TraceSpanEvent publishing with enablePlatformTracing",
                "platform-observability",
            ),
            (
                "AppAnalyticsQueryRequest PackageUsageSummary SubscriberSnapshot",
                "dx-isv-partner",
            ),
        ]
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                high_names = [match.plugin["name"] for match in matches if match.band == "high"]
                self.assertEqual(high_names, [expected])

    def test_real_tranche_precision_and_reduced_boundaries(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)

        for prompt in ("switch my git branch", "start a free trial for my photo editor"):
            with self.subTest(prompt=prompt):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                self.assertFalse(any(
                    match.plugin["name"] == "dx-org-lifecycle" and match.band == "high"
                    for match in matches
                ))

        promotion_matches = self.mod.score_prompt_against_catalog(
            "promote my DevOps Center work item", data
        )
        devops = next(
            match for match in promotion_matches if match.plugin["name"] == "dx-devops"
        )
        # Matching is plugin-level: strong DevOps Center + work-item evidence can
        # still identify this reduced plugin, but its curated text must never
        # claim that the deferred promotion capability is bundled.
        devops_text = " ".join([
            devops.plugin["match"]["description"],
            *devops.plugin["match"]["keywords"],
            *devops.plugin["match"]["examplePrompts"],
        ]).lower()
        self.assertIsNone(re.search(r"\bpromot(?:e|es|ed|ing|ion)\b", devops_text))

    def test_remaining_product_precision_and_reduced_boundaries(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)

        negative_cases = [
            ("encrypt a local zip archive", "platform-trust-security"),
            ("replace a React hook", "commerce-b2b"),
            ("create a generic iOS app", "mobile-development"),
            ("build a generic iOS app using SwiftUI", "mobile-development"),
            ("add login to my existing iOS app using Firebase", "mobile-development"),
            ("trace a local Python program", "platform-observability"),
            ("query website analytics", "dx-isv-partner"),
        ]
        for prompt, plugin_name in negative_cases:
            with self.subTest(prompt=prompt, plugin=plugin_name):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                self.assertFalse(any(
                    match.plugin["name"] == plugin_name and match.band == "high"
                    for match in matches
                ))

        catalog_text = {}
        for plugin_name in (
            "platform-trust-security",
            "commerce-b2b",
            "mobile-development",
            "platform-observability",
            "dx-isv-partner",
        ):
            plugin = next(row for row in data["plugins"] if row["name"] == plugin_name)
            catalog_text[plugin_name] = " ".join([
                plugin["match"]["description"],
                *plugin["match"]["keywords"],
                *plugin["match"]["examplePrompts"],
            ]).lower()

        self.assertNotRegex(
            catalog_text["platform-trust-security"], r"\b(?:datamask|data mask|sandbox)\b"
        )
        self.assertNotRegex(catalog_text["commerce-b2b"], r"\bcreat(?:e|es|ed|ing|ion)\b")
        self.assertRegex(catalog_text["mobile-development"], r"\bmobile sdk\b")
        self.assertNotRegex(catalog_text["platform-observability"], r"\banaly(?:ze|zes|zed|zing|sis)\b")
        self.assertNotRegex(
            catalog_text["dx-isv-partner"],
            r"\b(?:dev hub|scratch org|listing|publish|publishing)\b",
        )

    def test_mobile_development_covers_app_creation_scope(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)

        positive_prompts = [
            "build a Salesforce iOS app with Mobile SDK",
            "add Mobile SDK to my existing Android app",
            "add MobileSync and SmartStore offline storage to my mobile app",
            "add biometric login to my Salesforce mobile app",
            "set up Salesforce authentication in my Mobile SDK app",
        ]
        for prompt in positive_prompts:
            with self.subTest(prompt=prompt):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                self.assertTrue(any(
                    match.plugin["name"] == "mobile-development" and match.band == "high"
                    for match in matches
                ))

        negative_prompts = [
            "create a generic iOS app",
            "build a generic iOS app using SwiftUI",
            "add login to my existing iOS app using Firebase",
            "build a to-do list Android app in Kotlin",
        ]
        for prompt in negative_prompts:
            with self.subTest(prompt=prompt):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                self.assertFalse(any(
                    match.plugin["name"] == "mobile-development" and match.band == "high"
                    for match in matches
                ))

    def test_agentforce_only_prompt_does_not_high_match_mobile_development(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)
        matches = self.mod.score_prompt_against_catalog(
            "author and test a new Agentforce .agent file for an employee agent", data
        )
        self.assertFalse(any(
            match.plugin["name"] == "mobile-development" and match.band == "high"
            for match in matches
        ))

    def test_empty_catalog_yields_an_empty_list(self):
        self.assertEqual(
            self.mod.score_prompt_against_catalog("build a flow", {"plugins": []}), []
        )

    def test_empty_prompt_yields_an_empty_list(self):
        data = self.mod.load_catalog(PLUGIN_ROOT)
        self.assertEqual(self.mod.score_prompt_against_catalog("", data), [])

    def test_match_shape_exposes_plugin_score_band_and_matched_terms(self):
        # A single-plugin catalog degenerates BM25 idf (every term's doc
        # frequency equals total_docs), so a second, disjoint-vocabulary
        # plugin is included purely to give the scorer contrast to work with.
        plugin = self._plugin(
            "flow-plugin", "Build and automate Salesforce Flows.", ["flow", "automation"], ["build a flow"]
        )
        unrelated = self._plugin(
            "unrelated-plugin",
            "Analyze and secure Apex code for governor limit violations.",
            ["apex", "security", "governor limits"],
            ["analyze my apex code"],
        )
        matches = self.mod.score_prompt_against_catalog(
            "build a flow", {"plugins": [plugin, unrelated]}
        )
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.plugin["name"], "flow-plugin")
        self.assertGreater(match.score, 0)
        self.assertIn(match.band, {"high", "medium"})
        self.assertTrue(match.matched_terms)
        self.assertIsInstance(match.matched_terms, frozenset)


if __name__ == "__main__":
    unittest.main(verbosity=2)

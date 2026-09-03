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

    def test_provenance_hash_is_the_sha256_of_the_marketplace_bytes(self):
        # The provenance digest is the whole point of the generated artifact: it
        # binds the catalog to the exact marketplace bytes it was built from. Pin
        # that it is literally sha256(marketplace file bytes) -- not sha256 of the
        # serialized catalog, not a placeholder constant, both of which would also
        # be 64 hex chars and pass the shape check in _validate_catalog.
        import hashlib
        marketplace_bytes = (REPO_ROOT / self.mod.MARKETPLACE_RELATIVE).read_bytes()
        data = self.mod.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        self.assertEqual(
            data["generatedFrom"]["marketplaceSha256"],
            hashlib.sha256(marketplace_bytes).hexdigest(),
        )

    def test_check_detects_a_marketplace_edit_invisible_to_the_flattened_rows(self):
        # check() must go stale on ANY marketplace content change, including one
        # that leaves every flattened plugin row byte-identical (reformatted
        # whitespace / reordered top-level keys). The provenance sha is the ONLY
        # signal that catches this class of drift -- the flattened rows alone
        # wouldn't -- so this proves the digest is actually consulted by check(),
        # not just emitted. Built on a synthetic repo so the real marketplace is
        # never mutated.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            (repo_root / ".claude-plugin").mkdir(parents=True)
            (repo_root / "skills").mkdir()
            marketplace_path = repo_root / self.mod.MARKETPLACE_RELATIVE
            entry = {
                "name": "sample-plugin",
                "source": "./plugins/sample-plugin",
                "description": "A sample plugin for provenance testing.",
                "keywords": ["sample"],
                "metadata": {"match": {"examplePrompts": ["test the sample plugin"]}},
            }
            marketplace = {"name": "test-marketplace", "plugins": [entry]}
            marketplace_path.write_text(
                json.dumps(marketplace, indent=2), encoding="utf-8"
            )
            (repo_root / "config.yml").write_text("internalPlugins: []\n", encoding="utf-8")
            artifact = repo_root / self.mod.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            # Write the artifact via _serialized rather than generate(), which uses
            # write_text(newline=...) (Python 3.10+) -- these tests run on the 3.9
            # CI baseline. The bytes are identical to what generate() emits on a
            # POSIX runner.
            artifact.write_text(
                self.mod._serialized(self.mod.build_catalog(repo_root, repo_root)),
                encoding="utf-8",
            )
            self.assertTrue(self.mod.check(repo_root, repo_root, artifact))

            # Reformat the marketplace bytes only -- same parsed object, same
            # flattened rows, DIFFERENT bytes => different sha => stale.
            reformatted = json.dumps(marketplace, indent=4) + "\n"
            self.assertNotEqual(reformatted.encode("utf-8"), marketplace_path.read_bytes())
            marketplace_path.write_text(reformatted, encoding="utf-8")
            with self.assertRaisesRegex(self.mod.PluginCatalogError, "stale"):
                self.mod.check(repo_root, repo_root, artifact)

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
        optional_match_keys = {"anchorTerms", "anchorCompanions", "entryCommand"}
        for row in data["plugins"]:
            self.assertEqual(set(row), {"name", "source", "match"})
            self.assertTrue(required_match_keys <= set(row["match"]) <= required_match_keys | optional_match_keys)
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

    def _plugin(self, name, description, keywords, example_prompts, source="./x",
                anchor_terms=None, anchor_companions=None):
        match = {"description": description, "keywords": keywords, "examplePrompts": example_prompts}
        if anchor_terms:
            match["anchorTerms"] = anchor_terms
        if anchor_companions:
            match["anchorCompanions"] = anchor_companions
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

    def test_anchor_companion_gates_a_common_word_anchor_on_a_corroborating_token(self):
        # An anchor term that is itself an everyday word ("drive", a verb in
        # "drive adoption/revenue") declares anchorCompanions so it only anchors
        # when a corroborating token is co-present -- proxying the bigram
        # "test drive" via the token "test". This is the mechanism behind
        # test-drive's leak fix, isolated from BM25 corpus noise. Score alone
        # cannot separate the leak from the keeper; the companion token can.
        gated = self._plugin(
            "drive-plugin",
            "Take a guided test drive of a rehearsable end-to-end product build.",
            ["test drive", "guided walkthrough", "rehearsable build"],
            ["take Service Cloud for a test drive"],
            anchor_terms=["drive", "walkthrough"],
            anchor_companions={"drive": ["test"]},
        )
        # A disjoint second plugin gives BM25 idf something to work with.
        unrelated = self._plugin(
            "flow-plugin",
            "Build and automate record-triggered Salesforce Flows.",
            ["flow", "automation"],
            ["build a record-triggered flow"],
        )
        catalog_data = {"plugins": [gated, unrelated]}

        # Bare "drive" as a verb, no "test" companion -> the anchor does not fire
        # even though "drive" is a matched term that would otherwise clear score.
        matches = self.mod.score_prompt_against_catalog(
            "drive adoption of a rehearsable build across the team", catalog_data
        )
        self.assertNotIn("drive-plugin", {match.plugin["name"] for match in matches})

        # The "test" companion present -> the "drive" anchor fires and it surfaces.
        matches = self.mod.score_prompt_against_catalog(
            "take a test drive of the rehearsable build", catalog_data
        )
        self.assertIn("drive-plugin", {match.plugin["name"] for match in matches})

        # A companion-less anchor on the SAME plugin ("walkthrough") still fires
        # on its own -- companions gate only the term that declares them.
        matches = self.mod.score_prompt_against_catalog(
            "give me a guided walkthrough of the rehearsable build", catalog_data
        )
        self.assertIn("drive-plugin", {match.plugin["name"] for match in matches})

    def test_real_test_drive_catalog_declares_the_drive_companion(self):
        # Lock the leak fix into the checked-in artifact: if someone strips
        # anchorCompanions from salesforce-test-drive, bare "drive" starts
        # leaking onto the proactive surfaces again. Guard both the data and the
        # end-to-end behavioural consequence.
        data = self.mod.load_catalog(PLUGIN_ROOT)
        row = next(p for p in data["plugins"] if p["name"] == "salesforce-test-drive")
        self.assertEqual(row["match"].get("anchorCompanions"), {"drive": ["test"]})
        self.assertIn("drive", row["match"].get("anchorTerms", []))

        # Mirror the proactive surface: the always-active foundation plugin is
        # excluded from the candidate corpus before scoring.
        data = {
            **data,
            "plugins": [p for p in data["plugins"] if p["name"] != "salesforce-development"],
        }
        # Isolate the "drive" companion: a near-identical prompt pair where
        # "drive" is the ONLY anchor candidate (no "walkthrough"/"rehearsable"
        # to fire on their own), differing only by the "test" companion token.
        # The bigram present -> high; strip "test" and the anchor is gated out.
        without_test = "take Service Cloud for a drive"
        with_test = "take Service Cloud for a test drive"
        self.assertFalse(any(
            m.plugin["name"] == "salesforce-test-drive" and m.band == "high"
            for m in self.mod.score_prompt_against_catalog(without_test, data)
        ))
        self.assertTrue(any(
            m.plugin["name"] == "salesforce-test-drive" and m.band == "high"
            for m in self.mod.score_prompt_against_catalog(with_test, data)
        ))

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

    def test_test_drive_only_surfaces_on_explicit_walkthrough_intent(self):
        # salesforce-test-drive is deliberately shy. On the proactive surfaces
        # (UserPromptSubmit / SessionStart, which score with
        # require_anchor_terms=True) it may interrupt a developer ONLY when the
        # prompt carries explicit "test drive" / "guided walkthrough" /
        # "rehearsable build" intent. A serious developer who knows what they
        # want -- deploying Apex, building a flow -- or who merely says "drive"
        # / "guided" / "Google Drive" in passing must never have this
        # learning-engine plugin proposed at them unprompted. Its anchor set is
        # kept to the distinctive tokens {drive, walkthrough, rehearsable} for
        # exactly this reason ("demo"/"guided" are intentionally NOT anchors:
        # both collide with everyday developer phrasing and the former also
        # eroded dx-org-lifecycle's precision on "trial org for this demo").
        data = self.mod.load_catalog(PLUGIN_ROOT)
        # Mirror the real proactive surface: the foundation plugin is always
        # active and excluded from the candidate corpus before scoring (see
        # test_real_tranche_prompts_have_one_high_confidence_product_route).
        data = {
            **data,
            "plugins": [p for p in data["plugins"] if p["name"] != "salesforce-development"],
        }

        explicit_requests = [
            "take Service Cloud for a test drive",
            "test drive the service help agent",
            "I want to test drive building a website chat widget",
            "give me a guided walkthrough of building a Service help agent",
            "show me a rehearsable end-to-end Salesforce build I can follow",
        ]
        for prompt in explicit_requests:
            with self.subTest(explicit=prompt):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                self.assertTrue(any(
                    match.plugin["name"] == "salesforce-test-drive" and match.band == "high"
                    for match in matches
                ))

        serious_developer_prompts = [
            "drive adoption of my new feature",              # "drive" as a verb
            "read the quarterly report from Google Drive",   # unrelated "drive"
            "guided setup for my scratch org",               # "guided" is common
            "deploy my Apex classes to production",          # knows what they want
            "build a record-triggered flow for approvals",
        ]
        for prompt in serious_developer_prompts:
            with self.subTest(serious=prompt):
                matches = self.mod.score_prompt_against_catalog(prompt, data)
                self.assertFalse(any(
                    match.plugin["name"] == "salesforce-test-drive" and match.band == "high"
                    for match in matches
                ))

    def test_tokenize_lowercases_and_drops_stopwords_and_single_chars(self):
        # _tokenize is the front door of the scorer: everything the BM25 pass
        # sees is what survives here. Three filters run, each load-bearing:
        # (1) lowercase, so casing never splits a term; (2) the _GENERIC_MATCH_TERMS
        # stoplist, so request scaffolding ("build", "a", "with") is not product
        # evidence; (3) the `len(token) > 1` short-token drop, so a lone letter or
        # digit ("x", "5") cannot become a scored term. This last filter is
        # exercised nowhere else -- relaxing it to `>= 1` would readmit single
        # chars as evidence with no other test failing.
        self.assertEqual(
            self.mod._tokenize("Build a FLOW with X 5 Approvals"),
            ["flow", "approvals"],
        )
        # A non-stoplisted single character alone tokenizes to nothing (proving the
        # drop is the length filter, not stoplist membership).
        self.assertEqual(self.mod._tokenize("z"), [])
        self.assertEqual(self.mod._tokenize("7"), [])
        # Punctuation is a separator, not a token; distinctive multi-char words
        # survive regardless of surrounding noise.
        self.assertEqual(self.mod._tokenize("LWC, React!! shadcn"), ["lwc", "react", "shadcn"])

    def test_bm25_idf_is_monotonic_in_document_frequency(self):
        # The load-bearing ranking property, tested at the seam: holding term
        # frequency, doc length, and corpus size constant, a term's BM25 score
        # must strictly DECREASE as it appears in more documents. This is why a
        # distinctive product word (rare across the catalog) outweighs a generic
        # word shared by every plugin -- and why matching degenerates in a tiny
        # corpus (every term is "common", its idf collapses).
        doc_tokens = ["zephyr", "widget", "widget"]
        common = dict(
            query_terms={"zephyr"}, doc_tokens=doc_tokens, avg_doc_len=3.0, total_docs=20
        )
        rare, _ = self.mod._bm25_score(doc_freq={"zephyr": 1}, **common)
        mid, _ = self.mod._bm25_score(doc_freq={"zephyr": 10}, **common)
        ubiquitous, _ = self.mod._bm25_score(doc_freq={"zephyr": 20}, **common)
        self.assertGreater(rare, mid)
        self.assertGreater(mid, ubiquitous)
        self.assertGreaterEqual(ubiquitous, 0.0)  # idf never goes negative here

    def test_bm25_term_frequency_saturates_sub_linearly(self):
        # BM25_K1 is the term-frequency saturation knob: repeating a query term
        # in a document must raise the score (more evidence) but with DIMINISHING
        # returns -- never linearly. Hold idf (doc_freq), doc length, and corpus
        # size constant by padding every document to the same length, so the ONLY
        # variable is how many times the matched term appears. If a regression set
        # K1 absurdly high (approaching raw-count scoring) or removed the
        # saturation denominator, doubling the frequency would ~double the score
        # and this guard would fire.
        common = dict(
            query_terms={"zephyr"}, doc_freq={"zephyr": 1}, avg_doc_len=10.0, total_docs=20
        )
        once, _ = self.mod._bm25_score(doc_tokens=["zephyr"] + ["pad"] * 9, **common)
        twice, _ = self.mod._bm25_score(doc_tokens=["zephyr", "zephyr"] + ["pad"] * 8, **common)
        four, _ = self.mod._bm25_score(doc_tokens=["zephyr"] * 4 + ["pad"] * 6, **common)
        self.assertGreater(twice, once)              # more frequency => more score
        self.assertLess(twice, 2 * once)             # ...but strictly sub-linear
        self.assertLess(four - twice, twice - once)  # marginal gain diminishes

    def test_bm25_penalizes_longer_documents_at_equal_term_frequency(self):
        # BM25_B is the length-normalization knob: at IDENTICAL raw term
        # frequency, a term occurring in a short focused document must outscore
        # the same term buried in a long padded one, so a sprawling marketplace
        # description cannot out-rank a tight one just by being longer. B=0 would
        # disable this normalization entirely (short == long) -- this guard pins
        # that the penalty is active.
        common = dict(
            query_terms={"zephyr"}, doc_freq={"zephyr": 1}, avg_doc_len=10.0, total_docs=20
        )
        short, _ = self.mod._bm25_score(doc_tokens=["zephyr"] + ["pad"] * 4, **common)
        long, _ = self.mod._bm25_score(doc_tokens=["zephyr"] + ["pad"] * 19, **common)
        self.assertGreater(short, long)

    def test_jaccard_overlap_ratio_and_empty_union_guard(self):
        # _jaccard is the evidence-agreement signal the dedup gate multiplies
        # against the score margin. Pin its exact ratios and the empty-union
        # guard (its `if not union: return 0.0` short-circuit is unreachable from
        # the scorer's only caller, since every scored candidate matched >=1 term,
        # so it is asserted directly here or not at all). An off-by-one in the
        # intersection/union arithmetic would silently reshape every collapse
        # decision.
        self.assertEqual(self.mod._jaccard(frozenset(), frozenset()), 0.0)
        self.assertEqual(self.mod._jaccard(frozenset({"a", "b"}), frozenset({"a", "b"})), 1.0)
        self.assertEqual(self.mod._jaccard(frozenset({"a", "b", "c"}), frozenset({"a"})), 1 / 3)
        self.assertEqual(self.mod._jaccard(frozenset({"a"}), frozenset({"b"})), 0.0)
        # The exact 0.6 threshold boundary the collapse gate keys on.
        self.assertEqual(
            self.mod._jaccard(frozenset({"a", "b", "c", "d"}), frozenset({"a", "b", "c", "e"})), 0.6
        )

    def test_collapse_keeps_both_when_overlap_is_high_but_score_gap_is_wide(self):
        # The load-bearing half of _collapse_near_duplicates' documented AND
        # condition: two candidates matched on substantially the SAME evidence
        # (Jaccard >= 0.6) must still BOTH survive when their scores differ by
        # more than DEDUP_SCORE_MARGIN (1.0). Every other collapse test uses
        # identical plugins (gap 0, full overlap -> collapse) or disjoint vocab
        # (overlap 0 -> keep); none exercises "high overlap, wide score gap ->
        # keep both". A regression that collapsed on overlap ALONE (dropping the
        # score-margin conjunct) would silently suppress a legitimately strong
        # plugin behind a weak one sharing its evidence -- and pass every existing
        # test. Built by calling the collapse fn directly with hand-made Matches
        # so the score gap and overlap are controlled independently.
        Match = self.mod.Match
        shared = frozenset({"flow", "automation", "record"})
        strong = Match(plugin={"name": "strong"}, score=5.0, band="high", matched_terms=shared)
        weak = Match(plugin={"name": "weak"}, score=3.0, band="medium", matched_terms=shared)
        kept = self.mod._collapse_near_duplicates(
            [strong, weak],
            margin=self.mod.DEDUP_SCORE_MARGIN,
            overlap_threshold=self.mod.DEDUP_OVERLAP_THRESHOLD,
        )
        self.assertEqual([m.plugin["name"] for m in kept], ["strong", "weak"])

        # Boundary mirror: the score-margin comparison is inclusive (`<=`), so a
        # gap of EXACTLY the margin with the same high overlap DOES collapse --
        # the lower-scoring twin is suppressed. This pins the `<=` (not `<`).
        weak_at_margin = Match(
            plugin={"name": "weak"}, score=4.0, band="high", matched_terms=shared
        )
        collapsed = self.mod._collapse_near_duplicates(
            [strong, weak_at_margin],
            margin=self.mod.DEDUP_SCORE_MARGIN,
            overlap_threshold=self.mod.DEDUP_OVERLAP_THRESHOLD,
        )
        self.assertEqual([m.plugin["name"] for m in collapsed], ["strong"])

    def test_collapse_boundary_is_inclusive_at_the_overlap_threshold(self):
        # The overlap side of the AND: at a small score gap (<= margin), overlap
        # EXACTLY at DEDUP_OVERLAP_THRESHOLD (0.6) collapses, and overlap just
        # below it (0.5) keeps both. Together with the test above this pins both
        # conjuncts of the gate at their boundaries -- the seam most vulnerable to
        # a `>=`/`>` or `<=`/`<` off-by-one regression.
        Match = self.mod.Match
        # Jaccard == 0.6 (>= threshold) -> collapse the lower-scoring twin.
        at = [
            Match(plugin={"name": "hi"}, score=5.0, band="high",
                  matched_terms=frozenset({"a", "b", "c", "d"})),
            Match(plugin={"name": "lo"}, score=4.5, band="high",
                  matched_terms=frozenset({"a", "b", "c", "e"})),
        ]
        kept_at = self.mod._collapse_near_duplicates(
            at, margin=self.mod.DEDUP_SCORE_MARGIN, overlap_threshold=self.mod.DEDUP_OVERLAP_THRESHOLD
        )
        self.assertEqual([m.plugin["name"] for m in kept_at], ["hi"])
        # Jaccard == 0.5 (< threshold) -> both distinct plugins survive.
        below = [
            Match(plugin={"name": "hi"}, score=5.0, band="high",
                  matched_terms=frozenset({"a", "b", "c"})),
            Match(plugin={"name": "lo"}, score=4.5, band="high",
                  matched_terms=frozenset({"a", "b", "d"})),
        ]
        kept_below = self.mod._collapse_near_duplicates(
            below, margin=self.mod.DEDUP_SCORE_MARGIN, overlap_threshold=self.mod.DEDUP_OVERLAP_THRESHOLD
        )
        self.assertEqual([m.plugin["name"] for m in kept_below], ["hi", "lo"])

    def test_scoring_is_deterministic_and_sorted_descending(self):
        # No set-iteration nondeterminism may leak into the output: the same
        # prompt against the same catalog must return byte-identical results
        # across runs (scores are order-independent sums; the final sort is
        # stable), and the ranking must be non-increasing by score.
        data = self.mod.load_catalog(PLUGIN_ROOT)
        prompt = "configure a DevOps Center test pipeline and promote a work item"
        first = self.mod.score_prompt_against_catalog(prompt, data)
        for _ in range(5):
            again = self.mod.score_prompt_against_catalog(prompt, data)
            self.assertEqual(
                [(m.plugin["name"], m.score, m.band, m.matched_terms) for m in first],
                [(m.plugin["name"], m.score, m.band, m.matched_terms) for m in again],
            )
        scores = [m.score for m in first]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_equal_scoring_distinct_plugins_keep_catalog_order(self):
        # Tie-break is the stable sort's contract: two distinct plugins that
        # score identically (disjoint vocab -> not collapsed by dedup) must
        # preserve their catalog input order, not reorder run-to-run. Built as
        # mirror-image plugins so both score exactly the same on a two-term
        # prompt naming one distinctive word from each.
        left = self._plugin(
            "alpha-plugin", "Alpha zephyr tooling.", ["zephyr"], ["use zephyr"]
        )
        right = self._plugin(
            "beta-plugin", "Beta quokka tooling.", ["quokka"], ["use quokka"]
        )
        catalog_data = {"plugins": [left, right]}
        matches = self.mod.score_prompt_against_catalog(
            "zephyr and quokka", catalog_data, require_anchor_terms=False
        )
        self.assertEqual([m.plugin["name"] for m in matches], ["alpha-plugin", "beta-plugin"])
        self.assertEqual(matches[0].score, matches[1].score)

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

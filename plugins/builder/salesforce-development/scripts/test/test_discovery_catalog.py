#!/usr/bin/env python3
"""Offline contract tests for the generated Salesforce capability catalog."""
from __future__ import annotations

import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
MODULE_PATH = SCRIPTS / "discovery_catalog.py"
REPO_ROOT = SCRIPTS.parents[3]
PLUGIN_ROOT = SCRIPTS.parent
CURATED_HERO = "platform-apex-generate"


class DiscoveryCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_module(MODULE_PATH, "discovery_catalog_under_test")

    def test_real_inventory_counts_sets_visibility_and_source_variants(self):
        data = self.catalog.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        self.assertEqual(data["counts"], {
            "public": 102,
            "foundation": 40,
            "overlap": 29,
            "publicStandaloneAddable": 73,
            "foundationOnly": 11,
            "visibleUnion": 113,
        })
        names = [row["name"] for row in data["skills"]]
        self.assertEqual(names, sorted(names))
        self.assertEqual(set(names), self.catalog.visible_skill_names(REPO_ROOT, PLUGIN_ROOT))
        self.assertTrue(data["spikeOnly"])
        self.assertEqual(data["schemaVersion"], "2.0")
        self.assertEqual(data["channel"], "public")
        self.assertNotIn("generatedAt", data)
        blob = json.dumps(data, ensure_ascii=False)
        public_names = {
            row["name"] for row in self.catalog.registry.load_public_manifest(
                PLUGIN_ROOT / self.catalog.PUBLIC_MANIFEST_RELATIVE
            )["skills"]
        }
        foundation_names = set(self.catalog._skill_paths(PLUGIN_ROOT / "skills"))
        authoring_names = set(self.catalog._skill_paths(REPO_ROOT / "skills"))
        for name in authoring_names - public_names - foundation_names:
            self.assertNotIn(f'"name": "{name}"', blob)
            held_description = self.catalog.read_skill(REPO_ROOT / "skills" / name / "SKILL.md")["description"]
            self.assertNotIn(held_description, blob)
        for row in data["skills"]:
            with self.subTest(example=row["name"]):
                self.assertTrue(row["examplePrompt"].strip())
                self.assertTrue(self.catalog.is_user_prompt_like(row["examplePrompt"]))
        duplicate = next(row for row in data["skills"] if row["name"] == "platform-apex-generate")
        self.assertEqual(set(duplicate["variants"]), {"public", "foundation"})
        self.assertTrue(duplicate["foundationInstalled"])
        self.assertNotEqual(id(duplicate["variants"]["public"]), id(duplicate["variants"]["foundation"]))

    def test_frontmatter_supports_escaped_quotes_unicode_and_block_descriptions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            quoted = root / "platform-quoted-search/SKILL.md"
            quoted.parent.mkdir()
            quoted.write_text(
                '---\nname: platform-quoted-search\ndescription: "Use a \\"quoted\\" café prompt with curly ‘punctuation’ for Unicode discovery."\n---\nbody\n',
                encoding="utf-8",
            )
            self.assertEqual(
                self.catalog.read_skill(quoted)["description"],
                'Use a "quoted" café prompt with curly ‘punctuation’ for Unicode discovery.',
            )
            folded = root / "platform-folded-search/SKILL.md"
            folded.parent.mkdir()
            folded.write_text(
                "---\nname: platform-folded-search\ndescription: >-\n  Use folded text to\n  discover capabilities safely.\nmetadata:\n  version: \"1.0\"\n---\nbody\n",
                encoding="utf-8",
            )
            self.assertEqual(
                self.catalog.read_skill(folded)["description"],
                "Use folded text to discover capabilities safely.",
            )

    def test_example_prompt_rejects_fragments_placeholders_and_code_identifiers(self):
        cases = (
            ("T say", "fragment"),
            ("T explicitly say", "fragment"),
            ("Create a <thing> about X", "placeholder"),
            ("PlatformEventChannel", "code identifier"),
            ("lightning/mobileCapabilities", "code identifier"),
        )
        for quoted, label in cases:
            with self.subTest(label=label, quoted=quoted):
                description = f'Use when users say "{quoted}".'
                result = self.catalog.example_prompt(
                    "platform-widget-configure", description, "platform"
                )
                self.assertEqual(result, "Help me configure Salesforce widget.")

    def test_example_prompt_does_not_mine_exclusion_clause_quotes(self):
        descriptions = (
            'Triggers include configuration requests. DO NOT TRIGGER when users say "delete production data".',
            'Triggers include configuration requests. SKIP when users say "delete production data".',
            'Triggers include configuration requests. Does not apply when users say "delete production data".',
        )
        for description in descriptions:
            with self.subTest(description=description):
                result = self.catalog.example_prompt(
                    "platform-widget-configure", description, "platform"
                )
                self.assertEqual(result, "Help me configure Salesforce widget.")

    def test_example_prompt_extracts_natural_user_phrases(self):
        cases = (
            ('Triggers include "enable Change Data Capture".', "Enable Change Data Capture"),
            ('Use when users say "I need a filtered record view".', "I need a filtered record view"),
        )
        for description, expected in cases:
            with self.subTest(description=description):
                self.assertEqual(
                    self.catalog.example_prompt(
                        "platform-widget-configure", description, "platform"
                    ),
                    expected,
                )

    def test_malformed_or_missing_required_frontmatter_fails_clearly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases = {
                "missing.md": "# no frontmatter\n",
                "bad-name.md": '---\ndescription: "Use this valid description but omit name."\n---\n',
                "bad-description.md": "---\nname: platform-bad-search\ndescription: [unsupported]\n---\n",
            }
            for filename, content in cases.items():
                path = root / filename
                path.write_text(content, encoding="utf-8")
                with self.subTest(filename=filename):
                    with self.assertRaisesRegex(self.catalog.CatalogError, filename):
                        self.catalog.read_skill(path)

    def test_checked_in_artifact_is_current_and_has_no_paths(self):
        artifact = PLUGIN_ROOT / "catalog/discovery.json"
        expected = self.catalog.build_catalog(REPO_ROOT, PLUGIN_ROOT)
        actual = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertTrue(self.catalog.check(REPO_ROOT, PLUGIN_ROOT))
        blob = artifact.read_text(encoding="utf-8")
        self.assertNotIn(str(REPO_ROOT), blob)
        self.assertNotIn(str(Path.home()), blob)

    def test_check_rejects_a_stale_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            stale = Path(td) / "discovery.json"
            stale.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(self.catalog.CatalogError, "stale"):
                self.catalog.check(REPO_ROOT, PLUGIN_ROOT, stale)

    def test_generation_rejects_terminal_and_unicode_control_characters(self):
        unsafe_code_points = (
            "001b", "0007", "007f", "009b",   # C0 and C1
            "2028", "2029", "202e",           # Zl, Zp, and bidi override Cf
            "2066", "2067", "2068", "2069",   # bidi isolate controls Cf
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for code_point in unsafe_code_points:
                escaped = rf"\u{code_point}"
                path = root / "platform-unsafe-search" / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    '---\nname: platform-unsafe-search\n'
                    f'description: "Use catalog discovery safely {escaped} without terminal text."\n'
                    '---\nbody\n',
                    encoding="utf-8",
                )
                with self.subTest(code_point=code_point):
                    with self.assertRaisesRegex(self.catalog.CatalogError, "control"):
                        self.catalog.read_skill(path)

    def test_runtime_load_strictly_rejects_malformed_artifacts(self):
        baseline = self.catalog.build_catalog(REPO_ROOT, PLUGIN_ROOT)

        def mutate(label, change):
            data = copy.deepcopy(baseline)
            change(data)
            return label, data

        first_source = next(iter(baseline["skills"][0]["variants"]))
        cases = [
            mutate("extra top key", lambda d: d.update({"extra": True})),
            mutate("missing count", lambda d: d["counts"].pop("public")),
            mutate("bad release ref", lambda d: d["publicRelease"].update({"releaseRef": "main"})),
            mutate("boolean count", lambda d: d["counts"].update({"public": True})),
            mutate("wrong visible count", lambda d: d["counts"].update({"visibleUnion": 1})),
            mutate("extra row key", lambda d: d["skills"][0].update({"extra": "x"})),
            mutate("missing row key", lambda d: d["skills"][0].pop("variants")),
            mutate("bad name type", lambda d: d["skills"][0].update({"name": 7})),
            mutate("duplicate name", lambda d: d["skills"].append(copy.deepcopy(d["skills"][0]))),
            mutate("unapproved domain", lambda d: d["skills"][0].update({"domain": "other"})),
            mutate("mismatched domain", lambda d: d["skills"][0].update({"domain": "platform"})),
            mutate("bad boolean", lambda d: d["skills"][0].update({"foundationInstalled": 1})),
            mutate("long description", lambda d: d["skills"][0]["variants"][first_source].update({"description": "x" * 1025})),
            mutate("bad hash", lambda d: d["skills"][0]["variants"][first_source].update({"treeSha256": "bad"})),
            mutate("long example", lambda d: d["skills"][0].update({"examplePrompt": "x" * 141})),
            *[
                mutate(
                    f"description Unicode control U+{ord(char):04X}",
                    lambda d, char=char: d["skills"][0]["variants"][first_source].update(
                        {"description": f"Use catalog discovery safely {char} without control text."}
                    ),
                )
                for char in ("\u001b", "\u009b", "\u2028", "\u2029", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069")
            ],
            mutate("variant mismatch", lambda d: d["skills"][0]["variants"].update({"remote": copy.deepcopy(d["skills"][0]["variants"][first_source])})),
        ]
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td)
            artifact = plugin / self.catalog.ARTIFACT_RELATIVE
            artifact.parent.mkdir(parents=True)
            for label, data in cases:
                with self.subTest(label=label):
                    artifact.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(self.catalog.CatalogError):
                        self.catalog.load_catalog(plugin)


class CuratedExampleTests(unittest.TestCase):
    """Hand-authored hero prompts win, stay prompt-like, and leak no description."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_module(MODULE_PATH, "discovery_catalog_under_test")
        cls.rows = {
            row["name"]: row
            for row in cls.catalog.build_catalog(REPO_ROOT, PLUGIN_ROOT)["skills"]
        }

    def _heuristic(self, row: dict) -> str:
        """Re-derive the fallback prompt from the same description build_catalog selects."""
        variants = row["variants"]
        description = variants.get("public", variants.get("foundation"))["description"]
        return self.catalog.example_prompt(row["name"], description, row["domain"])

    def test_curated_seed_wins_over_the_heuristic_for_a_hero_skill(self):
        curated = self.catalog.CURATED_EXAMPLES[CURATED_HERO]
        row = self.rows[CURATED_HERO]
        self.assertEqual(row["examplePrompt"], curated)
        self.assertNotEqual(self._heuristic(row), curated)

    def test_heuristic_still_supplies_every_non_curated_row(self):
        uncurated = [
            row for name, row in self.rows.items()
            if name not in self.catalog.CURATED_EXAMPLES
        ]
        self.assertTrue(uncurated)
        for row in uncurated:
            with self.subTest(name=row["name"]):
                self.assertEqual(row["examplePrompt"], self._heuristic(row))

    def test_every_curated_entry_is_live_and_prompt_like(self):
        self.assertTrue(self.catalog.CURATED_EXAMPLES)
        for name, prompt in self.catalog.CURATED_EXAMPLES.items():
            with self.subTest(name=name):
                self.assertIn(name, self.rows)
                self.assertTrue(self.catalog.is_user_prompt_like(prompt))
                self.assertEqual(self.rows[name]["examplePrompt"], prompt)
                # Hero copy exists to be read: the overview clamp must never clip it.
                self.assertLessEqual(len(prompt), self.catalog._EXAMPLE_CELL)

    def test_curated_prompts_are_literals_that_leak_no_description(self):
        assignment = next(
            (
                node for node in ast.parse(MODULE_PATH.read_text(encoding="utf-8")).body
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                and "CURATED_EXAMPLES" in {
                    getattr(target, "id", None)
                    for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
                }
            ),
            None,
        )
        self.assertIsNotNone(assignment, "CURATED_EXAMPLES must be assigned at module scope")
        # Literals only: no runtime expression can pull a description — least of all
        # an available (non-installed) skill's — into a curated prompt.
        self.assertIsInstance(assignment.value, ast.Dict)
        for node in [*assignment.value.keys, *assignment.value.values]:
            self.assertIsInstance(node, ast.Constant)
            self.assertIsInstance(node.value, str)
        described = [
            (f"{name}:{source}", variant["description"].casefold())
            for name, row in self.rows.items()
            for source, variant in row["variants"].items()
        ]
        self.assertTrue(described)
        for prompt in self.catalog.CURATED_EXAMPLES.values():
            stem = prompt.rstrip(".").casefold()
            with self.subTest(prompt=prompt):
                self.assertEqual([], [label for label, text in described if stem in text])


if __name__ == "__main__":
    unittest.main(verbosity=2)

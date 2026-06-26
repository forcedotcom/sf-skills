"""Tests for ``parse_bundle`` — Bot.bot + GenAiPlannerBundle parsing.

Covers the four public functions:

- ``classify_generation``    pure str → str
- ``extract_planner_name``   reads bots/*.bot from a tmp WORK_DIR
- ``extract_bundle``         reads genAiPlannerBundles/*.genAiPlannerBundle
- ``atomic_write``           tmp-file + os.replace semantics

All filesystem fixtures are constructed inline under ``tmp_path`` — no
external fixture files needed. XML mirrors the real Salesforce metadata
shape (sf: namespace) so the parser exercises its real code path.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from . import _bootstrap  # noqa: F401  — sys.path setup

import parse_bundle  # type: ignore


SF_NS = "http://soap.sforce.com/2006/04/metadata"


def _bot_xml(version: str, planner_name: str | None = "MyPlanner") -> str:
    """Minimal Bot.bot XML with one botVersions block.

    If ``planner_name`` is None, omit the <conversationDefinitionPlanners>
    block — caller can use this to exercise the empty-planner branch.
    """
    cdp_block = (
        f"""    <conversationDefinitionPlanners>
      <genAiPlannerName>{planner_name}</genAiPlannerName>
    </conversationDefinitionPlanners>"""
        if planner_name is not None
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Bot xmlns="{SF_NS}">
  <botVersions>
    <fullName>{version}</fullName>
{cdp_block}
  </botVersions>
</Bot>
"""


def _bundle_xml(
    *,
    planner_type: str = "Atlas__Reasoning",
    description: str = "demo",
    master_label: str = "Demo",
    topics: list[dict] | None = None,
    planner_actions: list[dict] | None = None,
) -> str:
    """Build a genAiPlannerBundle XML body.

    Each topic dict supports keys ``name``, ``actions`` (list of dicts with
    keys ``name``, ``invocationTarget``, ``invocationTargetType``).
    """
    topics = topics or []
    planner_actions = planner_actions or []

    def _topic_xml(t: dict) -> str:
        actions = "".join(
            f"""    <localActions>
      <developerName>{a['name']}</developerName>
      <invocationTarget>{a.get('invocationTarget', '')}</invocationTarget>
      <invocationTargetType>{a.get('invocationTargetType', '')}</invocationTargetType>
    </localActions>
"""
            for a in t.get("actions", [])
        )
        return f"""  <localTopics>
    <developerName>{t['name']}</developerName>
    <masterLabel>{t.get('masterLabel', '')}</masterLabel>
    <canEscalate>{str(t.get('canEscalate', False)).lower()}</canEscalate>
{actions}  </localTopics>
"""

    def _planner_action_xml(a: dict) -> str:
        return f"""  <plannerActions>
    <developerName>{a['name']}</developerName>
    <invocationTarget>{a.get('invocationTarget', '')}</invocationTarget>
    <invocationTargetType>{a.get('invocationTargetType', '')}</invocationTargetType>
  </plannerActions>
"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<GenAiPlannerBundle xmlns="{SF_NS}">
  <plannerType>{planner_type}</plannerType>
  <description>{description}</description>
  <masterLabel>{master_label}</masterLabel>
{''.join(_topic_xml(t) for t in topics)}{''.join(_planner_action_xml(a) for a in planner_actions)}</GenAiPlannerBundle>
"""


# -----------------------------------------------------------------------------
# classify_generation — pure str → str
# -----------------------------------------------------------------------------


class ClassifyGenerationTests(unittest.TestCase):

    def test_aicopilot_prefix_classifies_as_classic(self):
        self.assertEqual(parse_bundle.classify_generation("AiCopilot__Foo"), "classic")

    def test_atlas_prefix_classifies_as_nga(self):
        self.assertEqual(parse_bundle.classify_generation("Atlas__Reasoning"), "nga")

    def test_unknown_prefix_classifies_as_unknown(self):
        self.assertEqual(parse_bundle.classify_generation("SomethingElse"), "unknown")

    def test_empty_string_classifies_as_unknown(self):
        self.assertEqual(parse_bundle.classify_generation(""), "unknown")

    def test_none_classifies_as_unknown(self):
        self.assertEqual(parse_bundle.classify_generation(None), "unknown")  # type: ignore[arg-type]


# -----------------------------------------------------------------------------
# extract_planner_name — reads bots/*.bot under WORK_DIR
# -----------------------------------------------------------------------------


class ExtractPlannerNameTests(unittest.TestCase):

    def _setup_bot(self, tmp: Path, version: str, planner_name: str | None = "MyPlanner") -> Path:
        bots_dir = tmp / "sf_meta" / "wave1_bot" / "unpackaged" / "bots"
        bots_dir.mkdir(parents=True)
        bot_file = bots_dir / "MyAgent.bot"
        bot_file.write_text(_bot_xml(version, planner_name))
        return tmp

    def test_returns_planner_name_when_botversion_matches(self):
        with TemporaryDirectory() as t:
            tmp = self._setup_bot(Path(t), "v1", "MyPlanner")
            self.assertEqual(parse_bundle.extract_planner_name(tmp, "v1"), "MyPlanner")

    def test_returns_empty_when_botversion_does_not_match(self):
        with TemporaryDirectory() as t:
            tmp = self._setup_bot(Path(t), "v1", "MyPlanner")
            self.assertEqual(parse_bundle.extract_planner_name(tmp, "v99"), "")

    def test_returns_empty_when_no_planner_block(self):
        # Bot has the right version but no <conversationDefinitionPlanners>
        with TemporaryDirectory() as t:
            tmp = self._setup_bot(Path(t), "v1", planner_name=None)
            self.assertEqual(parse_bundle.extract_planner_name(tmp, "v1"), "")

    def test_returns_empty_when_bots_dir_missing(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)  # no sf_meta/wave1_bot/...
            self.assertEqual(parse_bundle.extract_planner_name(tmp, "v1"), "")

    def test_returns_empty_when_xml_is_malformed(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            bots_dir = tmp / "sf_meta" / "wave1_bot" / "unpackaged" / "bots"
            bots_dir.mkdir(parents=True)
            (bots_dir / "Broken.bot").write_text("<<<not xml>>>")
            self.assertEqual(parse_bundle.extract_planner_name(tmp, "v1"), "")

    def test_falls_back_to_plannerName_then_fullName(self):
        # Build a bot with sf:plannerName instead of sf:genAiPlannerName.
        with TemporaryDirectory() as t:
            tmp = Path(t)
            bots_dir = tmp / "sf_meta" / "wave1_bot" / "unpackaged" / "bots"
            bots_dir.mkdir(parents=True)
            (bots_dir / "Fallback.bot").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<Bot xmlns="{SF_NS}">
  <botVersions>
    <fullName>v1</fullName>
    <conversationDefinitionPlanners>
      <plannerName>FallbackPlanner</plannerName>
    </conversationDefinitionPlanners>
  </botVersions>
</Bot>
""")
            self.assertEqual(
                parse_bundle.extract_planner_name(tmp, "v1"),
                "FallbackPlanner",
            )


# -----------------------------------------------------------------------------
# extract_bundle — reads genAiPlannerBundles/*.genAiPlannerBundle
# -----------------------------------------------------------------------------


class ExtractBundleTests(unittest.TestCase):

    def _setup_bundle(self, tmp: Path, body: str, dirname: str = "MyPlanner") -> None:
        bundle_dir = (
            tmp / "sf_meta" / "wave1_bundle" / "unpackaged" / "genAiPlannerBundles" / dirname
        )
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "MyPlanner.genAiPlannerBundle").write_text(body)

    def test_returns_skeleton_when_planner_dir_missing(self):
        with TemporaryDirectory() as t:
            out = parse_bundle.extract_bundle(Path(t), "MyPlanner")
        self.assertEqual(out["topics"], [])
        self.assertEqual(out["plannerActions"], [])
        self.assertEqual(out["plannerType"], None)
        self.assertEqual(out["plannerName"], "MyPlanner")
        self.assertEqual(out["generation"], "unknown")

    def test_extracts_planner_type_description_and_master_label(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            self._setup_bundle(tmp, _bundle_xml(
                planner_type="Atlas__Reasoning",
                description="My agent",
                master_label="My Agent",
            ))
            out = parse_bundle.extract_bundle(tmp, "MyPlanner")
        self.assertEqual(out["plannerType"], "Atlas__Reasoning")
        self.assertEqual(out["description"], "My agent")
        self.assertEqual(out["masterLabel"], "My Agent")
        self.assertEqual(out["generation"], "nga")

    def test_extracts_topics_with_localActions(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            self._setup_bundle(tmp, _bundle_xml(topics=[{
                "name": "Greetings",
                "masterLabel": "Greetings",
                "actions": [
                    {"name": "Hello", "invocationTarget": "say_hello",
                     "invocationTargetType": "apex"},
                    {"name": "Bye", "invocationTarget": "say_bye",
                     "invocationTargetType": "apex"},
                ],
            }]))
            out = parse_bundle.extract_bundle(tmp, "MyPlanner")
        self.assertEqual(len(out["topics"]), 1)
        self.assertEqual(out["topics"][0]["name"], "Greetings")
        self.assertEqual(len(out["topics"][0]["actions"]), 2)
        self.assertEqual(out["topics"][0]["actions"][0]["name"], "Hello")
        self.assertEqual(out["topics"][0]["actions"][0]["invocationTargetType"], "apex")

    def test_extracts_plannerActions_classic_shape(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            self._setup_bundle(tmp, _bundle_xml(
                planner_type="AiCopilot__Foo",
                planner_actions=[
                    {"name": "Search", "invocationTarget": "search",
                     "invocationTargetType": "flow"},
                ],
            ))
            out = parse_bundle.extract_bundle(tmp, "MyPlanner")
        self.assertEqual(out["generation"], "classic")
        self.assertEqual(len(out["plannerActions"]), 1)
        self.assertEqual(out["plannerActions"][0]["name"], "Search")

    def test_skips_topic_without_developerName(self):
        # Build XML where one topic has no <developerName> — should be dropped.
        with TemporaryDirectory() as t:
            tmp = Path(t)
            broken = f"""<?xml version="1.0" encoding="UTF-8"?>
<GenAiPlannerBundle xmlns="{SF_NS}">
  <plannerType>Atlas__Reasoning</plannerType>
  <localTopics>
    <masterLabel>NoName</masterLabel>
  </localTopics>
  <localTopics>
    <developerName>Good</developerName>
  </localTopics>
</GenAiPlannerBundle>
"""
            self._setup_bundle(tmp, broken)
            out = parse_bundle.extract_bundle(tmp, "MyPlanner")
        self.assertEqual(len(out["topics"]), 1)
        self.assertEqual(out["topics"][0]["name"], "Good")

    def test_returns_skeleton_when_xml_is_malformed(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            self._setup_bundle(tmp, "<<<broken>>>")
            out = parse_bundle.extract_bundle(tmp, "MyPlanner")
        # Malformed → no fields populated, but skeleton shape preserved.
        self.assertEqual(out["topics"], [])
        self.assertEqual(out["plannerActions"], [])
        self.assertEqual(out["plannerType"], None)


# -----------------------------------------------------------------------------
# atomic_write — tmp-file + os.replace
# -----------------------------------------------------------------------------


class AtomicWriteTests(unittest.TestCase):

    def test_writes_content_to_target_path(self):
        with TemporaryDirectory() as t:
            target = Path(t) / "out.txt"
            parse_bundle.atomic_write(target, "hello\n")
            self.assertEqual(target.read_text(), "hello\n")

    def test_overwrites_existing_file(self):
        with TemporaryDirectory() as t:
            target = Path(t) / "out.txt"
            target.write_text("old")
            parse_bundle.atomic_write(target, "new")
            self.assertEqual(target.read_text(), "new")

    def test_no_tmp_file_left_behind_after_success(self):
        with TemporaryDirectory() as t:
            target = Path(t) / "out.txt"
            parse_bundle.atomic_write(target, "x")
            # the .tmp sibling should NOT remain
            tmp_sibling = target.with_suffix(target.suffix + ".tmp")
            self.assertFalse(tmp_sibling.exists())


# -----------------------------------------------------------------------------
# main() — orchestration via env vars
# -----------------------------------------------------------------------------


class MainTests(unittest.TestCase):

    def _setup_full_workdir(self, tmp: Path) -> None:
        # Bot file
        bots_dir = tmp / "sf_meta" / "wave1_bot" / "unpackaged" / "bots"
        bots_dir.mkdir(parents=True)
        (bots_dir / "MyAgent.bot").write_text(_bot_xml("v1", "MyPlanner"))
        # Bundle file
        bundle_dir = (
            tmp / "sf_meta" / "wave1_bundle" / "unpackaged"
            / "genAiPlannerBundles" / "MyPlanner"
        )
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "MyPlanner.genAiPlannerBundle").write_text(_bundle_xml())

    def test_main_writes_bundle_parsed_json_and_returns_zero(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            self._setup_full_workdir(tmp)
            old = dict(os.environ)
            os.environ["WORK_DIR"] = str(tmp)
            os.environ["AGENT_VERSION"] = "v1"
            try:
                rc = parse_bundle.main()
            finally:
                os.environ.clear()
                os.environ.update(old)
            self.assertEqual(rc, 0)
            parsed = json.loads((tmp / "_bundle_parsed.json").read_text())
            self.assertEqual(parsed["plannerName"], "MyPlanner")
            self.assertEqual(parsed["plannerType"], "Atlas__Reasoning")
            self.assertEqual(parsed["generation"], "nga")
            # _agent_generation.txt is newline-terminated for shell sourcing
            self.assertEqual(
                (tmp / "_agent_generation.txt").read_text(), "nga\n"
            )

    def test_main_returns_one_when_env_missing(self):
        # Both WORK_DIR and AGENT_VERSION required; remove WORK_DIR.
        old = dict(os.environ)
        os.environ.pop("WORK_DIR", None)
        os.environ["AGENT_VERSION"] = "v1"
        try:
            rc = parse_bundle.main()
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertEqual(rc, 1)

    def test_main_emits_empty_skeleton_when_planner_unresolved(self):
        # Bot file has no <conversationDefinitionPlanners> → planner_name == ""
        with TemporaryDirectory() as t:
            tmp = Path(t)
            bots_dir = tmp / "sf_meta" / "wave1_bot" / "unpackaged" / "bots"
            bots_dir.mkdir(parents=True)
            (bots_dir / "MyAgent.bot").write_text(_bot_xml("v1", planner_name=None))
            old = dict(os.environ)
            os.environ["WORK_DIR"] = str(tmp)
            os.environ["AGENT_VERSION"] = "v1"
            try:
                rc = parse_bundle.main()
            finally:
                os.environ.clear()
                os.environ.update(old)
            self.assertEqual(rc, 0)
            parsed = json.loads((tmp / "_bundle_parsed.json").read_text())
            self.assertIsNone(parsed["plannerName"])
            self.assertEqual(parsed["topics"], [])
            self.assertEqual((tmp / "_agent_generation.txt").read_text(), "unknown\n")


if __name__ == "__main__":
    unittest.main()

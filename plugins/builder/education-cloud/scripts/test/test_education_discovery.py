"""Exercise the active public entry using the real discovery runtime."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
SCRIPTS = ROOT / "plugins/builder/salesforce-development/scripts"
sys.path.insert(0, str(SCRIPTS))

class EducationDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "config.yml").is_file():
            raise unittest.SkipTest("requires the authoring repository and internal publication metadata")
        global plugin_catalog, sf_context
        import plugin_catalog
        import sf_context
        cls.candidate = plugin_catalog.build_catalog(ROOT, SCRIPTS.parent)

    def matches(self, prompt, enabled=(), surface="user-prompt"):
        with patch.object(plugin_catalog, "load_catalog", return_value=self.candidate), \
             patch.object(sf_context, "_load_plugin_catalog_module", return_value=plugin_catalog), \
             patch.object(sf_context, "_enabled_plugin_names", return_value=set(enabled)), \
             patch.object(sf_context, "_plugin_match_sensitivity", return_value="standard"), \
             patch.object(sf_context, "_plugin_display_name", return_value="salesforce-development"), \
             patch.object(sf_context, "_load_plugin_proposals", return_value={}), \
             patch.object(sf_context, "_save_plugin_proposals"), \
             patch.object(sf_context, "_fire_plugin_telemetry_event"):
            return sf_context._plugin_catalog_match(prompt, "edu-test", surface)

    def test_public_entry_is_in_checked_catalog_and_publication(self):
        data = plugin_catalog.build_catalog(ROOT, SCRIPTS.parent)
        self.assertIn("education-cloud", {x["name"] for x in data["plugins"]})
        plugin_catalog.check(ROOT, SCRIPTS.parent)
        entry = next(x for x in json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())["plugins"]
                     if x["name"] == "education-cloud")
        self.assertEqual("public", entry["metadata"]["distribution"]["sf-skills"]["visibility"])

    def test_each_curated_example_recommends_education_at_high_confidence(self):
        edu = next(x for x in self.candidate["plugins"] if x["name"] == "education-cloud")
        for prompt in edu["match"]["examplePrompts"]:
            with self.subTest(prompt=prompt):
                result = self.matches(prompt)
                self.assertIn("education-cloud", {x["name"] for x in result})
                scored = plugin_catalog.score_prompt_against_catalog(prompt, self.candidate)
                edu_matches = [m for m in scored if m.plugin["name"] == "education-cloud"]
                self.assertEqual(1, len(edu_matches))
                self.assertEqual("high", edu_matches[0].band)

    def test_original_education_prompts_remain_high_on_both_surfaces(self):
        prompts = [
            "Enable Education Cloud recruitment and admissions domains",
            "Generate an academic calendar with semester terms and sessions",
            "Migrate our course catalog into Education Cloud LearningCourse records",
            "Configure a multi-campus institutional hierarchy with Business Profiles",
            "Set up the Education Cloud Student Recruitment Agent for admissions and campus tours",
            "Migrate university courses into LearningCourse records",
            "Set up student enrollment",
        ]
        for prompt in prompts:
            for surface in ("user-prompt", "discovery-command"):
                with self.subTest(prompt=prompt, surface=surface):
                    edu = [m for m in self.matches(prompt, surface=surface)
                           if m["name"] == "education-cloud"]
                    self.assertEqual(1, len(edu))
                    self.assertEqual("high", edu[0]["band"])

    def test_unrelated_and_generic_overlapping_tasks_do_not_recommend_education(self):
        for surface in ("user-prompt", "session-start", "discovery-command", "bypass-gate"):
            self.assertIn("education-cloud", {x["name"] for x in self.matches(
                "Generate an academic calendar with semester terms and sessions", surface=surface)})
        for prompt in ["Create a custom field", "Plan an office calendar",
                       "Set up B2B commerce catalog", "Create a generic Agentforce service agent",
                       "Configure an employee recruitment agent", "Configure Service Cloud queues",
                       "Set up an office calendar", "Create a company holiday calendar",
                       "Migrate our commerce product catalog",
                       "Set up an employee recruitment agent for hiring",
                       "Create a campus hierarchy for field service territories",
                       "Plan the institutional knowledge article hierarchy",
                       "Show me the academic calendar for my kid's school"]:
            for surface in ("user-prompt", "session-start", "discovery-command", "bypass-gate"):
                with self.subTest(prompt=prompt, surface=surface):
                    self.assertNotIn("education-cloud", {x["name"] for x in self.matches(prompt, surface=surface)})

    def test_commerce_overlap_preserves_commerce_as_top_explicit_match(self):
        result = self.matches("Set up B2B commerce catalog", surface="discovery-command")
        self.assertEqual("commerce-b2b", result[0]["name"])
        self.assertNotIn("education-cloud", {
            x["name"] for x in self.matches("Set up B2B commerce catalog")})

    def test_education_recruitment_and_generic_agentforce_keep_distinct_owners(self):
        prompt = "Set up the Education Cloud Student Recruitment Agent for admissions and campus tours"
        result = self.matches(prompt)
        self.assertIn("education-cloud", {x["name"] for x in result})
        generic = self.matches("Create a generic Agentforce service agent")
        self.assertIn("agentforce-adlc", {x["name"] for x in generic})
        explicit = self.matches(prompt, surface="discovery-command")
        self.assertIn("education-cloud", {x["name"] for x in explicit})

    def test_enabled_plugin_is_suppressed_on_all_surfaces(self):
        prompt = "Generate an academic calendar with semester terms and sessions"
        for surface in ("user-prompt", "session-start", "discovery-command", "bypass-gate"):
            with self.subTest(surface=surface):
                self.assertIn("education-cloud", {x["name"] for x in self.matches(prompt, surface=surface)})
                self.assertNotIn("education-cloud", {
                    x["name"] for x in self.matches(prompt, enabled={"education-cloud"}, surface=surface)})

if __name__ == "__main__":
    unittest.main()

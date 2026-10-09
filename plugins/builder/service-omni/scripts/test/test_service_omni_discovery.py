"""Discovery contracts for the registered Omni-Channel plugin."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
SCRIPTS = ROOT / 'plugins/builder/salesforce-development/scripts'
sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServiceOmniDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load('omni_catalog', SCRIPTS / 'plugin_catalog.py')
        cls.context = load('omni_context', SCRIPTS / 'sf_context.py')
        cls.marketplace = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        cls.entry = next(p for p in cls.marketplace['plugins'] if p['name'] == 'service-omni')
        cls.registered = cls.catalog.build_catalog(ROOT, SCRIPTS.parent)

    def names(self, prompt):
        return {m.plugin['name'] for m in self.catalog.score_prompt_against_catalog(prompt, self.registered) if m.band == 'high'}

    def test_registered_entry_is_in_real_catalog_and_public_distribution(self):
        self.assertEqual(self.entry['metadata']['distribution']['sf-skills']['visibility'], 'public')
        current = self.catalog.build_catalog(ROOT, SCRIPTS.parent)
        self.assertIn('service-omni', [p['name'] for p in current['plugins']])
        self.assertTrue(self.catalog.check(ROOT, SCRIPTS.parent))

    def test_registered_entry_matches_coordinator_routing_and_supervisor_tasks(self):
        for prompt in self.entry['metadata']['match']['examplePrompts']:
            with self.subTest(prompt=prompt):
                self.assertIn('service-omni', self.names(prompt))

    def test_unrelated_tasks_do_not_recommend_omni(self):
        for prompt in ['generate an Apex trigger for Account', 'build a Lightning Web Component',
                       'configure OAuth Named Credentials', 'configure a marketing campaign',
                       'route traffic to my website', 'set up supervisor settings for a Linux process',
                       'show user presence status in Slack']:
            with self.subTest(prompt=prompt):
                self.assertNotIn('service-omni', self.names(prompt))

    def test_voice_call_phrases_recommend_omni(self):
        for prompt in ['route VoiceCall records', 'configure Salesforce voice call routing',
                       'configure Omni voice calls routing', 'route a VoiceCall']:
            with self.subTest(prompt=prompt):
                self.assertIn('service-omni', self.names(prompt))

    def test_ambiguous_settings_and_queues_fail_evidence_on_all_surfaces(self):
        for prompt in ['Omni Studio settings', 'configure Omni Studio settings',
                       'create a Salesforce queue for Leads', 'configure Salesforce queues']:
            for anchors in (True, False):
                with self.subTest(prompt=prompt, anchors=anchors):
                    matches = self.catalog.score_prompt_against_catalog(
                        prompt, self.registered, require_anchor_terms=anchors)
                    self.assertNotIn('service-omni', [m.plugin['name'] for m in matches])

    def test_engagement_and_omni_boundaries(self):
        self.assertNotIn('service-omni', self.names('set up a Salesforce Digital Engagement messaging channel'))
        self.assertIn('service-engagement', self.names('set up a Salesforce Digital Engagement messaging channel'))
        self.assertNotIn('service-engagement', self.names('configure classic Omni Supervisor queues and users'))
        combined = self.names('set up a Salesforce Digital Engagement messaging channel and configure Omni queue routing with presence statuses')
        self.assertIn('service-omni', combined)
        self.assertIn('service-engagement', combined)

    def test_explicit_discovery_preserves_existing_high_confidence_routes(self):
        corpus = {**self.registered, 'plugins': [p for p in self.registered['plugins']
                  if p['name'] != 'salesforce-development']}
        for expected, prompt in [
            ('dx-devops', 'configure a DevOps Center test pipeline'),
            ('service-engagement', 'set up a Salesforce Digital Engagement messaging channel'),
        ]:
            with self.subTest(prompt=prompt):
                matches = self.catalog.score_prompt_against_catalog(
                    prompt, corpus, require_anchor_terms=False)
                self.assertEqual([m.plugin['name'] for m in matches if m.band == 'high'], [expected])

    def test_runtime_suppresses_already_installed_plugin(self):
        context = self.context
        module = types.SimpleNamespace(load_catalog=lambda root: self.registered,
                                       score_prompt_against_catalog=self.catalog.score_prompt_against_catalog)
        with mock.patch.object(context, '_load_plugin_catalog_module', return_value=module), \
             mock.patch.object(context, '_plugin_display_name', return_value='salesforce-development'), \
             mock.patch.object(context, '_plugin_match_sensitivity', return_value='standard'), \
             mock.patch.object(context, '_load_plugin_proposals', return_value={}), \
             mock.patch.object(context, '_save_plugin_proposals'), \
             mock.patch.object(context, '_enabled_plugin_names', return_value=set()):
            before = context._plugin_catalog_match('configure classic Omni Supervisor queues and users', 'omni-test', 'user-prompt')
            self.assertIn('service-omni', [p['name'] for p in before])
            with mock.patch.object(context, '_enabled_plugin_names', return_value={'service-omni'}):
                after = context._plugin_catalog_match('configure classic Omni Supervisor queues and users', 'omni-test', 'user-prompt')
                self.assertNotIn('service-omni', [p['name'] for p in after])


if __name__ == '__main__':
    unittest.main()

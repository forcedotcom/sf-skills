"""Capability evidence regressions through scorer and real proposal consumers.

PRECISION_OTHER_MARKETPLACE optionally adds the other PR's entry to the catalog
for combined validation; default execution validates this PR independently.
"""
import copy
import io
import json
import os
import sys
import tempfile
import unittest
import uuid
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
ROOT = SCRIPTS.parents[3]
TARGETS = {'education-cloud', 'service-omni'}
NEGATIVES = [
    'Write a course syllabus', 'Manage a campus network',
    'Set up an employee training course catalog',
    'Migrate our online course catalog to Shopify',
    'Configure admissions FAQs and campus tours in WordPress',
    'Build an Education Cloud admissions FAQ and campus tour website',
    'Create a generic Agentforce service agent',
    'Create an Agentforce agent for Education Cloud admissions',
    'Configure Kubernetes queue routing', 'Configure RabbitMQ queue routing',
    'Configure skills-based routing in Zendesk',
    'show user presence status in Slack',
    'set up supervisor settings for a Linux process',
    'Set up an employee recruitment agent for hiring',
    'Create a course catalog for our university',
    'Configure university admissions',
    'Omni Studio settings', 'Configure Omni Studio settings',
    'Create a Salesforce queue for Leads', 'Route traffic to my website',
    'Configure Salesforce voice call transcripts',
    'Configure Salesforce storage capacity alerts',
    'Increase Salesforce API capacity', 'Check Salesforce data storage capacity',
    'Configure voice routing in Amazon Connect', 'Set up Twilio voice routing',
    'Route voice traffic through Twilio',
    'Create a campus hierarchy for field service territories',
    'Plan the institutional knowledge article hierarchy',
    "Show me the academic calendar for my kid's school",
    'Route voice calls', 'Please route voice calls',
    'Can you route voice calls?', 'Configure voice call routing',
]
POSITIVES = {
    'education-cloud': [
        'Enable Education Cloud recruitment and admissions domains',
        'Generate an academic calendar with semester terms and sessions',
        'Generate academic sessions and registration windows',
        'Migrate our course catalog into Education Cloud',
        'Configure a multi-campus hierarchy',
        'Migrate our course catalog into Education Cloud LearningCourse records',
        'Configure a multi-campus institutional hierarchy with Business Profiles',
        'Set up the Education Cloud Student Recruitment Agent for admissions and campus tours',
    ],
    'service-omni': [
        'Route VoiceCall records', 'Please route VoiceCall records',
        'Can you route VoiceCall records?', 'Configure Salesforce voice call routing',
        'Configure Omni voice call routing', 'Configure Salesforce work sharing',
        'Configure Salesforce agent capacity', 'Configure Salesforce agents capacity',
        # Agent capacity is capability evidence even without a vendor cue.
        'Configure generic queue routing and agent capacity',
        'Configure Salesforce presence statuses', 'Set up Salesforce routing for chats',
        'Configure Case queue routing', 'Deploy a routing flow for VoiceCall',
        'I need to route Cases to service queues', 'I need to route VoiceCall to a queue',
        'Configure Salesforce queues and agent capacity',
        'Configure skills-based routing for Cases',
        'Configure Salesforce queue routing and agent capacity',
        'Deploy Salesforce presence statuses',
    ],
}


class PluginEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_module(SCRIPTS / 'plugin_catalog.py', 'precision_catalog')
        cls.context = load_module(SCRIPTS / 'sf_context.py', 'precision_context')
        cls.data = cls.catalog.build_catalog(ROOT, SCRIPTS.parent)
        other = os.environ.get('PRECISION_OTHER_MARKETPLACE')
        if other:
            marketplace = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
            existing = {p['name'] for p in marketplace['plugins']}
            marketplace['plugins'] += [p for p in json.loads(Path(other).read_text())['plugins']
                                       if p['name'] in TARGETS and p['name'] not in existing]
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / '.claude-plugin').mkdir()
                (root / '.claude-plugin/marketplace.json').write_text(json.dumps(marketplace))
                (root / 'config.yml').write_text((ROOT / 'config.yml').read_text())
                cls.data = cls.catalog.build_catalog(root, SCRIPTS.parent)
        cls.present = TARGETS & {p['name'] for p in cls.data['plugins']}

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        td = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.project = Path(td)
        (self.project / 'sfdx-project.json').write_text('{"packageDirectories":[]}')
        config = self.project / 'config'
        config.mkdir()
        (config / 'settings.json').write_text('{"enabledPlugins":{"salesforce-development@salesforce":true}}')
        previous = Path.cwd()
        os.chdir(self.project)
        self.addCleanup(os.chdir, previous)
        self.stack.enter_context(patch.dict(os.environ, {
            'CLAUDE_CONFIG_DIR': str(config), 'SF_PLUGIN_MATCH_SENSITIVITY': 'standard',
            'SF_HOOK_UI_MODE': 'full', 'SF_TELEMETRY_DISABLED': '1',
        }))
        c = self.context
        for name, value in [
            ('_load_plugin_catalog_module', self.catalog),
            ('_plugin_display_name', 'salesforce-development'),
            ('_plugin_match_sensitivity', 'standard'),
            ('_load_plugin_flow', None),
            ('_enabled_plugin_names', set()),
        ]:
            self.stack.enter_context(patch.object(c, name, return_value=value))
        self.stack.enter_context(patch.object(c, '_load_plugin_proposals', side_effect=lambda _: {}))
        self.stack.enter_context(patch.object(c, '_entered_this_session', return_value=True))
        self.stack.enter_context(patch.object(c, '_welcomed_this_session', return_value=True))
        for name in ('_save_plugin_proposals', '_open_plugin_flow', '_fire_plugin_telemetry_event'):
            self.stack.enter_context(patch.object(c, name))
        self.stack.enter_context(patch.object(self.catalog, 'load_catalog', return_value=self.data))
        self.stack.enter_context(patch.object(c, '_PROMPT_RUNTIME_DIR', self.project / 'runtime'))

    def score(self, prompt, anchors=True):
        corpus = {**self.data, 'plugins': [p for p in self.data['plugins']
                                         if p['name'] != 'salesforce-development']}
        return self.catalog.score_prompt_against_catalog(prompt, corpus, require_anchor_terms=anchors)

    def surfaced(self, prompt, surface):
        c = self.context
        out = io.StringIO()
        session = 'precision-' + uuid.uuid4().hex
        with redirect_stdout(out):
            if surface == 'user-prompt':
                payload = {'hook_event_name': 'UserPromptSubmit', 'session_id': session,
                           'prompt_id': 'p1', 'prompt': prompt}
                with patch.object(c.sys, 'stdin', io.StringIO(json.dumps(payload))):
                    self.assertEqual(0, c.cmd_prompt_dispatch())
            elif surface == 'discovery-command':
                self.assertEqual(0, c.cmd_plugin_match(['--json', '--session-id', session, prompt]))
            elif surface == 'bypass-gate':
                payload = {'session_id': session, 'tool_name': 'Write',
                           'tool_input': {'file_path': 'example.txt', 'content': 'example'}}
                with patch.object(c.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                     patch.object(c, '_skills_first_match', return_value=None), \
                     patch.object(c, '_prompt_text', return_value=prompt), \
                     patch.object(c, '_recorded_catalog_prompt_eligible', return_value=True):
                    self.assertEqual(0, c.cmd_skills_first_advisory())
            else:
                # SessionStart has file signals rather than free-form user prompts.
                # Feed a controlled query through the actual slot consumer.
                with patch.object(c, '_detect_plugin_signals', return_value=[('agentforce', 'controlled evidence', prompt)]):
                    model, paint = c._session_start_plugin_slot(session, 'startup', self.project)
                out.write(model + paint)
        return out.getvalue()

    def test_negatives_have_neither_high_nor_medium_candidates_and_never_surface(self):
        for prompt in NEGATIVES:
            for anchors in (True, False):
                with self.subTest(prompt=prompt, anchors=anchors):
                    self.assertFalse(TARGETS & {m.plugin['name'] for m in self.score(prompt, anchors)})
            for surface in ('user-prompt', 'session-start', 'discovery-command', 'bypass-gate'):
                with self.subTest(prompt=prompt, surface=surface):
                    output = self.surfaced(prompt, surface)
                    for name in TARGETS:
                        self.assertNotIn(name, output)

    def test_supported_and_curated_requests_pass_action_gate_and_surface(self):
        for name in self.present:
            row = next(p for p in self.data['plugins'] if p['name'] == name)
            for prompt in POSITIVES[name] + row['match']['examplePrompts']:
                with self.subTest(name=name, prompt=prompt):
                    self.assertTrue(self.context._plugin_prompt_requests_action(prompt))
                    self.assertIn(name, {m.plugin['name'] for m in self.score(prompt) if m.band == 'high'})
                for surface in ('user-prompt', 'session-start', 'discovery-command', 'bypass-gate'):
                    with self.subTest(name=name, prompt=prompt, surface=surface):
                        self.assertIn(name, self.surfaced(prompt, surface))

    def test_route_requests_preserve_neighboring_plugin_recommendations(self):
        for name, prompt in [
            ('service-engagement', 'Route Omni-Channel work items to agents'),
            ('experience-lwc', 'route traffic to Experience Cloud LWC site'),
        ]:
            with self.subTest(name=name, prompt=prompt):
                self.assertTrue(self.context._plugin_prompt_requests_action(prompt))
                self.assertIn(name, self.surfaced(prompt, 'user-prompt'))
        for prompt in ['Route settings for Experience Cloud LWC are incorrect',
                       'Route failed for Omni-Channel work items']:
            with self.subTest(prompt=prompt):
                self.assertFalse(self.context._plugin_prompt_requests_action(prompt))
                output = self.surfaced(prompt, 'user-prompt')
                for name in ('service-engagement', 'experience-lwc', 'service-omni'):
                    self.assertNotIn(name, output)

    def test_route_observations_do_not_proactively_surface(self):
        for prompt in ['Route settings for voice calls are incorrect',
                       'Route failed for voice calls']:
            with self.subTest(prompt=prompt):
                self.assertFalse(self.context._plugin_prompt_requests_action(prompt))
                self.assertNotIn('service-omni', self.surfaced(prompt, 'user-prompt'))

    def test_information_only_prompt_scores_but_does_not_proactively_surface(self):
        for name in self.present:
            prompt = 'What is ' + ('an academic calendar with semester terms?' if name == 'education-cloud'
                                   else 'Omni queue routing and presence?')
            self.assertIn(name, {m.plugin['name'] for m in self.score(prompt)})
            self.assertFalse(self.context._plugin_prompt_requests_action(prompt))
            self.assertNotIn(name, self.surfaced(prompt, 'user-prompt'))
            self.assertIn(name, self.surfaced(prompt, 'discovery-command'))

    def test_installed_plugins_suppressed_on_every_surface(self):
        with patch.object(self.context, '_enabled_plugin_names', return_value=self.present):
            for name in self.present:
                for surface in ('user-prompt', 'session-start', 'discovery-command', 'bypass-gate'):
                    self.assertNotIn(name, self.surfaced(POSITIVES[name][0], surface))

    def test_existing_curated_routes_and_session_start_signals(self):
        for name, prompt in [
            ('experience-lwc', 'Build an LWC datatable with wire service and Jest tests'),
            ('experience-react', 'Scaffold a Salesforce React UI bundle with Tailwind and shadcn'),
            ('experience-cms', 'Find an existing Salesforce CMS media asset'),
            ('agentforce-adlc', 'Create a generic Agentforce service agent'),
            ('dx-devops', 'Configure a DevOps Center test pipeline'),
            ('service-engagement', 'Set up a Salesforce Digital Engagement messaging channel'),
            ('commerce-b2b', 'Set up a B2B commerce catalog'),
        ]:
            for surface in ('user-prompt', 'discovery-command', 'bypass-gate'):
                with self.subTest(name=name, surface=surface):
                    out = self.surfaced(prompt, surface)
                    self.assertIn(name, out)
                    for target in TARGETS:
                        self.assertNotIn(target, out)
        for path in ['force-app/main/default/lwc/example/example.js-meta.xml',
                     'ui/example.tsx', 'agents/example.agent',
                     'force-app/main/default/managedContentTypes/example.xml']:
            file = self.project / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('fixture')
        detected = self.context._detect_plugin_signals(self.project)
        self.assertEqual({'lwc','react','agentforce','cms'}, {s[0] for s in detected})
        for _, _, query in detected:
            self.assertFalse(TARGETS & {m.plugin['name'] for m in self.score(query)})
        expected = {'experience-lwc','experience-react','agentforce-adlc','experience-cms'}
        for _, _, query in detected:
            self.assertTrue(expected & {m.plugin['name'] for m in self.score(query) if m.band == 'high'})
        model, paint = self.context._session_start_plugin_slot('precision-signals','startup',self.project)
        for name in expected:
            self.assertIn(name, model + paint)
        for name in TARGETS:
            self.assertNotIn(name, model + paint)

    def test_messaging_setup_and_combined_routing_ownership(self):
        if 'service-omni' not in self.present:
            self.skipTest('Omni is not present in this independent catalog')
        setup = 'Set up a Salesforce Digital Engagement messaging channel'
        combined = setup + ' and configure Omni queue routing with presence statuses'
        for surface in ('user-prompt','session-start','discovery-command','bypass-gate'):
            self.assertNotIn('service-omni', self.surfaced(setup, surface))
            self.assertIn('service-engagement', self.surfaced(setup, surface))
            output = self.surfaced(combined, surface)
            self.assertIn('service-engagement', output)
            self.assertIn('service-omni', output)

    def test_all_curated_routes_keep_the_existing_discovery_confidence_bar(self):
        for row in self.data['plugins']:
            if row['name'] == 'salesforce-development':
                continue
            for prompt in row['match']['examplePrompts']:
                with self.subTest(plugin=row['name'], prompt=prompt):
                    self.assertIn(row['name'], {m.plugin['name'] for m in self.score(prompt, False)
                                               if m.band == 'high'})

    def test_optional_policy_preserves_scores_and_legacy_anchor_bypass(self):
        for row in self.data['plugins']:
            if row['name'] not in self.present:
                self.assertNotIn('enforceAnchorsOnAllSurfaces', row['match'])
        before = copy.deepcopy(self.data)
        for row in before['plugins']:
            row['match'].pop('enforceAnchorsOnAllSurfaces', None)
        for name in self.present:
            prompt = POSITIVES[name][0]
            old = self.catalog.score_prompt_against_catalog(prompt, before, require_anchor_terms=False)
            new = self.catalog.score_prompt_against_catalog(prompt, self.data, require_anchor_terms=False)
            old = {m.plugin['name']: (m.score,m.band) for m in old}
            for m in new:
                self.assertEqual(old[m.plugin['name']], (m.score,m.band))
        row = copy.deepcopy(self.data['plugins'][0])
        row['match'] = {'description':'Unique task vocabulary', 'keywords':['unique'],
                        'examplePrompts':['Create a unique task'], 'anchorTerms':['absent']}
        catalog = {**self.data, 'plugins':[row]}
        self.assertFalse(self.catalog.score_prompt_against_catalog('unique task vocabulary',catalog))
        self.assertTrue(self.catalog.score_prompt_against_catalog('unique task vocabulary',catalog,require_anchor_terms=False))

    def test_policy_validation_build_and_load(self):
        for bad in [None, 0, 1, 'true', 'false', [], {}, ['omni']]:
            with self.subTest(value=bad):
                data = copy.deepcopy(self.data)
                data['plugins'][0]['match']['enforceAnchorsOnAllSurfaces'] = bad
                with self.assertRaises(self.catalog.PluginCatalogError):
                    self.catalog._validate_catalog(data, 'fixture')
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    (root / '.claude-plugin').mkdir()
                    entry = {'name': 'example', 'source': './plugins/example',
                             'description': 'Example capability', 'keywords': ['example'],
                             'metadata': {'match': {'examplePrompts': ['Create an example'],
                                                    'anchorTerms': ['example'],
                                                    'enforceAnchorsOnAllSurfaces': bad}}}
                    (root / '.claude-plugin/marketplace.json').write_text(
                        json.dumps({'name': 'example', 'plugins': [entry]}))
                    (root / 'config.yml').write_text('internalPlugins: []')
                    with self.assertRaises(self.catalog.PluginCatalogError):
                        self.catalog.build_catalog(root, root)
        # Enforcing an absent gate is a configuration error, not silent opt-in.
        data = copy.deepcopy(self.data)
        data['plugins'][0]['match'].pop('anchorTerms', None)
        data['plugins'][0]['match'].pop('anchorCompanions', None)
        data['plugins'][0]['match']['enforceAnchorsOnAllSurfaces'] = True
        with self.assertRaisesRegex(self.catalog.PluginCatalogError, 'requires anchorTerms'):
            self.catalog._validate_catalog(data, 'fixture')
        data['plugins'][0]['match']['enforceAnchorsOnAllSurfaces'] = False
        self.catalog._validate_catalog(data, 'fixture')

    def test_replaced_evidence_field_cannot_be_silently_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / '.claude-plugin').mkdir()
            entry = {'name': 'example', 'source': './plugins/example',
                     'description': 'Example capability', 'keywords': ['example'],
                     'metadata': {'match': {'examplePrompts': ['Create an example'],
                                            'requiredEvidence': [['example']]}}}
            (root / '.claude-plugin/marketplace.json').write_text(
                json.dumps({'name': 'example', 'plugins': [entry]}))
            (root / 'config.yml').write_text('internalPlugins: []')
            with self.assertRaisesRegex(self.catalog.PluginCatalogError, 'uses replaced'):
                self.catalog.build_catalog(root, root)



if __name__ == '__main__':
    unittest.main()

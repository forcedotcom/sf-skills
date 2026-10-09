"""The release verifier rejects mirror drift, unsafe trees, and scope changes."""
import importlib.util
import io
from unittest import mock
import json
import shutil
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[2]
AUTHORING = PLUGIN.parents[2] / 'skills'
spec = importlib.util.spec_from_file_location('omni_release', PLUGIN / 'scripts/verify-public-plugin-release.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class ReleaseVerifierTests(unittest.TestCase):
    def test_real_tree_passes(self):
        self.assertGreater(verifier.verify(PLUGIN, AUTHORING)['files'], 24)

    def test_source_pre_copy_check_keeps_sor_and_full_parity(self):
        # release-to-public.yml runs this from the public checkout with relative
        # paths, pointing --plugin-root at the SOURCE plugin plus --public-root.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            plugin = repo / 'plugins/builder/service-omni'
            shutil.copytree(PLUGIN, plugin)
            shutil.copytree(AUTHORING, repo / 'skills')
            (repo / 'sf-skills/skills').mkdir(parents=True)
            command = [sys.executable, str(PLUGIN / 'scripts/verify-public-plugin-release.py'),
                       '--plugin-root', '../plugins/builder/service-omni',
                       '--authoring-root', '../skills', '--public-root', 'skills']
            run = lambda: subprocess.run(command, cwd=repo / 'sf-skills', capture_output=True, text=True)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            # Source mirror drift must still fail in this mode.
            drifted = plugin / 'skills/service-omni-base-settings-configure/SKILL.md'
            drifted.write_text(drifted.read_text(encoding='utf-8') + '\n', encoding='utf-8')
            result = run()
            self.assertEqual(result.returncode, 1)
            self.assertIn('byte or mode mismatch', result.stderr)

    def test_public_copy_passes_before_and_after_real_sanitization(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / 'service-omni'
            shutil.copytree(PLUGIN, plugin)
            # The release workflow strips SoR before checking the destination.
            for sidecar in plugin.rglob('sor.yaml'):
                sidecar.unlink()
            command = [sys.executable, str(PLUGIN / 'scripts/verify-public-plugin-release.py'),
                       '--plugin-root', str(plugin), '--authoring-root', str(AUTHORING),
                       '--public-root', str(Path(tmp) / 'skills')]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            # Untouched files on subsequent releases have already been sanitized.
            sanitizer = AUTHORING.parent / 'scripts/release-ci/sanitize-public-skills.mjs'
            subprocess.run(['node', str(sanitizer),
                            *map(str, plugin.glob('skills/*/SKILL.md'))],
                           check=True, capture_output=True, text=True)
            later = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(later.returncode, 0, later.stderr)
            # Sanitized destinations must still fail canonical SOURCE parity.
            with self.assertRaises(verifier.ReleaseGateError):
                verifier.verify(plugin, AUTHORING)
            skill = plugin / 'skills/service-omni-base-settings-configure'
            (skill / 'sor.yaml').write_text('internal', encoding='utf-8')
            with self.assertRaisesRegex(verifier.ReleaseGateError, 'sor.yaml'):
                verifier.verify(plugin, AUTHORING, Path(tmp) / 'skills')
            (skill / 'sor.yaml').unlink()
            (skill / 'SKILL.md').unlink()
            with self.assertRaisesRegex(verifier.ReleaseGateError, 'missing SKILL.md'):
                verifier.verify(plugin, AUTHORING, Path(tmp) / 'skills')

    def test_unquoted_public_visibility_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / 'service-omni'
            authoring = Path(tmp) / 'authoring'
            shutil.copytree(PLUGIN, plugin)
            shutil.copytree(PLUGIN / 'skills', authoring)
            for root in (plugin / 'skills', authoring):
                path = root / 'service-omni-base-settings-configure/SKILL.md'
                path.write_text(path.read_text(encoding='utf-8').replace(
                    'visibility: "public"', 'visibility: public'), encoding='utf-8')
            self.assertGreater(verifier.verify(plugin, authoring)['files'], 0)

    def test_invalid_inputs_fail_cleanly(self):
        for mutation in ('roster-json', 'roster-encoding', 'manifest-shape',
                         'frontmatter-missing', 'frontmatter-unclosed', 'skill-encoding'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                plugin = Path(tmp) / 'service-omni'
                authoring = Path(tmp) / 'authoring'
                shutil.copytree(PLUGIN, plugin)
                shutil.copytree(PLUGIN / 'skills', authoring)
                if mutation.startswith('roster'):
                    path = plugin / 'scripts/skill-roster.json'
                    path.write_bytes(b'{' if mutation == 'roster-json' else b'\xff')
                elif mutation == 'manifest-shape':
                    (plugin / '.claude-plugin/plugin.json').write_text('[]', encoding='utf-8')
                else:
                    path = authoring / 'service-omni-base-settings-configure/SKILL.md'
                    contents = {'frontmatter-missing': b'no header',
                                'frontmatter-unclosed': b'---\nname: test\n',
                                'skill-encoding': b'\xff'}
                    path.write_bytes(contents[mutation])
                with mock.patch('sys.stderr', new_callable=io.StringIO) as stderr:
                    result = verifier.main(['--plugin-root', str(plugin),
                                            '--authoring-root', str(authoring)])
                self.assertEqual(result, 1)
                self.assertIn('public plugin release gate failed:', stderr.getvalue())
                self.assertNotIn('Traceback', stderr.getvalue())

    def test_rejects_release_tree_mutations(self):
        for mutation in ('missing', 'extra', 'bytes', 'mode', 'symlink', 'transient', 'identity'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                plugin = Path(tmp) / 'service-omni'
                shutil.copytree(PLUGIN, plugin)
                skill = plugin / 'skills/service-omni-base-settings-configure'
                if mutation == 'missing':
                    shutil.rmtree(skill)
                elif mutation == 'extra':
                    (plugin / 'skills/unapproved-skill').mkdir()
                elif mutation == 'bytes':
                    (skill / 'SKILL.md').write_text('modified', encoding='utf-8')
                elif mutation == 'mode':
                    p = skill / 'SKILL.md'
                    p.chmod(p.stat().st_mode ^ 0o100)
                elif mutation == 'symlink':
                    (plugin / 'leak').symlink_to(AUTHORING)
                elif mutation == 'transient':
                    (plugin / '__pycache__').mkdir()
                elif mutation == 'identity':
                    p = plugin / '.claude-plugin/plugin.json'
                    data = json.loads(p.read_text(encoding="utf-8"))
                    data['name'] = 'another-plugin'
                    p.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(verifier.ReleaseGateError):
                    verifier.verify(plugin, AUTHORING)


if __name__ == '__main__':
    unittest.main()

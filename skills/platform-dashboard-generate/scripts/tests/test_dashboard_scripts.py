#!/usr/bin/env python3
"""Contract tests for the three dashboard scripts. Standard library only; no org needed.

Run: python3 scripts/tests/test_dashboard_scripts.py
verify_dashboard.py runs against a fake `sf` on PATH, so nothing reaches a real org.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True  # leave no __pycache__ in the skill folder

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(SKILL, "scripts")
EXAMPLE = os.path.join(SKILL, "examples", "dashboards", "Sales_Dashboards", "Sales_Pipeline.dashboard-meta.xml")
REPORTS = os.path.join(SKILL, "examples", "reports")

sys.path.insert(0, SCRIPTS)
import rich_text  # noqa: E402


def run(script, args, stdin=None, env=None):
    p = subprocess.run([sys.executable, "-B", os.path.join(SCRIPTS, script), *args], input=stdin,
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def mutated_example(old, new):
    """Copy the example dashboard with one change; returns its path inside a temp dir."""
    text = open(EXAMPLE, encoding="utf-8").read()
    assert old in text, old
    d = tempfile.mkdtemp()
    path = os.path.join(d, "Broken.dashboard-meta.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new, 1))
    return path


class RichTextTests(unittest.TestCase):
    def test_encode_from_stdin_round_trips(self):
        spec = [{"text": "Pipeline overview", "size": "24px", "bold": True}, {"text": "Source: Opportunities"}]
        code, out, err = run("rich_text.py", ["encode", "-"], stdin=json.dumps(spec))
        self.assertEqual(code, 0, err)
        stored = ET.fromstring("<x>" + out.strip() + "</x>").text  # undo the XML layer, as a deploy does
        delta = rich_text.decode_stored(stored)
        errs, _ = rich_text.validate_delta(delta)
        self.assertEqual(errs, [])
        self.assertEqual("".join(op["insert"] for op in delta), "Pipeline overview\nSource: Opportunities\n")

    def test_unknown_key_is_refused(self):
        code, out, err = run("rich_text.py", ["encode", "-"], stdin='[{"text": "x", "fontSize": "20px"}]')
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")

    def test_javascript_link_is_refused(self):
        code, _, err = run("rich_text.py", ["encode", "-"], stdin='[{"text": "x", "link": "javascript:alert(1)"}]')
        self.assertEqual(code, 2, err)

    def test_example_text_widget_checks_clean(self):
        code, _, err = run("rich_text.py", ["check", EXAMPLE])
        self.assertEqual(code, 0, err)


class ValidateTests(unittest.TestCase):
    def test_example_is_valid_against_its_reports(self):
        code, out, err = run("validate_dashboard.py", [EXAMPLE, "--reports", REPORTS, "--json"])
        self.assertEqual(code, 0, out + err)
        doc = json.loads(out)
        self.assertTrue(doc["ok"])
        self.assertTrue(doc["checkedAgainstReports"])
        self.assertEqual(len(doc["files"]), 1)

    def test_invented_element_fails(self):
        path = mutated_example("<dashboardGridLayout>", "<gridLayout>")
        text = open(path, encoding="utf-8").read().replace("</dashboardGridLayout>", "</gridLayout>", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, out, err = run("validate_dashboard.py", [path])
        self.assertEqual(code, 1, out + err)
        self.assertIn("gridLayout", out + err)

    def test_html_text_widget_fails(self):
        text = open(EXAMPLE, encoding="utf-8").read()
        start = text.index("<richTextContent>") + len("<richTextContent>")
        end = text.index("</richTextContent>")
        path = mutated_example(text[start:end], "&lt;b&gt;Pipeline&lt;/b&gt;")
        code, out, err = run("validate_dashboard.py", [path])
        self.assertEqual(code, 1, out + err)
        self.assertIn("blank", out + err)

    def test_missing_file_is_an_invalid_call(self):
        code, _, err = run("validate_dashboard.py", [os.path.join(tempfile.gettempdir(), "no-such.dashboard-meta.xml")])
        self.assertEqual(code, 2, err)


class FakeSf:
    """Puts an `sf` on PATH that records its arguments and fails like an unreachable org."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp()
        self.log = os.path.join(self.dir, "calls.log")
        sf = os.path.join(self.dir, "sf")
        with open(sf, "w") as f:
            f.write('#!/bin/sh\necho "$@" >> "%s"\necho \'{"status": 1, "message": "fake org"}\'\nexit 1\n' % self.log)
        os.chmod(sf, 0o755)
        self.env = dict(os.environ, PATH=self.dir + os.pathsep + os.environ.get("PATH", ""))
        return self

    def calls(self):
        return open(self.log).read() if os.path.exists(self.log) else ""

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)


class VerifyTests(unittest.TestCase):
    def test_contradictory_flags_are_refused_before_any_sf_call(self):
        with FakeSf() as fake:
            code, _, err = run("verify_dashboard.py", ["-o", "dev", "Folder/Dash", "--no-refresh",
                                                       "--allow-production-refresh"], env=fake.env)
            self.assertEqual(code, 2, err)
            self.assertEqual(fake.calls(), "")

    def test_org_with_shell_characters_is_refused(self):
        with FakeSf() as fake:
            code, _, err = run("verify_dashboard.py", ["-o", "dev;rm -rf ~", "Folder/Dash"], env=fake.env)
            self.assertEqual(code, 2, err)
            self.assertEqual(fake.calls(), "")

    def test_abbreviated_option_is_refused(self):
        with FakeSf() as fake:
            code, _, err = run("verify_dashboard.py", ["-o", "dev", "Folder/Dash", "--allow-production"], env=fake.env)
            self.assertEqual(code, 2, err)
            self.assertEqual(fake.calls(), "")

    def test_org_failure_is_exit_3_not_a_dashboard_problem(self):
        with FakeSf() as fake:
            code, _, err = run("verify_dashboard.py", ["-o", "dev", "Folder/Dash", "--api", "66.0"], env=fake.env)
            self.assertEqual(code, 3, err)
            self.assertNotEqual(fake.calls(), "")


class CrashTests(unittest.TestCase):
    def test_a_crash_exits_3_in_every_script(self):
        for script in ("rich_text.py", "validate_dashboard.py", "verify_dashboard.py"):
            path = os.path.join(SCRIPTS, script)
            src = open(path, encoding="utf-8").read().replace(
                'if __name__ == "__main__":', 'def main(*a, **k):\n    raise RuntimeError("boom")\n\nif __name__ == "__main__":', 1)
            code = ("import sys; sys.dont_write_bytecode = True; sys.argv = [%r]; "
                    "exec(compile(%r, %r, 'exec'), {'__name__': '__main__', '__file__': %r})" % (path, src, path, path))
            p = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
            with self.subTest(script=script):
                self.assertEqual(p.returncode, 3, p.stderr)
                self.assertIn("INTERNAL ERROR", p.stderr)


class XmlSafetyTests(unittest.TestCase):
    BOMB = ('<?xml version="1.0" encoding="{enc}"?>\n<!DOCTYPE d [<!ENTITY a "aaaaaaaaaa">'
            '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>\n'
            '<Dashboard xmlns="http://soap.sforce.com/2006/04/metadata"><title>&b;</title></Dashboard>\n')

    def write(self, text, encoding):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "Bomb.dashboard-meta.xml")
        with open(path, "w", encoding=encoding) as f:
            f.write(text)
        return path

    def test_entity_declarations_are_refused_in_utf8_and_utf16(self):
        for enc in ("UTF-8", "UTF-16"):
            path = self.write(self.BOMB.format(enc=enc), enc.lower())
            for script, args in (("validate_dashboard.py", [path]), ("rich_text.py", ["check", path])):
                with self.subTest(encoding=enc, script=script):
                    code, out, err = run(script, args)
                    self.assertIn(code, (1, 2), out + err)
                    self.assertRegex(out + err, "DOCTYPE|UTF-8")
                    self.assertNotIn("aaaaaaaaaa", out + err)


class NoLeftoversTest(unittest.TestCase):
    def test_no_bytecode_in_the_skill_folder(self):
        run("validate_dashboard.py", [EXAMPLE])
        found = [r for r, dirs, _ in os.walk(SKILL) if "__pycache__" in dirs]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

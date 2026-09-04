"""Unit tests for validate-policy-tree.py.

Pure, deterministic cap/name checks on a DsarPolicy tree JSON — unit tested here
rather than via evals (evals score the LLM-authored artifact against a gold; they
do not assert the validator's fail-closed behavior).

The filename has hyphens, so it is loaded by path via importlib rather than a
normal import.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "validate-policy-tree.py"
_spec = importlib.util.spec_from_file_location("validate_policy_tree", _SCRIPT)
vpt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vpt)


def _root(name="ContactRoot", **over):
    node = {"developerName": name, "object": "Contact", "fields": ["Email"], "children": []}
    node.update(over)
    return node


def _tree(dev="CustomerPortability", roots=None):
    return {"developerName": dev, "roots": roots if roots is not None else [_root()]}


class NameValidationTests(unittest.TestCase):
    def test_plain_name_ok(self):
        vpt.check_name("ContactRoot", "where")  # does not raise

    def test_trailing_newline_rejected(self):
        # Regression: ^...$ with .match() accepted "Foo\n" because $ matches
        # before a final newline. \A...\Z must reject it.
        with self.assertRaises(vpt.TreeError):
            vpt.check_name("ContactRoot\n", "where")

    def test_embedded_newline_rejected(self):
        with self.assertRaises(vpt.TreeError):
            vpt.check_name("Contact\nRoot", "where")

    def test_leading_digit_rejected(self):
        with self.assertRaises(vpt.TreeError):
            vpt.check_name("1Contact", "where")

    def test_empty_or_nonstring_rejected(self):
        with self.assertRaises(vpt.TreeError):
            vpt.check_name("", "where")
        with self.assertRaises(vpt.TreeError):
            vpt.check_name(None, "where")


class TreeValidationTests(unittest.TestCase):
    def test_minimal_valid_tree(self):
        self.assertEqual(vpt.validate(_tree()), 1)

    def test_trailing_newline_devname_fails_end_to_end(self):
        with self.assertRaises(vpt.TreeError):
            vpt.validate(_tree(roots=[_root(name="ContactRoot\n")]))

    def test_too_many_children_rejected(self):
        kids = [_root(name=f"Child{i}") for i in range(vpt.MAX_CHILDREN + 1)]
        with self.assertRaises(vpt.TreeError):
            vpt.validate(_tree(roots=[_root(children=kids)]))

    def test_empty_roots_rejected(self):
        with self.assertRaises(vpt.TreeError):
            vpt.validate(_tree(roots=[]))


if __name__ == "__main__":
    unittest.main()

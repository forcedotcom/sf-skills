"""Tests for resolve_invocation_target.resolve_target_id never raises,
and `resolve_or_unresolved` records unknown prefixes + invalid shapes into
`_unresolved[]` so the wave orchestrator can keep running when Salesforce
ships a new NGA target type.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401

import resolve_invocation_target as rit  # type: ignore


# A valid-shape Salesforce Id is 15 or 18 alphanumeric chars. Prefixes below
# are chosen to avoid collision with _PREFIX_MAP so they exercise the
# "unknown prefix" path.
_APEX_ID_15 = "01p0000000ABC12"
_APEX_ID_18 = "01p0000000ABC12AAA"
_FLOW_DEF_ID_15 = "3000000000XYZ99"
_FLOW_VER_ID_15 = "3010000000XYZ99"
_PROMPT_ID_15 = "0hf0000000QRS77"
_UNKNOWN_PREFIX_ID_15 = "0aN000000000XYZ"


class KnownPrefixTests(unittest.TestCase):
    def test_apex_prefix(self):
        self.assertEqual(rit.resolve_target_id(_APEX_ID_15), ("apex", "tooling_soql"))

    def test_flow_definition_prefix(self):
        self.assertEqual(
            rit.resolve_target_id(_FLOW_DEF_ID_15),
            ("flow_definition", "tooling_soql"),
        )

    def test_flow_version_prefix(self):
        self.assertEqual(
            rit.resolve_target_id(_FLOW_VER_ID_15),
            ("flow_version", "tooling_soql"),
        )

    def test_prompt_template_prefix(self):
        self.assertEqual(
            rit.resolve_target_id(_PROMPT_ID_15),
            ("prompt_template", "retrieve_required"),
        )

    def test_eighteen_char_id_works(self):
        self.assertEqual(
            rit.resolve_target_id(_APEX_ID_18),
            ("apex", "tooling_soql"),
        )


class UnknownPrefixTests(unittest.TestCase):
    def test_resolve_target_id_never_raises(self):
        # Unknown prefix → ("unknown", "skip"), no exception.
        self.assertEqual(
            rit.resolve_target_id(_UNKNOWN_PREFIX_ID_15),
            ("unknown", "skip"),
        )

    def test_resolve_or_unresolved_records_unknown_prefix(self):
        unresolved: list[dict] = []
        result = rit.resolve_or_unresolved(_UNKNOWN_PREFIX_ID_15, unresolved)
        self.assertEqual(result, ("unknown", "skip"))
        self.assertEqual(len(unresolved), 1)
        entry = unresolved[0]
        self.assertEqual(entry["id"], _UNKNOWN_PREFIX_ID_15)
        self.assertEqual(entry["reason"], "unknown-id-prefix:0aN")

    def test_known_prefix_does_not_touch_unresolved(self):
        unresolved: list[dict] = []
        result = rit.resolve_or_unresolved(_APEX_ID_15, unresolved)
        self.assertEqual(result, ("apex", "tooling_soql"))
        self.assertEqual(unresolved, [])


class InvalidShapeTests(unittest.TestCase):
    def test_empty_string(self):
        unresolved: list[dict] = []
        result = rit.resolve_or_unresolved("", unresolved)
        self.assertEqual(result, ("unknown", "skip"))
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], "invalid-id-format")
        self.assertEqual(unresolved[0]["id"], "")

    def test_none_coerced_via_str(self):
        unresolved: list[dict] = []
        result = rit.resolve_or_unresolved(None, unresolved)
        self.assertEqual(result, ("unknown", "skip"))
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], "invalid-id-format")
        self.assertEqual(unresolved[0]["id"], "None")

    def test_wrong_length_is_invalid(self):
        # A 10-char id-like string is not 15 or 18 — invalid shape, not
        # an unknown prefix.
        unresolved: list[dict] = []
        rit.resolve_or_unresolved("01pABC1234", unresolved)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], "invalid-id-format")

    def test_bad_chars_rejected(self):
        # 15-char length but contains punctuation — not an Id shape.
        unresolved: list[dict] = []
        rit.resolve_or_unresolved("01p!!!!!!!!!!99", unresolved)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], "invalid-id-format")

    def test_short_string_is_invalid(self):
        unresolved: list[dict] = []
        rit.resolve_or_unresolved("ab", unresolved)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], "invalid-id-format")


class RegisteredPrefixesTests(unittest.TestCase):
    def test_exact_membership(self):
        self.assertEqual(
            rit.REGISTERED_PREFIXES,
            frozenset({"01p", "300", "301", "0hf"}),
        )

    def test_is_frozenset(self):
        """Immutable so callers can't accidentally corrupt the table."""
        self.assertIsInstance(rit.REGISTERED_PREFIXES, frozenset)


class ResolveTargetIdRobustnessTests(unittest.TestCase):
    """`resolve_target_id` is the lower-level helper — it must also never
    raise, even on garbage input."""

    def test_none_input(self):
        self.assertEqual(rit.resolve_target_id(None), ("unknown", "skip"))  # type: ignore[arg-type]

    def test_empty_string(self):
        self.assertEqual(rit.resolve_target_id(""), ("unknown", "skip"))

    def test_too_short(self):
        self.assertEqual(rit.resolve_target_id("ab"), ("unknown", "skip"))


if __name__ == "__main__":
    unittest.main()

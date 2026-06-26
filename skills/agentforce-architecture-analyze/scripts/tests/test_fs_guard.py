"""Tests for fs_guard Python-importable validators + api_version check."""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401

from config import fs_guard  # type: ignore — re-exported from _shared/


class ValidateApiNameTests(unittest.TestCase):
    def test_valid_name_passes(self):
        fs_guard.validate_api_name("MyAgent", label="name")
        fs_guard.validate_api_name("Foo_v2", label="name")
        fs_guard.validate_api_name("x", label="name")

    def test_dotdot_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name("..", label="agent_api_name")

    def test_slash_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name("foo/bar", label="agent_api_name")

    def test_dotdot_in_path_segment_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name("foo/../bar", label="agent_api_name")

    def test_null_byte_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name("foo\x00bar", label="name")

    def test_empty_string_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name("", label="name")

    def test_none_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name(None, label="name")

    def test_non_string_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_name(42, label="name")

    def test_validation_error_carries_label(self):
        with self.assertRaises(fs_guard.ValidationError) as ctx:
            fs_guard.validate_api_name("bad/name", label="agent_api_name")
        self.assertEqual(ctx.exception.label, "agent_api_name")


class ValidateApiVersionTests(unittest.TestCase):
    def test_v60_0_ok(self):
        fs_guard.validate_api_version("v60.0", label="api_version")

    def test_v66_0_ok(self):
        fs_guard.validate_api_version("v66.0", label="api_version")

    def test_v60_no_minor_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_version("v60", label="api_version")

    def test_bare_number_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_version("60.0", label="api_version")

    def test_slash_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_version("v60.0/../", label="api_version")

    def test_dotdot_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_version("..", label="api_version")

    def test_empty_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_api_version("", label="api_version")


class ValidateOrgId15Tests(unittest.TestCase):
    def test_valid_15_char_alnum_ok(self):
        fs_guard.validate_org_id_15("00Dxx0000000000", label="org_id_15")

    def test_slash_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_org_id_15("00D/x0000000000", label="org_id_15")

    def test_wrong_length_rejected(self):
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_org_id_15("00Dxx000000000", label="org_id_15")
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_org_id_15("00Dxx0000000000X", label="org_id_15")

    def test_underscore_rejected(self):
        # ORG_ID_15_RE forbids underscores — stricter than api_name.
        with self.assertRaises(fs_guard.ValidationError):
            fs_guard.validate_org_id_15("00Dxx00000000_0", label="org_id_15")


class CliApiVersionCheckTests(unittest.TestCase):
    """The api_version check type is registered in VALID_CHECKS + CHECKS."""

    def test_registered_in_valid_checks(self):
        self.assertIn("api_version", fs_guard.VALID_CHECKS)

    def test_registered_in_checks_dispatch(self):
        self.assertIn("api_version", fs_guard.CHECKS)

    def test_check_function_exists(self):
        self.assertTrue(callable(fs_guard.check_api_version))


if __name__ == "__main__":
    unittest.main()

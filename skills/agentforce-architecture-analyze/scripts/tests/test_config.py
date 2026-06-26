"""Tests for config path builders validate every component."""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401

import config  # type: ignore
from config import fs_guard  # type: ignore — re-exported from _shared/


class BuildAgentDataDirTests(unittest.TestCase):
    def test_valid_inputs_produce_expected_path(self):
        p = config.build_agent_data_dir(
            org_id_15="00Dxx0000000000",
            agent_api_name="MyAgent",
            agent_version="v5",
        )
        self.assertEqual(p.name, "MyAgent__v5")
        self.assertEqual(p.parent.name, "00Dxx0000000000")
        # Full path must be under DATA_ROOT.
        self.assertTrue(str(p).startswith(str(config.DATA_ROOT)))

    def test_dotdot_in_agent_api_name_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_agent_data_dir(
                org_id_15="00Dxx0000000000",
                agent_api_name="..",
                agent_version="v5",
            )

    def test_slash_in_agent_api_name_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_agent_data_dir(
                org_id_15="00Dxx0000000000",
                agent_api_name="foo/bar",
                agent_version="v5",
            )

    def test_slash_in_org_id_15_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_agent_data_dir(
                org_id_15="00D/x0000000000",
                agent_api_name="MyAgent",
                agent_version="v5",
            )

    def test_dotdot_in_agent_version_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_agent_data_dir(
                org_id_15="00Dxx0000000000",
                agent_api_name="MyAgent",
                agent_version="..",
            )


class BuildAgentCacheDirTests(unittest.TestCase):
    def test_valid_inputs_produce_expected_path(self):
        p = config.build_agent_cache_dir(
            org_id_15="00Dxx0000000000",
            agent_api_name="MyAgent",
            agent_version="v5",
        )
        self.assertEqual(p.name, "MyAgent__v5")
        self.assertTrue(str(p).startswith(str(config.CACHE_ROOT)))

    def test_slash_in_any_component_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_agent_cache_dir(
                org_id_15="00Dxx0000000000",
                agent_api_name="foo/bar",
                agent_version="v5",
            )


class BuildProbeCacheDirTests(unittest.TestCase):
    def test_valid_api_version_ok(self):
        p = config.build_probe_cache_dir(
            org_id_15="00Dxx0000000000",
            api_version="v60.0",
        )
        self.assertEqual(p.name, "v60.0")
        self.assertTrue(str(p).startswith(str(config.PROBE_CACHE_ROOT)))

    def test_v60_no_minor_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_probe_cache_dir(
                org_id_15="00Dxx0000000000",
                api_version="v60",
            )

    def test_api_version_with_slash_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_probe_cache_dir(
                org_id_15="00Dxx0000000000",
                api_version="v60.0/../",
            )

    def test_api_version_dotdot_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_probe_cache_dir(
                org_id_15="00Dxx0000000000",
                api_version="..",
            )

    def test_slash_in_org_id_raises(self):
        with self.assertRaises(fs_guard.ValidationError):
            config.build_probe_cache_dir(
                org_id_15="00D/x0000000000",
                api_version="v60.0",
            )


if __name__ == "__main__":
    unittest.main()

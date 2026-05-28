"""Tests for ``resolve_session.main`` CLI.

Argparse-driven — exercises every branch:
- UUID pass-through
- --disk-only hit / miss
- live path with --org
- disk-first fallback when no --org
- not-found-no-org error
"""
from __future__ import annotations

import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import resolve_session  # type: ignore
from .fixtures.synthetic_session import IDS, write_to_disk  # type: ignore


class _MainHarness:
    """Patch sys.argv + stdout/stderr; optionally plant the synthetic
    fixture under DATA_ROOT for disk-resolution tests."""

    def __init__(self, *, argv: list[str], plant_fixture: bool = False):
        self.argv = argv
        self.plant_fixture = plant_fixture

    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self._tmpdir = Path(self._tmp.name)
        if self.plant_fixture:
            write_to_disk(self._tmpdir)
        self._patches = [
            mock.patch.object(resolve_session.sys, "argv",
                              ["resolve_session.py", *self.argv]),
            mock.patch.object(resolve_session, "DATA_ROOT", self._tmpdir),
        ]
        for p in self._patches:
            p.start()
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self._stdout_patch = mock.patch("sys.stdout", self.stdout)
        self._stderr_patch = mock.patch("sys.stderr", self.stderr)
        self._stdout_patch.start()
        self._stderr_patch.start()
        return self

    def __exit__(self, *exc):
        self._stderr_patch.stop()
        self._stdout_patch.stop()
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()


# -----------------------------------------------------------------------------
# UUID pass-through
# -----------------------------------------------------------------------------


class UuidPassThroughTests(unittest.TestCase):

    def test_uuid_input_prints_unchanged_returns_zero(self):
        with _MainHarness(argv=["--id", IDS.SID]) as h:
            rc = resolve_session.main()
        self.assertEqual(rc, 0)
        self.assertIn(IDS.SID, h.stdout.getvalue())


# -----------------------------------------------------------------------------
# --disk-only branch
# -----------------------------------------------------------------------------


class DiskOnlyBranchTests(unittest.TestCase):

    def test_disk_only_hit_prints_uuid(self):
        with _MainHarness(
            argv=["--id", "0MwTESTMSG12345AAA", "--disk-only"],
            plant_fixture=True,
        ) as h:
            rc = resolve_session.main()
        self.assertEqual(rc, 0)
        self.assertIn(IDS.SID, h.stdout.getvalue())

    def test_disk_only_miss_returns_one(self):
        with _MainHarness(
            argv=["--id", "0Mw000000000000", "--disk-only"],
            plant_fixture=True,
        ) as h:
            rc = resolve_session.main()
        self.assertEqual(rc, 1)
        self.assertIn("no local session dir matches", h.stderr.getvalue())


# -----------------------------------------------------------------------------
# Live path with --org
# -----------------------------------------------------------------------------


class LiveOrgPathTests(unittest.TestCase):

    def test_live_path_returns_uuid_from_resolver(self):
        with _MainHarness(
            argv=["--id", "0MwTESTMSG12345AAA", "--org", "my-org"],
        ) as h:
            with mock.patch.object(
                resolve_session, "resolve", return_value="resolved-uuid",
            ) as r:
                rc = resolve_session.main()
            r.assert_called_once_with("0MwTESTMSG12345AAA", org="my-org")
        self.assertEqual(rc, 0)
        self.assertIn("resolved-uuid", h.stdout.getvalue())


# -----------------------------------------------------------------------------
# Disk-first convenience fallback
# -----------------------------------------------------------------------------


class DiskFirstFallbackTests(unittest.TestCase):

    def test_disk_hit_when_no_org_supplied(self):
        # No --org but disk resolution succeeds via fixture.
        with _MainHarness(
            argv=["--id", "0MwTESTMSG12345AAA"],
            plant_fixture=True,
        ) as h:
            rc = resolve_session.main()
        self.assertEqual(rc, 0)
        self.assertIn(IDS.SID, h.stdout.getvalue())

    def test_disk_miss_no_org_returns_two_with_hint(self):
        # No --org AND disk miss → exit 2 + helpful stderr.
        with _MainHarness(
            argv=["--id", "0Mw000000000000"],
        ) as h:
            rc = resolve_session.main()
        self.assertEqual(rc, 2)
        self.assertIn("not found on disk", h.stderr.getvalue())
        self.assertIn("--org <alias> required", h.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

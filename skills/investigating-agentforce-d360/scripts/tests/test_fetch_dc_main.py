"""Tests for ``fetch_dc.main`` orchestration.

Drives the CLI via ``argv`` patching. Mocks at three boundaries so we
exercise the orchestration without spawning real DC/HTTP/sf-CLI work:

- ``preflight_dc_access``           returns (url, token) or raises DcAccessDenied
- ``_run_waterfall``                stubbed; mutates ctx the way the real waterfall would
- ``assemble_dc.main_for_session``  patched to no-op
- ``render_dc.main_for_session``    patched to no-op
"""
from __future__ import annotations

import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import fetch_dc  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import IDS, write_to_disk  # type: ignore


def _fake_waterfall(ctx: dict) -> None:
    """Mutate ctx the way the real waterfall would: stamp identity +
    append a few query entries. Keeps `_write_manifest` happy."""
    ctx["org_id_15"] = IDS.ORG_ID_15
    ctx["agent_api_name"] = IDS.AGENT_API
    ctx["agent_version"] = IDS.AGENT_VERSION
    ctx["session_shape"] = "complete"
    ctx["queries"].append({
        "name": "sessions", "wave": 1, "rows": 1,
        "elapsed_ms": 50, "status": "ok",
    })
    ctx["queries"].append({
        "name": "interactions", "wave": 1, "rows": 3,
        "elapsed_ms": 60, "status": "ok",
    })


class _MainHarness:
    """Patch DATA_ROOT + the 4 boundary functions so main() runs offline."""

    def __init__(self, *, raise_dc_access_denied=None,
                 is_tty: bool = False):
        self.raise_dc_access_denied = raise_dc_access_denied
        self.is_tty = is_tty

    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self._tmpdir = Path(self._tmp.name)
        # Pre-create the session dir so _write_manifest's mkdir works
        # without surprises.
        write_to_disk(self._tmpdir)
        if self.raise_dc_access_denied is not None:
            preflight_mock = mock.patch.object(
                fetch_dc, "preflight_dc_access",
                side_effect=self.raise_dc_access_denied,
            )
        else:
            preflight_mock = mock.patch.object(
                fetch_dc, "preflight_dc_access",
                return_value=("https://example.salesforce.com", "TOKEN"),
            )
        self._patches = [
            mock.patch.object(paths, "DATA_ROOT", self._tmpdir),
            preflight_mock,
            mock.patch.object(fetch_dc, "_run_waterfall",
                              side_effect=_fake_waterfall),
            mock.patch("assemble_dc.main_for_session", return_value=0),
            mock.patch("render_dc.main_for_session", return_value=0),
            mock.patch.object(fetch_dc.sys.stdin, "isatty",
                              return_value=self.is_tty),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------


class MainHappyPathTests(unittest.TestCase):

    def test_main_returns_zero_with_no_assemble_no_render(self):
        with _MainHarness():
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org",
                 "--no-assemble", "--no-render"],
            ):
                rc = fetch_dc.main()
        self.assertEqual(rc, 0)

    def test_main_writes_manifest_under_data_root(self):
        with _MainHarness() as h:
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org",
                 "--no-assemble", "--no-render"],
            ):
                fetch_dc.main()
            manifest_path = (
                h._tmpdir
                / IDS.ORG_ID_15
                / f"{IDS.AGENT_API}__{IDS.AGENT_VERSION}"
                / IDS.SID
                / "dc._session_manifest.json"
            )
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["session_id"], IDS.SID)
        self.assertEqual(manifest["session_shape"], "complete")

    def test_main_invokes_assemble_and_render_by_default(self):
        # Without --no-assemble / --no-render, both should be called once.
        with _MainHarness():
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org"],
            ):
                # Re-patch the targets at call site to capture.
                with mock.patch("assemble_dc.main_for_session") as ams:
                    with mock.patch("render_dc.main_for_session") as rms:
                        rc = fetch_dc.main()
        self.assertEqual(rc, 0)
        ams.assert_called_once_with(IDS.SID)
        rms.assert_called_once_with(IDS.SID)

    def test_main_skips_assemble_when_flag_set(self):
        with _MainHarness():
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org",
                 "--no-assemble"],
            ):
                with mock.patch("assemble_dc.main_for_session") as ams:
                    with mock.patch("render_dc.main_for_session") as rms:
                        rc = fetch_dc.main()
        self.assertEqual(rc, 0)
        ams.assert_not_called()
        rms.assert_called_once()

    def test_main_skips_render_when_flag_set(self):
        with _MainHarness():
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org",
                 "--no-render"],
            ):
                with mock.patch("assemble_dc.main_for_session") as ams:
                    with mock.patch("render_dc.main_for_session") as rms:
                        rc = fetch_dc.main()
        self.assertEqual(rc, 0)
        ams.assert_called_once()
        rms.assert_not_called()

    def test_main_verbose_flag_propagates_to_ctx(self):
        captured_ctx = {}

        def capture(ctx):
            captured_ctx.update(ctx)
            _fake_waterfall(ctx)

        with _MainHarness():
            # Override the waterfall mock to capture ctx
            with mock.patch.object(fetch_dc, "_run_waterfall",
                                   side_effect=capture):
                with mock.patch.object(
                    fetch_dc.sys, "argv",
                    ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org",
                     "--verbose", "--no-assemble", "--no-render"],
                ):
                    fetch_dc.main()
        self.assertTrue(captured_ctx["verbose"])


# -----------------------------------------------------------------------------
# Messaging-id input
# -----------------------------------------------------------------------------


class MainMessagingIdTests(unittest.TestCase):

    def test_messaging_id_resolves_to_uuid_via_disk(self):
        # Fixture's session row has the messaging id wired up. Patch the
        # resolver at the source module so fetch_dc's lazy import sees it.
        with _MainHarness():
            with mock.patch(
                "resolve_session.resolve_disk_or_live",
                return_value=IDS.SID,
            ):
                with mock.patch.object(
                    fetch_dc.sys, "argv",
                    ["fetch_dc.py",
                     "--session", "0MwTESTMSG12345AAA",
                     "--org", "my-org",
                     "--no-assemble", "--no-render"],
                ):
                    rc = fetch_dc.main()
        self.assertEqual(rc, 0)


# -----------------------------------------------------------------------------
# DcAccessDenied → routes through _handle_dc_access_denied
# -----------------------------------------------------------------------------


class MainDcAccessDeniedTests(unittest.TestCase):

    def test_returns_exit_dc_access_denied_in_headless(self):
        exc = fetch_dc.DcAccessDenied("401", "Unauthorized")
        with _MainHarness(raise_dc_access_denied=exc, is_tty=False):
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org"],
            ):
                with mock.patch("sys.stdout", io.StringIO()):
                    rc = fetch_dc.main()
        self.assertEqual(rc, fetch_dc.EXIT_DC_ACCESS_DENIED)

    def test_returns_exit_dc_access_denied_in_tty_choice_1(self):
        exc = fetch_dc.DcAccessDenied("403", "Forbidden")
        with _MainHarness(raise_dc_access_denied=exc, is_tty=True):
            with mock.patch.object(
                fetch_dc.sys, "argv",
                ["fetch_dc.py", "--session", IDS.SID, "--org", "my-org"],
            ):
                # Interactive prompt: feed "1" via stdin.
                with mock.patch.object(
                    fetch_dc.sys, "stdin",
                    io.StringIO("1\n"),
                ):
                    with mock.patch.object(fetch_dc, "_log"):
                        rc = fetch_dc.main()
        self.assertEqual(rc, fetch_dc.EXIT_DC_ACCESS_DENIED)


if __name__ == "__main__":
    unittest.main()

"""Tests for ``resolve_session.resolve_from_disk``.

The function walks ``DATA_ROOT`` for ``dc.sessions.json`` files and
returns the AI-agent session UUID whose row has a matching
``ssot__RelatedMessagingSessionId__c``. Must work across:

  - the nested layout (``<org>/<agent>__<ver>/<uuid>/``),
  - historic flat layout (``<uuid>/``),
  - user-created archive suffix dirs (skip — stale duplicate rows),
  - distinct-UUID multi-match (SystemExit),
  - UUID pass-through (no-op).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import resolve_session  # type: ignore


_UUID_A = "019dface-0000-7000-8000-000000000001"
_UUID_B = "019dface-0000-7000-8000-000000000002"
_MSG_ID = "0MwTESTMSG67890BBB"


def _write_sessions_row(session_dir: Path, uuid: str, msg_id: str) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "dc.sessions.json").write_text(json.dumps([{
        "ssot__Id__c": uuid,
        "ssot__RelatedMessagingSessionId__c": msg_id,
    }]))


class ResolveFromDiskTests(unittest.TestCase):

    def test_nested_layout_finds_uuid(self):
        """``<org>/<agent>/<uuid>/dc.sessions.json`` — the current layout
        produced by ``storage.save``. Must find the messaging id."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_sessions_row(
                root / "00D000000000000" / "DemoAgent__v5" / _UUID_A,
                _UUID_A, _MSG_ID,
            )
            with mock.patch.object(resolve_session, "DATA_ROOT", root):
                self.assertEqual(resolve_session.resolve_from_disk(_MSG_ID), _UUID_A)

    def test_flat_layout_still_finds_uuid(self):
        """Historic ``<uuid>/dc.sessions.json`` layout — same rglob walk
        catches it. Regression guard for backwards compatibility."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_sessions_row(root / _UUID_A, _UUID_A, _MSG_ID)
            with mock.patch.object(resolve_session, "DATA_ROOT", root):
                self.assertEqual(resolve_session.resolve_from_disk(_MSG_ID), _UUID_A)

    def test_archive_suffix_dirs_are_skipped(self):
        """Primary ``<uuid>/`` + duplicate ``<uuid> - archive 1/`` hold
        identical rows. The archive copy must not trigger a multi-match."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org_agent = root / "00D000000000000" / "DemoAgent__v5"
            _write_sessions_row(org_agent / _UUID_A, _UUID_A, _MSG_ID)
            _write_sessions_row(
                org_agent / f"{_UUID_A} - archive 1", _UUID_A, _MSG_ID,
            )
            with mock.patch.object(resolve_session, "DATA_ROOT", root):
                self.assertEqual(resolve_session.resolve_from_disk(_MSG_ID), _UUID_A)

    def test_distinct_uuids_with_same_msg_id_raise(self):
        """Two DISTINCT uuid dirs carrying the same messaging id is the
        real ambiguity case — SystemExit with both uuids listed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org_agent = root / "00D000000000000" / "DemoAgent__v5"
            _write_sessions_row(org_agent / _UUID_A, _UUID_A, _MSG_ID)
            _write_sessions_row(org_agent / _UUID_B, _UUID_B, _MSG_ID)
            with mock.patch.object(resolve_session, "DATA_ROOT", root):
                with self.assertRaises(SystemExit) as cm:
                    resolve_session.resolve_from_disk(_MSG_ID)
                msg = str(cm.exception)
                self.assertIn(_UUID_A, msg)
                self.assertIn(_UUID_B, msg)
                self.assertIn("matches 2", msg)

    def test_uuid_input_passes_through(self):
        """UUID input is returned as-is without scanning. The caller
        validates disk presence downstream."""
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(resolve_session, "DATA_ROOT", Path(tmp)):
                self.assertEqual(resolve_session.resolve_from_disk(_UUID_A), _UUID_A)


if __name__ == "__main__":
    unittest.main()

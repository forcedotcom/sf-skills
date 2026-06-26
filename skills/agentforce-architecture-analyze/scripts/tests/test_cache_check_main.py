"""In-process tests for ``cache_check.main``.

The existing ``test_cache_check.py`` drives main via subprocess (so its
Python branches don't show up in coverage). This file calls main()
directly, patching ``os.environ`` + ``config.CACHE_ROOT`` so all the
hit/miss decision branches register.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import cache_check  # type: ignore
import config  # type: ignore


def _build_valid_manifest(*, data_path: str,
                          built_at_utc: str | None = None,
                          schema_version: str = "3.1",
                          node_count: int = 5,
                          depth: int = 2,
                          ttl_days: int = 7,
                          partial: bool = False,
                          unresolved_count: int = 0,
                          generation: str = "nga",
                          bot_id: str = "0Xx000000000Demo",
                          master_label: str = "Demo Agent",
                          version_auto_picked: bool = False,
                          planner_name: str = "DemoPlanner",
                          kind_counts: dict | None = None) -> dict:
    if built_at_utc is None:
        built_at_utc = (
            dt.datetime.now(dt.timezone.utc)
            .isoformat().replace("+00:00", "Z")
        )
    return {
        "schema_version": schema_version,
        "built_at_utc": built_at_utc,
        "node_count": node_count,
        "depth": depth,
        "ttl_days": ttl_days,
        "data_path": data_path,
        "partial": partial,
        "unresolved_count": unresolved_count,
        "agent": {
            "generation": generation,
            "bot_id": bot_id,
            "master_label": master_label,
            "_version_auto_picked": version_auto_picked,
            "planner_name": planner_name,
        },
        "kind_counts": kind_counts or {"TOPIC": 2, "STANDARD_ACTION": 3},
    }


class _CacheHarness:
    """Patch CACHE_ROOT + os.environ + capture stdout."""

    def __init__(self, *, env_overrides: dict | None = None,
                 manifest: dict | None = None,
                 plant_data_file: bool = True):
        self.env_overrides = env_overrides or {}
        self.manifest = manifest
        self.plant_data_file = plant_data_file

    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        # Build a 4-deep CACHE_ROOT so cache_dir lives strictly inside it
        # (the rmtree guard refuses paths NOT under CACHE_ROOT).
        self.cache_root = self.tmpdir / "cache" / "investigating-agentforce-architecture"
        self.cache_root.mkdir(parents=True)
        self.cache_dir = self.cache_root / "ALPHA0000000000" / "MyAgent__v1"
        self.cache_dir.mkdir(parents=True)
        self.data_dir = self.tmpdir / "data" / "ALPHA0000000000" / "MyAgent__v1"
        self.work_dir = self.tmpdir / "work"
        self.work_dir.mkdir(parents=True)

        # Plant the authoritative tree file UNDER cache_dir (where
        # finalize.py originally wrote it). cache_check copies it INTO
        # data_dir on hit, so source and dest must be different files.
        self.tree_path = self.cache_dir / "MyAgent_v1_metadata_tree.json"
        if self.plant_data_file:
            self.tree_path.write_text(json.dumps({
                "agent": {"api_name": "MyAgent", "version": "v1"},
                "session": {"_schema_version": 1},
            }))

        # Plant the manifest under cache_dir
        if self.manifest is not None:
            (self.cache_dir / "manifest.json").write_text(
                json.dumps(self.manifest)
            )
        elif self.manifest is None and self.plant_data_file:
            # Default valid manifest pointing at the planted tree
            (self.cache_dir / "manifest.json").write_text(json.dumps(
                _build_valid_manifest(data_path=str(self.tree_path))
            ))

        self._env = {
            "CACHE_DIR": str(self.cache_dir),
            "DATA_DIR": str(self.data_dir),
            "WORK_DIR": str(self.work_dir),
            "AGENT_API_NAME": "MyAgent",
            "AGENT_VERSION": "v1",
        }
        self._env.update(self.env_overrides)

        self._saved_env = dict(os.environ)
        os.environ.update(self._env)

        self._patches = [
            mock.patch.object(config, "CACHE_ROOT", self.cache_root),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        # Restore env
        for k in self._env:
            os.environ.pop(k, None)
        os.environ.update(self._saved_env)
        self._tmp.cleanup()


def _run_main_capture() -> tuple[int, str]:
    """Call main() with stdout captured. Translates SystemExit into rc."""
    buf = io.StringIO()
    rc: int
    try:
        with mock.patch("sys.stdout", buf):
            rc = cache_check.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 0
    return rc, buf.getvalue()


# -----------------------------------------------------------------------------
# Hit path
# -----------------------------------------------------------------------------


class CacheHitTests(unittest.TestCase):

    def test_hit_emits_cache_hit_true_with_full_export_block(self):
        with _CacheHarness():
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=true", out)
        # Full hit block has these signature fields
        self.assertIn("CACHED_AT_UTC=", out)
        self.assertIn("NODE_COUNT=", out)
        self.assertIn("DEPTH=", out)
        self.assertIn("AGENT_GENERATION=", out)
        self.assertIn("BOT_ID=", out)
        self.assertIn("PLANNER_NAME=", out)

    def test_hit_copies_tree_into_data_dir(self):
        with _CacheHarness() as h:
            rc, _ = _run_main_capture()
            self.assertEqual(rc, 0)
            dst = h.data_dir / "MyAgent_v1_metadata_tree.json"
            # File search across resolved tree to dodge /private/var ↔ /var.
            written = list(h.tmpdir.rglob("MyAgent_v1_metadata_tree.json"))
        self.assertGreaterEqual(len(written), 1)

    def test_hit_stages_declared_action_tree_in_work_dir(self):
        with _CacheHarness() as h:
            _run_main_capture()
            staged = list(h.tmpdir.rglob("declared_action_tree.json"))
        self.assertGreaterEqual(len(staged), 1)

    def test_hit_emits_kind_counts_with_kc_prefix(self):
        with _CacheHarness():
            _, out = _run_main_capture()
        self.assertIn("KC_TOPIC=", out)
        self.assertIn("KC_STANDARD_ACTION=", out)


# -----------------------------------------------------------------------------
# Miss paths (each one exits 0 with CACHE_HIT=false)
# -----------------------------------------------------------------------------


class CacheMissTests(unittest.TestCase):

    def test_miss_when_force_refresh_true(self):
        with _CacheHarness(env_overrides={"FORCE_REFRESH": "true"}):
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)

    def test_miss_when_manifest_missing(self):
        # Build harness without auto-planted manifest
        with _CacheHarness(manifest={}, plant_data_file=False) as h:
            (h.cache_dir / "manifest.json").unlink()
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)

    def test_miss_when_manifest_malformed(self):
        with _CacheHarness(manifest={}) as h:
            (h.cache_dir / "manifest.json").write_text("<<<not json>>>")
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)

    def test_miss_with_invalidated_reason_on_schema_mismatch(self):
        # Schema version != config.SCHEMA_VERSION → rmtree + miss
        with _CacheHarness(manifest=_build_valid_manifest(
            data_path="/tmp/x", schema_version="2.0",
        )) as h:
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)
        self.assertIn("CACHE_INVALIDATED_REASON=schema-version-mismatch", out)
        # Cache dir got rmtree'd
        self.assertFalse(h.cache_dir.exists())

    def test_miss_when_data_path_missing(self):
        with _CacheHarness(manifest=_build_valid_manifest(
            data_path="/nope/not-a-real-path.json",
        )):
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)

    def test_miss_when_built_at_unparseable(self):
        with _CacheHarness() as h:
            (h.cache_dir / "manifest.json").write_text(json.dumps(
                _build_valid_manifest(
                    data_path=str(h.tree_path),
                    built_at_utc="not-a-timestamp",
                ),
            ))
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)

    def test_miss_when_ttl_expired(self):
        # built_at_utc is far in the past + ttl_days=1 → age > ttl → miss
        ancient = (dt.datetime.now(dt.timezone.utc)
                   - dt.timedelta(days=30)).isoformat().replace("+00:00", "Z")
        with _CacheHarness(manifest=None) as h:
            (h.cache_dir / "manifest.json").write_text(json.dumps(
                _build_valid_manifest(
                    data_path=str(h.tree_path),
                    built_at_utc=ancient,
                    ttl_days=1,
                ),
            ))
            rc, out = _run_main_capture()
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", out)

    def test_miss_when_required_env_missing(self):
        with _CacheHarness() as h:
            os.environ.pop("CACHE_DIR", None)
            buf = io.StringIO()
            rc: int
            try:
                with mock.patch("sys.stdout", buf):
                    with mock.patch("sys.stderr", io.StringIO()):
                        rc = cache_check.main()
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 0
        self.assertEqual(rc, 0)
        self.assertIn("CACHE_HIT=false", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

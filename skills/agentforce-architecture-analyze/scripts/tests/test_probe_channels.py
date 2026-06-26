"""Tests for channel probe TTL (7d), mandatory-field gate,
runtime invalidate + re-probe.

Every test mocks `sf_cli.run_sf` — no real org calls. Cache dir is
redirected into a tempdir via monkey-patching `config.PROBE_CACHE_ROOT`
to keep tests hermetic.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import time
import unittest
import unittest.mock as mock
from pathlib import Path

from . import _bootstrap  # noqa: F401

import config  # type: ignore
import probe_channels  # type: ignore


def _fake_describe_ok(fields: list[str]) -> dict:
    """Shape the sf_cli.run_sf output: success envelope wrapping a fields list."""
    return {
        "status": 0,
        "result": {
            "fields": [{"name": f, "queryable": True} for f in fields],
        },
    }


# A "universal" success payload: every mandatory field for every sObject
# present. Individual tests override for specific sObjects.
def _all_fields_ok_run_sf(recipe: str, **params: str) -> dict:
    sobject = params["SOBJECT"]
    mandatory = probe_channels.MANDATORY_FIELDS.get(sobject, set())
    # Add a couple of bonus fields so queryable_fields isn't identical to
    # mandatory_missing-inverse by construction.
    extra = {"CreatedDate", "LastModifiedDate"}
    return _fake_describe_ok(sorted(mandatory | extra))


class ProbeChannelsCacheTests(unittest.TestCase):
    """Cache hit / miss / TTL semantics."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig_root = config.PROBE_CACHE_ROOT
        config.PROBE_CACHE_ROOT = Path(self._tmp.name) / "_channel_probe"

    def tearDown(self) -> None:
        config.PROBE_CACHE_ROOT = self._orig_root

    def test_cache_hit_within_ttl_no_network(self):
        """A fresh cache file + force_refresh=False → no run_sf calls."""
        cache_dir = config.build_probe_cache_dir("00D000000000ABC", "v60.0")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "channels.json"
        payload = {
            "_schema": "channels/1",
            "_built_at_utc": time.time(),  # right now → fresh
            "status": "OK",
            "channels": {"BotDefinition": {"queryable_fields": ["Id"],
                                           "mandatory_missing": [],
                                           "describe_error": None}},
        }
        cache_file.write_text(json.dumps(payload))

        with mock.patch.object(probe_channels, "run_sf") as m:
            out = probe_channels.probe_channels(
                "myorg", "00D000000000ABC", "v60.0", force_refresh=False,
            )
        self.assertEqual(out["status"], "OK")
        m.assert_not_called()

    def test_cache_stale_triggers_reprobe(self):
        """Cached file older than TTL → re-run describes."""
        cache_dir = config.build_probe_cache_dir("00D000000000ABC", "v60.0")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "channels.json"
        stale = {
            "_schema": "channels/1",
            "_built_at_utc": time.time() - (8 * 86400),  # 8 days old
            "status": "OK",
            "channels": {},
        }
        cache_file.write_text(json.dumps(stale))

        with mock.patch.object(probe_channels, "run_sf",
                               side_effect=_all_fields_ok_run_sf) as m:
            out = probe_channels.probe_channels(
                "myorg", "00D000000000ABC", "v60.0", force_refresh=False,
            )
        self.assertEqual(out["status"], "OK")
        # One call per sObject.
        self.assertEqual(m.call_count, len(probe_channels.ALL_SOBJECTS))

    def test_force_refresh_always_reprobes(self):
        """force_refresh=True bypasses a fresh cache."""
        cache_dir = config.build_probe_cache_dir("00D000000000ABC", "v60.0")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "channels.json"
        fresh = {
            "_schema": "channels/1",
            "_built_at_utc": time.time(),
            "status": "OK",
            "channels": {},
        }
        cache_file.write_text(json.dumps(fresh))

        with mock.patch.object(probe_channels, "run_sf",
                               side_effect=_all_fields_ok_run_sf) as m:
            probe_channels.probe_channels(
                "myorg", "00D000000000ABC", "v60.0", force_refresh=True,
            )
        self.assertEqual(m.call_count, len(probe_channels.ALL_SOBJECTS))


class InvalidateAndReprobeTests(unittest.TestCase):
    """runtime escape valve when SOQL returns INVALID_FIELD."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig_root = config.PROBE_CACHE_ROOT
        config.PROBE_CACHE_ROOT = Path(self._tmp.name) / "_channel_probe"

    def tearDown(self) -> None:
        config.PROBE_CACHE_ROOT = self._orig_root

    def test_invalidate_deletes_cache_and_reruns(self):
        cache_dir = config.build_probe_cache_dir("00D000000000ABC", "v60.0")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "channels.json"
        cache_file.write_text(json.dumps({
            "_schema": "channels/1",
            "_built_at_utc": time.time(),
            "status": "OK",
            "channels": {},
        }))

        with mock.patch.object(probe_channels, "run_sf",
                               side_effect=_all_fields_ok_run_sf) as m:
            out = probe_channels.invalidate_and_reprobe(
                "myorg", "00D000000000ABC", "v60.0",
            )

        self.assertEqual(out["status"], "OK")
        self.assertTrue(cache_file.is_file(), "fresh cache must be rewritten")
        self.assertEqual(m.call_count, len(probe_channels.ALL_SOBJECTS))

    def test_invalidate_tolerates_missing_cache(self):
        """Cold-path invalidate (no file yet) must not crash."""
        with mock.patch.object(probe_channels, "run_sf",
                               side_effect=_all_fields_ok_run_sf):
            out = probe_channels.invalidate_and_reprobe(
                "myorg", "00D000000000ABC", "v60.0",
            )
        self.assertEqual(out["status"], "OK")


class MandatoryFieldGateTests(unittest.TestCase):
    """Missing mandatory field → status flips to PROBE_FAILED."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig_root = config.PROBE_CACHE_ROOT
        config.PROBE_CACHE_ROOT = Path(self._tmp.name) / "_channel_probe"

    def tearDown(self) -> None:
        config.PROBE_CACHE_ROOT = self._orig_root

    def test_missing_invocation_target_flags_probe_failed(self):
        """SF release drops `InvocationTarget` on
        GenAiFunctionDefinition → probe must surface PROBE_FAILED.
        """

        def mock_run_sf(recipe: str, **params: str) -> dict:
            sobject = params["SOBJECT"]
            mandatory = set(probe_channels.MANDATORY_FIELDS.get(sobject, set()))
            if sobject == "GenAiFunctionDefinition":
                # Simulate the schema drift: drop InvocationTarget.
                mandatory.discard("InvocationTarget")
            return _fake_describe_ok(sorted(mandatory))

        with mock.patch.object(probe_channels, "run_sf", side_effect=mock_run_sf):
            out = probe_channels.probe_channels(
                "myorg", "00D000000000ABC", "v60.0", force_refresh=True,
            )

        self.assertEqual(out["status"], "PROBE_FAILED")
        entry = out["channels"]["GenAiFunctionDefinition"]
        self.assertIn("InvocationTarget", entry["mandatory_missing"])
        # Other sObjects unaffected.
        self.assertEqual(
            out["channels"]["BotDefinition"]["mandatory_missing"], [],
        )


class CacheFilePermissionsTests(unittest.TestCase):
    """cached channels.json must be 0o600 (owner RW only)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig_root = config.PROBE_CACHE_ROOT
        config.PROBE_CACHE_ROOT = Path(self._tmp.name) / "_channel_probe"

    def tearDown(self) -> None:
        config.PROBE_CACHE_ROOT = self._orig_root

    def test_cache_file_is_mode_0o600(self):
        with mock.patch.object(probe_channels, "run_sf",
                               side_effect=_all_fields_ok_run_sf):
            probe_channels.probe_channels(
                "myorg", "00D000000000ABC", "v60.0", force_refresh=True,
            )
        cache_file = (
            config.build_probe_cache_dir("00D000000000ABC", "v60.0")
            / "channels.json"
        )
        self.assertTrue(cache_file.is_file())
        mode = stat.S_IMODE(cache_file.stat().st_mode)
        self.assertEqual(
            mode, 0o600,
            f"cache file mode must be 0o600, got 0o{mode:03o} ",
        )


class CacheFreshnessBoundsTests(unittest.TestCase):
    """`_is_cache_fresh` must reject future timestamps as stale.

    A `_built_at_utc` in the future is a symptom of clock skew (NTP
    drift after suspend, container clock jump) or cache tampering —
    either way, we treat it as untrustworthy and force a reprobe.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_future_timestamp_is_not_fresh(self):
        # Year 3000 → unambiguously future.
        future_epoch = 32503680000.0
        cache_file = Path(self._tmp.name) / "channels.json"
        cache_file.write_text(json.dumps({
            "_schema": "channels/1",
            "_built_at_utc": future_epoch,
            "status": "OK",
            "channels": {},
        }))
        self.assertFalse(
            probe_channels._is_cache_fresh(cache_file, ttl_days=7),
            "future _built_at_utc must be rejected as stale",
        )

    def test_present_timestamp_is_fresh(self):
        cache_file = Path(self._tmp.name) / "channels.json"
        cache_file.write_text(json.dumps({
            "_schema": "channels/1",
            "_built_at_utc": time.time(),
            "status": "OK",
            "channels": {},
        }))
        self.assertTrue(probe_channels._is_cache_fresh(cache_file, ttl_days=7))


class WriteCacheConcurrencyTests(unittest.TestCase):
    """concurrent _write_cache calls must not collide on tmp names.

    The prior design used `path.with_suffix(path.suffix + ".tmp")` — a
    deterministic name shared by every concurrent writer. This test
    fires N threads that all write the same target path; after the dust
    settles there must be exactly one final file, no leftover `.tmp`
    files, and the contents must be valid JSON from ONE of the writers
    (any of them is acceptable — what matters is integrity).
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_concurrent_writes_no_collision_no_corruption(self):
        import threading

        target_dir = Path(self._tmp.name) / "probe"
        target_path = target_dir / "channels.json"

        N = 8
        errors: list[BaseException] = []
        barrier = threading.Barrier(N)

        def worker(i: int) -> None:
            payload = {
                "_schema": "channels/1",
                "_built_at_utc": float(i + 1),
                "status": "OK",
                "channels": {"writer": {"queryable_fields": [f"w{i}"]}},
            }
            barrier.wait()  # maximise contention
            try:
                probe_channels._write_cache(target_path, payload)
            except BaseException as e:  # noqa: BLE001 — thread boundary
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        self.assertEqual(errors, [], f"worker errors: {errors}")
        self.assertTrue(target_path.is_file())

        # No stray tmp files left behind.
        leftover = list(target_dir.glob(".channels.*.tmp"))
        self.assertEqual(
            leftover, [],
            f"concurrent writes left tmp leftovers: {leftover}",
        )

        # Final file is parseable JSON (not a half-written corruption).
        parsed = json.loads(target_path.read_text())
        # One of the N payloads won the race; its _built_at_utc is in [1, N].
        self.assertIn(parsed["_built_at_utc"], [float(i + 1) for i in range(N)])

    def test_parent_dir_permissions_are_0o700(self):
        """parent dir is normalized to 0o700 after write.

        Even if the directory pre-existed with looser permissions, a
        successful _write_cache leaves it at 0o700.
        """
        target_path = Path(self._tmp.name) / "probe" / "channels.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Deliberately widen perms to prove _write_cache narrows them.
        os.chmod(target_path.parent, 0o755)

        probe_channels._write_cache(target_path, {
            "_schema": "channels/1",
            "_built_at_utc": time.time(),
            "status": "OK",
            "channels": {},
        })

        mode = stat.S_IMODE(target_path.parent.stat().st_mode)
        self.assertEqual(
            mode, 0o700,
            f"parent dir mode must be 0o700, got 0o{mode:03o}",
        )


if __name__ == "__main__":
    unittest.main()

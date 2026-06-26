"""cache_check.py schema-version mismatch → delete-on-read + MISS.

Covers:
  * manifest.schema_version == config.SCHEMA_VERSION → HIT
  * manifest.schema_version != config.SCHEMA_VERSION → MISS +
    CACHE_INVALIDATED_REASON=schema-version-mismatch + cache dir deleted
  * missing manifest → MISS (existing behavior preserved)
  * expired TTL + correct schema → MISS + dir NOT deleted
  * _safe_rmtree_under_cache_root refuses paths outside CACHE_ROOT
  * module import raises if CACHE_ROOT is a symlink

The script reads env vars + writes eval-able K=V lines to stdout +
exits 0 on both HIT and MISS. We drive it via subprocess so we exercise
the real stdout stream and exit code.
"""
from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from . import _bootstrap  # noqa: F401

import config  # type: ignore
import cache_check  # type: ignore


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent.parent
CACHE_CHECK = SCRIPTS_DIR / "cache_check.py"


def _parse_kv(stdout: str) -> dict[str, str]:
    """Parse the shlex-quoted K=V lines cache_check emits.

    cache_check writes one `K=V` per line, V shlex-quoted. For our tests
    we don't need full shell parsing — we just strip one surrounding
    single-quote layer if present.
    """
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        if v.startswith("'") and v.endswith("'") and len(v) >= 2:
            v = v[1:-1]
        out[k] = v
    return out


class CacheCheckSchemaVersionTests(unittest.TestCase):
    """strict schema-version match, delete-on-mismatch."""

    def setUp(self) -> None:
        # Isolated tempdir mirroring CACHE_ROOT so we can safely rmtree
        # anything under it. We override config.CACHE_ROOT for the
        # duration of each test — the script reads config.CACHE_ROOT at
        # rmtree-validation time, and we drive the script via subprocess
        # with CACHE_ROOT propagated through env only via a wrapper
        # below (subprocess-style overrides).
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.cache_root = self.root / "cache"
        self.data_root = self.root / "data"
        self.work_dir = self.root / "work"
        self.cache_root.mkdir()
        self.data_root.mkdir()
        self.work_dir.mkdir()
        # Agent-keyed sub-path under cache_root.
        self.agent = "TestAgent_v1"
        self.version = "v1"
        self.cache_dir = self.cache_root / "00D000000000ABC" / f"{self.agent}__{self.version}"
        self.data_dir = self.data_root / "00D000000000ABC" / f"{self.agent}__{self.version}"
        self.cache_dir.mkdir(parents=True)
        # Data file manifest points at — must exist for the HIT path.
        self.data_file = self.cache_dir / "metadata_tree.json"
        self.data_file.write_text(json.dumps({"root": {"kind": "Bot"}}))
        # summary.md dropped from the output contract — no
        # longer written by cache seeding.

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_manifest(self, schema_version: str, age_days: int = 0) -> None:
        built = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=age_days)
        manifest = {
            "schema_version": schema_version,
            "data_path": str(self.data_file),
            "built_at_utc": built.isoformat().replace("+00:00", "Z"),
            "ttl_days": 7,
            "node_count": 1,
            "depth": 1,
            "agent": {
                "generation": "Einstein",
                "bot_id": "0Xx000000000000",
                "master_label": "TestAgent",
                "planner_name": "p1",
            },
            "kind_counts": {"Bot": 1},
            "partial": False,
            "unresolved_count": 0,
        }
        (self.cache_dir / "manifest.json").write_text(json.dumps(manifest))

    def _run_with_patched_cache_root(self, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        """Patch config.CACHE_ROOT via a small wrapper — simpler than the
        HOME-redirect dance and keeps the test local to the module under
        test. We write a tiny entry-point that monkeypatches config
        before invoking cache_check.main, then runs it.
        """
        wrapper = self.root / "wrapper.py"
        wrapper.write_text(
            "import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
            "import config\n"
            "config.CACHE_ROOT = __import__('pathlib').Path(%r)\n"
            "import cache_check\n"
            "sys.exit(cache_check.main())\n"
            % (str(SCRIPTS_DIR), str(SCRIPTS_DIR.parent / 'tools'), str(self.cache_root))
        )
        env = os.environ.copy()
        env.update({
            "CACHE_DIR": str(self.cache_dir),
            "DATA_DIR": str(self.data_dir),
            "WORK_DIR": str(self.work_dir),
            "AGENT_API_NAME": self.agent,
            "AGENT_VERSION": self.version,
        })
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(wrapper)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_matching_schema_version_hits(self):
        self._write_manifest(config.SCHEMA_VERSION)
        cp = self._run_with_patched_cache_root()
        self.assertEqual(cp.returncode, 0, cp.stderr)
        kv = _parse_kv(cp.stdout)
        self.assertEqual(kv.get("CACHE_HIT"), "true", cp.stdout)
        self.assertNotIn("CACHE_INVALIDATED_REASON", kv)
        # Cache dir survives.
        self.assertTrue(self.cache_dir.exists())

    def test_legacy_schema_version_misses_and_deletes(self):
        """schema_version=2.4 (legacy) != 3.0 (current) → MISS + rmtree."""
        self._write_manifest("2.4")
        self.assertTrue(self.cache_dir.exists())
        cp = self._run_with_patched_cache_root()
        self.assertEqual(cp.returncode, 0, cp.stderr)
        kv = _parse_kv(cp.stdout)
        self.assertEqual(kv.get("CACHE_HIT"), "false")
        self.assertEqual(kv.get("CACHE_INVALIDATED_REASON"), "schema-version-mismatch")
        # Cache dir deleted by the safety-gated rmtree.
        self.assertFalse(self.cache_dir.exists(),
                         "cache_dir must be removed on schema-version mismatch")

    def test_unexpected_future_schema_version_misses_and_deletes(self):
        """Any value != current SCHEMA_VERSION invalidates (not just legacy)."""
        self._write_manifest("99.99")
        cp = self._run_with_patched_cache_root()
        kv = _parse_kv(cp.stdout)
        self.assertEqual(kv.get("CACHE_HIT"), "false")
        self.assertEqual(kv.get("CACHE_INVALIDATED_REASON"), "schema-version-mismatch")
        self.assertFalse(self.cache_dir.exists())

    def test_missing_manifest_misses_no_deletion(self):
        """Existing behavior: no manifest → MISS, NO rmtree, no reason emit."""
        # Don't write any manifest.
        cp = self._run_with_patched_cache_root()
        self.assertEqual(cp.returncode, 0, cp.stderr)
        kv = _parse_kv(cp.stdout)
        self.assertEqual(kv.get("CACHE_HIT"), "false")
        # Missing manifest is a different reason class — no invalidation
        # reason emitted here (cache is simply cold, not corrupt).
        self.assertNotIn("CACHE_INVALIDATED_REASON", kv)
        self.assertTrue(self.cache_dir.exists(),
                        "missing manifest must NOT trigger rmtree")

    def test_expired_ttl_with_matching_schema_misses_no_deletion(self):
        """TTL-expired cache with CURRENT schema → MISS but dir stays intact."""
        self._write_manifest(config.SCHEMA_VERSION, age_days=30)  # 30 > 7
        cp = self._run_with_patched_cache_root()
        kv = _parse_kv(cp.stdout)
        self.assertEqual(kv.get("CACHE_HIT"), "false")
        # No schema-mismatch reason — it's a stale cache, not a corrupt one.
        self.assertNotIn("CACHE_INVALIDATED_REASON", kv)
        self.assertTrue(self.cache_dir.exists(),
                        "expired TTL must NOT rmtree — just mark stale")


class SafeRmtreeUnderCacheRootTests(unittest.TestCase):
    """defensive: `_safe_rmtree_under_cache_root` refuses out-of-root paths."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.cache_root = self.root / "cache"
        self.cache_root.mkdir()
        # In-scope victim dir.
        self.in_scope = self.cache_root / "agent_v1"
        self.in_scope.mkdir()
        (self.in_scope / "some.txt").write_text("x")
        # Out-of-scope victim dir (sibling to cache_root).
        self.out_of_scope = self.root / "other"
        self.out_of_scope.mkdir()
        (self.out_of_scope / "important.txt").write_text("do not delete")

        # Monkeypatch config.CACHE_ROOT for the duration of each test.
        self._orig_root = config.CACHE_ROOT
        config.CACHE_ROOT = self.cache_root

    def tearDown(self) -> None:
        config.CACHE_ROOT = self._orig_root
        self.tmp.cleanup()

    def test_rmtree_under_cache_root_succeeds(self):
        ok = cache_check._safe_rmtree_under_cache_root(self.in_scope)
        self.assertTrue(ok)
        self.assertFalse(self.in_scope.exists())

    def test_rmtree_outside_cache_root_refused(self):
        ok = cache_check._safe_rmtree_under_cache_root(self.out_of_scope)
        self.assertFalse(ok, "out-of-root path must be refused")
        # File still present.
        self.assertTrue((self.out_of_scope / "important.txt").exists())

    def test_nonexistent_under_root_is_noop_success(self):
        """A caller asking to delete a path that doesn't exist under the
        root gets a silent success — matches rmtree's semantics for
        already-gone targets and avoids spurious error branches on the
        miss() path."""
        ghost = self.cache_root / "never_existed"
        ok = cache_check._safe_rmtree_under_cache_root(ghost)
        self.assertTrue(ok)


class SymlinkedCacheRootRejectedAtImportTests(unittest.TestCase):
    """module import raises if CACHE_ROOT is a symlink.

    A symlinked CACHE_ROOT would defeat the rmtree safety gate — both
    sides of `target.resolve().is_relative_to(root.resolve())` would
    collapse to the same symlink target, so the gate would approve
    deletion of arbitrary paths the attacker aimed the symlink at.
    The defence is a fail-fast guard at cache_check import time.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.real_target = self.root / "evil_target"
        self.real_target.mkdir()
        self.symlinked_root = self.root / "symlinked_cache_root"
        self.symlinked_root.symlink_to(self.real_target)
        self._orig_root = config.CACHE_ROOT

    def tearDown(self) -> None:
        # Restore and reload so the rest of the suite sees a clean module.
        config.CACHE_ROOT = self._orig_root
        importlib.reload(cache_check)
        self.tmp.cleanup()

    def test_symlinked_cache_root_raises_on_import(self):
        """Reloading cache_check with a symlinked CACHE_ROOT must raise
        RuntimeError — proof that the guard actually fires and the fix
        is load-bearing."""
        config.CACHE_ROOT = self.symlinked_root
        with self.assertRaises(RuntimeError) as ctx:
            importlib.reload(cache_check)
        msg = str(ctx.exception)
        # Message must name the offending path so operators can fix it
        # without spelunking the source. Don't over-specify wording —
        # future maintainers may clarify the phrasing.
        self.assertIn(str(self.symlinked_root), msg)
        self.assertIn("symlink", msg.lower())

    def test_real_directory_cache_root_passes(self):
        """Sanity: the guard is not over-broad — a real directory (the
        common case) reloads cleanly."""
        real_dir = self.root / "real_cache_root"
        real_dir.mkdir()
        config.CACHE_ROOT = real_dir
        # No raise.
        importlib.reload(cache_check)

    def test_nonexistent_cache_root_passes(self):
        """Pristine install: CACHE_ROOT hasn't been created yet.
        Path.is_symlink() returns False on non-existent paths, so import
        must succeed — the directory will be materialized on first write."""
        ghost = self.root / "does_not_exist_yet"
        self.assertFalse(ghost.exists())
        config.CACHE_ROOT = ghost
        # No raise.
        importlib.reload(cache_check)


if __name__ == "__main__":
    unittest.main()

"""Tests for parallel_retrieve.fetch_bodies_parallel uses as_completed
with (ok, result_or_exc) tuples — one failure MUST NOT abort the whole run.
`executor.map()` would raise on first failure and silently cancel the rest;
the whole point of this module is to never do that.
"""
from __future__ import annotations

import threading
import unittest
import urllib.error

from . import _bootstrap  # noqa: F401

import parallel_retrieve  # type: ignore


class AllSucceedTests(unittest.TestCase):
    def test_five_out_of_five_ok(self):
        tasks = [lambda i=i: i * 10 for i in range(5)]
        results = parallel_retrieve.fetch_bodies_parallel(tasks, max_workers=5)
        self.assertEqual(len(results), 5)
        for ok, _ in results:
            self.assertTrue(ok)
        # Order is preserved: results[i] corresponds to tasks[i].
        self.assertEqual([r for _, r in results], [0, 10, 20, 30, 40])


class OneFailureTests(unittest.TestCase):
    def test_four_ok_one_fail(self):
        def boom():
            raise RuntimeError("task-3-failed")

        tasks = [
            lambda: "a",
            lambda: "b",
            lambda: "c",
            boom,
            lambda: "e",
        ]
        results = parallel_retrieve.fetch_bodies_parallel(tasks, max_workers=3)
        self.assertEqual(len(results), 5)
        oks = [r[0] for r in results]
        self.assertEqual(oks, [True, True, True, False, True])
        # The failure slot carries the RuntimeError object, not a string.
        self.assertIsInstance(results[3][1], RuntimeError)
        self.assertIn("task-3-failed", str(results[3][1]))

    def test_function_does_not_raise_on_failure(self):
        """Top-level contract: one bad task does NOT abort the run."""
        tasks = [lambda: 1, lambda: (_ for _ in ()).throw(ValueError("x"))]
        # Must not raise.
        results = parallel_retrieve.fetch_bodies_parallel(tasks, max_workers=2)
        self.assertEqual(len(results), 2)


class AllFailTests(unittest.TestCase):
    def test_all_failures_function_still_returns(self):
        def fail(n):
            raise RuntimeError(f"task-{n}")

        tasks = [lambda n=i: fail(n) for i in range(5)]
        results = parallel_retrieve.fetch_bodies_parallel(tasks, max_workers=5)
        self.assertEqual(len(results), 5)
        for ok, exc in results:
            self.assertFalse(ok)
            self.assertIsInstance(exc, RuntimeError)


class ExceptionIdentityPreservedTests(unittest.TestCase):
    """Boundary: we must return the SAME exception object so
    callers can run it through `rest_client.redact_error` at log time.
    Auto-stringifying here would strip structured attrs (HTTPError.code,
    .headers) and potentially leak tokens before redaction runs."""

    def test_httperror_object_identity_preserved(self):
        # HTTPError with a body containing a bearer token — caller is
        # responsible for redacting at log time; we must not stringify.
        sentinel_body = b'{"access_token":"eyJtok.secret"}'
        exc = urllib.error.HTTPError(
            url="https://example.com/x",
            code=429,
            msg="Too Many Requests",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        # Stash the body where a caller could read it later.
        exc.body_bytes = sentinel_body  # type: ignore[attr-defined]

        def raises():
            raise exc

        results = parallel_retrieve.fetch_bodies_parallel([raises], max_workers=1)
        self.assertEqual(len(results), 1)
        ok, returned_exc = results[0]
        self.assertFalse(ok)
        # Identity check — the SAME object came back.
        self.assertIs(returned_exc, exc)
        # Structured attrs are intact for downstream triage.
        self.assertEqual(returned_exc.code, 429)
        self.assertEqual(returned_exc.body_bytes, sentinel_body)


class MaxWorkersOneSerializesTests(unittest.TestCase):
    def test_max_workers_one_ordering_deterministic(self):
        """With max_workers=1, tasks run one at a time — ordering is fully
        deterministic (and matches input order since results are indexed).
        """
        order_seen: list[int] = []
        lock = threading.Lock()

        def make_task(n):
            def task():
                with lock:
                    order_seen.append(n)
                return n
            return task

        tasks = [make_task(i) for i in range(10)]
        results = parallel_retrieve.fetch_bodies_parallel(tasks, max_workers=1)
        self.assertEqual([r for _, r in results], list(range(10)))
        # Serialized execution: tasks ran in submission order.
        self.assertEqual(order_seen, list(range(10)))


class EmptyTasksTests(unittest.TestCase):
    def test_empty_list_returns_empty_list(self):
        self.assertEqual(parallel_retrieve.fetch_bodies_parallel([]), [])


if __name__ == "__main__":
    unittest.main()

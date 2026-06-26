"""ThreadPoolExecutor orchestrator for Wave B body fetches.

one failure MUST NOT abort the whole run. Callers merge failed kinds
into `_unresolved[]` with `reason=f'{kind}-fetch-failed:{redact_error(exc)}'`
and emit STATUS=PARTIAL_OK. We return a mixed list of (ok, result_or_exc)
tuples instead of raising on the first failure — which is what
`ThreadPoolExecutor.map` would do (and silently cancel remaining work in
the process).

Exception identity is preserved on the failure path: callers get the exact
exception object back so they can run it through `rest_client.redact_error`
at the point of logging. We intentionally do NOT stringify here — doing so
would lose structured info (urllib.error.HTTPError.code, etc.) and could
leak tokens into intermediate strings before redaction runs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


def fetch_bodies_parallel(
    tasks: list[Callable[[], object]],
    *,
    max_workers: int = 5,
) -> list[tuple[bool, object]]:
    """Run zero-arg callables in parallel; return (ok, result_or_exc) per task.

    contract:
      * Each `task` is a zero-arg callable (use `functools.partial` to bind
        args at the call site).
      * On success, `(True, return_value)` is appended.
      * On any exception, `(False, exc)` is appended — the EXC object itself,
        not a stringification. Callers run it through `rest_client.redact_error`
        before logging.
      * Results are returned in INPUT ORDER, not completion order. Callers
        frequently zip results back to their input tasks to identify which
        target failed; completion order would break that contract.
      * Empty task list returns `[]` without spinning up a pool.
      * `max_workers=1` serializes — tasks run sequentially but the as_completed
        path is still used (deterministic ordering preserved via index map).
      * This function NEVER raises on a task failure. It may propagate
        programmer errors (e.g., a non-callable in `tasks`) at submit time;
        that's a bug surface, not a runtime failure mode.
    """
    if not tasks:
        return []

    # Pre-size the results list so we can assign by input index. This keeps
    # output ordering deterministic and independent of completion timing,
    # which matters for callers that identify failures positionally.
    results: list[tuple[bool, object] | None] = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {pool.submit(task): i for i, task in enumerate(tasks)}
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            try:
                results[idx] = (True, fut.result())
            except Exception as exc:  # noqa: BLE001 — see contract above
                # Preserve exc identity; do NOT stringify here. Callers run
                # this through rest_client.redact_error at log time .
                # We catch Exception (not BaseException) so KeyboardInterrupt
                # / SystemExit still propagate — those signal shutdown, not a
                # task failure.
                results[idx] = (False, exc)

    # All slots filled by construction — futures/indexes are 1:1 with input.
    return [r for r in results if r is not None]  # type: ignore[return-value]

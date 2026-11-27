# Parallelizing Phase 4 with an observer gate

Read this **only when delegation is permitted and the scan's worklist is large** — call sites scattered across many files/modules. For a handful of call sites in two files, skip all of this: edit inline, no ledger, no subagents. This machinery earns its overhead only at scale.

Phases 1–3 are sequential (you can't refactor before you've scanned, chosen a target, and put the new artifacts on the classpath), but **Phase 4 is embarrassingly parallel**: each file's call sites are independent, driven by the same matrix, and don't touch each other. Fan them out to subagents — group `filesTouchingSdk` into per-file (or per-module) units, one subagent per unit, each given: the files it owns, the exact matrix entries for the symbols in those files, and the platform's `refactoring-patterns-android.md` or `refactoring-patterns-ios.md`. This is a large speedup on real apps and keeps each agent's context small.

## Why a mechanism, not vigilance

You cannot observe a worker you're blocked on. So the liveness detection has to be built in:

1. **Dispatch each unit as a background task** — fire it, get a handle, don't wait synchronously. Synchronous dispatch freezes you until the worker returns, stuck or not, making stall detection impossible. Background dispatch is the load-bearing change.
2. **Give every worker a narrow contract AND a heartbeat obligation.** Contract: which files, which symbols, "return the diff plus flagged items." Obligation: **append events to a shared JSONL status ledger** as it works — `{"unit": "<id>", "event": "start|heartbeat|done|blocked", "ts": <int>, "filesTouched": [...], "flagged": [...]}`. A worker that goes quiet stops emitting `heartbeat`; that silence is how you detect a stall.
3. **Poll the ledger with the observer script — it, not your memory, is the source of truth.** Advance a reference tick each poll:

   ```bash
   python3 scripts/observe_workers.py --ledger status.jsonl --plan plan.json --now <tick>
   ```

   `plan.json` is `{"units": [...]}` — **every** unit from the scan's worklist, so completeness is verifiable. It classifies each as done / blocked / running / **stalled** (started, no heartbeat within `--stall-threshold` ticks) / **missing** (never reported), and prints a todo: which to **restart**, **dispatch**, or **demote**.
4. **Act on the todo.** Restart a stalled worker by cancelling and re-dispatching the *same* unit fresh (a clean context usually clears a wedged one). After `--max-restarts` (default 2) without reaching terminal, the script moves the unit to `DEMOTE→review` — stop retrying, record it under manual review with what was attempted. Never loop forever on one unit.

**Keep units independent so a restart is safe.** Each worker owns disjoint files; restarting one never corrupts another's work. Never let two workers edit the same file — partition by file, and hand a shared file (e.g. the `Application` class touched by both init and identity migrations) to a single worker.

## The gate

`observe_workers.py` exits `0` **only** when every planned unit has a terminal status (`done`/`blocked`); any stalled, missing, or unaccounted unit exits non-zero. **Do not enter Phase 5 until this script exits 0.** Because the Phase 5 report is built *from the ledger* — one row per planned unit with its terminal status and flagged items — a unit that never reported can't be silently dropped; it keeps the gate closed until you migrate it or explicitly demote it. Report from status, not recollection.

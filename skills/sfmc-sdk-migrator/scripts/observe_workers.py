#!/usr/bin/env python3
"""
observe_workers.py — Liveness gate for the parallel Phase 4 refactor.

Why this exists: SKILL.md tells the orchestrator to fan the refactor out to
subagents and restart stuck ones, but prose can't ENFORCE that. This script
turns "is a worker alive / done?" from a judgment call into a checkable fact.
Workers append machine-readable events to a shared status ledger; this script
reads the ledger against the planned work units and decides, deterministically:

  • which units are DONE / BLOCKED (terminal),
  • which are STALLED (started, but no heartbeat within the threshold),
  • which are MISSING (in the plan but never reported at all),
  • which have EXHAUSTED their restart budget (must be demoted to manual review).

Exit code is the forcing function: it's 0 ONLY when every planned unit has a
terminal status BACKED BY EVIDENCE. Any stalled / missing / unaccounted /
evidence-less unit → non-zero exit. Wire the orchestrator so it MUST NOT enter
Phase 5 (validate & report) until this script exits 0. That makes the reporting
system impossible to skip — the report is derived from the ledger, not memory.

--------------------------------------------------------------------------------
LEDGER PROTOCOL (workers -> ledger)

The ledger is a JSON Lines file (one JSON object per line). Each worker appends
events as it goes. `ts` is a monotonic-ish sequence the observer uses to measure
staleness WITHOUT needing a wall clock (Date.now() is intentionally avoided in
this skill's tooling). The reference tick defaults to the HIGHEST `ts` seen in
the ledger, so staleness detection works on a plain re-run with no --now: a unit
whose last heartbeat lags the newest event by >= the threshold is stalled. Pass
--now to advance the clock past the ledger (needed only when a SINGLE remaining
worker goes silent — with no newer events, the ledger's own max can't advance).

Required fields per event:
  { "unit": "<unit-id>", "event": "start|heartbeat|done|blocked|demoted", "ts": <int> }

Optional, honored when present:
  "filesTouched": ["app/.../App.kt", ...]   # what the worker edited
  "flagged":      [{"file":"..","line":12,"why":".."}]  # manual-review items
  "restart":      <int>                       # which restart attempt this is (0 = first run)
  "detail":       "free text (e.g. why blocked)"

Terminal events and the evidence each REQUIRES (an evidence-less terminal is not
trusted — it is reported as "<kind>-unverified", stays non-terminal, and holds
the gate closed, because a bare "done" with no diff is exactly how a silent
failure would masquerade as success):
  • "done"    — unit migrated. Requires evidence of work: at least one
                `filesTouched` entry, or `flagged` items, accumulated across the
                unit's events (a heartbeat may carry the files, the done need
                not repeat them). A unit that genuinely needed no change should
                say so via `flagged` (an explicit "reviewed, no change needed"),
                not a bare done.
  • "blocked" — worker gave up cleanly; only manual-review items remain.
                Requires a non-empty `flagged` list enumerating those items —
                that list IS the reason, and without it "blocked" is an empty
                claim. `blocked` is terminal, so an ALL-blocked run opens the
                gate (Phase 5 then emits a manual-review report for every unit);
                blockedCount is surfaced so that outcome can't be mistaken for a
                successful migration.
  • "demoted" — the ORCHESTRATOR (not the worker) records that a unit exhausted
                its restart budget and is moved to manual review. This is the
                terminal disposition for a unit the todo listed under "demote";
                without it, a stalled/missing-but-exhausted unit would never
                reach a terminal state and would jam the gate closed forever.
"start" and "heartbeat" are non-terminal.

--------------------------------------------------------------------------------
PLAN (orchestrator -> observer)

Pass the planned work units so the observer knows what MUST be accounted for.
Either:
  --plan plan.json      # {"units": ["u1","u2",...]}  or  ["u1","u2",...]
  --unit u1 --unit u2   # repeatable, for quick runs

Without a plan the script can only report what's in the ledger and cannot detect
MISSING units — so it refuses to exit 0 (there's nothing to prove completeness
against). Always pass a plan for the real gate.

--------------------------------------------------------------------------------
USAGE

  # after each poll, advance --now and re-check the gate:
  python3 observe_workers.py --ledger status.jsonl --plan plan.json --now 42

  --stall-threshold N   Ticks without a heartbeat before a started unit is
                        declared STALLED (default 30).
  --max-restarts N      Restart attempts allowed before a unit must be demoted
                        to manual review instead of retried again (default 2).
  --json                Emit JSON only (for the orchestrator to parse).

Output: per-unit status + an actionable "todo" list (restart these, demote
these, wait on these). Exit 0 only when all planned units are terminal.
"""
import argparse
import json
import sys

# "demoted" is a terminal disposition the ORCHESTRATOR writes for a unit whose
# restart budget ran out (see the protocol note). Without it, an exhausted
# stalled/missing unit could never become terminal and would jam the gate shut.
TERMINAL = {"done", "blocked", "demoted"}
NON_TERMINAL = {"start", "heartbeat"}
VALID_EVENTS = TERMINAL | NON_TERMINAL


def load_plan(args):
    units = list(args.unit or [])
    if args.plan:
        with open(args.plan, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("units", [])
        units.extend(str(u) for u in data)
    # de-dupe, preserve order
    seen, ordered = set(), []
    for u in units:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def load_ledger(path):
    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    events.append({"_malformed": True, "_lineno": lineno, "_raw": raw[:200]})
                    continue
                events.append(ev)
    except FileNotFoundError:
        pass  # no ledger yet == no worker has reported == all units MISSING
    return events


def summarize(units, events, now, stall_threshold, max_restarts):
    # Fold events per unit.
    state = {u: {
        "unit": u,
        "seen": False,
        "lastEvent": None,
        "lastTs": None,
        "lastHeartbeatTs": None,
        "terminal": None,          # "done" | "blocked" | None
        "restart": 0,
        "filesTouched": [],
        "flagged": [],
        "detail": None,
    } for u in units}

    extraneous = []   # events for units not in the plan
    malformed = []

    for ev in events:
        if ev.get("_malformed"):
            malformed.append(ev)
            continue
        u = ev.get("unit")
        etype = ev.get("event")
        if u not in state:
            extraneous.append(ev)
            continue
        if etype not in VALID_EVENTS:
            malformed.append({"_lineno": None, "_raw": json.dumps(ev)[:200]})
            continue
        s = state[u]
        s["seen"] = True
        ts = ev.get("ts")
        s["lastEvent"] = etype
        if isinstance(ts, int):
            s["lastTs"] = ts
            if etype in ("start", "heartbeat", "done"):
                s["lastHeartbeatTs"] = ts
        if etype in TERMINAL:
            s["terminal"] = etype
        if isinstance(ev.get("restart"), int):
            s["restart"] = max(s["restart"], ev["restart"])
        for fpath in ev.get("filesTouched", []) or []:
            if fpath not in s["filesTouched"]:
                s["filesTouched"].append(fpath)
        for fl in ev.get("flagged", []) or []:
            s["flagged"].append(fl)
        if ev.get("detail"):
            s["detail"] = ev["detail"]

    # Classify each unit. A terminal EVENT is trusted only with the evidence its
    # kind requires (see the protocol note): a bare "done" with no diff and a
    # bare "blocked" with no flagged items are exactly how a silent failure would
    # dress itself up as a terminal result, so they are demoted to a "-unverified"
    # status that is NOT terminal and keeps the gate closed.
    for u, s in state.items():
        term = s["terminal"]
        if term == "done":
            has_evidence = bool(s["filesTouched"]) or bool(s["flagged"])
            s["status"] = "done" if has_evidence else "done-unverified"
        elif term == "blocked":
            # The flagged list IS the reason a unit is blocked; without it the
            # claim is empty.
            s["status"] = "blocked" if s["flagged"] else "blocked-unverified"
        elif term == "demoted":
            # Orchestrator-authored disposition; terminal by definition.
            s["status"] = "demoted"
        elif not s["seen"]:
            s["status"] = "missing"          # never reported anything
        else:
            # started but not terminal — alive or stalled?
            hb = s["lastHeartbeatTs"]
            stale = (now is not None and isinstance(hb, int) and (now - hb) >= stall_threshold)
            if stale:
                s["status"] = "stalled"
            else:
                s["status"] = "running"
        # restart budget
        s["restartsExhausted"] = s["restart"] >= max_restarts

    return state, extraneous, malformed


# Statuses that count as a unit being genuinely accounted for (gate may open).
# The "-unverified" variants deliberately excluded: a claim without evidence is
# not a terminal result.
TERMINAL_STATUSES = {"done", "blocked", "demoted"}


def build_todo(state, max_restarts):
    restart, demote, wait, missing, verify = [], [], [], [], []
    for u, s in state.items():
        st = s["status"]
        if st in ("stalled", "missing"):
            if s["restartsExhausted"]:
                demote.append(u)   # tried enough; move to manual review
            elif st == "stalled":
                restart.append(u)
            else:
                missing.append(u)  # never started — dispatch it (attempt 0)
        elif st == "running":
            wait.append(u)
        elif st in ("done-unverified", "blocked-unverified"):
            # Claimed terminal but produced no evidence — treat like a stalled
            # worker: re-dispatch to actually do (and report) the work, or demote
            # if it has burned its restarts. This is what stops a bare "done"
            # from waving a silently-failed unit through the gate.
            (demote if s["restartsExhausted"] else verify).append(u)
    return {"restart": restart, "demote": demote, "dispatch": missing,
            "wait": wait, "verify": verify}


def main():
    ap = argparse.ArgumentParser(description="Liveness gate for parallel refactor workers.")
    ap.add_argument("--ledger", required=True, help="Path to the JSONL status ledger workers append to.")
    ap.add_argument("--plan", help="JSON file listing planned unit ids ({'units':[...]} or [...]).")
    ap.add_argument("--unit", action="append", help="Planned unit id (repeatable).")
    ap.add_argument("--now", type=int, default=None, help="Current reference tick for staleness math.")
    ap.add_argument("--stall-threshold", type=int, default=30, help="Ticks without heartbeat => stalled.")
    ap.add_argument("--max-restarts", type=int, default=2, help="Restarts before a unit must be demoted.")
    ap.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = ap.parse_args()

    units = load_plan(args)
    events = load_ledger(args.ledger)

    # Reference tick for staleness. Default to the highest ts in the ledger so a
    # plain re-run detects a worker that fell behind the pack WITHOUT the caller
    # having to thread a clock in. --now overrides (and is the only way to catch
    # the last remaining worker going silent, since then no newer event exists to
    # advance the ledger's own max). Explicit --now wins even if it's below the
    # ledger max, so a caller can deliberately look at an earlier point.
    ledger_max_ts = max((ev["ts"] for ev in events
                         if isinstance(ev.get("ts"), int)), default=None)
    now = args.now if args.now is not None else ledger_max_ts

    state, extraneous, malformed = summarize(
        units, events, now, args.stall_threshold, args.max_restarts
    )
    todo = build_todo(state, args.max_restarts)

    counts = {}
    for s in state.values():
        counts[s["status"]] = counts.get(s["status"], 0) + 1

    have_plan = bool(units)
    all_terminal = have_plan and all(s["status"] in TERMINAL_STATUSES for s in state.values())
    # The gate: green ONLY with a plan AND every planned unit in a verified
    # terminal status (evidence-less "-unverified" claims do NOT count).
    gate_open = all_terminal

    blocked_count = counts.get("blocked", 0)
    demoted_count = counts.get("demoted", 0)

    report = {
        "ledger": args.ledger,
        "now": now,
        "nowSource": "arg" if args.now is not None else ("ledgerMax" if ledger_max_ts is not None else "none"),
        "stallThreshold": args.stall_threshold,
        "maxRestarts": args.max_restarts,
        "planKnown": have_plan,
        "units": [state[u] for u in units],
        "counts": counts,
        # Surfaced so an all-blocked / heavily-demoted run that legally opens the
        # gate can't be mistaken for a clean migration — Phase 5 must emit a
        # manual-review report for these.
        "blockedCount": blocked_count,
        "demotedCount": demoted_count,
        "manualReviewCount": blocked_count + demoted_count,
        "todo": todo,
        "extraneousEvents": len(extraneous),
        "malformedLines": len(malformed),
        "gateOpen": gate_open,
    }
    print(json.dumps(report, indent=2))

    if not args.json:
        e = sys.stderr
        print("", file=e)
        print("=== worker observation ===", file=e)
        if not have_plan:
            print("  NO PLAN PASSED — cannot verify completeness. Pass --plan/--unit.", file=e)
        marks = {"done": "✓", "blocked": "▣", "demoted": "⇩ MANUAL", "running": "…",
                 "stalled": "✗ STALLED", "missing": "✗ MISSING",
                 "done-unverified": "✗ DONE (no evidence)",
                 "blocked-unverified": "✗ BLOCKED (no reason)"}
        for u in units:
            s = state[u]
            mark = marks.get(s["status"], s["status"])
            extra = f" (restarts={s['restart']}{'/EXHAUSTED' if s['restartsExhausted'] else ''})" if s["restart"] else ""
            flg = f" [{len(s['flagged'])} flagged]" if s["flagged"] else ""
            fls = f" [{len(s['filesTouched'])} files]" if s["filesTouched"] else ""
            print(f"  {mark:<22} {u}{extra}{flg}{fls}", file=e)
        if todo["restart"]:
            print(f"  RESTART now : {', '.join(todo['restart'])}", file=e)
        if todo["verify"]:
            print(f"  RE-DISPATCH (claimed terminal, no evidence): {', '.join(todo['verify'])}", file=e)
        if todo["dispatch"]:
            print(f"  DISPATCH    : {', '.join(todo['dispatch'])}", file=e)
        if todo["demote"]:
            print(f"  DEMOTE→review: {', '.join(todo['demote'])} (restart budget exhausted — write a 'demoted' event)", file=e)
        if todo["wait"]:
            print(f"  still running: {', '.join(todo['wait'])}", file=e)
        if report["manualReviewCount"]:
            print(f"  ⚠ {report['manualReviewCount']} unit(s) need MANUAL review "
                  f"(blocked={blocked_count}, demoted={demoted_count}) — Phase 5 must report these, "
                  f"not silently count them as migrated", file=e)
        if malformed:
            print(f"  ⚠ {len(malformed)} malformed ledger line(s) ignored", file=e)
        if extraneous:
            print(f"  ⚠ {len(extraneous)} event(s) for units not in the plan", file=e)
        print(f"  now={now} (source={report['nowSource']}, stall≥{args.stall_threshold})", file=e)
        print(f"  GATE: {'OPEN — all units terminal, safe to enter Phase 5' if gate_open else 'CLOSED — do NOT proceed to validate/report'}", file=e)

    # Exit code IS the gate. 0 only when every planned unit is terminal.
    sys.exit(0 if gate_open else 1)


if __name__ == "__main__":
    main()

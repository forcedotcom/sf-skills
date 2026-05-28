---
name: investigating-agentforce-d360
description: "Data Cloud 360° view of a single Agentforce session. Pulls 24 STDM + GenAI DMO rows via the DC Query REST API, assembles a hierarchical session tree (Interaction → Step → Generation → GatewayRequest), renders a human-readable summary with transcript + per-turn topic/action invocations + LLM generations + tool calls + audit chain. TRIGGER when user asks to trace, inspect, summarize, or describe a specific Agentforce session by session id (Agent Session UUID `019d…` or MessagingSession id `0Mw…`). Also triggers on session discovery — find/list/search sessions by time, agent, channel, outcome, or conversation text — when the user has no session id yet. DO NOT TRIGGER for design-time architecture questions (use investigating-agentforce-architecture instead) or for runtime perf/latency/SLO questions that require platform telemetry beyond Data Cloud."
license: Apache-2.0
compatibility: "Requires Agentforce license, Data Cloud enabled on the target org, sf CLI authenticated to target org, Python 3.10+"
metadata:
  version: "1.0"
  last_updated: "2026-05-28"
  author: "Raghul Jayagopal (RJ), Salesforce ANZ FDE"
---

# investigating-agentforce-d360 — Data Cloud 360° session view

Hierarchical session reconstruction from Data Cloud STDM + GenAI DMOs for one Agentforce session. Three stages — fetch → assemble → render. Typical wall-clock: ~10–30s for a ~15-turn session.

The pipeline is **DC-only**: it reads runtime audit rows that Data Cloud has materialized. It is **not** a runtime-availability tool — see "DC-only blind spot" below for what this skill cannot answer.

## When to use

Trigger this skill when the user:
- Asks to **trace / inspect / describe / summarize** a specific Agentforce session by id.
- **Doesn't have a session id?** Asks to **find / list / search / discover** sessions by time / agent / channel / outcome / conversation text. The skill runs a Data Cloud discovery query, prints a numbered picker, and the user picks one UUID to trace.
- Says things like: "trace session `<uuid>`", "summarize what happened in `0Mw…`", "find escalated sessions today on Messaging in `<org>`", "Data Cloud snapshot for session `<uuid>`".

**DO NOT trigger** when the question is about:
- The agent's **declared architecture** — topic/action tree, flow inventory, Apex classes, prompt templates. Use `investigating-agentforce-architecture` instead.
- Runtime **availability** questions — *which* topic/action was *eligible* for the planner on a given turn, or *why* the LLM picked one over another. DC alone can't answer these (see "DC-only blind spot").

## If the user hasn't given enough to proceed

When invoked with no session id AND no discovery criteria, print this block **verbatim** — do not paraphrase, do not pre-run any script. Trigger condition: the input is empty OR contains no session-id shape (neither a UUID nor a `0Mw…` messaging id) AND no discovery expression (no time phrase / `--agent` / `--channel` / `--outcome` / `--grep` / verbs like "find" / "list").

> Which session should I pull from Data Cloud, and in which org?
>
> I need:
> - **Session id** — either an Agent Session UUID (`019db7f6-…`) or a MessagingSession id (`0Mw…`, 15/18 chars).
>   - **No session id?** — Tell me what you remember and I'll find it: how recent (e.g. "last 2 hours", "today", a date), which agent, which channel (Messaging / Builder / Voice), how it ended (escalated, user ended, transferred, timed out), or a phrase from the conversation. I'll show matching sessions as a numbered list — you pick one, I pull it.
> - **Org alias** — for `sf` CLI auth (the alias you configured with `sf org login`).
>
> Artifacts land in `~/.claude/data/investigating-agentforce-d360/<org_id15>/<agent>__<ver>/<session_id>/`.

## Session id forms — UUID or MessagingSession id

Both forms are accepted on `--session`:

| Form | Example | Resolution |
|---|---|---|
| Agent Session UUID | `019dface-0000-7000-8000-000000000002` | Pass-through |
| MessagingSession id (`0Mw` prefix) | `0MwTESTMSG12345AAA` | Resolved via `resolve_session.py` — live DC lookup on first fetch, disk-first thereafter |

**Multi-match is real.** One MessagingSession id can map to multiple Agent Session UUIDs. On multi-match the resolver prints every candidate and exits non-zero; the user re-invokes with a specific UUID.

Artifacts always land under `~/.claude/data/investigating-agentforce-d360/<org_id15>/<agent>__<ver>/<session_id>/` — the messaging id is a lookup key only, never a directory name. The dominant agent (first in `sorted(agents_observed)`) names the `<agent>__<ver>/` segment.

## Resolving the script prefix

The default install puts the skill under `~/.claude/skills/`. If the skill
was cloned somewhere else (e.g. directly from the `forcedotcom/sf-skills`
repo into a custom path), set `SKILL_ROOT` to point at the skill directory.

```bash
prefix="${SKILL_ROOT:-$HOME/.claude/skills/investigating-agentforce-d360}/scripts"
```

Every subsequent invocation in this doc uses `"$prefix/..."`.

## First-run permissions

On first invocation only, run the allowlist grant. This registers the skill's
`python3 scripts/*.py` and `sf org display ...` invocation patterns into
Claude Code's `permissions.allow` list in `~/.claude/settings.json`, so the
subsequent fetch / assemble / render stages don't prompt for permission on
every shell call. The script is idempotent — subsequent runs see the
sentinel file (`~/.claude/.investigating-agentforce-d360.allowlist-done.v1`)
and exit immediately. Reads/writes only `~/.claude/`; touches no org data.

```bash
python3 "${SKILL_ROOT:-$HOME/.claude/skills/investigating-agentforce-d360}/tools/grant_allowlist.py"
```

## Session discovery (no id yet)

When the user doesn't have a session id, run `discover_sessions.py` against the STDM session DMO. Prints a numbered picker; user picks one; proceed with the chosen UUID.

```bash
python3 "$prefix/discover_sessions.py" --org <alias> [filters...]
```

**Filters** (all optional except `--org`): `--since <expr>` (default last 24h; accepts "last 2 hours", "today", ISO dates), `--agent <api-name>`, `--channel <Messaging|Builder|Voice>`, `--outcome <USER_ENDED|ESCALATED|TRANSFERRED|TIMEOUT|NOT_SET>`, `--grep <substring>` (conversation text), `--tz <IANA>`, `--limit <N>` (default 20).

**Output**: markdown table with `#`, `UUID`, `Start (UTC)`, `Agent`, `Channel`, `Duration`, `Outcome`. User replies with a number; proceed with that UUID.

## Pipeline — three stages

```
fetch_dc.py     →  24 dc.<name>.json + dc._session_manifest.json     (DC Query REST waterfall, 5 waves)
assemble_dc.py  →  dc._session_tree.json                             (pure in-memory hierarchical join)
render_dc.py    →  dc._session_summary.md                            (human summary, multi-section)
```

Each stage is independently runnable. `fetch_dc.py --session <sid> --org <alias>` chains all three by default.

### Invocation

```bash
python3 "$prefix/fetch_dc.py" --session <session-id-or-messaging-id> --org <alias>
```

Flags: `--verbose` for per-DMO row counts; `--no-assemble` / `--no-render` to stop early.

### Output artifacts

Everything lands under `~/.claude/data/investigating-agentforce-d360/<org_id15>/<agent>__<ver>/<session_id>/`:

```
dc.sessions.json              dc.steps.json                dc.gateway_requests.json
dc.interactions.json          dc.messages.json             dc.gateway_responses.json
dc.participants.json          dc.generations.json          dc.gateway_request_llm.json
dc.content_quality.json       dc.content_category.json     dc.gateway_request_metadata.json
dc.tags.json                  dc.tag_definitions.json      dc.gateway_request_tags.json
dc.tag_associations.json      dc.tag_definition_associations.json
dc.feedback.json              dc.feedback_details.json     dc.gateway_records.json
dc.moments.json               dc.moment_interactions.json
dc.telemetry_spans.json       dc.app_generation.json

dc._session_manifest.json     (per-DMO row counts + empties)
dc._session_tree.json         (hierarchical join — session → interactions → steps → messages → generations → gateway)
dc._session_summary.md        (rendered human summary)
```

Zero-row queries are recorded in the manifest with `status: empty`; no file is written. `assemble_dc` tolerates missing files. See `references/artifacts.md` for the full read order.

## The DC-only blind spot — read before committing to a root cause

DC alone answers **what happened** — steps that ran, generations that fired, gateway requests that were logged. It does NOT answer **what could have happened but didn't**:

- Which **topics were eligible** for the classifier on a given turn (this lives in runtime planner telemetry, not DC).
- Which **actions were declared** on a topic vs. which **survived rule expressions** and were actually offered to the LLM.
- Why the LLM picked one topic/action over another (the full prompt + response text only lives in the planner runtime telemetry).

If the user's question is about *why a particular topic or action was or wasn't used*, DC-only is almost never sufficient. **Tell the user**: "Availability questions need the runtime planner trace for that turn — which is outside this skill's Data Cloud surface. Check the platform telemetry that mirrors the planner's logged decisions." Don't fabricate a root cause from runtime-only evidence.

### What DC IS good at

- **What ran** — every step, every LLM call, every gateway request + response, in order, with timestamps and durations. Good for "walk me through the session".
- **What the user saw** — full message transcript (user + agent), ordered.
- **What the LLM produced** — generations, token counts, trust scores (toxicity, instruction adherence, content-category breakdown from `content_quality` + `content_category`).
- **Tool invocations** — action calls, inputs, outputs, errors (from `gateway_request_metadata` + `gateway_records`).
- **Feedback + flags** — user feedback, escalation markers, session-end type.
- **Audit integrity** — the 1:1 invariant between GatewayRequest and GatewayResponse is checked; drift is flagged in `counts.audit_chain_1to1_ok`.

## Prerequisites

| Tool | Required |
|---|---|
| `sf` CLI (authenticated against the target org) | yes — `sf org login web --alias <alias>` |
| Data Cloud enabled on the target org | yes — the STDM + GenAI DMOs must have materialized for the session |
| Python 3.10+ | yes — pipeline scripts |

## Typical prompts — what they map to

| User says | Skill does |
|---|---|
| *"Trace session `<uuid>` in my-org"* | `fetch_dc.py --session <uuid> --org my-org` → assemble → render |
| *"Summarize what happened in `0Mw…`"* | Resolve `0Mw…` → UUID, then full DC pipeline |
| *"Find escalated sessions today in my-org on Messaging"* | Run `discover_sessions.py --since today --outcome ESCALATED --channel Messaging`, print picker, user picks, then DC pipeline |
| *"Walk me through this session"* | Same as trace — read the rendered summary top to bottom |

## What comes back to the user

After the pipeline completes, the rendered `dc._session_summary.md` carries these top-level sections:

1. **Session identity** — UUID, start/end, duration, agent, channel, end type, participant counts
2. **Session bootstrap** — channel mode + bootstrap variables (`identity.mode`, `identity.bootstrap_variables`)
3. **ID reference** — full UUIDs for everything truncated in the hierarchical trace
4. **Transcript** — USER ↔ AGENT narrative per TURN interaction
5. **Complete hierarchical trace** — Interaction → Step → Generation → GatewayRequest, with `+start + duration = +end` math
6. **Per-turn summary** — one row per interaction
7. **Planner LLM calls (full prompts + responses)** — opt-in via `--show-prompts`; suppressed by default
8. **Visual analysis** — gantt + LLM-call overlay
9. **Session counts** — engineer-facing table of manifest counts
10. **Empties diagnostics** — one row per DMO with `rows == 0` and a populated `_unavailable_reason`
11. **Catalog (session-filtered)** — TagDefinitions / TagDefinitionAssociations / Tags filtered to agents observed in the session

For deep-dive, open `dc._session_tree.json` — the single source of truth the summary was rendered from. See `references/dc_pipeline_contract.md` for the full pipeline contract and `references/dc_dmo_fields.md` for per-DMO field reference.

## Caveats

- **`gateway_requests_dropped_by_stdm`** — when DC reports zero `gateway_requests` rows but runtime telemetry would show LLM calls did fire, this skill cannot definitively distinguish "STDM exporter dropped writes" from "logging genuinely disabled at the source". The session is reported as `planner_ran_no_gateway_logs`; the operator can check platform telemetry to disambiguate. See `references/dc_pipeline_contract.md` §2.8.
- **Latency** — Generation and GatewayRequest carry single-write timestamps, not start/end pairs. The renderer does not compute "latencies" between them — that delta reflects DC's serialization order, not how long the LLM call took.
- **Data Cloud materialization lag** — fresh sessions may show `interactions_not_materialized_yet` if STDM hasn't caught up. Re-run after a minute or two.

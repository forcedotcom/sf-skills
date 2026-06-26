# agentforce-d360-analyze

Data Cloud 360° view of a single Agentforce session. Pulls 24 STDM + GenAI DMOs from Salesforce Data Cloud, assembles a hierarchical session tree (Interaction → Step → Generation → GatewayRequest), and renders a human-readable markdown summary.

This skill is **DC-only** — it reads runtime audit data that Salesforce Data Cloud has materialized for a session. It does not call into runtime telemetry, performance services, or any Splunk / observability surface.

Input: an Agent Session UUID (`019d…`) **or** a MessagingSession id (`0Mw…`, 15/18 chars), and an `sf` CLI org alias.

Output: per-DMO JSON artifacts plus three derived files under `~/.vibe/data/agentforce-d360-analyze/<org_id15>/<agent>__<version>/<session_id>/` (default; override per-script with `--data-dir <path>`):

- `dc.<name>.json` — 24 raw DMO results (one per query in the waterfall)
- `dc._session_manifest.json` — per-DMO row counts, classified `session_shape`, and empty-by-design reasons
- `dc._session_tree.json` — hierarchical join (the primary artifact; the summary is rendered from this)
- `dc._session_summary.md` — human-readable summary, up to 11 sections

---

## Runtime budget

**~10–30s typical** on a 15-turn session. The 5-wave fetch waterfall fans out 24 queries; later waves depend on ids harvested from earlier waves, so wave-to-wave is sequential, but each wave's queries run concurrently within the wave.

---

## Prerequisites

| Tool | Why |
|---|---|
| `sf` CLI (authenticated against the target org) | Shells `sf org display --target-org <alias> --json` for the Data Cloud Query REST API access token |
| Data Cloud enabled on the target org | Required — the STDM + GenAI DMOs must have materialized for the session |
| Python 3.10+ | `pathlib`, dataclasses, `\|` union types |

---

## Usage

Invoked conversationally through whatever skill-aware runtime hosts it. Example prompts:

| User says | Skill does |
|---|---|
| `trace session 019dface-... in my-org` | Run the 3-stage pipeline: fetch → assemble → render |
| `summarize what happened in 0MwTESTMSG12345AAA` | Resolve the messaging id → UUID, then run the pipeline |
| `find escalated sessions today on Messaging in my-org` | Run `discover_sessions.py`, print a numbered picker, user picks one, then run the pipeline |
| `walk me through this session` | Same as trace — the rendered summary reads top-to-bottom |

See `SKILL.md` for the full TRIGGER conditions, flag table, and the "DC-only blind spot" guidance.

---

## Pipeline

Three stages, each independently runnable:

```
fetch_dc.py     →  24 dc.<name>.json + dc._session_manifest.json   (DC Query REST waterfall)
assemble_dc.py  →  dc._session_tree.json                           (in-memory hierarchical join)
render_dc.py    →  dc._session_summary.md                          (markdown rendering)
```

`fetch_dc.py --session <sid> --org <alias>` chains all three by default. Pass `--no-assemble` / `--no-render` to stop early.

---

## Artifacts read order

1. **`dc._session_summary.md`** — human-readable, top-to-bottom answers "what happened in this session?"
2. **`dc._session_tree.json`** — single source of truth, the hierarchical join the summary was rendered from
3. **`dc._session_manifest.json`** — open this when something looks missing in the tree (per-DMO row counts, empty-by-design reasons)
4. **`dc.<name>.json`** — raw per-DMO rows, only when the manifest reports an unexpected count

See `references/artifacts.md` for the full inventory.

---

## What this skill does NOT answer

DC alone tells you **what happened** — every step, every LLM call, every gateway request, in order, with timestamps. It does **not** tell you **what could have happened but didn't**:

- Which **topics were eligible** for the classifier on a given turn
- Which **actions survived rule expressions** and were actually offered to the LLM
- Why the LLM picked one topic/action over another

If the user's question is about *why a particular topic or action was or wasn't used*, DC-only is almost never sufficient. See "DC-only blind spot" in `SKILL.md`.

For design-time architecture questions (topic/action tree, flow inventory, Apex classes, prompt templates), use the sibling skill `agentforce-architecture-analyze` instead.

---

## Layout

```
agentforce-d360-analyze/
├── SKILL.md                               ← runtime-parsed entry point (TRIGGER / DO NOT TRIGGER, flags, prompts)
├── README.md                              ← this file
├── scripts/
│   ├── fetch_dc.py                        ← 5-wave DC fetch + chained pipeline driver
│   ├── assemble_dc.py                     ← in-memory hierarchical join → dc._session_tree.json
│   ├── render_dc.py                       ← markdown rendering → dc._session_summary.md
│   ├── discover_sessions.py               ← session picker by time / agent / channel / outcome / grep
│   ├── resolve_session.py                 ← `0Mw…` MessagingSession id → Agent Session UUID
│   ├── dc.py                              ← DC Query REST API client (load_sql, post)
│   ├── storage.py                         ← per-session JSON writer (path-validated)
│   ├── config.py                          ← shared constants + DATA_ROOT re-export
│   ├── _shared/                           ← path / SQL helpers (paths, fs_guard, sql)
│   └── tests/                             ← pytest suite (372 tests + 18 subtests)
├── references/
│   ├── artifacts.md                       ← the full per-session artifact inventory
│   ├── dc_dmo_fields.md                   ← per-DMO field reference + cross-DMO join map
│   └── dc_pipeline_contract.md            ← pipeline contract: tree shape + render-stage section list
└── assets/
    └── dc/                                ← 26 .sql templates loaded by dc.load_sql
```

---

## Authored by

Raghul Jayagopal (RJ), Salesforce ANZ FDE.

---

## License

Apache-2.0. See repository root `LICENSE`.

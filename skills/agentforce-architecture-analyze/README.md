# agentforce-architecture-analyze

Declared architecture snapshot for a single Agentforce agent: planner + topics + actions + flows + Apex + prompts + NGA plugins. Reads design-time metadata only (`BotDefinition` + `GenAi*` Tooling objects + Metadata API retrieve) — no runtime audit data.

Input: an `agent_api_name` (the `BotDefinition.DeveloperName`) and an org alias. Optional `agent_version_api_name` to pin a version; otherwise the active `BotVersion` resolves.

Output: two files under `~/.vibe/data/agentforce-architecture-analyze/<org_id15>/<agent>__<version>/` — a normalized `<agent>_<ver>_metadata_tree.json` and a human-readable `<agent>_<ver>_architecture.md`. Override with `--data-dir <path>` (other runtimes pass this to land artifacts under their own distribution layout).

---

## Runtime budget

**30–45s typical, ≤60s hard cap** on the reference fixtures.

A naive sequential implementation (Metadata API retrieves only) would take 90–220s. Speedup: **3–5×**.

Scaling note: large bots with many flows scale approximately linearly in flow count. Each Flow metadata retrieve is an individual SOQL round-trip; a 20-flow bot takes proportionally longer than a 5-flow bot. The 7 planner-side Tooling SOQL fan-outs are constant-cost (single fan-out regardless of bot size); the flow/apex body fetch wave scales with ref count.

---

## Prerequisites

| Tool | Why |
|---|---|
| `sf` CLI (authenticated against the target org) | Shells `sf org display --target-org <alias> --json` for access token, and `sf sobject describe` for the 7-day channel probe |
| Python 3.10+ | `pathlib`, dataclasses, `\|` union types, `concurrent.futures` |

---

## Usage

Invoked conversationally through whatever skill-aware runtime hosts it. Example prompts:

| User says | Skill does |
|---|---|
| `document the architecture of MyAgent in my-org-alias` | Resolve active version, fetch tree, render architecture.md + Mermaid |
| `draw the invocation graph for MySalesAgent v5 in my-org-alias-3` | Same, pinned to v5 |
| `what tools does MyAgent2 have in my-org-alias-2` | Fetch tree, surface the plugin/function inventory from the rendered architecture.md |
| `re-fetch the architecture of MyAgent — I think metadata changed` | Pass `--force` to bypass the cache |

See `SKILL.md` for the full flag table and sample prompts.

---

## Directory layout

```
agentforce-architecture-analyze/
├── SKILL.md                       Skill contract (inputs, outputs, pipeline, invariants)
├── README.md                      This file
├── assets/
│   ├── soql/*.soql                Tooling + Data SOQL templates
│   ├── cli/*.yaml                 sf CLI recipes (subprocess invocation specs)
│   └── mermaid/*.mmd              Mermaid templates for the invocation graph
├── references/
│   ├── soql_fields.md             Per-sObject field reference (13 sObjects)
│   ├── architecture_sections.md   Section-by-section structure of the rendered architecture.md
│   └── contract.json              metadata_tree.json schema contract
├── scripts/
│   ├── _shared/                   Path helpers + fs_guard validators + sql escapers
│   ├── main.py                    Orchestrator entry point
│   ├── config.py                  Shared paths, cache TTLs, validated path builders
│   ├── soql_loader.py             Template loader with fs_guard-validated substitution
│   ├── sf_cli.py                  sf CLI subprocess wrapper (yaml.safe_load + stderr redaction)
│   ├── rest_client.py             urllib wrapper (Authorization-stripping redirect handler)
│   ├── resolve_bot.py             BotDefinition + BotVersion + planner name lookup
│   ├── retrieve_planner.py        Metadata retrieve for GenAiPlannerBundle + NGA plugins
│   ├── parallel_retrieve.py       7-channel parallel Tooling SOQL fan-out
│   ├── parse_bundle.py            XML → normalized node shapes
│   ├── parse_wave.py              BFS expansion of flow/apex/prompt refs
│   ├── probe_channels.py          7-day-TTL channel describe probe
│   ├── cache_check.py             Asset-hash-aware cache freshness
│   ├── finalize.py                Merge waves → metadata_tree.json
│   ├── render_architecture.py     architecture.md + Mermaid graph
│   ├── resolve_invocation_target.py  ID-prefix router for NGA InvocationTargets
│   ├── emit_env.py                Env-var emit helper (Phase 0.5)
│   ├── emit_result.py             Final RESULT block renderer
│   ├── sanitize.py                Stdin → safe-string filter
│   ├── write_emit_ctx.py          Per-phase ctx writer
│   └── tests/                     Unit + integration tests (unittest)
```

---

## Architecture

### Channel strategy — SOQL-first

```
Seed query: planner_definition_by_agent_chain (chain-LIKE lookup → planner id)

6 parallel Tooling SOQL channels (keyed on the resolved planner id):
    - plugins_by_planner
    - planner_bundle_functions (join)
    - functions_by_plugins
    - planner_attrs_by_parent_ids
    - plugin_functions_by_plugin_ids (join)
    - plugin_instructions_by_plugin_ids

+ Data API SOQL for Flow / Apex bodies (batched by id list)
+ Metadata retrieve ONLY for:
    - GenAiPromptTemplate (prompt bodies)
    - NGA external plugins (when planner is ConcurrentMultiAgentOrchestration etc.)
```

Most of the 3–5× speedup over a naive Metadata-API-only implementation comes from collapsing a sequential zip-retrieve chain into a single Tooling SOQL fan-out.

### Planner normalization — classic ReAct vs NGA

One tree shape, two planner families:

| `PlannerType` examples | Family | InvocationTarget style |
|---|---|---|
| `ReactAiPlannerV1`, `SequentialPlannerIntentClassifier` | Classic ReAct | DeveloperName strings |
| `ConcurrentMultiAgentOrchestration`, `AnthropicCompatibleV1` | NGA | Sometimes 15/18-char Ids (ID-prefix routed) |

`resolve_invocation_target.py` routes NGA InvocationTargets by Salesforce ID prefix (`01p` → ApexClass, `301` → Flow, etc.). Unknown prefixes become `_unresolved[]` entries with `reason="unknown-id-prefix:<prefix>"` — never silently dropped.

### Cache layers

1. **Tree cache** — `metadata_tree.json` is reused unless `--force`. Cache key includes asset-hashes of every SOQL / YAML / Mermaid template shipped with the skill, so changing a template busts the cache automatically.
2. **Channel probe cache** — 7-day TTL on `sf sobject describe` results for the 13 sObjects the skill touches. `--reprobe` forces a refresh (needed after Salesforce quarterly releases that rename / remove fields). Mandatory-field gate: a probe that sees any mandatory field missing (per `probe_channels.MANDATORY_FIELDS`) flips `status: PROBE_FAILED` so the caller surfaces a clean error.

---

## Key behaviors

### Idempotence

Re-running the same `(org, agent, version)` overwrites prior artifacts in place. Safe to run repeatedly during development.

### Partial-results surfacing

No silent drops. Any unresolved ref — unknown ID prefix, failed SOQL, missing describe field — lands in `_unresolved[]` with a `reason=...` string. Top-level `STATUS` is `OK` on a clean run, `PARTIAL_OK` when any channel degrades.

### Cycle handling

Per-branch ancestor-path cycle detection is the primary termination primitive: the same flow visited along its own ancestor chain emits `_cycle_back_to:<path>` instead of recursing. `MAX_BFS_DEPTH=20` is a defensive last-resort guard against pathological graphs that evade per-branch detection; real-world agents bottom out well before that.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `sf org display failed` | Re-authenticate: `sf org login web --alias <alias>` |
| `INVALID_FIELD` from a SOQL asset | Salesforce renamed / removed the field in a quarterly release. Run with `--reprobe` to refresh the 7-day channel cache and pick up the new schema |
| `STATUS=PROBE_FAILED` on first run | Channel probe saw a mandatory field missing. Check `channels.json` under the probe cache dir for which sObject / field — may require org-side feature enablement |
| Tree for classic ReAct agent shows `_unresolved` entries for NGA plugins | Expected — the NGA external-plugin retrieve is skipped when the planner shape is classic. Those entries can be ignored |

---

## Author

Raghul Jayagopal (RJ), Salesforce ANZ FDE.

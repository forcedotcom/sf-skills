---
name: agentforce-architecture-analyze
description: "Declared architecture snapshot for one Agentforce agent: planner, topics, actions, flows, Apex, prompt templates, and NGA plugins. Renders a human-readable architecture document and Mermaid invocation graph from design-time metadata (not runtime audit rows). TRIGGER when user asks to describe, diagram, inventory, audit, document, or diff (e.g. v3 vs v5) the architecture / action tree / topic structure / tool inventory of a specific agent by agent API name in a specific org. DO NOT TRIGGER for runtime session traces, conversation transcripts, generation timings, or gateway audit chains — this skill reads design-time metadata only (use agentforce-d360-analyze for session traces)."
metadata:
  version: "1.0"
  domains: ["Agentforce"]
  minApiVersion: "64.0"
  relatedSkills:
    - "agentforce-d360-analyze"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.136.8"
    - tool: ["python3"]
      semver: ">=3.10.0"
---

# agentforce-architecture-analyze — declared architecture snapshot

Design-time metadata tree for one Agentforce agent: planner → topics → actions → flows → Apex → prompts → NGA plugins. Reads declared metadata only — `BotDefinition`, `GenAiPlanner*`, `GenAiPlugin*`, `GenAiFunction*`, `Flow`, `ApexClass`, `GenAiPromptTemplate`. Does **not** read runtime audit rows.

**Runtime budget: 30–45s typical, ≤60s hard cap** on reference fixtures. Sequential baseline would be 90–220s; parallel Tooling SOQL fan-out delivers a 3–5× speedup. Large bots with many flows scale approximately linearly — each flow metadata retrieve is one round-trip.

Runs **inline** — no subagent. Every phase is deterministic file processing.

## If the user hasn't named an agent

Trigger condition: `$ARGUMENTS` names no agent (no `--agent` flag and no exact `BotDefinition` API name in the prose). Never invent an agent name. Instead, discover what the org actually contains — one read-only query, no pipeline yet. Use the `--org` alias if given, otherwise the default target org (omit `--target-org`):

```bash
sf data query --query "SELECT DeveloperName, MasterLabel FROM BotDefinition ORDER BY DeveloperName" \
  [--target-org <alias>] --json
```

If the user gave no org alias, the pipeline block defaults `--org` to the CLI default target org itself (`sf config get target-org --json` → `.result[0].value`) — you don't need to resolve it.

Then branch on the rows returned:

- **Zero agents** — tell the user the org has no Agentforce agents and stop. Do not fabricate an agent or a tree.
- **Exactly one agent, or exactly one whose `DeveloperName`/`MasterLabel` matches the user's description** (e.g. "support", "service", "sales") — use it, say explicitly which agent you picked and why, then run the pipeline block below with `ARG_AGENT=<DeveloperName>` (and `ARG_ORG=<alias>` if the user named one) set as its first lines, e.g. `ARG_AGENT=Customer_Support_Agent`. The block reads `ARG_*` from the environment; flags in `$ARGUMENTS` still override.
- **Otherwise** — print the block below, with the discovered agents listed as a numbered `DeveloperName — MasterLabel` table under the first line, and wait for the user to pick.
- **Query fails** (no default org, auth error) — print the block below without the list.

> Which agent should I document, and in which org?
>
> I need:
> - **Agent API name** — the `DeveloperName` of the `BotDefinition` (e.g. `MyAgent`, `MySalesAgent`). Not the label.
> - **Org alias** — for `sf` CLI auth (the alias you configured with `sf org login`)
>
> Optional:
> - **Version** — an `agent_version_api_name` like `v5`. If omitted, I'll resolve the active `BotVersion`.
> - **`--force`** — ignore cached tree; re-fetch everything.
> - **`--reprobe`** — re-run the 7-day channel-probe cache (only needed after a Salesforce release).
>
> I'll run the metadata pipeline inline. Artifacts land under `~/.vibe/data/agentforce-architecture-analyze/<org_id15>/<agent_api_name>__<agent_version>/` (overridable with `--data-dir`).

## Pipeline invocation

Run this block once the agent is known — from `--agent <api_name>` in `$ARGUMENTS`, or preset as `ARG_AGENT=<DeveloperName>` after discovery. `--org` (or `ARG_ORG`) is optional; without it the CLI default target org is used. One `python3` invocation drives the full pipeline. `main.py` writes `.emit_ctx.json`; `emit_result.py` reads it and prints the final `=== RESULT ===` block last to stdout.

```bash
set -euo pipefail

# zsh arrays are 1-indexed by default; bash arrays are 0-indexed.
# This block uses 0-indexed semantics throughout (_args[$i] starting at i=0),
# so under zsh + `set -u` the very first read of `_args[0]` would trip
# `parameter not set`. KSH_ARRAYS makes zsh treat arrays as 0-indexed,
# matching the bash shebang's expectation. No-op under bash.
[ -n "${ZSH_VERSION:-}" ] && setopt KSH_ARRAYS

# <SKILL_DIR> = absolute path of this skill's own directory (the folder holding
# this SKILL.md); substitute it from the skill path in context. Runtimes install
# skills in different places, so also probe the known install roots and use the
# first that actually contains this skill's scripts. An exported SKILL_ROOT wins.
_skill=agentforce-architecture-analyze
for _c in "${SKILL_ROOT:-}" "<SKILL_DIR>" \
          "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/$_skill}" \
          "${VIBES_SKILLS_DIR:+$VIBES_SKILLS_DIR/$_skill}" \
          "$HOME/.claude/skills/$_skill" "$PWD/.claude/skills/$_skill" \
          "${PLUGIN_ROOT:-$HOME/.vibe/skills}/$_skill"; do
  [ -n "$_c" ] || continue
  # Some stagers (ADK eval) nest the bundled files under <skill>/artifacts/.
  for _r in "$_c" "$_c/artifacts"; do
    [ -f "$_r/scripts/main.py" ] && { SKILL_ROOT="$_r"; break 2; }
  done
done
[ -f "${SKILL_ROOT:-}/scripts/main.py" ] || { echo "$_skill: scripts not found — set SKILL_ROOT to this skill's directory" >&2; exit 1; }

# Argument parser. Accepts both `--org foo` and `--org=foo`.
# `$ARGUMENTS` is the raw user input Claude Code substitutes; it may be unset
# or plain prose. Each ARG_* starts from the environment, so a value resolved
# during discovery can be preset (e.g. `ARG_AGENT=MyAgent` on the first line);
# flags in $ARGUMENTS still override.
ARG_ORG="${ARG_ORG:-}"
ARG_AGENT="${ARG_AGENT:-}"
ARG_VERSION="${ARG_VERSION:-}"
ARG_FORCE="${ARG_FORCE:-}"
ARG_REPROBE="${ARG_REPROBE:-}"
ARG_PARALLELISM="${ARG_PARALLELISM:-}"
ARG_MAX_MERMAID="${ARG_MAX_MERMAID:-}"

# Word-split $ARGUMENTS (zsh needs SH_WORD_SPLIT for that) with globbing off
# so prose like `*` never expands to filenames.
[ -n "${ZSH_VERSION:-}" ] && setopt SH_WORD_SPLIT
set -f
# shellcheck disable=SC2206
_args=(${ARGUMENTS:-})
set +f
i=0
while [ $i -lt ${#_args[@]} ]; do
 tok="${_args[$i]}"
 case "$tok" in
 --org=*) ARG_ORG="${tok#--org=}" ;;
 --org) i=$((i+1)); ARG_ORG="${_args[$i]:-}" ;;
 --agent=*) ARG_AGENT="${tok#--agent=}" ;;
 --agent) i=$((i+1)); ARG_AGENT="${_args[$i]:-}" ;;
 --version=*) ARG_VERSION="${tok#--version=}" ;;
 --version) i=$((i+1)); ARG_VERSION="${_args[$i]:-}" ;;
 --parallelism=*) ARG_PARALLELISM="${tok#--parallelism=}" ;;
 --parallelism) i=$((i+1)); ARG_PARALLELISM="${_args[$i]:-}" ;;
 --max-mermaid-nodes=*) ARG_MAX_MERMAID="${tok#--max-mermaid-nodes=}" ;;
 --max-mermaid-nodes) i=$((i+1)); ARG_MAX_MERMAID="${_args[$i]:-}" ;;
 --force) ARG_FORCE="1" ;;
 --reprobe) ARG_REPROBE="1" ;;
 esac
 i=$((i+1))
done

# No org named anywhere: fall back to the sf CLI default target org
# (`sf config get target-org --json` -> .result[0].value). Extracted with sed
# so the block needs neither jq nor an inline interpreter; any failure leaves
# ARG_ORG empty and the usage block below fires.
if [ -z "$ARG_ORG" ] && command -v sf >/dev/null 2>&1; then
 _cfg="$(sf config get target-org --json 2>/dev/null || true)"
 _cfg="$(printf '%s\n' "$_cfg" | sed -n 's/.*"value"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' || true)"
 ARG_ORG="${_cfg%%$'\n'*}"
fi

# Usage block if required flags missing. Agent reads stderr,
# prints verbatim, and stops — does NOT pre-run main.py.
if [ -z "$ARG_ORG" ] || [ -z "$ARG_AGENT" ]; then
 cat >&2 <<'USAGE'
> Which agent should I document, and in which org?
>
> I need:
> - **Agent API name** — the BotDefinition.DeveloperName (e.g. `MyAgent`)
> - **Org alias** — for `sf` CLI auth (the alias you configured with `sf org login`);
>   only needed when no default target org is set (`sf config set target-org <alias>`)
>
> Optional flags:
> - `--version v5` — pin a specific BotVersion (default: Active+highest)
> - `--force` — bypass cache
> - `--reprobe` — force channel-probe refresh
> - `--parallelism N` — ThreadPoolExecutor size (default 5)
> - `--max-mermaid-nodes N` — cap Mermaid node count (default 80)
USAGE
 exit 2
fi

# Fresh work dir per invocation. Epoch + random suffix avoids collisions
# between concurrent runs on the same host.
WORK_DIR="/tmp/agentforce-architecture-analyze-$(date +%s)-$RANDOM"
mkdir -p "$WORK_DIR"

# Input validation at the boundary, BEFORE any python3 call.
# fs_guard exits 1 and prints an INVALID_INPUT RESULT block on failure;
# `|| exit 1` is mandatory — bare calls silently continue past failures.
python3 "$SKILL_ROOT/scripts/_shared/fs_guard.py" "$ARG_AGENT" agent_api_name api_name || exit 1
python3 "$SKILL_ROOT/scripts/_shared/fs_guard.py" "$ARG_ORG" org_alias not_empty || exit 1
python3 "$SKILL_ROOT/scripts/_shared/fs_guard.py" "$WORK_DIR" WORK_DIR symlink || exit 1
python3 "$SKILL_ROOT/scripts/_shared/fs_guard.py" "$WORK_DIR" WORK_DIR owned || exit 1
if [ -n "$ARG_VERSION" ]; then
 python3 "$SKILL_ROOT/scripts/_shared/fs_guard.py" "$ARG_VERSION" agent_version api_name || exit 1
fi

# Single python3 call drives all pipeline phases. main.py writes
# `.emit_ctx.json` into $WORK_DIR — emit_result.py then renders the
# RESULT block from that ctx. No subprocess-per-phase.
_main_args=(--org-alias "$ARG_ORG" --agent "$ARG_AGENT" --work-dir "$WORK_DIR")
[ -n "$ARG_VERSION" ] && _main_args+=(--version "$ARG_VERSION")
[ -n "$ARG_FORCE" ] && _main_args+=(--force)
[ -n "$ARG_REPROBE" ] && _main_args+=(--reprobe)
[ -n "$ARG_PARALLELISM" ] && _main_args+=(--parallelism "$ARG_PARALLELISM")
[ -n "$ARG_MAX_MERMAID" ] && _main_args+=(--max-mermaid-nodes "$ARG_MAX_MERMAID")

# main.py returns nonzero on terminal failures; we DON'T short-circuit —
# emit_result still publishes the failure RESULT block. `set -e` is
# temporarily relaxed around this single call.
set +e
python3 "$SKILL_ROOT/scripts/main.py" "${_main_args[@]}"
_rc=$?
set -e

# Final RESULT block is emit_result.py's stdout — MUST be the last thing
# stdout sees. emit_result exits 0 on render success; the bash harness
# propagates main.py's rc for the agent's exit status.
WORK_DIR="$WORK_DIR" python3 "$SKILL_ROOT/scripts/emit_result.py"
exit "$_rc"
```

## Inputs

| Input | Flag | Required | Default |
|---|---|---|---|
| `org_alias` | `--org` | no | sf CLI default target org (`sf config get target-org`) |
| `agent_api_name` | `--agent` | yes | — |
| `agent_version_api_name` | `--version` | no | active BotVersion |
| `force_refresh` | `--force` | no | false (honor cache) |
| `reprobe` | `--reprobe` | no | false (honor 7-day channel-probe cache) |
| `parallelism` | `--parallelism` | no | 5 |
| `max_mermaid_nodes` | `--max-mermaid-nodes` | no | 80 |
| `data_dir` | `--data-dir` | no | `~/.vibe/data/agentforce-architecture-analyze` |
| `cache_dir` | `--cache-dir` | no | `~/.vibe/cache/agentforce-architecture-analyze` |

## Outputs

All artifacts under `~/.vibe/data/agentforce-architecture-analyze/<org_id15>/<agent_api_name>__<agent_version>/` (default; override with `--data-dir <path>`):

```xml
<agent>_<ver>_metadata_tree.json   primary artifact — normalized planner/topic/action/flow/apex/prompt/plugin tree
<agent>_<ver>_architecture.md      human-readable section-by-section rendering (H1 + 7 numbered sections, plus a conditional Dependency graph appendix). Mermaid diagrams are embedded inside the relevant sections (Action tree, Data flow, and Dependency graph)
```

## Pipeline — inline, no subagent

```text
resolve_bot.py        → BotDefinition + BotVersion + planner name lookup
retrieve_planner.py   → Metadata API zip retrieve for GenAiPlannerBundle (+ NGA plugins if present)
parallel_retrieve.py  → 6 parallel Tooling SOQL channels fan out from the planner id
                          (resolved by the `planner_definition_by_agent_chain` seed query):
                          - plugins_by_planner (GenAiPluginDefinition)
                          - planner_bundle_functions (GenAiPlannerFunctionDef join)
                          - functions_by_plugins (GenAiFunctionDefinition)
                          - planner_attrs_by_parent_ids (GenAiPlannerAttrDefinition)
                          - plugin_functions_by_plugin_ids (GenAiPluginFunctionDef join)
                          - plugin_instructions_by_plugin_ids (GenAiPluginInstructionDef)
parse_bundle.py       → parse retrieved XML into normalized node shapes
parse_wave.py         → BFS expansion: flow/apex/prompt refs discovered in nodes
                          → SOQL for Flow/Apex bodies (batched by id list)
                          → Metadata retrieve ONLY for GenAiPromptTemplate (+ NGA external plugins conditionally)
finalize.py           → merge waves into metadata_tree.json
render_architecture.py → <agent>_<ver>_architecture.md + Mermaid invocation graph (capped at --max-mermaid-nodes)
```

**Channel strategy — SOQL-first.**
- **Tooling SOQL** for every normalized tree node (planner, plugins, functions, plugin-functions, plugin-instructions, planner-functions, planner-attrs) — 6 parallel channels keyed on planner id, plus the `planner_definition_by_agent_chain` seed query that resolves the planner id from the agent chain.
- **Data API SOQL** for Flow (by id) and Apex (by id or name) bodies — batched.
- **Metadata retrieve** only for two cases: (a) `GenAiPromptTemplate` (prompt bodies aren't cleanly exposed via Tooling SOQL), and (b) NGA **external plugins** when the planner is Native Generative Agent shape (skipped for classic ReAct).

This is where the 3–5× speedup comes from. A naive implementation would retrieve everything via Metadata API zips sequentially; parallel Tooling SOQL covers ~80% of the tree in a single fan-out.

## Planner shapes — classic ReAct vs NGA

The skill normalizes two planner families into a single tree shape:

| Shape | `GenAiPlannerDefinition.PlannerType` | InvocationTarget style | NGA plugins? |
|---|---|---|---|
| **Classic ReAct** | `ReactAiPlannerV1` / `SequentialPlannerIntentClassifier` / etc. | DeveloperName strings | no |
| **NGA** | `ConcurrentMultiAgentOrchestration` / `AnthropicCompatibleV1` / etc. | Sometimes 15/18-char Ids (ID-prefix routed) | yes (external plugins via Metadata retrieve) |

The ID-prefix router in `resolve_invocation_target.py` distinguishes the two: NGA InvocationTargets that look like ids (`01p…` = ApexClass, `301…` = Flow, etc.) get resolved via id-scoped SOQL; DeveloperName targets go through name-scoped SOQL. Unknown prefixes surface as `_unresolved[]` with `reason="unknown-id-prefix:<prefix>"` — never silently dropped.

## Caching

- **Tree cache**: `metadata_tree.json` is reused unless `--force` is passed. Cache key includes the asset-hash of every `.soql` / `.yaml` / `.mmd` template bundled with the skill — bump a template, the cache busts automatically.
- **Channel probe cache**: 7-day TTL on the per-org `sf sobject describe` results that validate every field name the SOQL assets reference. A Salesforce quarterly release that renames / removes a field triggers `status: PROBE_FAILED`; `--reprobe` forces a refresh.

## Prerequisites

| Tool | Required |
|---|---|
| `sf` CLI (authenticated against the target org) | yes — `sf org login web --alias <alias>`, and the CLI must provide `sf org auth show-access-token` (startup preflight enforces this) |
| Python 3.10+ | yes |

## Reference docs to load when needed

Do NOT load eagerly. Load when the user's question requires it:

- `references/soql_fields.md` — per-sObject field reference for the 13 sObjects this skill touches (2 Data API + 11 Tooling), with `[mandatory]` vs `[optional]` tags. Load when the user asks about a specific field, or when debugging an `INVALID_FIELD` SOQL error.
- `references/contract.json` — machine-readable schema for `metadata_tree.json`. Load when writing downstream tooling that consumes the tree.
- `references/architecture_sections.md` — section-by-section structure of the rendered `<agent>_<ver>_architecture.md`.

## Invariants worth knowing upfront

- **Pipeline is deterministic.** Same `(org, agent, version)` + static org metadata → byte-identical `<agent>_<ver>_metadata_tree.json` and `<agent>_<ver>_architecture.md`. Only manifest timestamps drift across re-runs.
- **Forward-only traversal.** Every discovered ref goes forward from planner → children. No backward lookups.
- **Partial results are surfaced, not silenced.** Any unresolved reference lands in `_unresolved[]` with `reason=...`. `STATUS=PARTIAL_OK` if any channel failed; `STATUS=OK` only on a clean run.
- **Cycle detection is per-branch.** Same flow visited along its own ancestor chain emits `_cycle_back_to:<path>` instead of recursing. A defensive `MAX_BFS_DEPTH=20` guard backs the per-branch ancestor set; real-world agents bottom out well before either limit fires. (Earlier docs claimed a hard cap of 5; that was the historical limit and was abandoned because shared utility flows like `handleFlowFault` tripped it on every nested tree — see `config.MAX_BFS_DEPTH` for the rationale.)
- **Child ordering is alphabetical by `api_name` (case-insensitive).** Topics come before non-topic plannerActions at the root level. Flow-actionCall order is NOT sorted — that's the flow author's execution sequence.

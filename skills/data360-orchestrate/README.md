# data360-orchestrate

Salesforce Data Cloud skill family for sf-skills. This is the **cross-phase orchestrator** for community-driven Data Cloud workflows built around the external `sf data360` CLI runtime.

## What this skill is for

Use `data360-orchestrate` when the task spans multiple Data Cloud phases:
- connection + ingestion + harmonization setup
- troubleshooting a Data Cloud pipeline end to end
- managing data spaces or data kits
- deciding which specialized Data Cloud skill to use next

## What this skill is *not*

- It does **not** vendor or fork the external Data Cloud CLI plugin.
- It does **not** use MCP.
- It does **not** replace phase-specific skills once the problem is localized.
- It does **not** cover STDM/session tracing/parquet analysis; use `agentforce-observe` for that.

## Data Cloud skill family

| Skill | Purpose |
|---|---|
| [data360-orchestrate](../data360-orchestrate/) | Orchestrator, data spaces, data kits, cross-phase workflows |
| [data360-connect](../data360-connect/) | Connections, connectors, source discovery |
| [data360-prepare](../data360-prepare/) | Data streams, DLOs, transforms, DocAI |
| [data360-harmonize](../data360-harmonize/) | DMOs, mappings, identity resolution, data graphs |
| [data360-segment](../data360-segment/) | Segments, calculated insights |
| [data360-activate](../data360-activate/) | Activations, activation targets, data actions |
| [data360-query](../data360-query/) | SQL, async query, vector search, search indexes |

## Runtime model

This family assumes:
- Salesforce CLI (`sf`)
- a Data Cloud-enabled org
- the external community `sf data360` plugin linked into `sf`

See [references/plugin-setup.md](references/plugin-setup.md).

## Deterministic helpers included

| Path | Purpose |
|---|---|
| [scripts/bootstrap-plugin.sh](scripts/bootstrap-plugin.sh) | Clone/update the community plugin, compile it, and link it into `sf` |
| [scripts/verify-plugin.sh](scripts/verify-plugin.sh) | Check that the runtime is available before starting Data Cloud work |
| [scripts/diagnose-org.mjs](scripts/diagnose-org.mjs) | Classify org readiness by phase before mutating Data Cloud assets |
| [references/feature-readiness.md](references/feature-readiness.md) | Map high-signal errors and feature gates to concrete next steps |
| [assets/definitions/](assets/definitions/) | Generic JSON templates for repeatable Data Cloud definition files |
| [UPSTREAM.md](UPSTREAM.md) | Upstream mapping for future distillation and maintenance |

## Generic templates

The family includes reusable starting points for:
- data streams
- DMOs
- mappings
- identity resolution rulesets
- segments
- search indexes

These are intentionally generic and should be adapted to the target org.

## Quick start

### 1. Verify the runtime

```bash
bash ./scripts/verify-plugin.sh
# or with an org alias
bash ./scripts/verify-plugin.sh myorg
```

The helper treats `sf data360 doctor` as advisory and falls back to additional read-only smoke checks when an org is only partially provisioned.

### 2. Diagnose feature readiness before mutating

```bash
node ./scripts/diagnose-org.mjs -o myorg --json
# optional retrieve-plane probe, only when you know the table is real
node ./scripts/diagnose-org.mjs -o myorg --phase retrieve --describe-table MyDMO__dlm --json
```

Use the diagnose helper to distinguish between:
- feature-gated modules
- empty-but-enabled modules
- query-plane issues
- runtime/auth problems

### 3. Bootstrap the plugin if needed

```bash
python3 ~/.claude/sf-skills-install.py --with-datacloud-runtime
# or run the helper script directly
bash ./scripts/bootstrap-plugin.sh
```

### 4. Start with read-only inspection

```bash
sf data360 man
sf data360 doctor -o myorg 2>/dev/null
sf data360 dmo list -o myorg 2>/dev/null
sf data360 segment list -o myorg 2>/dev/null
sf data360 activation platforms -o myorg 2>/dev/null
```

## Common examples

```text
"Set up a Customer 360 proof of concept in Data Cloud"
"Troubleshoot why my unified profiles are not increasing"
"I need to figure out whether this issue is in mappings, identity resolution, or segment SQL"
"Show me how to inspect data spaces and data kits for this org"
```

## References

- [SKILL.md](SKILL.md) - Orchestrator guidance
- [references/plugin-setup.md](references/plugin-setup.md) - Plugin install and verification
- [references/feature-readiness.md](references/feature-readiness.md) - Readiness classification and setup guidance
- [UPSTREAM.md](UPSTREAM.md) - Upstream tracking and distillation policy
- [CREDITS.md](CREDITS.md) - Contributor and source attribution

## Primary contributor

**Gnanasekaran Thoppae** — primary contributor for the data360-orchestrate family.

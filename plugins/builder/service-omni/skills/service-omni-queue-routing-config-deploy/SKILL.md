---
name: service-omni-queue-routing-config-deploy
description: "Use to create or update a QueueRoutingConfig record on a Salesforce org via the Data API (idempotent SOQL detect + REST upsert). Naming is target-derived: Case→Case_Routing_Config, VoiceCall→Voice_Routing_Config, Incident→Incident_Routing_Config, MessagingSession→Messaging_Routing_Config (via QRC_ROUTING_TARGET), or pass an explicit developer-name/label/capacity/priority. RoutingModel MostAvailable (default) or LeastActive. Triggers: create a Case or Voice routing config, deploy a QueueRoutingConfig, set up queue routing for Omni Cases/Voice, configure CapacityWeight per queue. Do not use for attribute-based routing (IsAttributeBased=true is out of scope) or routing models other than MostAvailable/LeastActive."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-queue-deploy"
    - "service-omni-service-channel-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.9"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-queue-routing-config-deploy

Create or update a `QueueRoutingConfig` via the Data API. This record tells Omni-Channel how to distribute work to agents on a queue: the routing model (`MostAvailable` for round-robin-style, `LeastActive` for load-balancing), how much capacity each work item consumes (`CapacityWeight` or `CapacityPercentage`), the push timeout, and the routing priority. It is a prerequisite for an Omni-routed `Queue` — `service-omni-queue-deploy` binds the queue to the config Id this skill returns. Detection is by `DeveloperName`, so the skill POSTs a new record or PATCHes an existing one to align, and is safe to re-run.

## Inputs

```bash
bash scripts/upsert-and-report.sh <org-alias> [routing-model] [developer-name] [master-label] [capacity-weight] [routing-priority] [overflow-assignee] [push-timeout]
# Case_Routing_Config, preserve model / create MostAvailable:
bash scripts/upsert-and-report.sh myorg
# align the Case QRC to LeastActive:
bash scripts/upsert-and-report.sh myorg LeastActive
# Voice_Routing_Config (coordinator path):
QRC_ROUTING_TARGET=VoiceCall bash scripts/upsert-and-report.sh myorg
# set a fallback/overflow assignee (route overflow work to a supervisor):
QRC_OVERFLOW_ASSIGNEE=supervisor@example.com bash scripts/upsert-and-report.sh myorg
# Voice uses 100% capacity and a 30-second push timeout:
QRC_ROUTING_TARGET=VoiceCall QRC_CAPACITY_PERCENTAGE=100 QRC_PUSH_TIMEOUT=30 bash scripts/upsert-and-report.sh myorg MostAvailable
```

- `org-alias` (required).
- `routing-model` (optional, or `ROUTING_MODEL_INPUT`) — `MostAvailable` | `LeastActive`. Omitted: an existing record's model is preserved; a new record is created `MostAvailable`. Provided: written on create, aligned on an existing record.
- `developer-name` / `master-label` / `capacity-weight` (1..100) / `routing-priority` (≥1) — positional after routing-model, or via `QRC_DEVELOPER_NAME` / `QRC_MASTER_LABEL` / `QRC_CAPACITY_WEIGHT` / `QRC_ROUTING_PRIORITY`. Label, weight `5`, and priority `1` are defaults only when creating a new record; omitted values preserve an existing record.
- `QRC_CAPACITY_PERCENTAGE` (optional, 0..100) — use percentage capacity instead of weight. It is mutually exclusive with an explicitly supplied capacity weight; switching modes clears the old sibling field.
- `overflow-assignee` (optional 7th positional, or `QRC_OVERFLOW_ASSIGNEE`) — the fallback User (Username or `005` Id) that receives work when every queue member is unavailable (`OverflowAssigneeId`). Resolved to an **active** User Id before the write; omitted leaves an existing record's overflow untouched and a new record with none.
- `push-timeout` (optional 8th positional, or `QRC_PUSH_TIMEOUT`, 0..3600 seconds) — how long Omni waits for an agent to accept pushed work. Omitted preserves an existing value.
- `QRC_ROUTING_TARGET` (env) — `Case | VoiceCall | Incident | MessagingSession`; selects the canonical naming defaults. `service-omni-channel-setup-coordinate` sets this per target.

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL), Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled (`service-omni-base-settings-configure`) — otherwise `QueueRoutingConfig` is not writable (`INVALID_TYPE`).
- The three-way `safe_to_write` production guard applies.

## Run

`upsert-and-report.sh` performs detect → upsert → verify:

1. Query `QueueRoutingConfig WHERE DeveloperName = '<target-derived-or-explicit>'`, capturing the existing Id and field values.
2. Compare against the requested/canonical values.
3. POST a new record when none exists; no-op (`reused`) when all fields already match; PATCH when a field differs.
4. Re-query to confirm the final state; block if the re-query shows a mismatch.

## Behavior

**Target-derived naming.** With no explicit name, the DeveloperName follows the routing target (`Case_Routing_Config`, `Voice_Routing_Config`, etc.), so re-runs and the coordinator converge on the same record rather than creating parallel duplicates.

**Preserve over churn.** On an existing record, omitted routing model, label, routing priority, capacity mode/value, overflow assignee, push timeout, and attribute-based flag are preserved. Defaults (`MostAvailable`, target-derived label, weight `5`, priority `1`, non-attribute-based) apply only to a brand-new record. Capacity uses exactly one mode; explicitly changing from weight to percentage, or back, clears the old sibling field so the record cannot contain conflicting capacity settings.

**Fallback / overflow routing.** In the `QueueBased` model, "fallback" is the queue's overflow assignee — the User who receives work when no queue member is available (rather than the item sitting queued indefinitely). Agent availability is an async Omni decision, not observable in a routing flow, so this belongs on the `QueueRoutingConfig`, not the flow. When `overflow-assignee` is provided the skill resolves it to an active User (blocking on an unknown or inactive user, since overflow to an inactive user would silently strand work), writes `OverflowAssigneeId`, and verifies it round-trips.

**Read-back reporting.** All reported field values are re-queried from the org after the write (`values_source: "requeried"`), not echoed from inputs — a 201/204 only means the write was accepted. The skill never deletes a `QueueRoutingConfig` (queues, agents, and work skills may reference the Id) — it always PATCHes to align.

## Output contract

A single JSON object with `status` ∈ `created` | `reused` | `updated` | `blocked`, plus `routing_target`, `developer_name`, `id`, `master_label`, `routing_model`, `routing_priority`, `capacity_mode`, `capacity_weight`, `capacity_percentage`, `is_attribute_based`, `push_timeout`, `overflow_assignee_id`, `overflow_assignee_requested`, `values_source`, a `before` snapshot, `manual_actions`, and `blocking_issue`.

- `created` — no record existed; POST succeeded.
- `reused` — a record existed with all fields matching; no-op.
- `updated` — a record existed but a field differed; PATCH succeeded.
- `blocked` — precondition failed (Omni not enabled, production org, a post-write mismatch, or an `overflow-assignee` that did not resolve to exactly one active User).

`before.existed` records whether a matching record was present at start (with its prior `capacity_weight`/`routing_model` when so); `id` is populated for every non-blocked status; `blocking_issue` is non-null only for `blocked`.

## Limitations

- Attribute-based routing (`IsAttributeBased=true`) is out of scope — it requires an additional attribute schema.
- Only `MostAvailable` and `LeastActive` are supported on v66.
- Per-channel capacity weighting is deprecated on v66 (see `service-omni-service-channel-configure`); per-agent capacity totals are configured elsewhere.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | On unexpected errors or when customizing fields — QueueRoutingConfig schema, RoutingModel semantics, and how CapacityWeight interacts with agent capacity |
| `scripts/tests/test_queue_routing_config_contracts.py` | When validating changes — run `python3 scripts/tests/test_queue_routing_config_contracts.py` from this skill directory |

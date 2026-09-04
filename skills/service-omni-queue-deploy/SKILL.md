---
name: service-omni-queue-deploy
description: "Use to verify or create a Queue on a Salesforce org for a routable sObject (Case | Incident | MessagingSession | VoiceCall), discovered via its QueueSobject binding rather than by hardcoded name. Reuses whatever queue already routes the target sObject; with --create-if-missing it creates a Queue via the Metadata API (Group + QueueSobject) when none is bound and aligns its QueueRoutingConfigId to a caller-specified QRC. Returns created, reused, updated, or blocked. Triggers: verify or create a queue for Case/Incident/Messaging/Voice routing, align queue routing config, set up an Omni voice queue. Do not use to add users to the queue (service-omni-queue-members-assign) or for sObjects outside Case/Incident/MessagingSession/VoiceCall."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-channel-setup-coordinate"
    - "service-omni-queue-members-assign"
    - "service-omni-queue-routing-config-deploy"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-queue-deploy

Verify that a `Group` (Type='Queue') exists with a `QueueSobject` binding to the requested routable sObject, reusing whatever is already there. With `--create-if-missing`, create the queue via the Metadata API (Group + QueueSobject) when none is bound, and optionally align its `QueueRoutingConfigId` to a caller-specified QRC. The skill discovers the queue by its `QueueSobject.SobjectType` binding, not by name, because real orgs name queues inconsistently (`CaseQueue`, `messagingqueue`, `Omni_Demo_Cases_Queue`) — the functional link between a queue and the routing it supports is the binding, not the `DeveloperName`. It is invoked by `service-omni-channel-setup-coordinate`; queue membership is a separate leaf (`service-omni-queue-members-assign`) and the QRC it aligns to comes from `service-omni-queue-routing-config-deploy`.

## Inputs

```bash
bash scripts/verify-and-align.sh <org-alias> [Case|Incident|MessagingSession|VoiceCall] [routing_config_dn] [queue_developer_name] [--create-if-missing]
# create + bind a Voice queue on a fresh org:
bash scripts/verify-and-align.sh myorg VoiceCall Voice_Routing_Config "" --create-if-missing
```

- `org-alias` (required).
- `sobject_type` (optional, default `Case`).
- `routing_config_dn` (optional) — when passed, forces alignment to that QRC; when omitted for Case it defaults to `Case_Routing_Config`; when omitted for other sObjects the skill reports the existing binding without forcing.
- `queue_developer_name` (optional 4th positional) — the explicit queue to operate on, or the name to create with `--create-if-missing`.
- `--create-if-missing` (flag, or `QUEUE_CREATE_IF_MISSING=1`) — create the queue via the Metadata API when none is bound; label defaults to a spaced form of the DeveloperName (override via `QUEUE_LABEL`).

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL), Service Cloud license, `sf` CLI ≥ 2.139.6.
- The target sObject is enabled on the org — verified via `EntityDefinition` before any write; missing sObjects block with a feature-enablement click-path (Incident Management for Incident, Enhanced Messaging for MessagingSession).
- When `routing_config_dn` is supplied, that QRC must already exist (resolved by DeveloperName); otherwise the run blocks with a pointer to `service-omni-queue-routing-config-deploy`.
- The three-way `safe_to_write` production guard applies.

## Run

`verify-and-align.sh` runs the full sequence and emits the report:

1. **Prereq** — confirm the sObject via `EntityDefinition`.
2. **Discover** — `QueueSobject WHERE SobjectType = '<sobject_type>'`. A hit is reused. No hit: create via the Metadata API when `--create-if-missing`, else block with a Setup click-path.
3. **Inspect** — read the queue's `QueueRoutingConfigId` and its full `QueueSobject` list.
4. **Align (optional)** — when `routing_config_dn` is supplied, resolve its Id and PATCH `Group.QueueRoutingConfigId` if drifted.
5. **Re-query** — confirm convergence and emit JSON.

## Behavior

**Discovery over naming.** Any queue whose `QueueSobject` routes the target sObject is *the* queue for that sObject, regardless of its name. A name-based check would miss a queue like `messagingqueue` and either block or create a duplicate.

**Creation is idempotent.** Metadata deploy upserts by fullName, so `--create-if-missing` adopts/updates an existing same-named queue rather than making a second one. Creation ships the minimal safe set (`doesSendEmailToMembers=false` plus the sObject binding) and never deletes existing `QueueSobject` rows — other sObjects may be intentionally routed through the same queue.

**Forced vs discovered QRC.** For Case, the coordinator wants deterministic alignment to `Case_Routing_Config`, so the skill forces it. For other sObjects with no coordinator-owned QRC, the skill reports whatever the queue is already bound to (`source: discovered`) rather than forcing a name that may not exist. QRC Ids are resolved by `DeveloperName` at runtime — never hardcoded.

**Ambiguity.** If multiple distinct queues bind the same sObject, the skill does not guess — it blocks and asks the operator to disambiguate, unless a canonical name matches or an explicit `queue_developer_name` pins the exact queue.

**PATCH hygiene.** `sf api request rest` prints a beta warning on stderr; the skill captures stderr separately so it cannot corrupt JSON parsing, and it preserves the queue Id on PATCH (never delete + recreate) because downstream references point to it.

## Output contract

A single JSON object with `status` ∈ `created` | `reused` | `updated` | `blocked`, plus `sobject_type`, `developer_name`, `queue_created`, `id`, `queue_routing_config_id`, `queue_routing_config_developer_name`, `queue_routing_config_source` (`forced` | `discovered`), `queue_sobjects`, a `before` snapshot, `manual_actions`, and `blocking_issue`.

- `created` — no queue was bound and `--create-if-missing` created one (binding its QRC when supplied).
- `reused` — a bound queue existed and, if a QRC was passed, already matched (no PATCH).
- `updated` — a bound queue existed but the caller-supplied QRC was drifted; PATCH ran.
- `blocked` — sObject absent, no bound queue and no `--create-if-missing`, supplied QRC missing, or the re-query showed state did not converge.

`queue_created` is `true` only when this run deployed a new queue; `blocking_issue` names the specific precondition that failed and `manual_actions` carries the click-path.

## Limitations

- Only `Case`, `Incident`, `MessagingSession`, `VoiceCall` — extend by adding a dispatcher branch.
- Never deletes a queue or its `QueueSobject` rows, and never modifies queue members.
- Creation ships a minimal queue shape; exotic fields (`doesIncludeBosses`, email routing address) are not set.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | On a block for a missing queue (manual click-path) or unexpected Data API errors — Queue/QueueSobject schema, the Metadata API creation shape, and the stderr-separation and queue-naming-variance notes |

---
name: service-omni-presence-status-deploy
description: "Create the standard Available and Busy presence statuses needed for Omni-Channel routing. TRIGGER when users ask to deploy Omni presence statuses, configure agent availability, deploy Omni status metadata, create an Available status for Case, Incident, Messaging, or Voice, or add the standard Busy status. DO NOT TRIGGER for custom status designs, unsupported objects, or PresenceUserConfig capacity."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-permission-set-assign"
    - "service-omni-service-channel-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-presence-status-deploy

Deploy the sObject-specific `Available_<X>` ServicePresenceStatus bound to that sObject's ServiceChannel, and ensure a universal `Busy` status exists, in one atomic Metadata API deploy. Every Omni agent needs an "available for work" status carrying a channel (so incoming work routes) and an "off-work" status (so they can step away). A presence status binds to exactly one ServiceChannel by DeveloperName, so each routing target needs its own Available status. It pairs with `service-omni-permission-set-assign`, which grants agents access to the statuses this skill deploys, and is invoked once per routing target by `service-omni-channel-setup-coordinate`.

| Target sObject | Available status | Bound channel |
|---|---|---|
| `Case` | `Available_Case` | `Cases` |
| `Incident` | `Available_Incident` | `Incidents` |
| `MessagingSession` | `Available_Messaging` | `sfdc_livemessage` |
| `VoiceCall` | `Available_Voice` | `sfdc_phone` |

**Busy is UI-defined, not metadata-defined.** The Omni "Busy vs Online" option is not expressible via the Metadata API — a `ServicePresenceStatus` carries only `<label>` and `<channels>`, and a status with no channels is treated as busy. The conventional busy DeveloperName is simply `Busy`, and most orgs already have one, so this skill reuses an existing `Busy` and deploys the bundled asset only when none exists. A busy status is not required to receive work — the Available status carrying the channel is what routes it.

## Inputs

```bash
bash scripts/deploy-and-report.sh <org-alias> [Case|Incident|MessagingSession|VoiceCall]
```

- `org-alias` (required).
- `sobject_type` (optional, default `Case`).

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL), Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled (`service-omni-base-settings-configure`) — otherwise the deploy fails with `INVALID_TYPE`.
- The target sObject's ServiceChannel exists (`service-omni-service-channel-configure`) — otherwise the deploy fails with `Value '<channel>' is not valid`. `Incident` requires the Incident Management feature enabled; `MessagingSession` requires Enhanced Messaging.
- The three-way `safe_to_write` production guard applies.

## Run

`deploy-and-report.sh` deploys the `Available_<X>` status (and `Busy` only when the org has none) in one Metadata API call, then maps the per-component `files[].state` to a skill status:

- `reused` — every component `Unchanged`.
- `updated` — any component `Changed`, none `Created`.
- `created` — any component `Created`.

There is no separate detect step — Salesforce's `files[].state` is authoritative. The deploy uses explicit `--metadata` flags (never `--source-dir`) so unrelated assets cannot piggyback.

## Behavior

**Reuse over redeploy.** An existing `Busy` is detected and left untouched; only a missing one is deployed. The skill never deletes or overwrites presence statuses it did not deploy — orgs often carry other custom statuses (`Omni_OnBreak`, `availableForMiaw`).

**Schema.** The XML omits `<statusType>` (removed in v66; online/busy is inferred from the presence of `<channels>`), and the skill never SOQL-queries `StatusType` (not queryable on v66 — only Id, DeveloperName, MasterLabel are reliable). `Available_Messaging` binds the standard `sfdc_livemessage` channel that Enhanced Messaging always ships.

## Output contract

A single JSON object with `status` ∈ `created` | `reused` | `updated` | `blocked`, `sobject_type`, a `presence_statuses` array (each with `developer_name`, `label`, `channels`, `state`, and — for `Busy` — `reused_existing`), `deploy_id`, `manual_actions`, and `blocking_issue`.

- `blocked` — deploy failed (missing prereq, schema mismatch, or org error); `manual_actions` names the prerequisite skill to run and `blocking_issue` is an operator-friendly translation of the Salesforce error.
- `deploy_id` is populated on every run (Salesforce issues one even for no-op deploys).

## Limitations

- Deploys only the `Available_<X>` + `Busy` pair — custom statuses require forking the `assets/servicePresenceStatuses/*.xml`.
- Only `Case`, `Incident`, `MessagingSession`, `VoiceCall` — extend by adding a dispatcher branch and a matching asset.
- Does not configure `PresenceUserConfig` capacity or decline reasons, and never deletes existing statuses.

## References

| File | When to read |
|---|---|
| `assets/package.xml` | Load when preparing the explicit Metadata API deployment for the selected Available status and the optional Busy status |
| `references/api-notes.md` | On unexpected deploy behavior — the v66 XML schema (no `statusType`), channel-binding rules, and MessagingSession-specific notes |

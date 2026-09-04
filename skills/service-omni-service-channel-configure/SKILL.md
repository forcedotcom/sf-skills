---
name: service-omni-service-channel-configure
description: "Use to ensure exactly one ServiceChannel exists on a Salesforce org for a routable sObject (Case | Incident | MessagingSession | VoiceCall), reusing any standard or custom channel already bound to that sObject and only deploying a canonical template when none exists. Salesforce enforces one ServiceChannel per RelatedEntity, so the skill detects via the Tooling API first. Standard channels ship for Case (Cases), MessagingSession (sfdc_livemessage), VoiceCall (sfdc_phone); Incident has none. Triggers: configure ServiceChannel for Case/Incident/Messaging/Voice routing, add Incident or Voice routing to Omni. Do not use to tune per-sObject capacity (use PresenceUserConfig.Capacity), to reset a mis-configured channel to canonical shape, or for sObjects outside Case/Incident/MessagingSession/VoiceCall."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-service-channel-configure

Ensure exactly one `ServiceChannel` is present for a routable sObject, reusing whatever is already bound (Salesforce standard or a pre-existing custom channel) and deploying the skill's canonical v66 template only when none exists. Salesforce enforces one ServiceChannel per `RelatedEntity`, so the skill detects first and never deploys blindly — deploying a second channel for an sObject that already has one fails with "This Salesforce object is already in use by another Service channel." It handles one sObject per call; callers configuring multiple sObjects invoke it once for each sObject, after `service-omni-base-settings-configure` has enabled Omni-Channel.

| sObject | Standard channel (if any) | Canonical asset |
|---|---|---|
| `Case` | `Cases` | `Cases.serviceChannel-meta.xml` |
| `Incident` | none (Incident Management sObject) | `Incidents.serviceChannel-meta.xml` — deployed on first run |
| `MessagingSession` | `sfdc_livemessage` | `MessagingSessions.serviceChannel-meta.xml` — deployed only if the standard channel is missing |
| `VoiceCall` | `sfdc_phone` | `VoiceCalls.serviceChannel-meta.xml` — deployed only if the standard channel is missing |

## Inputs

```bash
bash scripts/deploy-and-report.sh <org-alias> [Case|Incident|MessagingSession|VoiceCall]
```

- `org-alias` (required).
- `sobject_type` (optional, default `Case`) — one of `Case | Incident | MessagingSession | VoiceCall`.

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL), Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled (`service-omni-base-settings-configure`) — `ServiceChannel` is only queryable/writable when `enableOmniChannel=true`; a `INVALID_TYPE` on deploy means base settings are off.
- `Incident` requires the Incident Management feature enabled; `MessagingSession` requires Enhanced Messaging. The skill verifies `EntityDefinition` first and blocks with a click-path when the target sObject is absent.

## Run

`deploy-and-report.sh` performs the prereq check, discovery, and (only when needed) deploy, then emits the report:

1. **Prereq** — confirm the target sObject is queryable via `EntityDefinition`; block with a click-path otherwise.
2. **Discover** — query the Tooling API for a `ServiceChannel` with `RelatedEntity = <sobject_type>`. `ServiceChannel` is a Tooling entity on v66; the standard Data API returns `INVALID_TYPE`. A hit means reuse.
3. **Deploy** (only when nothing was found) — `sf project deploy start` of the canonical XML (`Cases` | `Incidents` | `MessagingSessions` | `VoiceCalls`); a `Changed` state is `created`, `Unchanged` is `reused`.

## Behavior

**Detect-then-reuse-or-deploy.** Because Salesforce rejects a second channel per `RelatedEntity`, deploy-first is unsafe: an operator who renamed the standard `Cases` channel would hit the "already in use" error instead of gracefully reusing. Tooling discovery is fast and returns both the reuse decision and the discovered `DeveloperName` in one call. The trade-off is that the skill cannot tell "our canonical shape matches" from "some custom channel is bound" — an operator with a non-canonical channel gets `reused` and their channel is left untouched (v1 never overwrites operator state).

**Capacity model.** The canonical assets use `TAB_BASED` for every variant. `STATUS_BASED` requires companion fields whose full schema is undocumented, so it is out of scope; per-agent capacity tuning belongs to `PresenceUserConfig.Capacity`, not this skill.

**Concurrency.** If a deploy fails with "already in use," another process created the channel between discovery and deploy; the skill soft-fails and a re-run reuses it.

## Output contract

A single JSON object per invocation with `status` ∈ `created` | `reused` | `blocked`, plus `sobject_type`, `channel_developer_name`, `channel_id`, `channel_origin`, `target_capacity_model`, `target_related_entity_type`, `before_state`, `deploy_id`, `manual_actions`, and `blocking_issue`.

- `reused` — an existing channel was found (discovery hit, or a deploy returned `Unchanged`).
- `created` — no channel existed; the canonical XML deployed with `Changed`.
- `blocked` — the sObject is not on the org, base settings are off (`INVALID_TYPE`), or a race left the channel already in use.
- `channel_origin` is one of `salesforce_standard` (an `sfdc_*` name or `Cases`), `canonical_asset` (a shipped asset name), `canonical_template` (freshly deployed this run), or `custom` (a pre-existing org-specific channel).
- `channel_id` is populated whenever a channel exists (`null` on `blocked`); `deploy_id` is populated only on the deploy branch; `blocking_issue` is non-null only when `status: blocked`.

## Limitations

- One sObject per invocation.
- Only `Case`, `Incident`, `MessagingSession`, `VoiceCall` are supported — extend by adding an `assets/force-app/main/default/serviceChannels/<Name>.serviceChannel-meta.xml` file and a dispatcher branch.
- Always reuses an existing channel; it does not reset a mis-configured channel to canonical shape.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | On unexpected discovery results, deploy failures, or sObject-specific schema questions |

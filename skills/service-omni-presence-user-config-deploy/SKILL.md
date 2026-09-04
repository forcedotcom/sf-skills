---
name: service-omni-presence-user-config-deploy
description: "Use to deploy an Omni PresenceUserConfig (presence configuration) as one whole-record Metadata write with the decline/ACW fields set consistently: Auto-Accept off, Decline on, Decline Reason on (with a PresenceDeclineReason deployed in the same package), and an After-Conversation-Work wrap-up timer. Agents are assigned by username. Idempotent via the Metadata API files[].state signal. Triggers: create presence configuration, enable decline + decline reason + ACW wrap-up timer for agents, assign presence config to users. Do not use for ServicePresenceStatus (separate skill), for permission-set access to statuses, or to set the channel-level ACW timer on a ServiceChannel."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-agent-users-create"
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-presence-status-deploy"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-presence-user-config-deploy

Deploy an Omni **PresenceUserConfig** (the "presence configuration" that governs how work is offered to agents) together with the **PresenceDeclineReason** it references, in one atomic Metadata API package. The decline / auto-accept / decline-reason / ACW fields have cross-field validators — enabling Decline requires Auto-Accept off, Decline Reason requires Decline on, and the ACW timer must be paired with its max time — so they can only be set correctly as a **single whole-record write**, not field-by-field. This skill encodes that consistent record and assigns it to the given agents. It runs after `service-omni-agent-users-create` / `service-omni-presence-status-deploy` and is invoked by `service-omni-channel-setup-coordinate` as a rep-experience step.

## Inputs

```bash
bash scripts/deploy-and-report.sh <org-alias> [config_developer_name] [agent_usernames_csv]
```

- `org-alias` (required).
- `config_developer_name` (optional, default `Omni_Demo_Presence_Config`).
- `agent_usernames_csv` (optional). Comma-separated Usernames (`…@…`) and/or 15/18-char User Ids (`005…`) to assign; Ids are resolved to usernames (metadata assigns by username). May also be set via `AGENT_USERNAMES_CSV`. Empty → the config deploys with no user assignments.

Env overrides: `DECLINE_REASON_LABEL` (default `Training`), `DECLINE_REASON_DEVELOPER_NAME` (default derived from the label), `CAPACITY` (default `5`, 1–100), `ACW_SECONDS` (default `60`, 10–3600), `PRESENCE_STATUS_ON_DECLINE` (optional ServicePresenceStatus DeveloperName).

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled (`service-omni-base-settings-configure`).
- Any `PRESENCE_STATUS_ON_DECLINE` must already exist (`service-omni-presence-status-deploy`).
- The three-way `safe_to_write` production guard applies.

## Run

`deploy-and-report.sh` materializes two components into a temp DX project and deploys them in one call:

1. `PresenceDeclineReason:<reason>` — the decline reason (label only).
2. `PresenceUserConfig:<config>` — capacity + label, `enableAutoAccept=false`, `enableDecline=true`, `enableDeclineReason=true`, `declineReasons=<reason>`, `hasAfterConvoWorkTimer=true`, `afterConvoWorkMaxTime=<ACW_SECONDS>`, optional `presenceStatusOnDecline`, and `assignments/users` for the resolved agents.

Elements are emitted in strict XSD order. Idempotency comes from the Metadata API `files[].state` per component (`Unchanged`→reused, `Changed`→updated, `Created`→created); the deploy runs `--async` and polls to a terminal state.

## Behavior

**Whole-record + consistent.** The record is always emitted with the validator-safe combination, so a re-deploy is a clean no-op rather than a field diff that could trip a cross-field rule.

**Non-destructive.** Only the named config and decline reason are written; other presence configs and decline reasons on the org are never touched. Assignments are declared for the resolved agents; the skill does not remove users it did not add (a redeploy declares the full assignment set for this config).

## Output contract

A single JSON object: `status` ∈ `created` | `updated` | `reused` | `blocked`, `config` (`{developer_name, label, capacity, acw_seconds, state}`), `decline_reason` (`{developer_name, label, state}`), `assigned_usernames`, `deploy_id`, `manual_actions`, `blocking_issue`.

## Limitations

- One presence configuration per invocation.
- Encodes the decline+ACW rep profile from the steel thread; other field combinations require forking the XML template.
- Does **not** set the channel-level After-Conversation-Work timer on a `ServiceChannel` (a separate concern), deploy `ServicePresenceStatus`, or grant status access via permission set.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | PresenceUserConfig cross-field validators, XSD element order, decline-reason packaging, and ACW field pairing |
| `scripts/tests/_bootstrap.py` | Test bootstrap loaded by the contract suite to locate the skill root and run its shell entry point |
| `scripts/tests/test_presence_user_config_contracts.py` | Run after changing the deployment script to verify guard, whole-record, membership, and output contracts |

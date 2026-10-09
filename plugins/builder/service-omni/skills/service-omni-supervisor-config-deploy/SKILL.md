---
name: service-omni-supervisor-config-deploy
description: "Use to stand up a headless Omni-Channel Supervisor Configuration by deploying the classic OmniSupervisorConfig (parent plus supervisor-user and queue companions) in one atomic Metadata API deploy, idempotent via the deploy state. Requires active supervisor users, Omni base settings, and the monitored queues. Triggers: set up Omni Supervisor, configure the classic Supervisor Command Center. Do not use to create supervisor users, assign the ContactCenterSupervisor permission set, or deploy queues, service channels, or presence statuses."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-agent-work-sharing-configure"
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-presence-status-deploy"
    - "service-omni-queue-deploy"
    - "service-omni-service-channel-configure"
    - "service-omni-supervisor-permset-assign"
    - "service-omni-supervisor-surface-deploy"
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

# service-omni-supervisor-config-deploy

Deploy the classic Omni-Channel Supervisor Configuration (`OmniSupervisorConfig`) to a Salesforce org in a single Metadata API deploy. `OmniSupervisorConfig` is a full Metadata API type whose XSD embeds every companion as a repeatable child element, so the whole configuration — parent plus companions — lands atomically from one `.omniSupervisorConfig-meta.xml` file, and Salesforce rolls the companions back together on a partial failure. By default the deploy binds supervisors explicitly by user and lists the queues they monitor; profile scope is optional (see Behavior).

## Inputs

`bash scripts/deploy-and-report.sh <org-alias> [supervisor_count] [additional_queues_csv] [profiles_csv] [skill_visibility] [config_developer_name]`

- `org-alias` (required) — must resolve via `sf org display --target-org <alias>`.
- `supervisor_count` (optional, default `1`, range `1..5`) — how many active `supervisor{N}.<suffix>@example.com` users to detect and bind.
- `additional_queues_csv` (optional) — queue DeveloperNames to bind. When the coordinator supplies this list it is authoritative; when omitted, the canonical `CaseQueue`, `messagingqueue` defaults are used. Every requested queue must already exist on the org.
- `profiles_csv` (optional) — opt into profile-based fallback scope; supply metadata profile fullNames (e.g. `Standard,ServiceCloud`). Omit it to bind supervisors by user only.
- `skill_visibility` (optional, or `OMNI_SUPERVISOR_SKILL_VISIBILITY`) — `AllSkills` or `AnySkill`. Omitted values preserve an existing config's selection; a new config defaults to `AllSkills`.
- `config_developer_name` (optional, or `OMNI_SUPERVISOR_CONFIG_DEVELOPER_NAME`; default `Omni_Supervisor`) — the exact classic `OmniSupervisorConfig.DeveloperName` to create or reconcile. Supply it when an org has multiple supervisor configurations; the skill never guesses between candidates. `OMNI_SUPERVISOR_CONFIG_MASTER_LABEL` optionally sets the label for a new config. Existing labels are preserved by default.

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license present, `sf` CLI ≥ 2.139.6.
- Active supervisor users exist; their supervisor access is granted separately by `service-omni-supervisor-permset-assign`.
- Omni-Channel base settings are enabled (`service-omni-base-settings-configure`) and the monitored queues exist (`service-omni-queue-deploy`).
- **Production guardrail:** the script computes `safe_to_write` as `IsSandbox` OR `TrialExpirationDate != null` OR `OrganizationType` in {Developer Edition, Base Edition}, and blocks with no override when it is false. Any unmet precondition returns `status: blocked` with a `blocking_issue` and a click-path.

## Run

One script does detect, deploy, and verify:

```bash
bash scripts/deploy-and-report.sh <org-alias> [supervisor_count] [additional_queues_csv] [profiles_csv] [skill_visibility] [config_developer_name]
```

It resolves the deploy artifact's tokens from live org state (discovered supervisor users, verified queues, and — only when `profiles_csv` is given — validated profiles), materializes the selected DeveloperName into the metadata filename and package manifest, then re-queries that same selected config to confirm the parent and its companion rows persisted before emitting JSON to stdout. The coordinator (`service-omni-channel-setup-coordinate`) invokes it with the authoritative queue list and selected supervisor config; standalone runs use the canonical defaults.

## Behavior

**Companions.** The deployed config always carries `omniSupervisorConfigUser` (one per supervisor) and `omniSupervisorConfigQueue` (one per monitored queue). It follows the same single-file Metadata deploy shape as `service-omni-service-channel-configure` and `service-omni-presence-status-deploy`.

**Profile scope is a fallback, off by default.** Core resolves a supervisor's configuration by `OmniSupervisorConfigUser` first, and only falls back to `OmniSupervisorConfigProfile` — matched against *that supervisor's own profile* — when the supervisor has no user row (`RealTimeQueueServiceImpl.getSupervisorConfigId`). Because this skill binds every supervisor by user, profile companions are unnecessary and are omitted unless you pass `profiles_csv`. When supplied, values must be metadata fullNames (the `<profile>` element resolves against the fullName — `Standard`, `ServiceCloud`, `Admin` — not the SOQL `User.Profile.Name` label); the skill validates each against `sf org list metadata -m Profile` and blocks on any the org does not expose.

**Idempotency and surface preservation.** Status follows the Metadata deploy component state: `Unchanged` → `reused`, `Changed` → `updated`, `Created` → `created`. Any other state is a hard failure rather than a silent `reused`. Before updating an existing parent, the skill snapshots its reference-free `OmniSupervisorConfigAction` and `OmniSupervisorConfigTab` rows, validates that each can be recreated safely, then restores and re-queries them after the deploy. A custom/reference-bearing surface blocks before deployment instead of risking silent loss. When reconciling an existing config or verifying preservation, invoke only this skill; do not invoke `service-omni-supervisor-surface-deploy`, because adding standard rows afterward could mask a preservation failure. The companion surface skill remains responsible only for a separate request to add new standard actions or tabs.

**Fail-closed verification.** The deploy `status` must be `Succeeded` (not `SucceededPartial`). After the parent config is queryable, the script re-queries the child `OmniSupervisorConfigUser` and `OmniSupervisorConfigQueue` rows and requires at least the intended counts — the parent existing does not prove the companions landed. Every read must return a parseable `.result.records` array; an inconclusive read never counts as zero. Requested queues are validated against `^[A-Za-z0-9_]{1,80}$` before use, and every requested queue must exist or the run blocks (dropping one silently would under-provision the config).

## Output contract

A single JSON object to stdout. `status` is one of `created`, `updated`, `reused`, or `blocked`. The object also carries `config_developer_name`, `config_id`, `skill_visibility`, `surface_preservation` snapshot/restoration counts, `supervisor_users_bound`/`supervisor_users_count`, `queues_bound`/`queues_count`, `queue_source` (`caller_supplied` or `canonical_default`), the re-queried `verified_companion_user_count`/`verified_companion_queue_count`, `deploy_id`, `state`, `manual_actions`, and `blocking_issue`. `blocking_issue` is `null` unless `status: blocked`, in which case it names the missing prerequisite with a click-path in `manual_actions`. Re-running an unchanged config returns `reused` and performs no functional change.

Org-side spot-check:

```sql
SELECT Id, DeveloperName, MasterLabel FROM OmniSupervisorConfig WHERE DeveloperName='<config_developer_name>'
SELECT COUNT(Id) FROM OmniSupervisorConfigUser  WHERE OmniSupervisorConfigId = :configId
SELECT COUNT(Id) FROM OmniSupervisorConfigQueue WHERE OmniSupervisorConfigId = :configId
```

## Limitations

- Populates user and queue companions (plus optional profile scope). Existing reference-free Action and Tab rows are preserved across an update; new standard rows are added separately by `service-omni-supervisor-surface-deploy`. Custom-action, FlexiPage, AWS-dashboard, and AI-agent rows require external references and therefore block an update rather than being reconstructed incompletely.
- Binds supervisor users discovered by the `supervisor{N}.<suffix>@example.com` pattern; it does not create them.
- Does not change AgentWork sharing because that org-wide access control is separate from `OmniSupervisorConfig`. Use `service-omni-agent-work-sharing-configure` for supported metadata detection and the explicitly confirmed `Private` to `Read` operation.
- Does not activate the Command Center V2 runtime (a separate settings flip).

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | On a deploy failure — field-by-field `OmniSupervisorConfig` schema and companion sObject semantics |
| `assets/force-app/main/default/omniSupervisorConfigs/Omni_Supervisor.omniSupervisorConfig-meta.xml` | The token-templated deploy artifact (`__MASTER_LABEL__`, `__SUPERVISOR_USERS_XML__`, `__PROFILE_SCOPE_XML__`, `__QUEUE_LIST_XML__`, `__SKILL_VISIBILITY__`); it is materialized under the selected DeveloperName at runtime |
| `assets/package.xml`, `assets/sfdx-project.json` | Manifest and project scaffold materialized into the temp deploy dir |

---
name: service-omni-channel-setup-coordinate
description: "Use to stand up Omni-Channel setup headlessly on Salesforce: base settings, agent users, service channels, routing configs, queues (create and align) and members, presence statuses, permission assignments, the classic Omni Supervisor config plus its action/tab surface, and — for Case and VoiceCall — the record-triggered routing flow. Supports Case, Incident, MessagingSession, and VoiceCall targets; reuses existing records and creates what is missing. Opt-in extras: presence user config, Omni sidebar, skills-based routing, and field-based WorkSkillRouting; also reports (read-only) whether the org is on the classic supervisor surface or Command Center V2. Triggers: set up Omni-Channel, configure Omni routing, provision Omni agents or supervisors, configure Case/Incident/Messaging/Voice routing. Do not use for Agentforce agents or bots, a single existing Omni field change, bare metadata deployment (use platform-metadata-deploy), or to enable Command Center V2 (not writable via the Metadata API)."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion TodoWrite
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "platform-metadata-deploy"
    - "service-agentforce-human-escalation-configure"
    - "service-omni-agent-users-create"
    - "service-omni-base-settings-configure"
    - "service-omni-command-center-analyze"
    - "service-omni-permission-set-assign"
    - "service-omni-presence-status-deploy"
    - "service-omni-presence-user-config-deploy"
    - "service-omni-queue-deploy"
    - "service-omni-queue-members-assign"
    - "service-omni-queue-routing-config-deploy"
    - "service-omni-routing-flow-deploy"
    - "service-omni-service-channel-configure"
    - "service-omni-sidebar-configure"
    - "service-omni-skills-based-routing-configure"
    - "service-omni-supervisor-config-deploy"
    - "service-omni-supervisor-permset-assign"
    - "service-omni-supervisor-surface-deploy"
    - "service-omni-supervisor-users-create"
    - "service-omni-work-skill-routing-configure"
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

# service-omni-channel-setup-coordinate

Align an org toward a working Omni-Channel setup: detect what already exists and create or deploy only the missing pieces, up to a routed environment with agents, queues, presence statuses, and permissions. Full create-and-bind routing (queue + `QueueRoutingConfig` + outbound routing flow) is provided for `Case` and `VoiceCall`; `Incident` and `MessagingSession` are **verified/adopted only** by this coordinator — it reports their state and reuses existing config but does not create a missing queue/QRC/flow for them (use `service-agentforce-human-escalation-configure` for a created-and-bound `MessagingSession` handoff). This is a coordinator — it sequences the child leaf skills against a canonical set of steps and performs no writes of its own. Each leaf owns one primitive; the coordinator resolves per-org IDs, passes them between leaves, and enforces a shared reuse-vs-create and safety contract. It blocks with a click-path only for prerequisites an operator must action (a missing feature license, or a target sObject that is not enabled).

`python3` is listed only because the bundled contract tests (`scripts/tests/test_omni_contracts.py`) use it; running the coordinator itself needs only `jq` and `sf`.

## Inputs

Confirm these once, up front, before any write:

- Agent count (default `3`, range `1..10`) and supervisor count (default `1`, range `1..5`).
- Real login email (used for password-reset flows).
- `routing_targets` (default `["Case"]`) — any subset of `Case | Incident | MessagingSession | VoiceCall`. Only `Case` and `VoiceCall` get full create-queue + QRC + routing-flow; `Incident` and `MessagingSession` are verified/adopted (report-only).
- Service-channel strategy — reuse standard (`Cases`, `sfdc_livemessage`, default) or create a custom channel.
- Agent/supervisor profile — the driver provisions users on the `Service Cloud User` profile by default (Omni needs a Service Cloud license). Some orgs ship that license under a differently named profile (e.g. `Service Cloud`); override via `OMNI_AGENT_PROFILE` / `OMNI_SUPERVISOR_PROFILE` without editing the script. The user-create leaves block if the named profile is absent.
- Runtime proof (optional) — `OMNI_RUNTIME_PROOF=1` makes the routing-flow leaf fire the trigger (fail-soft); `OMNI_RUNTIME_PROOF_REQUIRED=1` makes proof blocking. QueueBased proof requires `PendingServiceRouting` or `AgentWork`. SkillsBased proof requires a `PendingServiceRouting` with at least one `SkillRequirement`, which is the acceptance signal that `WorkSkillRouting` actually ran. The throwaway record is always cleaned up.
- Queue selection (optional) — set `OMNI_CASE_QUEUE_DEVELOPER_NAME`, `OMNI_VOICE_QUEUE_DEVELOPER_NAME`, `OMNI_INCIDENT_QUEUE_DEVELOPER_NAME`, or `OMNI_MESSAGING_QUEUE_DEVELOPER_NAME` when the target must use a specific existing or canonical queue. Without an override, each leaf uses its target-derived default.
- Routing-config selection (optional) — set `OMNI_CASE_ROUTING_CONFIG_DEVELOPER_NAME` or `OMNI_VOICE_ROUTING_CONFIG_DEVELOPER_NAME` to select an existing QRC explicitly. When only a queue override is supplied, the coordinator first adopts that queue's linked `QueueRoutingConfig.DeveloperName`; it creates the canonical QRC only when the queue has no linked config.
- Queue routing controls (optional) — `OMNI_QRC_PUSH_TIMEOUT` sets the agent acceptance timeout and `OMNI_QRC_CAPACITY_PERCENTAGE` selects percentage capacity (for example, `100` for a VoiceCall that consumes the agent's full capacity). The coordinator passes both values to every QRC target.
- Routing mode — `OMNI_ROUTING_TYPE=QueueBased|SkillsBased` is optional. When all four `OMNI_WSR_ENTITY` / `OMNI_WSR_FIELD` / `OMNI_WSR_SKILL` / `OMNI_WSR_VALUE` inputs are supplied, the coordinator infers `SkillsBased`; otherwise it defaults to `QueueBased`. SkillsBased uses `OMNI_SKILL_OPTION=RunSBRRules` (the default), binds the provisioned agents to `OMNI_SBR_SKILL` (defaults to `OMNI_WSR_SKILL`), authors the WorkSkillRouting rule, and only then activates the flow. An incomplete mapping or mismatched SBR/WSR skill is rejected before any write. `OMNI_WSR_LABEL` optionally names the rule.
- Rep-experience stages (optional, default off) — `OMNI_REP_EXPERIENCE=1` adds presence user config (decline + decline reason + ACW) and the Omni sidebar. `OMNI_CONSOLE_APP=<app DeveloperName>` targets a specific console app; empty auto-detects one.
- Supervisor surface (always, after the config) — once `OmniSupervisorConfig` exists, the coordinator populates its standard action + tab surface (`OmniSupervisorConfigAction` / `OmniSupervisorConfigTab`) via the Data API. Just before the classic config deploy it also runs a read-only Command Center analysis that reports whether the org is on the classic surface or Command Center V2.
- Supervisor-config selection (optional) — set `OMNI_SUPERVISOR_CONFIG_DEVELOPER_NAME` to the exact classic `OmniSupervisorConfig.DeveloperName` that both the config and surface stages must reconcile. It defaults to `Omni_Supervisor`; use the override whenever the org has multiple configs so the coordinator never guesses. `OMNI_SUPERVISOR_CONFIG_MASTER_LABEL` optionally supplies the label when creating a new selected config.

Run it in plan or run mode:

```bash
bash scripts/integration-driver.sh --plan <org-alias> [agent_count] [routing_targets_csv] [supervisor_count]
bash scripts/integration-driver.sh --run  <org-alias> [agent_count] [routing_targets_csv] [supervisor_count]
```

`--plan` is a full read-only preview: each leaf runs its own detector and reports `reused`, `action_needed`, or `blocked`; a leaf whose prerequisite is not yet in place is reported as pending work rather than probed, so a plan never shows a misleading red for a step that is simply earlier in the sequence. A clean plan (all `reused`, exit 0) means the org is already configured; any yellow (exit 2) means work remains.

## Preconditions and safety

- Authenticated org via `sf` CLI using the My Domain URL (not `.lightning.force.com`).
- Service Cloud license with headroom for the agent count.
- `Incident` targets require the Incident Management feature enabled; `MessagingSession` requires Enhanced Messaging; `VoiceCall` requires Service Cloud Voice. The readiness check hard-fails with a click-path when a requested target sObject is absent.
- **Production guardrail:** `safe_to_write` is `true` iff any of `IsSandbox = true`, `TrialExpirationDate != null`, or `OrganizationType IN ('Developer Edition', 'Base Edition')`. The run hard-refuses when it is false. CDOs return `IsSandbox=false` with a non-null `TrialExpirationDate` and must be permitted, so `IsSandbox` alone is never the guard.

Readiness check (silent, mandatory, before any leaf runs):

1. `sf org display` → confirm the org alias is authenticated; refuse (exit 1) if not.
2. `Organization` (`IsSandbox`, `TrialExpirationDate`, `OrganizationType`) → compute `safe_to_write`; refuse (exit 1) if false.
3. Preflight entity availability → for each **non-`Case`** routing target, confirm the sObject exists via `EntityDefinition`; a missing target hard-fails with a feature-enablement click-path (exit 2). `Case` is assumed present and skipped.

Omni-Channel base-settings enablement is not a separate upfront probe — it is detected by the base-settings leaf (step 1), and downstream Omni-dependent leaves are deferred as pending in `--plan` until it is on. The driver does not pre-check `UserLicense` headroom or `ServicePresenceStatus`/`QueueRoutingConfig` availability in this readiness pass.

## Skills this coordinates

The coordinator delegates every write to a leaf skill. sObject-specific leaves (3, 5, 6, 6c, 7) loop once per routing target; the rest run once. For SkillsBased routing, steps 6a and 6b complete before any trigger flow is activated. Step 10a (`command-center-analyze`) is a read-only advisory and always runs. Step 11a (`supervisor-surface-deploy`) always runs after the supervisor config succeeds. Leaves 12–13 are the opt-in rep-experience stages (`OMNI_REP_EXPERIENCE=1`).

| # | Child skill | Role |
|---|---|---|
| 1 | `service-omni-base-settings-configure` | Deploy `Settings:OmniChannel` (5 toggles) |
| 2 | `service-omni-agent-users-create` | Provision the requested agent users |
| 3 | `service-omni-service-channel-configure` | Reuse the standard `ServiceChannel` for the target sObject, or deploy the canonical XML |
| 4 | `service-omni-queue-routing-config-deploy` | Upsert the target's `QueueRoutingConfig` (e.g. `Case_Routing_Config`, `Voice_Routing_Config`) |
| 5 | `service-omni-queue-deploy` | Discover or create (`--create-if-missing`) a `Queue` bound to the target sObject; align it to the QRC |
| 6 | `service-omni-queue-members-assign` | Assign users to the discovered queue |
| 6a | `service-omni-skills-based-routing-configure` | *(SkillsBased only)* Ensure the `Skill` and active agents' `SkillUser` bindings exist |
| 6b | `service-omni-work-skill-routing-configure` | *(SkillsBased only)* Author the required field-value → Skill rule before flow activation |
| 6c | `service-omni-routing-flow-deploy` | Deploy the record-triggered QueueBased or SkillsBased `Flow` for `Case`/`VoiceCall`; SkillsBased passes `skillOption=RunSBRRules` |
| 7 | `service-omni-presence-status-deploy` | Deploy `Available_<sObject>` bound to the matching channel and ensure a universal `Busy` status |
| 8 | `service-omni-permission-set-assign` | Assign the `Omni_Agent` PermissionSet to agent users; self-heals the bundled metadata when absent (run mode only) |
| 9 | `service-omni-supervisor-users-create` | Provision supervisor users |
| 10 | `service-omni-supervisor-permset-assign` | Assign the standard `ContactCenterSupervisor` PermissionSet to supervisor users |
| 10a | `service-omni-command-center-analyze` | **Read-only advisory** — report whether the org is on the classic supervisor surface or Command Center V2; never writes, never hard-blocks |
| 11 | `service-omni-supervisor-config-deploy` | Deploy `OmniSupervisorConfig` binding supervisor users to the queues discovered in step 5 |
| 11a | `service-omni-supervisor-surface-deploy` | Populate the supervisor **action + tab surface** (`OmniSupervisorConfigAction` / `OmniSupervisorConfigTab`) on the config from step 11 |
| 12 | `service-omni-presence-user-config-deploy` | *(opt-in)* Deploy `PresenceUserConfig` + `PresenceDeclineReason` (decline + ACW) and assign the provisioned agents |
| 13 | `service-omni-sidebar-configure` | *(opt-in)* Set `CustomApplication.isOmniPinnedViewEnabled=true` to pin the Omni utility region on a console app |
| — | `platform-metadata-deploy` | Underlying Metadata API deploys used by the deploy leaves |

## Behavior

**Reuse-vs-create contract (enforced for every entity).** Query by `DeveloperName` (or the natural key); reuse a standard record when present (`Cases`, `sfdc_livemessage`); create from the leaf's bundled definition when nothing exists; reconcile idempotently when a same-named custom record exists — never duplicate, rename, or mutate the identity of a standard or managed record.

**Ordering and gating.** Leaves run in dependency order. Base settings are a hard prerequisite for every write below. For SkillsBased routing, agent `SkillUser` bindings (6a) and the `WorkSkillRouting` rule (6b) must succeed before the routing-flow leaf (6c) can activate the trigger. The flow also requires the queue (5) and its members (6), and it round-trips `FlowDefinitionView.ActiveVersionId` to prove the flow is Active. A required runtime proof does not pass merely because a PSR exists: SkillsBased requires at least one `SkillRequirement` on that PSR.

**Supervisor path.** Supervisor users (9) use the same Anonymous Apex `System.setPassword` model as agent users. Because a password literal can be captured in an `ApexLog` when a debug TraceFlag is active, both user-create leaves fail closed *before* the first `System.setPassword`: they prove via a SOQL-filtered Tooling API query (`ExpirationDate > now`) that no active TraceFlag exists for the running user, and if that cannot be positively proven they set no password at all (users left ACTIVE and `reset_required`, with a `security_warning`). They never delete logs, so unrelated audit logs are untouched. The supervisor permset leaf (10) assigns the standard `ContactCenterSupervisor` — never the custom `Omni_Supervisor`, whose license-gated permissions fail assignment — and a contract test asserts this wiring. After the supervisor permset, a read-only Command Center analysis (10a) reports the org's supervisor surface (classic vs Command Center V2); it never writes and never hard-blocks (ambiguous detection is yellow, a clean read green). Once the config lands (11), the surface leaf (11a) inserts the standard action + tab companions (`OmniSupervisorConfigAction` / `OmniSupervisorConfigTab`) against the config's Id — plain Data API rows, so no metadata-file redeploy — and is idempotent (only missing types are inserted). It runs only after the config succeeds; a skipped or failed config skips the surface with a dependency note.

**Optional rep-experience stages.** With `OMNI_REP_EXPERIENCE=1`, presence user config (12) deploys a validator-safe `PresenceUserConfig` with its decline reason and assigns every resolved agent username, including reused users. Sidebar (13) pins the Omni utility region on `OMNI_CONSOLE_APP`, or auto-detects a single console app. SkillsBased routing is not a cosmetic rep-experience stage: when requested, its SkillUser and WorkSkillRouting prerequisites run before flow activation.

**Login-behavior gap.** The login-behavior radio (Setup → Omni-Channel Settings → "Define login behavior when an agent opens a new window/tab") has no public API on v66. After base settings deploy, the coordinator surfaces the exact click-path; it does not attempt to flip it via `enableOmniAutoLoginPrompt`, which deploys but does not drive the radio. See `references/gap-catalog.md`.

**Credentials.** Generated passwords are moved into a single restricted `CREDENTIALS.json` (mode 0600) and redacted from every other artifact. The write is atomic and fail-closed: on any redaction or verification failure the plaintext artifact is removed and the run aborts, so no plaintext password is left in the artifacts directory. The operator reads `CREDENTIALS.json` once, distributes securely, then deletes it.

## Output contract

The one deliverable is a single report file. As the final action you MUST use the `Write` tool to save the complete report to `omni-coordinate-report.md` in the current working directory — never deliver it only in chat. In `--run` mode it states what *is* (created resource, reused standard record, resolved decision) — no hedging. In `--plan` mode it states each leaf's honest disposition (`reused` / `action_needed` / pending) plus the coordinator's plan JSON (`dry_run: true`). Each leaf also writes its full JSON outcome (including every created record Id and deploy Id) to a per-skill artifact under the run's artifacts directory — that is the audit trail; user-facing output uses human-readable names, not record Ids. See `examples/output-templates.md` for the report shape.

**Run artifacts (run mode).** Alongside the per-skill artifacts, a `--run` writes three files into the run's artifacts directory (paths echoed in the report JSON as `run_log`, `deploy_ids_file`, `teardown_script`): `run.log` (sanitized, human-readable step sequence and result), `deploy_ids.json` (a provenance manifest — each entry's `provenance` is `created` / `updated` / `reused`, with resource ids, a `before` snapshot, and a pointer to the authoritative per-skill artifact), and `teardown.sh` (an auto-generated, **dry-run** reverse-dependency-order plan). The teardown script prints what a teardown would `REMOVE` (run-created), `RESTORE` (updated, with prior values), or `KEEP` (adopted/reused — never deleted) and makes no changes; destructive execution stays manual by design (see Limitations).

Report content rules:

- Report concrete outcomes, never intentions.
- Surface the login-behavior click-path whenever setup ran, even if the operator declined to turn the radio.
- Surface any hard fail from step 5 (no queue bound) as a manual action with a click-path.

## Limitations

- Routing-flow deploy covers `Case` and `VoiceCall` only.
- Classic `OmniSupervisorConfig` (including its action + tab surface) only. Command Center V2 (Enhanced Omni-Channel) is reported by the read-only analysis step but not enabled — the org preference is not writable via the Metadata API. The surface leaf populates only the reference-free standard action/tab types; custom-action, FlexiPage, AWS-dashboard, and AI-agent surfaces need an external reference and must be set up in Setup.
- The rep-experience stages (presence user config, decline reasons, sidebar) run only with `OMNI_REP_EXPERIENCE=1`. SkillsBased routing is selected explicitly or inferred from a complete `OMNI_WSR_*` mapping and runs independently of that flag.
- Teardown is **plan-only**: `--run` emits `deploy_ids.json` (a provenance manifest) and a dry-run `teardown.sh` that prints the reverse-order removal/restore plan, but does not execute destructive changes. Automated reversal is deliberately deferred until every leaf emits a normalized provenance block and the reversal is validated live — metadata-deployed components need destructiveChanges deploys and adopted records must never be deleted. Reversal today is a manual operator task guided by the plan and the per-skill artifacts.

### Use-case coverage (current)

| Use case | Status | What is / isn't headless |
| --- | --- | --- |
| Case routing | Ready | Full create-and-bind thread (queue + QRC + members + routing flow), idempotent; runtime `PendingServiceRouting` proof optional. |
| VoiceCall / AFCC routing | Conditional | QRC + queue + members + routing flow are deployable, but require a **provisioned Amazon/AFCC contact center** and a live Voice runtime to prove end-to-end. Contact-center provisioning is the caller's responsibility. |
| Open CTI → AFCC migration | Partial | The coordinator creates the Omni routing resources; it does not provision or migrate the contact center itself. |
| Incident routing | Partial | Service channel + presence are supported; the coordinator **verifies/adopts** Incident routing but does not create a missing queue/QRC/flow for it. |
| Generic MessagingSession routing | Partial | Service channel + presence supported; full create-and-bind is delegated to `service-agentforce-human-escalation-configure`, not run generically here. |
| Classic Omni Supervisor | Ready | Users, permissions, config, queues/users, and the action/tab surface companions are all implemented. |
| Command Center V2 | Detection only | The read-only analysis step reports classic vs V2; the org preference `CommandCenterForServiceV2` is **not writable via the Metadata API** (tracked: W-23827287) and must be enabled in Setup. |
| Supervisor monitoring OrgValues | Not implemented | `OmniSuperConvMonitor`, `OmniSuperAgentSneakpeek`, `OmniSuperClientSneakpeek`, `OmniSuperWhisper`, `OmniSuperAdminSkillQueue` are OrgValues with no proven supported external write API. |
| Omni Inbox | Not implemented | The sidebar leaf pins the Omni sidebar (`isOmniPinnedViewEnabled`); it does not create or configure Omni Inbox, a console app, or utility items. |

## References

| File | When to read |
|---|---|
| `references/gap-catalog.md` | The headless gaps (login-behavior radio, Agentforce routing target, Field Service skills routing) and how the coordinator handles each |
| `examples/output-templates.md` | Before emitting the report — canonical Setup Summary, Skill Outcomes, and Manual Actions blocks |

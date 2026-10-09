---
name: service-omni-routing-flow-deploy
description: "Use to deploy an Omni-Channel routing Flow for Case or VoiceCall and verify it routes work items to a queue or by skill. Supports the Case and VoiceCall steel thread with an autolaunched dryRun-gated variant and record-triggered QueueBased and SkillsBased variants. --trigger deploys a record-triggered variant; --routing-type SkillsBased evaluates WorkSkillRouting rules with a non-null skillOption; --runtime-proof checks routing evidence and, for SkillsBased, SkillRequirement rows. Triggers: deploy Omni routing flow for Case, deploy Omni routing flow for VoiceCall, wire VoiceCall routing, create a record-triggered Omni routing flow, verify a Case routing flow, deploy skills-based routing flow. Do not use for screen flows, platform-event-triggered flows, or Flow Tests."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-presence-status-deploy"
    - "service-omni-queue-deploy"
    - "service-omni-queue-routing-config-deploy"
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

# service-omni-routing-flow-deploy

> Voice runtime proof depends on a provisioned Contact Center. Flow redeploys report `Changed` even when the deployed configuration is unchanged.

Deploy an Omni-Channel routing Flow via the Metadata API, confirm it lands Active, and prove it routes work — either by CLI invocation (the autolaunched dry-run) or by observing real routing side effects (the record-triggered variant). `service-omni-channel-setup-coordinate` wires it in after `service-omni-queue-deploy` has produced the target queue and its members are bound.

## Variants

Four assets ship under `assets/force-app/main/default/flows/` — an autolaunched and a record-triggered variant for each of Case and VoiceCall. Selection is by `--target Case|VoiceCall` (default Case) and `--trigger`.

| Variant | Shape | Proves | Routes real work? |
|---|---|---|---|
| `Omni_Route_Cases` / `Omni_Route_VoiceCalls` (default) | Autolaunched, `dryRun` gate | CLI invocability via Actions REST, no side effects | No |
| `Omni_Route_Case_Trigger` / `Omni_Route_VoiceCall_Trigger` (`--trigger`) | Record-triggered on insert, calls `routeWork` | Real routing — the insert creates `PendingServiceRouting`/`AgentWork` | Yes |

The autolaunched variant de-risks the headless CLI path cheaply; the record-triggered variant proves real records reach a queue. A full steel thread deploys the record-triggered variant.

With `--trigger --routing-type SkillsBased`, the record-triggered variant is drawn from a sibling `<FlowDN>.SkillsBased.flow-meta.xml` asset that emits `routingType=SkillsBased` plus a non-null `skillOption`. The base trigger flows hardcode `routingType=QueueBased`, so a skills-based-routing org config never takes effect at runtime — this variant is what makes it route by skill (W-24069467).

## Inputs

```bash
bash scripts/deploy-and-report.sh <org-alias> [flow_developer_name] [--target Case|VoiceCall] [--trigger] [--routing-type QueueBased|SkillsBased] [--skill-option RunSBRRules|DefineSkillRequirements|Both] [--runtime-proof] [--require-proof] [--skip-invoke]
# autolaunched smoke test (Case):
bash scripts/deploy-and-report.sh myorg
# record-triggered Voice routing with runtime proof:
bash scripts/deploy-and-report.sh myorg --target VoiceCall --trigger --runtime-proof
# skills-based Case routing (platform evaluates WorkSkillRouting rules):
bash scripts/deploy-and-report.sh myorg --target Case --trigger --routing-type SkillsBased --runtime-proof
```

- `--target Case|VoiceCall` (default Case) — selects the flow pair.
- `--trigger` — deploy the record-triggered variant with dynamic token resolution.
- `--routing-type QueueBased|SkillsBased` (default QueueBased; env `OMNI_ROUTING_TYPE`) — `SkillsBased` deploys the `<FlowDN>.SkillsBased` variant that calls `routeWork` with `routingType=SkillsBased`, so the org's skills-based routing config takes effect at runtime instead of being inert. It deploys under the same DeveloperName, replacing the QueueBased trigger (never two triggers on one object).
- `--skill-option RunSBRRules|DefineSkillRequirements|Both` (default `RunSBRRules`; env `OMNI_SKILL_OPTION`; SkillsBased only) — `RunSBRRules`/`Both` make the platform evaluate the org's `WorkSkillRouting` rules server-side and attach matching `SkillRequirement` rows to the PSR; `DefineSkillRequirements` uses only skills the flow itself passes. A SkillsBased deploy with an empty/invalid skillOption is **refused** (exit 2): a null skillOption NPEs the platform `routeWork` action and rolls back the triggering insert (W-24069761), so the asset always carries a non-null value.
- `--runtime-proof` (implies `--trigger`) — after deploy, insert a target record. QueueBased accepts a `PendingServiceRouting` or `AgentWork` row. SkillsBased requires a `PendingServiceRouting` with at least one `SkillRequirement`, proving that `RunSBRRules` evaluated the active `WorkSkillRouting` rule. Proof is fail-soft unless required. The record is always deleted afterward.
- `--require-proof` (implies `--runtime-proof`; also `OMNI_RUNTIME_PROOF_REQUIRED=1`) — makes that proof blocking; the release gate for the Voice steel thread.
- `--skip-invoke` (autolaunched only) — deploy + verify Active, no Actions REST call.
- Token overrides (`--trigger`): `QUEUE_DEVELOPER_NAME`, `ROUTING_CONFIG_DEVELOPER_NAME`, `SERVICE_CHANNEL_DEVELOPER_NAME`. The coordinator always supplies these three from the resources it established for the target, so the flow binds the same channel/queue/QRC rather than a guessed default.

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6, `jq` ≥ 1.6.
- Omni-Channel base settings enabled (`service-omni-base-settings-configure`) — the routing action resolves only when Omni is on; the flow deploys without it but fails at runtime.
- Record-triggered runs need a deployed ServiceChannel (`service-omni-service-channel-configure`), Queue (`service-omni-queue-deploy`), and QueueRoutingConfig (`service-omni-queue-routing-config-deploy`) to resolve their tokenized IDs; runtime proof additionally needs an agent online with a compatible presence status (`service-omni-presence-status-deploy`).
- The three-way `safe_to_write` production guard applies.

## Run

`deploy-and-report.sh` deploys, verifies, and (per variant) proves routing:

1. **Resolve tokens** (record-triggered only) — the committed asset carries `__QUEUE_ID__`, `__ROUTING_CONFIG_ID__`, `__SERVICE_CHANNEL_ID__`, and channel name/label tokens. The skill resolves each by DeveloperName into a materialized copy that is never committed (the asset stays tokenized for portability). A ServiceChannel that does not resolve fails closed rather than embedding an empty id.
2. **Deploy** — `sf project deploy start --metadata "Flow:<FlowDN>"`; the `files[].state` maps to `reused`/`updated`/`created`.
3. **Verify Active** — retrieve the Flow and confirm its resource IDs, `routingType`, and SkillsBased `skillOption` still match; otherwise redeploy. Confirm an active version exists.
4. **Prove routing** — autolaunched: POST to `/actions/custom/flow/<FlowDN>` with `{"dryRun":true}` and assert `isSuccess` and `dryRunOk`. Record-triggered: insert a target record and observe routing. SkillsBased success additionally requires one or more `SkillRequirement` rows on the PSR.

## Behavior

**Two shapes, two verification paths.** "Can we invoke a routing flow headlessly?" and "do real records route to a queue?" are different questions. The autolaunched `dryRun` flow answers the first in one side-effect-free HTTP call — the flow must have a code path that succeeds without prerequisites, so `dryRun=true` takes an assignment step and returns `dryRunOk=true`. Record-triggered flows are not exposed as custom actions, so the only headless proof is inserting the source record and observing `PendingServiceRouting`/`AgentWork`. The PSR row alone proves the flow routed; agent assignment depends on Omni distribution, not the flow.

**Active-version round trip.** For the record-triggered variant, component deploy state proves only the transaction, not that an active version exists. The skill prefers `FlowDefinitionView.ActiveVersionId` and falls back to the active Tooling `Flow` row when that view is unavailable. It fails closed when neither source proves an active version, so `flow_active:true` is never reported without evidence.

**Binding-drift redeploy.** `reused` means an active version already exists and its embedded queue/QRC/ServiceChannel IDs, routing type, and SkillsBased skill option match the request. If a binding or routing mode drifted, the skill redeploys instead of reusing. `OMNI_FLOW_FORCE=1` forces a redeploy.

**Idempotency quirk.** Unlike most metadata types, `Flow` deploys are not byte-idempotent — Salesforce reports `Changed` on identical redeploys because every deploy is a potential version bump. Treat `updated` from this skill as "successfully redeployed," not "operator modified the flow."

**Safety.** Deploys use explicit `--metadata "Flow:<DN>"` (never `--source-dir`) so sibling flows are untouched, and the skill never overwrites a Flow it did not author — the coordinator supplies `flow_developer_name` deliberately. `flow_developer_name` is validated against `^[A-Za-z][A-Za-z0-9_]{0,79}$` because it is interpolated into the Actions REST URL path.

## Output contract

A single JSON object with `status` ∈ `created` | `reused` | `updated` | `blocked`, `flow_developer_name`, `flow_state`, `flow_active`, `deploy_id`, `manual_actions`, and `blocking_issue`. The autolaunched variant adds `verification_path` and `invocation_smoke_test` (`attempted`, `success`, `endpoint`, `dry_run_ok`). The record-triggered variant adds `mode: "record_triggered"`, `target`, `flow_active_version_id`, `routing_type`, `skill_option` (the skillOption when SkillsBased, else null), `resolved` (queue/routing_config/service_channel), and `runtime_proof` (`attempted`, `required`, `success`, `record_id`, `pending_service_routing`, `agent_work`, `reason`). Under `--routing-type SkillsBased`, `runtime_proof` also carries `skill_requirement_count` and `skill_requirements` — the `SkillRequirement` rows the platform attached to the PSR (the skills-based acceptance signal).

- `blocked` — deploy failed; the flow is not Active; the autolaunched invocation failed; a queue/QRC could not be resolved; the ServiceChannel did not resolve; or `--require-proof` was set and the mode-specific proof was not observed. For SkillsBased, a PSR with zero `SkillRequirement` rows is not a passing proof. A plain `--runtime-proof` failure remains fail-soft.
- `runtime_proof.attempted` is `false` unless `--runtime-proof`/`--require-proof` was passed; the throwaway record is always cleaned up.

## Limitations

- Case and VoiceCall only; extend by forking the closest asset and preserving the `dryRun`/`dryRunOk` contract (autolaunched) or the `routeWork` + tokenized-ID pattern (record-triggered).
- Does not register the Flow on a queue's routing configuration — that binding belongs to `service-omni-queue-routing-config-deploy`.
- Does not handle screen flows, platform-event-triggered flows, or Flow Tests.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | On unexpected deploy or verification behavior — variant comparison, the token-resolution table, Flow schema, the Actions REST response shape, and record-DML verification |

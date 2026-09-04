---
name: service-agentforce-human-escalation-configure
description: "Use to configure and verify Agentforce agent-to-human escalation, including human handoff, a staffed fallback queue, and failure-threshold directives. Triggers: configure agent escalation, escalate to a human agent, agent handoff to a queue, configure a human escalation queue, set an Agentforce fallback handoff. Do not use to create an agent or configure inbound channel routing; use service-agentforce-channel-configure for inbound routing."
metadata:
  version: "1.0"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "service-agentforce-channel-configure"
    - "service-digital-engagement-channel-configure"
    - "service-itsm-agentic-setup-agentforce-coordinate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "license"
      value: "Agentforce"
allowed-tools: Bash Read Write AskUserQuestion
---

# Configure Agentforce Agent → Human Escalation

Wire an Agentforce agent so it can hand a conversation off to a human agent through an Omni-Channel queue. This skill configures and verifies the escalation surfaces, then reports a single machine-readable JSON verdict. It is **idempotent** per developer name and **refuses to write to production orgs**. It runs standalone or as a stage in a larger setup flow (after the agent is created and active).

The agent, queue, outbound flow name, routed context object, service channel, and failure thresholds are all inputs, so the same skill serves any scenario (IT employee support, customer messaging, etc.) — the caller supplies the scenario-specific identifiers.

This skill is the **authoritative owner of agent-to-human (outbound) escalation**. `service-agentforce-channel-configure` may wire a basic outbound flow + `connection` block in the same pass as inbound channel setup, but it delegates full escalation configuration and verification here.

## The honest boundary — what is deterministic vs. directive vs. runtime

Escalation in Agentforce is assembled from surfaces with different verifiability:

- **Deterministic** (this skill writes and/or round-trip verifies via the Metadata/Data API): `canEscalate=true` on the escalation topic (`GenAiPlugin`); `outboundRouteConfigs` on the agent's Messaging planner surface (`GenAiPlannerBundle`), where the SAME block couples `outboundRouteName` to `outboundRouteType=OmniChannelFlow` on a Messaging-class surface; a QueueBased outbound `RoutingFlow` with a non-null `ActiveVersionId`; a human queue with a `QueueSobject` for the context object, its `QueueRoutingConfig` bound to the queue, and **at least one active human member** (a queue with zero members can never route an escalation to a human, so it never reaches `CONFIGURED`); and the agent Active after republish.
- **Directive / native policy** (authored as Agent Script instructions, **not** a metadata counter): the default **two consecutive failures** threshold plus per-topic overrides (e.g. **password reset = one failure**). There is no metadata field that counts failed turns — the threshold is instruction text, verified by an ADK eval rubric, not a runtime read. See [references/failure-policy.md](references/failure-policy.md).
- **Runtime / manual only**: the actual conversational trigger, `AgentWork` creation, and same-session context preservation. These cannot be driven headlessly — they are a documented manual test + eval rubric. See [references/runtime-verification.md](references/runtime-verification.md).

## Authoring models — classic vs next-gen (NGA)

Salesforce exposes two Agentforce authoring models, and Phase 1b auto-detects which the org supports from its metadata types. The routing infrastructure (queue, `QueueSobject`, members, `QueueRoutingConfig`, outbound `RoutingFlow`) is **identical in both**; only the agent-side escalation surface differs.

- **classic** — org exposes `GenAiPlugin` + `GenAiPlannerBundle`. The agent surface is `canEscalate` (topic) + `outboundRouteConfigs` (planner Messaging surface). This surface is authored in Phase 4 (hand-edited, or via the optional `AUTHOR_SURFACES=1` pass) and round-trip verified in Phase 7.
- **nga** — org exposes `AiAuthoringBundle` (Agent Script) and **no** `GenAiPlannerBundle`. There is no `outboundRouteConfigs` metadata; the agent surface is a reachable `@utils.escalate` action (Service agents) or a create-record action (Employee agents, which cannot use `@utils.escalate`), and the queue routing is carried entirely by the deterministic routing half. This skill **verifies** that surface from the retrieved bundle and delegates its **authoring** to `agentforce-generate`.
- **none** — neither surface is exposed → the skill fails closed before any write.

Detection can be pinned with `AUTHORING_MODEL_OVERRIDE=classic|nga` when both coexist. Full rules, the Service-vs-Employee split, and the NGA verdict set live in [references/nga-escalation.md](references/nga-escalation.md).

## Scope

- **In scope**: enabling the escalation topic (`canEscalate`); wiring `outboundRouteConfigs` on the `GenAiPlannerBundle` Messaging surface; deploying the bundled QueueBased outbound `RoutingFlow`; create-or-adopt of the human queue (`QueueSobject` for the context object) and its `QueueRoutingConfig`; authoring the failure-threshold directives; republish + reactivate; and a deterministic config round-trip verdict. Idempotent re-run.
- **Out of scope**: creating/activating the agent; inbound channel transport (`sessionHandlerAsa` on the `MessagingChannel`) and the agent's outbound `connection` block (owned by `service-agentforce-channel-configure`); provisioning the messaging channel itself (`service-digital-engagement-channel-configure`); broader Omni-Channel routing infrastructure; standalone queue provisioning outside an escalation context; and any production-org write.

---

## Inputs

| Input | Positional | Env | Default |
|---|---|---|---|
| Org alias | 1 (required) | — | — |
| Agent developer name | 2 | `AGENT_DEVELOPER_NAME` | `Support_Agent` |
| Queue developer name | 3 | `QUEUE_DEVELOPER_NAME` | `Human_Support_Queue` |
| Escalation topic API name | 4 | `ESCALATION_TOPIC_API_NAME` | (unset — surface unverified) |
| Planner bundle API name | 5 | `PLANNER_BUNDLE_API_NAME` | (unset — surface unverified) |
| Outbound flow developer name | — | `FLOW_DEVELOPER_NAME` | `Human_Escalation_Outbound_Flow` |
| Outbound flow label | — | `FLOW_LABEL` | flow name with `_` → space |
| Context object (routed sObject) | — | `CONTEXT_OBJECT` | `MessagingSession` |
| Service channel dev name / label | — | `SERVICE_CHANNEL_DEV_NAME` / `SERVICE_CHANNEL_LABEL` | `sfdc_livemessage` / `Messaging` |
| Human members to add if empty | — | `QUEUE_MEMBER_USERNAMES` | (unset) |
| Failure threshold (consecutive failed attempts before hand-off) | — | `DEFAULT_FAILURE_THRESHOLD` | `2` |
| Threshold directive authored (out-of-band flag) | — | `THRESHOLD_AUTHORED` | `0` |

For a non-`MessagingSession` context object (e.g. `Case`, `VoiceCall`), pass the matching `SERVICE_CHANNEL_DEV_NAME` / `SERVICE_CHANNEL_LABEL`.

## Preconditions

1. **`sf` CLI installed and authenticated** to the target org (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`.
2. **`node` ≥ 18** and **`jq`** on PATH (the deterministic classifiers and JSON assembly).
3. **The agent exists and its latest `BotVersion` is Active.** This skill fails closed if not.
4. **For `MessagingSession` handoff, an active `MessagingChannel` exists.** This skill fails closed if none is found. Other context objects use a different transport and are not gated on `MessagingChannel`.
5. **Sandbox / trial CDO / Developer Edition org.** The skill refuses to configure escalation on a real production customer org.

If a precondition fails, `sf` surfaces the raw error — do not fabricate state; surface it and stop.

---

## Workflow

### Phase 0 — Production write-guard (mandatory, first write-gate)

Before any write, the orchestrator queries `Organization` (`IsSandbox`, `TrialExpirationDate`, `OrganizationType`) and computes `safe_to_write`. If the org is a real production customer org, the skill emits `status: "BLOCKED"` and stops. This is enforced in `scripts/verify-and-configure.sh` — never bypass it.

### Phase 1 — Preconditions (read-only, fail closed)

1. **Agent Active** — SOQL `BotDefinition` (+ latest `BotVersion`), classified deterministically by [scripts/classify-agent-active.mjs](scripts/classify-agent-active.mjs). Not found or inactive → block with the activation click-path.
2. **Transport channel present** — for `MessagingSession`, SOQL `MessagingChannel WHERE IsActive=true`; zero rows → block with a pointer to `service-digital-engagement-channel-configure`.

### Phase 2 — Human queue (create-or-adopt) + members

Resolve the queue by DeveloperName. If missing, deploy a `Queue` (canonical Metadata API element order: `doesSendEmailToMembers`, `name`, `queueSobject`) with a `QueueSobject` for `CONTEXT_OBJECT`. For an adopted queue missing the binding, add the context object additively via the Data API. Create the `QueueRoutingConfig` if absent and bind it to the queue (`Group.QueueRoutingConfigId`), re-querying to confirm the bind persisted.

**Members (human routability):** the queue must have at least one active human member — otherwise the escalation routes to an empty queue. The skill counts `GroupMember` rows that resolve to an active `User`. If there are none and you pass `QUEUE_MEMBER_USERNAMES` (comma-separated usernames), it validates each against the username grammar up front, resolves the active `User`, and POSTs the `GroupMember`; it then re-counts. If the queue still has zero active human members the verdict is `INCOMPLETE` with `queueHasActiveDirectUserMember` in `missing` (an active direct user is necessary — not sufficient — for human routability; full Omni permission-set + presence-status eligibility is proven only at runtime). When there is no eligible member, the skill also skips QueueRoutingConfig binding and outbound-flow activation, so it never wires an empty queue. Use an approved Omni provisioning workflow when richer member reconciliation is required.

### Phase 3 — Outbound QueueBased RoutingFlow

Deploy the bundled outbound flow template [assets/force-app/main/default/flows/Human_Escalation_Outbound_Flow.flow-meta.xml](assets/force-app/main/default/flows/Human_Escalation_Outbound_Flow.flow-meta.xml), substituting the flow name/label, queue DeveloperName, and service-channel tokens. The flow looks the queue up by DeveloperName at runtime (portable, no hardcoded Id). After deploy, `FlowDefinitionView.ActiveVersionId` must be non-null.

### Phase 4 — Escalation topic + planner outbound route (doc-driven edits)

These two edits require per-org topic/bundle discovery, so they are authored explicitly (retrieve → edit → deploy), then verified by the orchestrator when you pass the topic/bundle API names. Follow [references/escalation-mechanism.md](references/escalation-mechanism.md):

1. Retrieve the escalation topic (`GenAiPlugin`), set `<canEscalate>true</canEscalate>`, deploy.
2. Retrieve the agent's `GenAiPlannerBundle`, add `outboundRouteConfigs` (`escalationMessage`, `outboundRouteName=<FLOW_DEVELOPER_NAME>`, `outboundRouteType=OmniChannelFlow`) on the Messaging planner surface, deploy. The verifier couples name + type inside the SAME block on a Messaging-class surface (via [scripts/extract-outbound-route.mjs](scripts/extract-outbound-route.mjs)) — a bundle with the right name and an `OmniChannelFlow` type in unrelated blocks will not pass.

### Phase 5 — Failure-threshold directives (native policy)

The failure threshold and any per-topic overrides are **directives, not enforced counters** — there is no metadata field that counts failed turns (see [references/failure-policy.md](references/failure-policy.md)). The orchestrator does **not** write these into the agent; it only renders `DEFAULT_FAILURE_THRESHOLD` (default `2`) into the local directive template [assets/escalation-thresholds.instructions.md](assets/escalation-thresholds.instructions.md) — pass e.g. `DEFAULT_FAILURE_THRESHOLD=3` for a three-attempt scenario — and reports that value under `threshold.default_failures` (with `threshold.directive_rendered`) as verdict evidence. Authoring the rendered directive into the agent's Agent Script is a manual/out-of-band step; set `THRESHOLD_AUTHORED=1` on the verifier run to record `threshold.authored=true`. The directive is eval-verified, never a headless runtime read, so it never blocks the deterministic verdict.

### Phase 6 — Republish + reactivate

After the Phase 4/5 edits, republish and reactivate the agent so they take effect. These are **manual operator commands** for the hand-edited path; the orchestrator itself only publishes/deactivates/reactivates the agent inside the optional `AUTHOR_SURFACES=1` pass (see "Running it"):

```bash
sf agent validate authoring-bundle --api-name "$AGENT_DN" --target-org "$ORG" --json
sf agent publish  authoring-bundle --api-name "$AGENT_DN" --target-org "$ORG" --json
sf agent activate --api-name "$AGENT_DN" --target-org "$ORG"
```

### Phase 7 — Deterministic verification (single JSON verdict)

The orchestrator round-trips every deterministic surface, assembles an evidence object, and classifies it with [scripts/verify-escalation-config.mjs](scripts/verify-escalation-config.mjs) into one of three states so a missing escalation policy can never masquerade as fully configured:

- `CONFIGURED` — all deterministic surfaces satisfied **and** the failure-threshold directive is authored.
- `ROUTING_CONFIGURED_POLICY_PENDING` — routing and the agent escalation surface are verified, but the failure-threshold directive (`thresholdAuthored`) is not yet confirmed. Author it (`AUTHOR_SURFACES=1` / `THRESHOLD_AUTHORED=1`) and re-run to reach `CONFIGURED`.
- `INCOMPLETE` — one or more deterministic surfaces are missing (see `missing[]`).

Note the NGA escalation-surface detection ([scripts/classify-nga-escalation.mjs](scripts/classify-nga-escalation.mjs)) is an **advisory preflight** — it matches for a reachable `@utils.escalate` / create-record action in the authoring bundle but does not prove runtime reachability from the topic. Treat a passing NGA surface check as a strong signal, not end-to-end runtime proof; confirm the live handoff with the Phase 8 runtime step.

### Phase 8 — Runtime / manual proof (out of headless scope)

Confirm the conversational trigger, `AgentWork` creation, and same-session context preservation with a live conversation — see [references/runtime-verification.md](references/runtime-verification.md).

---

## Running it

```bash
bash scripts/verify-and-configure.sh <org-alias> \
  [<agent-developer-name>] [<queue-developer-name>] \
  [<escalation-topic-api-name>] [<planner-bundle-api-name>]
```

- Positionals 2–5 also read from env (see the Inputs table). Further scenario inputs are env-only: `FLOW_DEVELOPER_NAME`, `FLOW_LABEL`, `CONTEXT_OBJECT`, `SERVICE_CHANNEL_DEV_NAME`, `SERVICE_CHANNEL_LABEL`, `QUEUE_MEMBER_USERNAMES`.
- `PLAN_ONLY=1` previews (read-only) and stops before any write.
- `THRESHOLD_AUTHORED=1` marks the directive policy as authored for the verdict.
- `AUTHOR_SURFACES=1` (optional, run mode) — deterministically author the two doc-driven surfaces instead of hand-editing XML, following the Agentforce lifecycle in `agentforce-generate/references/known-issues.md` (Issue 18): **publish** (regenerate the compiled bundle) → **retrieve** the `GenAiPlugin` topic + `GenAiPlannerBundle` in **metadata format** (`--target-metadata-dir … --unzip`) → **deactivate** the agent (deploys fail while it is active) → apply a schema-aware, XSD-ordered, loss-less, idempotent patch (`scripts/patch-escalation-surfaces.mjs`) that sets `canEscalate=true` (after `aiPluginUtterances`, before `description`) and inserts `outboundRouteConfigs` (`outboundRouteType=OmniChannelFlow`, **before `<surface>`** on a Messaging-class planner surface, targeting the outbound flow) → **deploy** with `--metadata-dir` → **activate** (fail-closed; the agent is never left inactive silently) → **re-read the latest `BotVersion`** so the verdict reflects the freshly-authored version. It requires the topic and/or bundle API names, runs only after the membership gate (never wires an empty queue), and **refuses** (blocks) rather than guess if it cannot find a safe, XSD-ordered patch point. Omit it to keep the skill verify-only.
- The `canEscalate` and `outboundRouteConfigs` surfaces are verified only when you pass `<escalation-topic-api-name>` / `<planner-bundle-api-name>` (they are authored via the doc-driven edits in Phase 4).

**Typical two-pass flow**: run once to stand up the queue + outbound flow and preconditions; perform the Phase 4/5/6 doc-driven edits; then re-run with the topic + bundle API names and `THRESHOLD_AUTHORED=1` to reach `CONFIGURED`.

## Output contract

A single JSON object to stdout:

```json
{
  "skill": "service-agentforce-human-escalation-configure",
  "status": "CONFIGURED",
  "agent": { "developer_name": "Support_Agent", "active": true },
  "queue": { "developer_name": "Human_Support_Queue", "id": "00G...", "active_direct_user_member_count": 1 },
  "outbound_flow": { "api_name": "Human_Escalation_Outbound_Flow", "active_version_id": "301..." },
  "escalation_topic": "Escalate_To_Human",
  "planner_bundle": "Support_Agent",
  "config_verification": {
    "verdict": "CONFIGURED",
    "deterministicPass": true,
    "directivePass": true,
    "checks": [],
    "missing": []
  },
  "next_steps": [],
  "manual_actions": [],
  "blocking_issue": null
}
```

- `status`: `CONFIGURED` (all deterministic surfaces satisfied), `INCOMPLETE` (some `config_verification.missing`), or `BLOCKED` (bad input / auth / production / precondition; exit 1).
- Re-running an already-configured org is a no-op that returns `CONFIGURED` (idempotent).

## Idempotency

Existing queue, `QueueSobject`, `QueueRoutingConfig`, queue members, and an already-active outbound flow are reused, not recreated (members are only added when the queue has zero active members and `QUEUE_MEMBER_USERNAMES` is supplied; already-present members are left untouched). The doc-driven edits (`canEscalate`, `outboundRouteConfigs`) are set-if-absent. A second run against a fully configured org performs no writes and returns `CONFIGURED`.

## Verification

Run the bundled escalation contract tests after changing this skill or its scripts:

```bash
python3 scripts/tests/test_escalation_contracts.py
```

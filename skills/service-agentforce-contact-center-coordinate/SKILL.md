---
name: service-agentforce-contact-center-coordinate
description: "Coordinates end-to-end setup of an Agentforce Contact Center voice channel: gathers country and phone-number-type selections, procures a chosen number, resolves its CommunicationChannelLine, verifies the number is live, and creates an active PstnVoice MessagingChannel. The user picks the routing model: Omni Queue (route to the contact center queue) or Omni Flow (route to an Agentforce agent, creating or reusing the agent plus its routing flows). Use when the user asks to set up an Agentforce Contact Center, provision a contact center phone number and voice channel together, or put an Agentforce agent on native voice. TRIGGER when the user says set up agentforce contact center, configure contact center voice, or create a voice channel with omni flow and an agentforce agent. DO NOT TRIGGER when only wiring an existing channel to an existing agent with no number to procure, or creating a non-voice messaging channel."
allowed-tools: Bash(sf org display:*) Bash(sf org create agent-user:*) Bash(sf data query:*) Bash(sf api request rest:*) Bash(sf agent:*) Bash(sf project deploy start:*) Bash(jq:*) Bash(scripts/*) Bash(./scripts/*) Bash(bash scripts/*) Read AskUserQuestion
metadata:
  version: "1.1"
  minApiVersion: "68.0"
  domains: ["Service", "Agentforce"]
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# service-agentforce-contact-center-coordinate: Set up an Agentforce Contact Center voice channel

Coordinates the full path from an authenticated org to a live inbound voice channel: procure a phone number, confirm it is provisioned, and create an active `PstnVoice` `MessagingChannel`. The user picks the **routing model** — **Omni Queue** (route calls straight to the Agentforce Contact Center queue) or **Omni Flow** (route to an Agentforce agent via an inbound routing flow, with the queue as fallback). The Omni Queue path only orchestrates the Number Management and MessagingChannel REST APIs. The Omni Flow path can additionally author/publish/activate an Agentforce agent and deploy its inbound (`Copilot`) and escalation (`QueueBased`) `RoutingFlow` flows before wiring the channel.

## Scope

- **In scope**: fetching available numbers, procuring a number, resolving its `CommunicationChannelLine`, verifying/reconciling live status, choosing the routing model, creating and activating a `PstnVoice` `MessagingChannel` (queue- or flow-routed), and — for the Omni Flow path — authoring/publishing/activating an Agentforce agent and deploying its inbound and escalation `RoutingFlow` flows. Ends with a setup summary.
- **Out of scope**: authenticating or provisioning the org (the target org must already be authenticated), enabling the Agentforce/Einstein Service Agent toggle (an org preference the operator flips — see `references/agentforce-prerequisite.md`), outbound/voice-tuning or wiring a *pre-existing* channel to an agent, and creating non-voice channels.

---

## Prerequisites

- **Authenticated org** — required for every path (this skill never runs an interactive login).
- **Omni Flow path only — Einstein and Agentforce Agents must be enabled in the org.** Before a voice channel can route to an Agentforce agent, an org admin must turn on **Einstein** (Setup → **Einstein Setup**) and then **Agentforce Agents** (Setup → Einstein → **Agentforce / Agents**) in the Setup UI. The skill then resolves or provisions the canonical **Einstein Agent User** (`Profile.Name = 'Einstein Agent User'`) that agent authoring and publish depend on. Do **not** use generic users whose username/profile merely contains `Agent` or `Bot`; those can generate/validate but fail publish. The **Omni Queue** path has **no** such prerequisite. Full steps: `references/agentforce-prerequisite.md`.

---

## Required Inputs

Gather or confirm before proceeding:

- **Target org**: an already-authenticated org. If the user names an alias, use it. If the user refers to their **default org** (or gives no alias), resolve it with `sf org display --json` and read `result.alias` (falling back to `result.username`); use that value as `<alias>` for every script. Do not run an interactive login.
- **Country**: `US` or `CA`.
- **Phone number type**: `10DLC` or `Toll Free`.
- **Selected number**: chosen by the user from the fetched list.
- **Routing model**: `Omni Queue` (default) or `Omni Flow`. Asked in Step 7.
- **(Omni Flow only) Agent source**: create a new Agentforce agent + routing flows, or reuse an existing published agent and its inbound routing flow.
- **(Omni Flow, new agent only) Agent business context**: agent name, agent description (the agent's role/purpose), and company name — passed to `sf agent generate agent-spec`. The agent name is used as the `<label>`, and the `<apiName>` is derived from it (normalization + uniqueness rule in Step 9 sub-step 3); do not prompt for role, website, or API name.

Do not proceed without an authenticated org and both the country and number-type selections. Collect the routing model and any Omni Flow inputs only if/when that path is chosen.

---

## Workflow

All steps are sequential. If a step fails, stop and report the error rather than continuing.

1. **Confirm the org connection** — run `sf org display --target-org <alias> --json` and read `result.instanceUrl`. If it fails, ask the user to authenticate the org first, then stop. Do not run an interactive login from this skill.

2. **Gather configuration** — use `AskUserQuestion` to collect **Country** (`US`/`CA`) and **Phone Number Type** (`10DLC`/`Toll Free`). Do not mark any option as recommended or default — present the choices neutrally. Wait for both before continuing.

3. **Fetch available numbers** — read `references/number_management_api.md` for the endpoint contract, then run `scripts/fetch-numbers.sh <alias> <country> <phoneType>`. Present the returned numbers as a numbered list and ask the user to select one — do not mark any number as recommended or default.

4. **Procure the selected number** — run `scripts/procure-number.sh <alias> <country> <phoneType> <number>`. On a non-2xx response, map the status via `references/number_management_api.md` and stop with a clear message.

5. **Resolve the ChannelLine** — run `scripts/resolve-channel-line.sh <alias> <number>`. It queries `CommunicationChannelLine` by `Code`, retrying on empty results. Capture the `ChannelLine` Id and `CodeStatus`.

6. **Verify the number is live** — run `scripts/verify-number-live.sh <alias> <number>`. It checks `CodeStatus` via the Tooling API, calls `numberStateReconcile` when not live, and polls per the strategy in `references/verification_and_errors.md`. Branch on the exit code: **exit 3** (still not `Live` after polling) → surface the warning and ask whether to wait or proceed; **exit 4** (`numberStateReconcile` returned a non-2xx) → **stop and report** per the stop-on-non-2xx rule — do not create a channel on top of a failed reconciliation.

7. **Choose the routing model** — use `AskUserQuestion` to ask how calls should route, then branch in Step 9:
   - **Omni Queue** (default) — route directly to the Agentforce Contact Center queue.
   - **Omni Flow** — route to an Agentforce agent via an inbound routing flow, with the queue as fallback.

8. **Resolve the contact center queue** — run `scripts/resolve-acc-queue.sh <alias>` to look up the Agentforce Contact Center default queue Id. Never hardcode a queue Id — it is org-specific. Both models need it: Omni Queue uses it as the channel's `SessionHandlerId`; Omni Flow uses it as the `FallbackQueueId` and the escalation-flow target.

9. **Create the active voice channel** — read `references/messaging_channel.md`, then follow the branch for the chosen routing model.

   **Omni Queue** — run `scripts/create-voice-channel.sh <alias> <number> <channelLineId> <queueId>`. This POSTs a `PstnVoice` `MessagingChannel` with `SessionHandlerId` set to the queue, `ChannelLineId` set to the resolved `CommunicationChannelLine` Id, and `IsActive: true`. Handle the field/status errors documented in that reference.

   **Omni Flow** — read `references/omni-flow-routing.md`, then:
   1. **Prerequisite gate** — run `scripts/check-agentforce-prereq.sh <alias>` (see `references/agentforce-prerequisite.md`). **Exit 0** → capture the printed canonical Einstein Agent User for `--agent-user`; the script reuses an existing `Einstein Agent User` or provisions one with `sf org create agent-user`. **Exit 3** → no canonical user could be found/provisioned, often because the toggle is off or no Agentforce Service Agent User license is available; prompt the user to fix the org and re-run. If the user allows a queue-only fallback, use the Omni Queue create above and note the fallback in the report.
   2. **New or existing agent** — use `AskUserQuestion`:
      - **Use existing** — ask for the published agent's API name/label and its inbound `RoutingFlow` DeveloperName, then run `scripts/resolve-flow-definition.sh <alias> <flowDeveloperName>` to get the inbound `FlowDefinition` Id (`300…`). `resolve-flow-definition.sh` verifies only that the *flow* has an active version, not that the agent is published and Active — confirm the agent's latest `BotVersion.Status = 'Active'` (`SELECT Status FROM BotVersion WHERE BotDefinition.DeveloperName = '<apiName>' ORDER BY VersionNumber DESC LIMIT 1`), or tell the user they are responsible for that, before continuing; otherwise the channel is created but calls won't route. Continue at sub-step 5.
      - **Create new** — continue at sub-step 3.
   3. **Author the agent** — collect the agent's business context via `AskUserQuestion`: only **agent name**, **agent description** (the agent's role/purpose — this becomes the spec's `--role`), and **company name** (do not prompt for role, website, or API name). Use the agent name as the `<label>`. Derive the `<apiName>` (it becomes the `BotDefinition.DeveloperName` and the routing-flow name base) from the agent name: PascalCase the words, keep only alphanumerics, start with a letter (prefix `A` if needed), cap at 60 chars. Confirm uniqueness via `sf data query --query "SELECT DeveloperName FROM BotDefinition WHERE DeveloperName = '<apiName>'" --target-org <alias>`; append a numeric suffix on a collision. First prepare the SFDX work dir with `scripts/prepare-agent-workdir.sh acc-voice-build`; `sf agent generate agent-spec` requires project context before the authoring-bundle script runs. From inside `acc-voice-build`, generate the spec: `sf agent generate agent-spec --type customer --tone neutral --max-topics 5 --agent-user <einsteinAgentUser> --role "<agent description>" --company-name "<company name>" --output-file specs/<apiName>.yaml --target-org <alias> --json`. Then, from the parent/original work dir, run `scripts/create-voice-agent.sh <alias> <apiName> <label> acc-voice-build/specs/<apiName>.yaml acc-voice-build`, which generates the authoring bundle, fixes the generated `default_agent_user`, deploys the `AiAuthoringBundle`, validates, publishes, and activates the agent. **Do not switch the planner to `Atlas__VoiceAgent`** — keep the publish-generated `Atlas__ConcurrentMultiAgentOrchestration` (deviation note in `references/omni-flow-routing.md`).
   4. **Deploy the routing flows** — run `scripts/create-routing-flows.sh <alias> <apiName> <label> <queueId> <queueName> acc-voice-build`. It renders and deploys the inbound (`<apiName>_Voice_Omni_Flow`, `Copilot`) and escalation (`<apiName>_Voice_Escalation`, `QueueBased`) flows from inside the prepared SFDX work dir, then prints the inbound `FlowDefinition` Id (`300…`) on stdout — capture it. Reuse the **same** `acc-voice-build` work dir as sub-step 3.
   5. **Create the channel** — run `scripts/create-voice-channel.sh <alias> <number> <channelLineId> <flowDefinitionId> <queueId>`. The 5th arg switches the POST to Omni Flow: `SessionHandlerId` = the inbound `FlowDefinition` Id, `FallbackQueueId` = the queue.

10. **Confirm setup and write the report** — read the created `MessagingChannel` back. Then write a report using **exactly** the structure in `assets/report-template.md`: fill every field with the real value produced during this run (org alias, country, phone-number type, routing model, the commands actually run, the procured number, the resolved `CommunicationChannelLine` Id and status, the queue resolved **by name** with its Id, and the created `PstnVoice` `MessagingChannel` Id, DeveloperName, ChannelLineId, IsActive, SessionHandlerId, and FallbackQueueId; for Omni Flow also the agent api-name/label and inbound `FlowDefinition` Id), and end with the one-line Outcome. Include the Omni Flow rows only when that path was taken. One line per item — no extra narrative, and do not omit a field that applies. If a step failed, still fill the fields reached and state the exact error and the step it failed at in Outcome.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Never run an interactive login; require a pre-authenticated org alias | Auth and org lifecycle are out of scope; keeps the skill portable across surfaces |
| Call APIs via `sf api request rest`; never extract the access token | Uses the CLI's stored session for `--target-org` — no raw token handling |
| Never hardcode a queue Id / `SessionHandlerId` / `FlowDefinition` Id | These are org-specific; always resolve them (queue in Step 8, flow via `resolve-flow-definition.sh`) |
| Attach routing via `SessionHandlerId` (+ `FallbackQueueId` for Omni Flow) — not `TargetQueueId` or `RoutingType` | Omni Queue: `SessionHandlerId` = queue Id. Omni Flow: `SessionHandlerId` = inbound `FlowDefinition` Id (`300…`), `FallbackQueueId` = queue Id |
| Omni Flow: publish **and** activate the agent and deploy the inbound flow (Active, `300`-prefix) before creating the channel | The channel's `SessionHandlerId` points at a live inbound `FlowDefinition` that references a published, active agent |
| Do not switch the agent's `plannerType` to `Atlas__VoiceAgent` | This org rejects it with an opaque error; keep the publish-generated `Atlas__ConcurrentMultiAgentOrchestration` — voice still routes via the `Copilot` flow (deviation) |
| If the Agentforce prerequisite is unmet or agent/flow creation fails, stop and report unless the user explicitly accepts the Omni Queue fallback | Some runs require a new Agentforce agent and Omni Flow channel; do not silently downgrade the routing model |
| Use `ChannelLineId` (not scalar `ChannelLine`) to link the CommunicationChannelLine | `ChannelLine` is the relationship name; the writable create field is `ChannelLineId` |
| `MessageType` must be `PstnVoice` and `IsActive: true` | Required for an active inbound voice channel |
| Do not set `IsoCountryCode` on `PstnVoice` channels | Not valid for this channel type |
| Stop and report on any non-2xx API response | Partial setup left silent is worse than a clear failure |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `ChannelLine` not found immediately after procurement | Records propagate asynchronously — retry with backoff (Step 5 script handles this) |
| Number `CodeStatus` not `Live` | Call `numberStateReconcile` and poll (Step 6 script); warn if it stays provisioning |
| `INVALID_FIELD: The value provided for foreign key reference ChannelLine is not a nested SObject` on channel create | The relationship name `ChannelLine` was sent as a scalar field — send the Id in `ChannelLineId` |
| `FIELD_INTEGRITY_EXCEPTION` blocking a non-live number | Expected when validation is enforced — wait for the number to become live, then retry |
| Duplicate `DeveloperName` | A channel with that name exists — derive a unique name or reuse the existing channel |
| Spaces in `phoneNumberType` (`Toll Free`) | URL-encode when building query strings (scripts handle this) |
| `sf agent generate agent-spec` fails with `RequiresProjectError` | Run `scripts/prepare-agent-workdir.sh acc-voice-build`, then invoke `sf agent generate agent-spec` from inside `acc-voice-build` with `--output-file specs/<apiName>.yaml` |
| `sf agent publish` says `default agent user NEW AGENT USER` | The generator left a placeholder in the `.agent` file — `create-voice-agent.sh` patches `default_agent_user` from the spec's `agentUser` before deploy/publish |
| `sf agent publish` says `Unable to access the Salesforce Agent APIs` or `User doesn't have access to use agent` | Usually the spec/bundle used a generic Agent/Bot-profile user. Run `scripts/check-agentforce-prereq.sh`; it must return a user whose profile is exactly `Einstein Agent User` |
| Opaque server error (e.g. `-1103525358`) when publishing/validating the agent | Caused by setting `plannerType: Atlas__VoiceAgent` — remove it and keep `Atlas__ConcurrentMultiAgentOrchestration` (deviation; `create-voice-agent.sh` never touches the planner) |
| Routing flow deploy fails with `does not contain a valid Salesforce DX project` | Use the same prepared `acc-voice-build` work dir; `create-routing-flows.sh` now runs `sf project deploy start` from inside that directory |
| `sf agent generate agent-spec` / publish fails on licensing or "default agent user" | Agentforce toggle is off or no Agentforce Service Agent User license is available. Enable it or free/provision a license (`references/agentforce-prerequisite.md`) |
| Using a `Flow` Id (`301…`) as `SessionHandlerId` | Wrong handle — `SessionHandlerId` needs the stable `FlowDefinition` Id (`300…`); `resolve-flow-definition.sh` returns it |
| Inbound flow deployed but the channel won't route to the agent | The agent must be **activated**, not just published, and the inbound flow must have an active version — `create-voice-agent.sh` verifies `BotVersion` is `Active`; `resolve-flow-definition.sh` exits 3 if there is no active version |

---

## Output Expectations

This skill primarily creates records in the target org:

- A procured phone number (Number Management).
- An active `PstnVoice` `MessagingChannel` — routed to the contact center queue (Omni Queue) or to an Agentforce agent via an inbound routing flow with the queue as fallback (Omni Flow).
- **Omni Flow only**: a published, active Agentforce agent plus two `RoutingFlow` flows (inbound `Copilot` + escalation `QueueBased`).
- A report written per `assets/report-template.md`, plus a final summary table (`references/setup_summary.md`).

The Omni Flow path also scaffolds a throwaway SFDX project under `acc-voice-build/` (spec, authoring bundle, flow metadata) to run the deploy — local build artifacts, not skill output.

---

## Cross-Skill Integration

The Omni Flow path wires inbound voice itself (agent → inbound `Copilot` flow → channel, plus an escalation flow), so it does **not** hand that wiring off to a separate channel-configuration skill. Deeper agent authoring beyond the voice service agent this skill generates (custom topics, actions, knowledge) is out of scope.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/number_management_api.md` | Steps 3–4 — Number Management endpoints, params, and status-code mapping |
| `references/verification_and_errors.md` | Step 6 — live-verification polling strategy and error handling |
| `references/messaging_channel.md` | Step 9 — MessagingChannel field contract (both routing models) and create-time error handling |
| `references/omni-flow-routing.md` | Step 9 (Omni Flow) — routing-model contract, agent→flow→channel wiring order, new-vs-existing fork, planner deviation, fallback rule |
| `references/agentforce-prerequisite.md` | Step 9 (Omni Flow) — Agentforce toggle prerequisite, preflight check, and Omni-Queue fallback |
| `references/setup_summary.md` | Step 10 — user-facing summary table and next steps |
| `assets/report-template.md` | Step 10 — exact structure for the written `report.md` |
| `assets/omni-flow.flow-meta.xml` | Step 9 (Omni Flow) — inbound `Copilot` RoutingFlow template (rendered by `create-routing-flows.sh`) |
| `assets/escalation-flow.flow-meta.xml` | Step 9 (Omni Flow) — escalation `QueueBased` RoutingFlow template (rendered by `create-routing-flows.sh`) |
| `scripts/prepare-agent-workdir.sh` | Step 9 (Omni Flow) — prepare the SFDX project context required before generating an agent spec |
| `scripts/fetch-numbers.sh` | Step 3 — fetch available default numbers |
| `scripts/procure-number.sh` | Step 4 — procure the selected number |
| `scripts/resolve-channel-line.sh` | Step 5 — resolve the CommunicationChannelLine with retry |
| `scripts/verify-number-live.sh` | Step 6 — verify/reconcile live status |
| `scripts/resolve-acc-queue.sh` | Step 8 — resolve the ACC default queue Id |
| `scripts/create-voice-channel.sh` | Step 9 — create the active PstnVoice channel (4-arg Omni Queue / 5-arg Omni Flow) |
| `scripts/check-agentforce-prereq.sh` | Step 9 (Omni Flow) — prerequisite gate; resolves the Einstein Agent User for `--agent-user` |
| `scripts/create-voice-agent.sh` | Step 9 (Omni Flow) — generate/validate/publish/activate the Agentforce voice agent |
| `scripts/create-routing-flows.sh` | Step 9 (Omni Flow) — deploy inbound + escalation flows; print the inbound `FlowDefinition` Id |
| `scripts/resolve-flow-definition.sh` | Step 9 (Omni Flow) — resolve an inbound flow's `FlowDefinition` Id (`300…`), incl. reusing an existing flow |

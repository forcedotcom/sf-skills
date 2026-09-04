# Gap Catalog

Documented gaps between the skills' scope and what is achievable headlessly on Salesforce v66. Each gap records its **surface behavior**, **root cause**, and **coordinator behavior** (what the coordinator does about it). Read this on demand — it is not needed for a happy-path run, but the coordinator's report must correctly surface every gap it encounters.

---

## Login-behavior radio (Setup UI-only)

**Where it lives:** Setup → Omni-Channel → Omni-Channel Settings → "Define login behavior when an agent using Omni-Channel opens a new window or tab" (three radio options).

**Surface behavior:** the radio has no public API on v66. The `enableOmniAutoLoginPrompt` boolean in `Settings:OmniChannel` deploys cleanly and round-trips through retrieve, but it does not drive the radio; flipping it in either direction leaves the UI option unchanged. The deploy is recorded in `SetupAuditTrail` as `omniAutoLoginPromptOnOff`.

**Root cause:** the radio is backed by a Setup endpoint not surfaced in any public sObject, Metadata, Tooling, or Connect API today.

**Coordinator behavior:** after the base-settings deploy step, emit the exact click-path in the report's *Manual Actions Required* section:

> Login-behavior radio — open Setup → Omni-Channel Settings → "Define login behavior when an agent opens a new window/tab" → select the desired option → Save.

Do not attempt to flip it via `enableOmniAutoLoginPrompt` (deploys but has no effect), and do not skip it silently.

---

## Agentforce Service Agent as a routing target

**Where it lives:** the routing-flow capability — `routeWork` supports `agentforceEmployeeAgentId`, `botId`, `copilotId`, `digitalWorkerId`, and `externalConversationBotId` as routing targets in addition to human agents and queues.

**Surface behavior:** on standard v66 trial CDOs, the `Bot`, `BotVersion`, `GenAiPlanner`, `GenAiPlugin`, `GenAiFunction`, and `CopilotAction` metadata types return `NOT_FOUND` on retrieve. Provisioning an Agentforce agent is UI-driven today; the artifacts to create one are not consistently available via the Metadata API.

**Root cause:** Agentforce agent provisioning is a separate product surface, not owned by this coordinator.

**Coordinator behavior:**

1. At the confirm-inputs step, ask whether an Agentforce Agent Id is available.
2. If yes — substitute it into the routing flow at deploy time.
3. If no — **do not deploy** an Agentforce-targeted routing flow. Deploying with the `__AGENTFORCE_AGENT_ID__` placeholder unresolved would push broken metadata, which the fail-closed contract forbids. Skip that flow and emit in the report's *Manual Actions Required* section:

> Agentforce Agent handoff — not configured: no Agent Id was provided, so no Agentforce-targeted routing flow was deployed (the coordinator never deploys an unresolved placeholder). Once an Agent Id is available, re-invoke the routing-flow skill with the Id to deploy. The re-run is idempotent — the flow is created/updated in place.

**Handoff contract (Agent Id producer → this coordinator):**

| Direction | Field | Producer | Consumer |
|---|---|---|---|
| ← input | `agent_id` (18-char Salesforce Id) | Agent provisioning surface | this coordinator's routing-flow step |
| ← input | `developer_name` (unique) | Agent provisioning surface | this coordinator (reuse detection) |
| ← input | `label` (human-readable) | Agent provisioning surface | this coordinator (report) |
| → output | `flow_id` (routing flow record Id) | this coordinator | Agent provisioning surface (its report) |

---

## Skills-based ServiceResourceSkill routing requires Field Service

**Where it lives:** skills-based routing via `ServiceResource` + `ServiceResourceSkill` records that map users → skills for Field Service-style skills-based routing.

**Surface behavior on a plain Service Cloud CDO (no Field Service license):**

- `ServiceResource` records can be created (`ResourceType=A` is writeable).
- `ServiceResource.IsActive` is absent from `describe`, is non-createable/non-updateable, and rejects PATCH with `INVALID_FIELD: No such column 'IsActive'`, yet appears as `null` on record `GET`. New records default to inactive with no headless activation path.
- `ServiceResourceSkill` POST fails with `INVALID_FIELD: This Service Resource is inactive. You can only assign Skill to active Service Resources.`
- Metadata deploy of `Settings:FieldService` returns "Not available for deploy for this organization".
- Tooling query on `FieldServiceSettings` returns "Cannot access: FieldServiceSettings in this organization".

**Root cause:** `ServiceResource.IsActive` is license-gated behind Field Service, and enabling Field Service is an org-level license grant not reachable through the Metadata, REST, or Tooling APIs.

**This does not break routing:** the routing operates via `Flow:routeWork` (SkillsBased mode) + a `WorkSkillRouting` rule, both of which work without any `ServiceResource*` records. SkillsBased `routeWork` looks up `Skill.DeveloperName` at runtime and matches against agent skill assignments made through the Skills UI (delivered by the permission set). `ServiceResourceSkill` is a Field Service-style resource↔skill mapping — a separate surface from the Omni-Channel skills-based routing the flow and rule already provide.

**Coordinator behavior:**

1. Pre-flight license probe — attempt a Tooling query on `FieldServiceSettings`. `Cannot access` means Field Service is not licensed.
2. If Field Service is absent: skip `ServiceResource`/`ServiceResourceSkill` creation, complete the `Skill` + `SkillType` creation (both work without it), complete the skill successfully (do not fail the coordinator), and surface the note below.
3. If Field Service is present: run the full flow — `Skill` → `SkillType` → `ServiceResource` (activate) → `ServiceResourceSkill`.

**Report language:**

> Field Service-style resource-skill mapping unavailable — this org has no Field Service license, so `ServiceResource` records cannot be activated and `ServiceResourceSkill` bindings cannot be created. Routing is unaffected — the routing flow uses SkillsBased routing which looks up `Skill` records directly, and the `WorkSkillRouting` rule adds skill requirements per matching field. To enable `ServiceResourceSkill` bindings later, get Field Service licensed on this org and re-invoke the skills-routing skill (idempotent — it detects the license and completes the SR/SRS steps).

**Payload rules (independent of license):**

- `ServiceResourceSkill` has only `ServiceResourceId`, `SkillId`, `EffectiveStartDate`. There is no `SkillLevel` field — do not include it.
- `WorkSkillRouting` is a Tooling-API-only entity; standard Data API queries return null. Use `/services/data/vXX/tooling/query` or `/services/data/vXX/tooling/sobjects/WorkSkillRouting/*`.

---

## AgentWork supervisor sharing control

**Where it lives:** the org-level Setup control that determines whether supervisors can see their representatives' `AgentWork`.

**Surface behavior:** validation through the available Data, Tooling, Metadata, and settings routes did not establish a supported writable contract for this control. A direct REST update must not be advertised as a working setup step without a confirmed entity, field, permissions contract, and read-back proof.

**Root cause:** this is an org-wide sharing/platform setting, not an `OmniSupervisorConfig`, queue, or permission-set companion owned by the current skills.

**Coordinator behavior:** do not attempt or claim a headless write. Report it as a manual/platform dependency when the use case requires supervisors to see rep work:

> AgentWork supervisor visibility — configure the owning sharing control in Setup and verify with a supervisor user. The current skills do not have a supported, verified headless write route for this org-wide setting.

---

## Adding a new gap

When a step surfaces a new gap, add a section with the same shape: surface behavior, root cause, and coordinator behavior. Update the coordinator's `SKILL.md` so its report surfaces the new gap.

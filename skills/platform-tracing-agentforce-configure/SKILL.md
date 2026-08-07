---
name: platform-tracing-agentforce-configure
description: "Generate AgentforcePlatformTracingSettings metadata to enable or disable Agentforce agent execution trace spans flowing to Data Cloud. Use this skill for any AgentforcePlatformTracingSettings metadata work. TRIGGER when: user mentions Agentforce tracing, agent trace spans, Data Cloud tracing, AgentforcePlatformTracingSettings, platform observability tracing, enable agent tracing, wants agent execution spans in Data Cloud, mentions .settings-meta.xml for AgentforcePlatformTracing, or asks about enabling observability for Agentforce agents. DO NOT TRIGGER when: user wants Platform Tracing for TraceSpanEvent (use platform-tracing-configure), wants to query or analyze existing agent trace data in Data Cloud (use agentforce-observe), wants Event Log Files or ELF configuration, wants Change Data Capture (use integration-eventing-cdc-configure), or wants ManagedEventSubscription (use integration-eventing-subscription-configure)."
metadata:
  version: "1.0"
  minApiVersion: "68.0"
  relatedSkills:
    - "agentforce-observe"
    - "integration-eventing-cdc-configure"
    - "integration-eventing-subscription-configure"
    - "platform-tracing-configure"
---

# Platform Tracing — Agentforce Configure

Generate AgentforcePlatformTracingSettings metadata to enable or disable forwarding of Agentforce agent execution trace spans to Data Cloud's ingestion pipeline. This is a singleton Settings type with one boolean field introduced in API v68.0 (Spring '25).

## Scope

- **In scope**: Generating `AgentforcePlatformTracing.settings-meta.xml` to enable or disable Agentforce agent tracing.
- **Out of scope**: Platform Tracing for TraceSpanEvent (use `platform-tracing-configure`). Event Log Files. Change Data Capture. Org permission provisioning. Data Cloud provisioning.

---

## Prerequisites

Before generating, inform the user of these requirements. The skill cannot check org state, but deploying without these prerequisites means the setting has no effect:

1. **Data Cloud must be provisioned** in the org — trace spans are forwarded to Data Cloud's ingestion pipeline. Without Data Cloud, there is no destination for the spans.
2. **`PlatformObservability` org permission** must be active — this permission gates the feature. It is provisioned (not settable via metadata).
3. **API version 68.0+** — the `AgentforcePlatformTracingSettings` type was introduced in Spring '25. Orgs on older API versions will not recognize it.

If the user reports the setting isn't working after deploy, the most likely cause is a missing prerequisite above.

---

## Clarifying Questions

Before generating, confirm with the user if not already clear:

- Enable or disable? (Which state do you want for Agentforce agent tracing?)

No other clarification needed — this is a singleton type with one boolean field.

---

## Required Inputs

Gather or infer before proceeding:

- **Desired state**: `true` (enable) or `false` (disable)

Defaults unless specified:
- If user says "enable" or "turn on": set to `true`
- If user says "disable" or "turn off": set to `false`

If the user provides a clear request, generate immediately without unnecessary back-and-forth.

---

## Workflow

1. **Warn about prerequisites** — inform the user that this feature requires Data Cloud and the `PlatformObservability` org permission.

2. **Read the template** — load `assets/AgentforcePlatformTracing-template.xml`.

3. **Generate the settings file** — replace `{ENABLED}` with `true` or `false` based on the user's desired state.

4. **Place the file** — output to `settings/AgentforcePlatformTracing.settings-meta.xml` in the project's source directory.

---

## Rules / Constraints

| Constraint | Rationale |
|---|---|
| Singleton — only one file per org, one boolean field | The metadata type has exactly one instance. Deploying the file sets the org-wide preference. |
| XML namespace must be `http://soap.sforce.com/2006/04/metadata` | Any other namespace causes deploy failure. |
| File must be named `AgentforcePlatformTracing.settings-meta.xml` | SFDX source format convention for this Settings type. |
| Only include `enableAgentforcePlatformTracing` field | No other fields exist on this type. |
| Requires API v68.0+ | Older orgs reject the metadata type entirely. |

---

## Gotchas

| Issue | Resolution |
|---|---|
| Deploy succeeds but tracing doesn't activate | Org lacks `PlatformObservability` permission or Data Cloud is not provisioned. These are provisioned, not settable via metadata. |
| `AgentforcePlatformTracingSettings` type not recognized | Org or tooling is on API version < 68.0. Update `sfdx-project.json` sourceApiVersion. |
| User confuses this with Platform Tracing (TraceSpanEvent) | Clarify: this sends Agentforce agent execution spans to Data Cloud. For TraceSpanEvent publishing, use the `platform-tracing-configure` skill. |

---

## Output Expectations

Deliverables:
- `settings/AgentforcePlatformTracing.settings-meta.xml`

Before delivering, verify:
- [ ] XML namespace is exactly `http://soap.sforce.com/2006/04/metadata`
- [ ] File is named `AgentforcePlatformTracing.settings-meta.xml`
- [ ] Only `enableAgentforcePlatformTracing` is present (no extra fields)

---

## Cross-Skill Integration

| Need | Delegate to |
|---|---|
| Enable TraceSpanEvent publishing (Platform Tracing) | `platform-tracing-configure` skill |
| Query or analyze existing Agentforce agent trace data in Data Cloud | `agentforce-observe` skill |
| Set up Change Data Capture | `integration-eventing-cdc-configure` skill |
| Configure ManagedEventSubscription | `integration-eventing-subscription-configure` skill |

---

## Reference File Index

| File | When to read |
|---|---|
| `assets/AgentforcePlatformTracing-template.xml` | Step 2 — template for generating the settings file |

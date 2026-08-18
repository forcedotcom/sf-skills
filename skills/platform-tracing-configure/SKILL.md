---
name: platform-tracing-configure
description: "Generate EventSettings metadata to enable or disable Platform Tracing (TraceSpanEvent publishing) in Event Monitoring. Use this skill for any EventSettings enablePlatformTracing metadata work. TRIGGER when: user mentions Platform Tracing, TraceSpanEvent, enable tracing in Event Monitoring Settings, event monitoring tracing toggle, enablePlatformTracing, .settings-meta.xml for Event settings tracing, turn on trace span events, or stop publishing trace spans. DO NOT TRIGGER when: user wants Agentforce agent tracing to Data Cloud (use platform-tracing-agentforce-configure), wants Event Log Files or ELF generation, wants Change Data Capture (use integration-eventing-cdc-configure), or wants ManagedEventSubscription (use integration-eventing-subscription-configure)."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "68.0"
  relatedSkills:
    - "integration-eventing-cdc-configure"
    - "integration-eventing-subscription-configure"
    - "platform-tracing-agentforce-configure"
---

# Platform Tracing — Configure

Generate EventSettings metadata to enable or disable the Platform Tracing toggle, which controls whether TraceSpanEvent is published at a sample rate. This modifies a single field (`enablePlatformTracing`) within the existing EventSettings metadata type.

## Scope

- **In scope**: Generating `Event.settings-meta.xml` with the `enablePlatformTracing` field to enable or disable TraceSpanEvent publishing.
- **Out of scope**: Agentforce agent tracing to Data Cloud (use `platform-tracing-agentforce-configure`). Other EventSettings fields (`enableDeleteMonitoringData`, `enableLoginForensics`, etc.) owned by other teams. Event Log Files. Change Data Capture.

---

## Prerequisites

Before generating, inform the user of these requirements:

1. **`PlatformTracing` org permission** must be active — this permission gates the feature. It is provisioned (not settable via metadata). Without it, the setting deploys but TraceSpanEvent is not published.
2. **API version 68.0+** — `enablePlatformTracing` on EventSettings was introduced in Spring '25. Orgs or tooling on older API versions will not recognize the field. Update `sfdx-project.json` `sourceApiVersion` to `68.0` or higher if on an older tooling version.

If the user reports the setting isn't working after deploy, the most likely cause is a missing prerequisite above.

---

## Clarifying Questions

Before generating, confirm with the user if not already clear:

- Enable or disable? (Which state do you want for Platform Tracing / TraceSpanEvent?)

No other clarification needed — this controls a single boolean field.

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

1. **Warn about prerequisites** — inform the user that this feature requires the `PlatformTracing` org permission and API version 68.0+.

2. **Read the template** — load `assets/EventSettings-template.xml`.

3. **Generate the settings file** — replace `{ENABLED}` with `true` or `false` based on the user's desired state.

4. **Place the file** — output to `settings/Event.settings-meta.xml` in the project's source directory.

---

## Rules / Constraints

| Constraint | Rationale |
|---|---|
| Only include `enablePlatformTracing` in generated metadata | Other fields in EventSettings are owned by other teams. Including them risks overwriting unrelated settings during deploy. |
| XML namespace must be `http://soap.sforce.com/2006/04/metadata` | Any other namespace causes deploy failure. |
| File must be named `Event.settings-meta.xml` | SFDX source format convention — the type name prefix for EventSettings is `Event`. |
| Requires `PlatformTracing` org permission | Without this permission, the setting deploys but has no effect on TraceSpanEvent publishing. |
| Requires API v68.0+ | Older orgs/tooling reject the field entirely. |

---

## Gotchas

| Issue | Resolution |
|---|---|
| Deploy succeeds but TraceSpanEvent not published | Org lacks the `PlatformTracing` permission. This is provisioned, not settable via metadata. |
| `enablePlatformTracing` field not recognized by org/tooling | Tooling is on API version < 68.0. Update `sfdx-project.json` `sourceApiVersion` to `68.0` or higher. |
| User confuses this with Agentforce tracing | Clarify: this publishes TraceSpanEvent for platform operations. For Agentforce agent spans to Data Cloud, use the `platform-tracing-agentforce-configure` skill. |
| User wants to configure all Event Monitoring settings | Only `enablePlatformTracing` is in scope. Other EventSettings fields are owned by other teams and not managed by this skill. |

---

## Output Expectations

Deliverables:
- `settings/Event.settings-meta.xml`

Before delivering, verify:
- [ ] XML namespace is exactly `http://soap.sforce.com/2006/04/metadata`
- [ ] File is named `Event.settings-meta.xml`
- [ ] Only `enablePlatformTracing` is present (no other EventSettings fields)
- [ ] Project `sourceApiVersion` in `sfdx-project.json` is `68.0` or higher

---

## Cross-Skill Integration

| Need | Delegate to |
|---|---|
| Enable Agentforce agent tracing to Data Cloud | `platform-tracing-agentforce-configure` skill |
| Set up Change Data Capture | `integration-eventing-cdc-configure` skill |
| Configure ManagedEventSubscription | `integration-eventing-subscription-configure` skill |

---

## Reference File Index

| File | When to read |
|---|---|
| `assets/EventSettings-template.xml` | Step 2 — template for generating the settings file |

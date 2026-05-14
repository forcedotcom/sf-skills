---
name: building-sf-integrations
description: "Salesforce integration architecture and runtime plumbing with 120-point scoring. Use this skill to set up Named Credentials, External Credentials, External Services, REST/SOAP callout patterns, Platform Events, and Change Data Capture. TRIGGER when: user sets up Named Credentials, External Services, REST/SOAP callouts, Platform Events, CDC, or touches .namedCredential-meta.xml files. DO NOT TRIGGER when: Connected App/OAuth config (use configuring-connected-apps), Apex-only logic (use generating-apex), or data import/export (use handling-sf-data)."
license: LICENSE.txt has complete terms
metadata:
  version: "1.1"
---

# building-sf-integrations: Salesforce Integration Patterns Expert

Use this skill when the user needs **integration architecture and runtime plumbing**: Named Credentials, External Credentials, External Services, REST/SOAP callout patterns, Platform Events, CDC, and event-driven integration design.

## When This Skill Owns the Task

Use `building-sf-integrations` when the work involves:
- `.namedCredential-meta.xml` or External Credential metadata
- outbound REST/SOAP callouts
- External Service registration from OpenAPI specs
- Platform Events, CDC, and event-driven architecture
- choosing sync vs async integration patterns

Delegate elsewhere when the user is:
- configuring the OAuth app itself → [configuring-connected-apps](../configuring-connected-apps/SKILL.md)
- writing Apex-only business logic → [generating-apex](../generating-apex/SKILL.md)
- deploying metadata → [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md)
- importing/exporting data → [handling-sf-data](../handling-sf-data/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- integration style: outbound callout, inbound event, External Service, CDC, platform event
- auth method
- sync vs async requirement
- system endpoint / spec details
- rate limits, retry expectations, and failure tolerance
- whether this is net-new design or repair of an existing integration

---

## Recommended Workflow

### 1. Choose the integration pattern
| Need | Default pattern |
|---|---|
| authenticated outbound API call | Named Credential / External Credential + Apex or Flow |
| spec-driven API client | External Service |
| trigger-originated callout | async callout pattern |
| decoupled event publishing | Platform Events |
| change-stream consumption | CDC |

### 2. Choose the auth model
Prefer secure runtime-managed auth:
- Named Credentials / External Credentials
- OAuth or JWT via the right credential model
- no hardcoded secrets in code

### 3. Generate from the right templates
Use the provided assets under:
- `assets/named-credentials/`
- `assets/external-credentials/`
- `assets/external-services/`
- `assets/callouts/`
- `assets/platform-events/`
- `assets/cdc/`
- `assets/soap/`

### 4. Validate operational safety
Check:
- timeout and retry handling
- async strategy for trigger-originated work
- logging / observability
- event retention and subscriber implications

### 5. Hand off deployment or implementation details
Use:
- [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) for deployment
- [generating-apex](../generating-apex/SKILL.md) for deeper service / retry code
- [generating-flow](../generating-flow/SKILL.md) for declarative HTTP callout orchestration

---

## High-Signal Rules

- never hardcode credentials
- do not do synchronous callouts from triggers
- define timeout behavior explicitly
- plan retries for transient failures
- use middleware / event-driven patterns when outbound volume is high
- prefer External Credentials architecture for new development when supported

Common anti-patterns:
- sync trigger callouts
- no retry or dead-letter strategy
- no request/response logging
- mixing auth setup responsibilities with runtime integration design

---

## Output Format

When finishing, report in this order:
1. **Integration pattern chosen**
2. **Auth model chosen**
3. **Files created or updated**
4. **Operational safeguards**
5. **Deployment / testing next step**

Suggested shape:

```text
Integration: <summary>
Pattern: <named credential / external service / event / cdc / callout>
Files: <paths>
Safety: <timeouts, retries, async, logging>
Next step: <deploy, register, test, or implement>
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| OAuth app setup | [configuring-connected-apps](../configuring-connected-apps/SKILL.md) | consumer key / cert / app config |
| advanced callout service code | [generating-apex](../generating-apex/SKILL.md) | Apex implementation |
| declarative HTTP callout / Flow wrapper | [generating-flow](../generating-flow/SKILL.md) | Flow orchestration |
| deploy integration metadata | [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) | validation and rollout |
| use integration from Agentforce | [developing-agentforce](../developing-agentforce/SKILL.md) | agent action composition |

---

## Reference Map

### Start here
- [references/named-credentials-guide.md](references/named-credentials-guide.md)
- [references/external-services-guide.md](references/external-services-guide.md)
- [references/callout-patterns.md](references/callout-patterns.md)
- [references/rest-callout-patterns.md](references/rest-callout-patterns.md)
- [references/security-best-practices.md](references/security-best-practices.md)

### Event-driven / platform patterns
- [references/event-patterns.md](references/event-patterns.md)
- [references/platform-events-guide.md](references/platform-events-guide.md)
- [references/cdc-guide.md](references/cdc-guide.md)
- [references/event-driven-architecture-guide.md](references/event-driven-architecture-guide.md)
- [references/messaging-api-v2.md](references/messaging-api-v2.md)

### CLI / automation / scoring
- [references/cli-reference.md](references/cli-reference.md)
- [references/named-credentials-automation.md](references/named-credentials-automation.md)
- [references/scoring-rubric.md](references/scoring-rubric.md)
- [scripts/README.md](scripts/README.md) — automation scripts overview (configure-named-credential.sh, set-api-credential.sh)

### Asset templates
- `assets/named-credentials/` — Named Credential XML templates (OAuth, JWT, Certificate, Custom auth)
- `assets/external-credentials/` — External Credential XML templates (OAuth, JWT)
- `assets/external-services/` — External Service registration template and operations guide
- `assets/callouts/` — REST sync, Queueable, retry handler, and HTTP response handler Apex templates
- `assets/platform-events/` — Platform Event definition, publisher, and subscriber templates
- `assets/cdc/` — CDC handler and subscriber trigger templates
- `assets/soap/` — SOAP callout service template and wsdl2apex guide
- `assets/endpoint-security/` — Remote Site Setting and CSP Trusted Site XML templates

### Automation hooks
- `hooks/scripts/suggest_credential_setup.py` — auto-suggests credential configuration steps when integration files are detected
- `hooks/scripts/validate_integration.py` — validates integration patterns before agent responses

---

## Output Expectations

When this skill completes an integration task, it produces:

1. **Credential metadata** — one or more files in `assets/named-credentials/` or `assets/external-credentials/` filled with org-specific values
2. **Callout Apex class** — a `.cls` file using the Named Credential pattern, with async/sync pattern chosen based on context
3. **Event/CDC artifacts** — Platform Event `.object-meta.xml`, subscriber trigger, or CDC config (when event-driven pattern is chosen)
4. **Endpoint security metadata** — Remote Site Setting and/or CSP Trusted Site XML files
5. **Scoring report** — 120-point score across 6 categories (Security, Error Handling, Bulkification, Architecture, Best Practices, Documentation)
6. **Next step** — a deployment or testing instruction for the generated artifacts

---

## Score Guide

| Score | Meaning |
|---|---|
| 108+ | strong production-ready integration design |
| 90–107 | good design with some hardening left |
| 72–89 | workable but needs architectural review |
| < 72 | unsafe / incomplete for deployment |

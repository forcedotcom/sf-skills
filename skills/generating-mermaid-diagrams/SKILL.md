---
name: generating-mermaid-diagrams
description: "Salesforce architecture diagrams using Mermaid with ASCII fallback. Use this skill when generating text-based diagrams for Salesforce architecture, OAuth flows, ERDs, integration sequences, or Agentforce structure. TRIGGER when: user says \"diagram\", \"visualize\", \"ERD\", or asks for sequence diagrams, flowcharts, class diagrams, or architecture visualizations in Mermaid. DO NOT TRIGGER when: user wants PNG/SVG image output (use generating-visual-diagrams), or asks about non-Salesforce systems."
license: MIT
compatibility: "Requires Mermaid-capable renderer for diagram previews"
metadata:
  version: "1.0"
---

# generating-mermaid-diagrams: Salesforce Diagram Generation

Use this skill when the user needs **text-based diagrams**: Mermaid diagrams for architecture, OAuth, integration flows, ERDs, or Agentforce structure, plus ASCII fallback when plain-text compatibility matters.

## Scope

### In Scope
Use `generating-mermaid-diagrams` when the user wants:
- Mermaid output
- ASCII fallback diagrams
- architecture, sequence, flowchart, or ERD views in markdown-friendly form
- diagrams that can live directly in docs, READMEs, or issues

### Out of Scope — Delegate elsewhere when the user wants:
- rendered PNG/SVG images or polished mockups → [generating-visual-diagrams](../generating-visual-diagrams/SKILL.md)
- non-Salesforce systems only → use a more general diagramming skill
- object discovery before an ERD → [generating-custom-object](../generating-custom-object/SKILL.md) or [generating-custom-field](../generating-custom-field/SKILL.md)

---

## Supported Diagram Families

| Type | Preferred Mermaid form | Typical use |
|---|---|---|
| OAuth / auth flows | `sequenceDiagram` | Authorization Code, JWT, PKCE, Device Flow |
| ERD / data model | `flowchart LR` | object relationships and sharing context |
| integration sequence | `sequenceDiagram` | request/response or event choreography |
| system landscape | `flowchart` | high-level architecture |
| role / access hierarchy | `flowchart` | users, profiles, permissions |
| Agentforce behavior map | `flowchart` | agent → topic → action relationships |

---

## Required Context to Gather First

Ask for or infer:
- diagram type
- scope and entities / systems involved
- output preference: Mermaid only, ASCII only, or both
- whether styling should be minimal, documentation-first, or presentation-friendly
- for ERDs: whether org metadata is available for grounding

---

## Recommended Workflow

### 1. Pick the right diagram structure
- use `sequenceDiagram` for time-ordered interactions
- use `flowchart LR` for ERDs and capability maps
- keep a single primary story per diagram when possible

### 2. Gather data
For ERDs and grounded diagrams:
- use [generating-custom-object](../generating-custom-object/SKILL.md) or [generating-custom-field](../generating-custom-field/SKILL.md) when real schema discovery is needed
- optionally use the local metadata helper script for counts / relationship context when appropriate

### 3. Generate Mermaid first
Apply:
- accurate labels
- simple readable node text
- consistent relationship notation
- restrained styling that renders cleanly in markdown viewers

### 4. Add ASCII fallback when useful
Provide an ASCII version when the user wants terminal compatibility or plaintext documentation.

### 5. Explain the diagram briefly
Call out the key relationships, flow direction, and any assumptions.

---

## High-Signal Rules

### For sequence diagrams
- use `autonumber` when step order matters
- distinguish requests vs responses clearly
- use notes sparingly for protocol detail

### For ERDs
- prefer `flowchart LR`
- keep object cards simple
- use clear relationship arrows
- avoid field overload unless the user explicitly asks for field-level detail
- color-code object types only when it improves readability

### For ASCII output
- keep width reasonable
- align arrows and boxes consistently
- optimize for readability over decoration

---

## Output Format

````markdown
## <Diagram Title>

### Mermaid Diagram
```mermaid
<diagram>
```

### ASCII Fallback
```text
<ascii>
```

### Notes
- <key point>
- <assumption or limitation>
````

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| real object / field definitions | [generating-custom-object](../generating-custom-object/SKILL.md) / [generating-custom-field](../generating-custom-field/SKILL.md) | grounded ERD generation |
| rendered diagram / image output | [generating-visual-diagrams](../generating-visual-diagrams/SKILL.md) | visual polish beyond Mermaid |
| connected-app auth setup context | [configuring-connected-apps](../configuring-connected-apps/SKILL.md) | accurate OAuth flows |
| Agentforce logic visualization | [developing-agentforce](../developing-agentforce/SKILL.md) | source-of-truth behavior details |
| Flow behavior diagrams | [generating-flow](../generating-flow/SKILL.md) | actual Flow logic grounding |

---

## Gotchas

| Issue | Resolution |
|---|---|
| Mermaid renderer not available | Provide ASCII fallback automatically; note that the Mermaid block still carries the diagram for copy-paste into a renderer |
| ERD becomes unreadable with too many objects | Split into sub-diagrams by domain (Sales, Service, etc.) and link them in prose |
| Sequence diagram step order unclear | Use `autonumber` directive to make step ordering explicit |
| OAuth flow actors differ by grant type | Read the relevant asset template first before generating to avoid actor mismatch |

---

## Reference File Index

### Conventions & rules — read before generating
- [references/diagram-conventions.md](references/diagram-conventions.md) — consistency rules for all diagram types
- [references/mermaid-reference.md](references/mermaid-reference.md) — Mermaid syntax quick reference
- [references/usage-examples.md](references/usage-examples.md) — worked examples per diagram type

### Styling
- [references/mermaid-styling.md](references/mermaid-styling.md) — theming and annotation patterns
- [references/color-palette.md](references/color-palette.md) — color-blind-friendly palette with hex values
- [references/erd-conventions.md](references/erd-conventions.md) — ERD-specific layout and notation rules

### Preview
- [references/preview-guide.md](references/preview-guide.md) — how to render Mermaid locally
- [scripts/README.md](scripts/README.md) — setup and usage instructions for all scripts in this skill
- [scripts/mermaid_preview.py](scripts/mermaid_preview.py) — live-reload preview server; run to preview diagrams in browser
- [scripts/query-org-metadata.py](scripts/query-org-metadata.py) — queries org schema to ground ERD generation

### OAuth flow templates — load the matching template when generating OAuth diagrams
- [assets/oauth/authorization-code.md](assets/oauth/authorization-code.md) — Authorization Code grant
- [assets/oauth/authorization-code-pkce.md](assets/oauth/authorization-code-pkce.md) — PKCE variant for mobile/SPA
- [assets/oauth/jwt-bearer.md](assets/oauth/jwt-bearer.md) — JWT Bearer server-to-server
- [assets/oauth/client-credentials.md](assets/oauth/client-credentials.md) — Client Credentials service accounts
- [assets/oauth/device-authorization.md](assets/oauth/device-authorization.md) — Device Flow for CLI/IoT
- [assets/oauth/refresh-token.md](assets/oauth/refresh-token.md) — Refresh Token renewal flow
- [assets/oauth/user-agent-social-sign-on.md](assets/oauth/user-agent-social-sign-on.md) — User-Agent / Social Sign-On

### Data model ERD templates — load the matching template when generating ERDs
- [assets/datamodel/salesforce-erd.md](assets/datamodel/salesforce-erd.md) — core Salesforce objects
- [assets/datamodel/sales-cloud-erd.md](assets/datamodel/sales-cloud-erd.md) — Sales Cloud objects
- [assets/datamodel/service-cloud-erd.md](assets/datamodel/service-cloud-erd.md) — Service Cloud objects
- [assets/datamodel/b2b-commerce-erd.md](assets/datamodel/b2b-commerce-erd.md) — B2B Commerce objects
- [assets/datamodel/campaigns-erd.md](assets/datamodel/campaigns-erd.md) — Campaigns and campaign member model
- [assets/datamodel/consent-erd.md](assets/datamodel/consent-erd.md) — Consent and privacy objects
- [assets/datamodel/files-erd.md](assets/datamodel/files-erd.md) — Files and ContentDocument model
- [assets/datamodel/forecasting-erd.md](assets/datamodel/forecasting-erd.md) — Forecasting objects
- [assets/datamodel/fsl-erd.md](assets/datamodel/fsl-erd.md) — Field Service Lightning objects
- [assets/datamodel/party-model-erd.md](assets/datamodel/party-model-erd.md) — Party model objects
- [assets/datamodel/quote-order-erd.md](assets/datamodel/quote-order-erd.md) — Quote and Order objects
- [assets/datamodel/revenue-cloud-erd.md](assets/datamodel/revenue-cloud-erd.md) — Revenue Cloud objects
- [assets/datamodel/scheduler-erd.md](assets/datamodel/scheduler-erd.md) — Scheduler objects
- [assets/datamodel/territory-management-erd.md](assets/datamodel/territory-management-erd.md) — Territory Management objects

### Other diagram templates
- [assets/architecture/system-landscape.md](assets/architecture/system-landscape.md) — system landscape overview template
- [assets/integration/api-sequence.md](assets/integration/api-sequence.md) — API callout sequence template
- [assets/agentforce/agent-flow.md](assets/agentforce/agent-flow.md) — Agentforce agent → topic → action flow
- [assets/role-hierarchy/user-hierarchy.md](assets/role-hierarchy/user-hierarchy.md) — role and permission hierarchy template

---

## Output Expectations

Deliverables produced by this skill for each request:

- **Mermaid code block** — fenced ` ```mermaid ` block ready to paste into GitHub, Confluence, or any Mermaid-capable renderer
- **ASCII fallback** (when requested or when Mermaid renderer is unavailable) — text-only diagram using box/arrow characters
- **Brief explanation** — 2-5 bullet points calling out key relationships, flow direction, and any assumptions or limitations in the diagram
- For ERDs: object cards with field labels and relationship type annotations
- For sequence diagrams: numbered steps (`autonumber`) with clear actor labels

---

## Score Guide

| Score | Meaning |
|---|---|
| 72–80 | production-ready diagram |
| 60–71 | clear and useful with minor polish left |
| 48–59 | functional but could be clearer |
| 35–47 | needs structural improvement |
| < 35 | inaccurate or incomplete |

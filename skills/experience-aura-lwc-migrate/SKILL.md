---
name: experience-aura-lwc-migrate
description: "Use this skill to analyze a Salesforce Aura component bundle (.cmp, .app, .evt, .intf, Controller.js, Helper.js, Renderer.js) and produce a framework-agnostic migration blueprint (PRD.yaml / PRD.md / PRD.json) capturing public API, data requirements, slots, events, states, accessibility, styling, localization, and security posture. This is Phase 1 (analysis + PRD) only — it does NOT author or edit component code, wire adapters, or Jest tests, and does not write .html/.js/.css/.js-meta.xml. TRIGGER when the user says \"analyze this Aura component\", \"migrate Aura\", \"convert .cmp\", \"produce a migration blueprint\", \"generate a PRD for this Aura component\", or mentions aura:attribute, aura:handler, force:recordData, $Label, $Resource, component.get, cmp.find, or an input directory containing .cmp files. DO NOT TRIGGER when there is no Aura source (delegate downstream LWC authoring to experience-lwc-generate), for post-migration scoring, or for refactoring an existing modern component."
metadata:
  version: "1.0"
  domains: ["Experience"]
  relatedSkills:
    - experience-lwc-generate
---
<!-- adk-managed-skill -->

# Migrating Aura to LWC

Migrate an existing Salesforce Aura component bundle to a Lightning Web Component using a PRD-driven workflow. The Aura source is analyzed through eight expert lenses (static references, data, API surface, slots, styling, default values, unknown dependencies, redundant-code cleanup) to produce a framework-agnostic PRD, which is handed to the LWC authoring skills and verified against the Aura→LWC completeness checklist.

## When to Use

- Porting an Aura bundle (`.cmp`, `.controller.js`, `.helper.js`, `.renderer.js`, `.css`, `.design`, `.evt`, `.intf`) to LWC.
- Producing a framework-agnostic PRD from Aura source so a sibling team can implement the LWC equivalent.
- Auditing an Aura component for patterns that need explicit mapping before LWC conversion (facets, `aura:id` DOM access, `force:recordData`, application events).

Do NOT use this skill for:
- Authoring a brand-new LWC from a Figma or PRD with no Aura source (delegate to `experience-lwc-generate`).
- Refactoring an existing LWC (delegate to `experience-lwc-generate`).
- Post-hoc completeness scoring of a conversion that was already done without this skill, or Lightning Out Beta → 2.0 host-page migration — no checked-in skill covers these today.

## Prerequisites

- Aura component bundle files (minimum: `.cmp`; usually also controller / helper / CSS / events / interfaces).
- Target LWC path (module folder) — discover the caller's module tree from `sfdx-project.json` `packageDirectories` (typically an `lwc/<name>/` subdirectory under one of the listed package paths).
- For resolver-assisted dependency lookup (Phase 2, step 7): the `@sfdc-internal/adk-knowledge` package installed in the caller's workspace. If it is not present, the skill surfaces the missing dependency as an unknown rather than failing.
- Awareness of the project's downstream LWC authoring flow — this skill hands off a PRD to that flow but does not invoke it.

## Core Principles

Apply the Aura → LWC migration principles before and during each phase: understand before converting, prioritize functionality equivalence over structural equivalence, leverage native web standards, migrate iteratively, and test thoroughly. The architectural deltas (two-way → one-way binding, Aura events → DOM events, `aura:id` → `this.template.querySelector`, etc.) are documented in [references/aura-migration-guidelines.md](references/aura-migration-guidelines.md).

## Knowledge Bases

- [references/aura-prd-framework.md](references/aura-prd-framework.md) — the 14-section framework for drafting a framework-agnostic PRD from an Aura component.
- [references/aura-migration-guidelines.md](references/aura-migration-guidelines.md) — core principles + Aura-vs-LWC architectural differences + markup / JS / event / lifecycle translation tables.
- [references/aura-reference-expert.md](references/aura-reference-expert.md) — static resources, global value providers, HTML-to-generic wording, URLs, component dependencies, `Aura.Action` handlers.
- [references/aura-data-expert.md](references/aura-data-expert.md) — data requirements, `force:recordData`, `lightning:recordViewForm`, Apex controllers.
- [references/aura-api-expert.md](references/aura-api-expert.md) — API surface: public attributes, methods, layout, component events, DOM events.
- [references/aura-slots-expert.md](references/aura-slots-expert.md) — default and named slots (Aura facets / `{!v.body}` → LWC slots).
- [references/aura-style-expert.md](references/aura-style-expert.md) — CSS, SLDS, design tokens, dynamic styling.
- [references/aura-values-expert.md](references/aura-values-expert.md) — default values and initialization patterns.
- [references/aura-resolver-expert.md](references/aura-resolver-expert.md) — resolving unknown components, events, interfaces, and libraries via the `@sfdc-internal/adk-knowledge` package.
- [references/aura-redundant-code-expert.md](references/aura-redundant-code-expert.md) — strip Aura-only noise (commented-out code, telemetry, unused private attributes/methods) from the PRD before LWC handoff.
- WCAG 2.2 — Aura-scoped accessibility reviewers (SC 1.3.1 (ii) Tables, 1.3.5 Identify Input Purpose, 3.2.1 On Focus, 3.2.2 On Input, 3.3.2 Labels or Instructions, 4.1.2 Name / Role / Value) are planned to land as a separate `accessibility-code-review-aura` skill in a follow-up PR; until then, Phase 3 applies the WCAG preamble inline.
- [references/aura-to-lwc-completeness-checklist.md](references/aura-to-lwc-completeness-checklist.md) — post-conversion verification rubric.

Open the relevant reference before drafting or enhancing the corresponding PRD section.

## Workflow

This skill covers the analysis and PRD-generation phases only. It **does not** produce, edit, or validate LWC bundles, wire adapters, or tests. Phases 1–3 below are mandatory when this skill is invoked. Phases 4–5 describe the recommended downstream authoring flow — they are informational follow-up guidance for the caller and are NOT executed by this skill.

### Phase 1 — Analyze and draft the PRD

**Goal:** produce a draft YAML PRD that captures every section of the 14-section framework.

1. Inspect the caller-supplied Aura bundle files. Extract the component name, the `access` attribute from the `.cmp` metadata, and every embedded/referenced component.
2. Apply the framework in [references/aura-prd-framework.md](references/aura-prd-framework.md). State the `access` attribute explicitly in the overview and describe its implications (GLOBAL: publicly available across namespaces; PRIVILEGED/PUBLIC: restricted; etc.).
3. Never list the host component itself in the `unknowns` section — that creates a circular dependency. If no valid unknowns exist, use an empty array.
4. Save the draft PRD to the workspace (e.g., `packages/skills/<skill>-workspace/<iteration>/PRD-draft.yaml`).

**Deliverable:** draft PRD (YAML) covering the 14 sections.

### Phase 2 — Enhance the PRD with Aura expert lenses

**Goal:** harden each section using the eight Aura expert frameworks.

Apply the experts in order. Each pass reads the draft PRD and rewrites the relevant sections in place.

1. **Reference analysis** — apply [references/aura-reference-expert.md](references/aura-reference-expert.md) to `staticReferences`, `componentCommunication`, and `unknowns`. Enumerate every `$Resource`, `$ContentAsset`, `$Label`, `$Browser`, `$Locale`, `/lightning/*` route, and `c:*` / `force:*` / `lightning:*` dependency. The blueprint must never directly contain the Aura-specific strings `$ContentAsset`, `$Label`, `$Resource`, `$Browser`, or `$Locale`; replace each with a description of intent.
2. **Data analysis** — apply [references/aura-data-expert.md](references/aura-data-expert.md) to `dataRequirements`. The blueprint `dataRequirements` must not contain `force:recordData` or `lightning:recordViewForm` — document the underlying record, fields, and object-API-name instead. Rename `sObjectName` → `objectApiName`. Capture Apex-controller method names, input parameters, and output shapes.
3. **API analysis** — apply [references/aura-api-expert.md](references/aura-api-expert.md) to `componentCommunication`, `interactions`, and `staticReferences`. Document every public attribute (with type, default, and all usage intents), `<aura:method>` declaration, event firing (`component.getEvent(...).fire()`), and `Object`-typed callback attribute (these become LWC custom events).
4. **Slots analysis** — apply [references/aura-slots-expert.md](references/aura-slots-expert.md) to `contentRequirements`. Translate every `{!v.body}` / `{#v.body}` to a default slot entry (LWC components can have only one default slot — capture the condition under which it is present) and every `<aura:attribute type="Aura.Component">` or `"Aura.Component[]"` to a named-slot entry.
5. **Style analysis** — apply [references/aura-style-expert.md](references/aura-style-expert.md) to `styling` and `dataRequirements`. Move styling-related attributes out of `dataRequirements` and into `styling`. Document SLDS hooks, custom CSS, and any dynamic styling driven by JS.
6. **Values analysis** — apply [references/aura-values-expert.md](references/aura-values-expert.md) to `dataRequirements`. For every Aura attribute, record its default value (type + literal; or namespace + name for `$Label` references) in the `what` property.
7. **Resolver analysis** — apply [references/aura-resolver-expert.md](references/aura-resolver-expert.md) to `unknowns`. For each unknown, parse namespace + name, look up the corresponding file under `node_modules/@sfdc-internal/adk-knowledge/dist/` using the mapping rules, and either inline the resolved content or leave a note that manual research is required. If the `@sfdc-internal/adk-knowledge` package is not installed, note the expected path and leave the unknown in place.
8. **Redundant-code cleanup** — apply [references/aura-redundant-code-expert.md](references/aura-redundant-code-expert.md) across the PRD. Remove commented-out markup/JS/CSS, telemetry/instrumentation, and private attributes/methods that aren't used elsewhere — these don't carry forward to LWC. Keep the PRD's JSON shape intact; sections may end up with empty arrays. Generate a short report listing only the items that actually changed.

**Deliverable:** enhanced PRD (YAML) with all eight expert passes applied.

### Phase 3 — Accessibility pass

**Goal:** ensure the PRD's `accessibility` section meets WCAG 2.2 minimums.

1. Apply the WCAG 2.2 reviewers inline against the Aura source files (`.cmp`, `.controller.js`, `.helper.js`, `.renderer.js`, `.css`). Cover the Aura-scoped Success Criteria: 1.3.1 (ii) Tables, 1.3.5 Identify Input Purpose, 3.2.1 On Focus, 3.2.2 On Input, 3.3.2 Labels or Instructions, 4.1.2 Name / Role / Value. (When the sibling `accessibility-code-review-aura` skill ships in a follow-up PR, hand off to it instead.)
2. Fold each finding into the PRD's `accessibility` section. For every requirement, capture the WCAG Success Criterion it satisfies and the proposed LWC implementation approach (semantic HTML first, ARIA only where semantic HTML cannot achieve the same outcome).
3. Only cite violations that directly break a WCAG Success Criterion. Do not suggest enhancements outside WCAG scope.

**Deliverable:** PRD with an accessibility section that lists each required feature, the WCAG Success Criterion it satisfies, and the LWC implementation approach.

### Phase 4 — Downstream authoring (follow-up guidance, not executed here)

Once the enhanced PRD is complete, the caller can hand it off to an LWC authoring workflow. This skill does not perform any authoring. Recommended downstream steps:

- Pass the enhanced PRD to `experience-lwc-generate` as the design input, substituting for a Figma / written-spec input. This skill does not invoke `experience-lwc-generate`; the caller triggers it as a follow-up step.
- For data access decisions (UIAPI / GraphQL / Apex), the caller may consult LDS-focused workflows to translate the PRD's `dataRequirements` section into concrete adapters.
- For SLDS styling decisions, the caller may consult an SLDS design workflow.

### Phase 5 — Downstream verification (follow-up guidance, not executed here)

After LWC authoring completes, the caller can verify the migrated component with the project's standard test and review workflows — Jest coverage, accessibility Jest, a11y / security / RTL review, telemetry, feature-flag gating, etc. Apply [references/aura-to-lwc-completeness-checklist.md](references/aura-to-lwc-completeness-checklist.md) as a final scoring pass on the completed LWC.

## Cross-References

- `experience-lwc-generate` — recommended downstream authoring handoff (non-executing; the caller triggers it after this skill's PRD is complete).

## Verification (PRD-only)

- The enhanced PRD covers all 14 framework sections with no `TODO` / placeholder entries.
- `dataRequirements` contains no direct references to `force:recordData` or `lightning:recordViewForm`, and no `sObjectName` keys (renamed to `objectApiName`).
- `staticReferences` and other sections contain no raw Aura strings like `$Resource`, `$Label`, `$ContentAsset`, `$Browser`, `$Locale`.
- Every `<aura:method>` appears in `interactions` with the corresponding trigger.
- Every `{!v.body}` / `{#v.body}` appears in `contentRequirements` as a default slot (with the presence condition).
- Every `<aura:attribute type="Aura.Component">` appears in `contentRequirements` as a named slot.
- Every unknown has been resolved via the `@sfdc-internal/adk-knowledge` package (or marked as manually-required with the attempted knowledge-file path).

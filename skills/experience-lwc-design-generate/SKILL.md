---
name: experience-lwc-design-generate
description: "Use when you need to create a brand new Lightning Web Component from a Figma design, a Product Requirements Document, or another design artifact — orchestrating the five-phase workflow (gather requirements → generate code → optimize → lint/format/compile → test) and stitching together the specialized skills for SLDS, LDS, base components, optimization, and testing. Use this skill whenever the user mentions building a new LWC from Figma, building an LWC from a PRD, generating an LWC from a design or screenshot, or migrating an Aura component as a fresh LWC build. DO NOT TRIGGER when refactoring an existing LWC (use experience-lwc-generate), for Aura → LWC in-place migration (out of scope for this skill), for standalone SLDS token or styling work (use design-systems-slds-apply), or for standalone data-layer work (use experience-lds-best-practices-apply or experience-lds-data-requirements-generate)."
metadata:
  version: "1.0"
  cliTools:
    - tool: ["eslint"]
      semver: ">=8.0"
    - tool: ["prettier"]
      semver: ">=2.0"
    - tool: ["python3"]
      semver: ">=3.8"
  relatedSkills:
    - design-systems-slds-apply
    - experience-lds-best-practices-apply
    - experience-lds-data-requirements-generate
    - experience-lwc-accessibility-validate
    - experience-lwc-base-components-integrate
    - experience-lwc-generate
    - experience-lwc-rtl-validate
    - experience-lwc-runtime-observe
    - experience-lwc-security-validate
    - experience-lwc-typescript-migrate
---
<!-- adk-managed-skill -->

# Creating LWC Components from Design

Orchestrate the end-to-end creation of a new Lightning Web Component from a design input (Figma, PRD, Aura source, or user description). This is the top-level workflow skill — it sequences the specialized sibling skills that own each stage. Org-aware data (LDS schema introspection, design-frame inspection) is resolved by handing off to `experience-lds-data-requirements-generate` or via design-tool URLs the user provides.

## When to Use

- Building a brand-new LWC from a Figma frame, PRD, or written spec.
- Migrating an Aura component to LWC as a fresh build (in-place Aura → LWC porting is out of scope for this skill).
- Creating a component whose requirements are still partly implicit and need distillation into a PRD before coding.

Do NOT use this skill for:
- Refactoring an existing LWC (use `experience-lwc-generate`).
- Aura → LWC in-place migration (out of scope for this skill).
- Pure styling or data-layer work (use the specialized skills directly).

## Prerequisites

- At least one design input: Figma URL, PRD markdown, Aura component source, or a textual spec.
- Target path (module folder) for the new LWC.
- For data-backed components: access to the org so `experience-lds-data-requirements-generate` and `experience-lds-best-practices-apply` can resolve the schema and adapter shapes.

## Knowledge Bases

- [references/prd-analysis-template.md](references/prd-analysis-template.md) — PRD section skeleton (copy it verbatim when producing a PRD).
- [references/figma-to-prd-blueprint.md](references/figma-to-prd-blueprint.md) — Figma-specific guidance for translating a frame into PRD sections (componentName/tagName, contentRequirements, dataRequirements, interactions, componentCommunication, states, accessibility/responsiveness/styling/localization/security). Read this before Phase 1.2 when the input is a Figma design.

## Workflow (mandatory five phases)

### Phase 1 — Gather PRD & requirements

**Goal:** produce a consolidated PRD that every later phase consumes.

1. **Obtain raw requirements** — collect the PRD, design spec, Figma URL, Aura source, or user text.
2. **Figma → PRD** (if applicable): follow [references/figma-to-prd-blueprint.md](references/figma-to-prd-blueprint.md) for the full Figma-frame analysis and PRD section guidelines. Inputs you need from the user: the Figma URL, a screenshot of the target frame, and (if Dev Mode is available) the metadata export for the node. Translate into the PRD skeleton from [references/prd-analysis-template.md](references/prd-analysis-template.md) using the section-by-section guidance in the blueprint.
3. **Aura → PRD** (if migrating): enumerate the Aura component's functionality that must be preserved — markup, controller/helper actions, events, attributes, and wired data — and feed that inventory into the PRD as explicit requirements. (In-place Aura → LWC porting is out of scope; this step only captures behavior for a fresh build.)
4. **Data requirements** (if the component reads/writes data): hand off to `experience-lds-data-requirements-generate`. That skill produces a validated data specification (object/field API names, recommended LDS API, implementation approach). Paste its output verbatim into the PRD.
5. **Adapter exploration**: hand off to `experience-lds-best-practices-apply` for the adapter selection rules (UI API vs GraphQL vs Apex) and the recommended wiring for the chosen approach.
6. **Naming**: `componentName` must be camelCase (e.g., `productCard`) and `tagName` must be its kebab-case form (e.g., `product-card`). Validate both with the bundled script — do not eyeball the check:

   ```bash
   "<skill_dir>/scripts/check-component-name.sh" <componentName> <tagName>
   ```

   The script exits nonzero (with an actionable stderr message) if either name is malformed or if the kebab form of `componentName` does not equal `tagName`.

**Deliverable:** a comprehensive PRD covering purpose, content, data, interactions, states, a11y, responsiveness, styling direction, localization, and security. Keep it checked into the workspace (e.g., `packages/skills/<skill>-workspace/<iteration>/PRD.md`).

### Phase 2 — Generate component code

**Goal:** initial `.html`, `.js`, `.css`, `.js-meta.xml` that strictly reflect the PRD.

1. Hand off to `experience-lwc-generate` with the PRD content as the spec. That skill owns PRD → code translation (events, getters, `@api`, `.js-meta.xml`, AI metadata) and is the authoring source of truth.
2. Use the SLDS decision hierarchy from `design-systems-slds-apply`:
   1. Prefer a matching Lightning Base Component (`experience-lwc-base-components-integrate`).
   2. Otherwise pick an SLDS Blueprint or utility class (per `design-systems-slds-apply`).
   3. Otherwise write custom CSS using SLDS styling hooks (also covered in `design-systems-slds-apply`).
3. Re-confirm the authoring baseline by walking the `experience-lwc-generate` checklist before proceeding.
4. Translate every PRD data requirement to either a wire adapter (UIAPI / GraphQL) or an explicit TODO.
5. Adhere strictly to the PRD:
   - Only include features and behaviors the PRD describes.
   - Mark uncertain areas with `// TODO:` comments that quote the PRD language raising the ambiguity.
   - Add extensive code comments explaining intent.
   - Do not split the component into more sub-components than the PRD implies.

**Deliverable:** a first-pass LWC bundle in the target path.

### Phase 3 — Optimize component

**Goal:** apply performance, maintainability, and best-practice fixes.

1. Walk the optimization checklist below before any other review:
   - Single responsibility, encapsulation, reusability.
   - Minimize DOM operations; batch updates via properties.
   - Audit event handlers and lifecycle hook usage (`renderedCallback` guards).
   - Consider lazy loading for heavy children.
2. Hand off to `experience-lwc-generate` for the LWC best-practices review pass (anti-patterns, reactivity, composition).
3. Hand off to the compliance suite for the pre-ship review — `experience-lwc-accessibility-validate` (a11y), `experience-lwc-security-validate` (LWS + Product Security), and `experience-lwc-rtl-validate` (RTL i18n). Run them together for the full quality pass.
4. If the component touches data, hand off to `experience-lds-best-practices-apply` for cache/consistency and referential-integrity checks.
5. Apply every accepted finding. Keep the PRD as the source of truth — do not add scope under the guise of optimization.

### Phase 4 — Lint, format, compile-check

Condition: only run steps whose tooling is configured in the project.

1. **Detect project tooling** — invoke the bundled detection script from the project root and read its `<tool>=yes|no` lines. Do NOT eyeball `package.json` / dotfiles in prose:

   ```bash
   "<skill_dir>/scripts/detect-project-tools.sh" <projectRoot>
   ```

   Sample output:

   ```text
   eslint=yes
   prettier=yes
   cursor-rules=no
   lwc-compiler=yes
   ```

   Run the substeps below only for tools reported `yes`; skip the rest.
2. **ESLint** (if `eslint=yes`) — run and fix all violations.
3. **Prettier** (if `prettier=yes`) — run for consistent formatting.
4. **Cursor rules** (if `cursor-rules=yes`) — apply every rule the project ships.
5. **LWC compiler** (if `lwc-compiler=yes`) — run via local dev server or SFDX; resolve every syntax/template error before moving on.

**Deliverable:** clean, validated component code.

### Phase 5 — Create tests

Hand off to `experience-lwc-accessibility-jest-run` for automated accessibility Jest coverage; add general-purpose Jest coverage in the same pass following the `experience-lwc-generate` test guidance, plus UTAM page object generation if the team requires it.

**Deliverable:** the LWC bundle with a passing test suite at or above the project's coverage threshold.

## Definition of Done

A new component built from this workflow is "done" only when **every** item below is true. Treat this as the canonical readiness checklist — copy it into the PR description so reviewers can confirm each line.

**Code completion** — no implementation gaps:

1. Every PRD requirement is either implemented or explicitly annotated with a `TODO:` and a linked tracking item. No silent gaps.
2. No `TODO`, `FIXME`, or `console.log` / `console.table` / `alert()` left in production paths.
3. No commented-out code blocks, no empty function bodies, no placeholder values, no dummy data, no unreferenced imports.
4. No `lwc:dom="manual"` regions or third-party-library escape hatches without a comment explaining why a native LWC pattern wasn't used.

**Compliance and quality:**

5. `.js-meta.xml` AI metadata passes the audit in `experience-lwc-generate` (component-wide `<ai><description>` set, plus an `<ai><property name="…" aiDescription="…"/></ai>` entry for every `@api` member exposed through `<targetConfig>`; no marketing language).
6. SLDS styling passes `design-systems-slds-apply` verification — no raw hex / px values, only styling hooks and SLDS utility classes.
7. Accessibility pass complete: `experience-lwc-accessibility-validate` for source review + `experience-lwc-accessibility-jest-run` for automated tests, both green.
8. Security + RTL pass complete: `experience-lwc-security-validate` + `experience-lwc-rtl-validate`, both green.

**Data + tests:**

9. Data layer verified against the referenced LDS adapters (every wire / imperative call is documented in the PRD's data section and matches one of the adapters from `experience-lds-best-practices-apply` or `experience-lds-data-requirements-generate`).
10. Jest tests green at the required coverage level for the project. New tests cover every `@api` surface, every dispatched event, and every error path (failed wire, failed apex, validation rejection).
11. UTAM page objects produced for any UI flow that needs cross-component browser-level testing (skip if not needed).

## Cross-References

- Skills chained by this workflow (in phase order):
  - `experience-lds-data-requirements-generate` — Phase 1.4 data spec (and Phase 1.5 adapter exploration alongside `experience-lds-best-practices-apply`).
  - `design-systems-slds-apply`, `experience-lwc-base-components-integrate` — Phase 2 styling decisions.
  - `experience-lwc-generate` — Phase 2 authoring baseline + Phase 3 best-practices review + Phase 5 AI-metadata audit.
  - `experience-lds-best-practices-apply` — Phase 2/3 data-layer adapter selection and consistency review.
  - `experience-lwc-accessibility-validate`, `experience-lwc-security-validate`, `experience-lwc-rtl-validate` — Phase 3 a11y/security/RTL review.
  - `experience-lwc-accessibility-jest-run` — Phase 5 automated a11y test generation.
  - Optional: add o11y instrumentation as a separate pass once the component stabilizes.
  - `experience-lwc-typescript-migrate` — optional once JS is green.
  - When the new component ships behind a flag, gate it with a feature flag during rollout.
  - `experience-lwc-api-docs-generate` — once the public API surface is stable.
- Org-aware inputs used by this workflow:
  - Figma URL + screenshot (and, if available, the developer's Dev Mode metadata export) — Phase 1.2 Figma input.
  - `experience-lds-data-requirements-generate` owns the org-schema introspection and data-spec validation used in Phase 1 when the component needs org-backed data — hand off to that skill rather than duplicating its work here.

## Examples

**Phase 1 PRD skeleton (fill from the Figma/PRD/Aura input)**

```text
Component: productCard (<product-card>)
Purpose: Render a compact summary of a product with quick actions.

Content requirements
- Hero image (Product.HeroImage__c)
- Title (Product.Name)
- Subtitle (Product.Tagline__c)
- Primary CTA button ("Add to cart")
- Secondary CTA icon button ("Favorite")

Data requirements
- Input: @api recordId (Product Id)
- Adapter: getRecord (UIAPI) with fields Name, Tagline__c, HeroImage__c
- Events out: addtocart{detail.recordId}, favorite{detail.recordId, detail.value}

States
- Loading (data not yet resolved)
- Error (adapter error)
- Empty (no record found)
- Default

Accessibility
- Title uses <h3>
- Icon-only button carries aria-label="Favorite"
- Card is a labelled region (role="group", aria-labelledby)

Responsiveness
- Full width < 480px
- Side-by-side image + text >= 480px

Styling
- Uses lightning-card wrapper
- Surface color: --slds-g-color-surface-container-1
- Shadow: --slds-g-shadow-1
```

**Phase 2 skeleton**

```javascript
import { LightningElement, api, wire } from 'lwc';
import { getRecord } from 'lightning/uiRecordApi';
import NAME from '@salesforce/schema/Product__c.Name';
import TAGLINE from '@salesforce/schema/Product__c.Tagline__c';
import HERO from '@salesforce/schema/Product__c.HeroImage__c';

const FIELDS = [NAME, TAGLINE, HERO];

export default class ProductCard extends LightningElement {
    @api recordId;

    @wire(getRecord, { recordId: '$recordId', fields: FIELDS })
    record;

    get hasRecord() { return this.record?.data != null; }
    get isLoading() { return !this.record; }
    get hasError()  { return !!this.record?.error; }
    get name()      { return this.record?.data?.fields?.Name?.value ?? ''; }
    get tagline()   { return this.record?.data?.fields?.Tagline__c?.value ?? ''; }
    get heroUrl()   { return this.record?.data?.fields?.HeroImage__c?.value ?? ''; }

    handleAddToCart() {
        this.dispatchEvent(new CustomEvent('addtocart', { detail: { recordId: this.recordId }, bubbles: true, composed: true }));
    }
    handleFavorite(event) {
        this.dispatchEvent(new CustomEvent('favorite', { detail: { recordId: this.recordId, value: event.detail.value }, bubbles: true, composed: true }));
    }
}
```

## Verification

- Every PRD section is traceable to at least one block of code or an explicit TODO.
- Phases 1–5 were executed in order; no step was skipped.
- Accessibility, SLDS, data-layer, and AI metadata reviews all pass.
- Coverage meets or exceeds the project's threshold.
- The component renders correctly in `experience-lwc-runtime-observe` across the responsive breakpoints enumerated in the PRD.

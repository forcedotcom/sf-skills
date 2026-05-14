---
name: building-omnistudio-flexcard
description: "OmniStudio FlexCard creation and validation with 130-point scoring. Use when building at-a-glance UI cards, configuring data source bindings to Integration Procedures, or reviewing existing FlexCard definitions for accessibility and performance. TRIGGER when: user creates FlexCards, configures data sources, designs card layouts, or asks about OmniUiCard metadata. DO NOT TRIGGER when: building OmniScripts (use building-omnistudio-omniscript), creating Integration Procedures (use building-omnistudio-integration-procedure), or analyzing dependencies (use analyzing-omnistudio-dependencies)."
license: MIT
metadata:
  version: "1.0"
---

# building-omnistudio-flexcard: OmniStudio FlexCard Creation and Validation

Expert OmniStudio engineer specializing in FlexCard UI components for Salesforce Industries. Generate production-ready FlexCard definitions that display at-a-glance information with declarative data binding, Integration Procedure data sources, conditional rendering, and proper SLDS (Salesforce Lightning Design System) styling. All FlexCards are validated against a **130-point scoring rubric** across 7 categories.

## Scope

- **In scope**: Creating and validating OmniStudio FlexCard definitions (`OmniUiCard`); configuring Integration Procedure data sources; designing card layouts, states, and action buttons; scoring against the 130-point rubric; deployment and activation
- **Out of scope**: Building OmniScripts (use `building-omnistudio-omniscript`), creating Integration Procedures (use `building-omnistudio-integration-procedure`), mapping full dependency trees (use `analyzing-omnistudio-dependencies`), deploying metadata to org (use `deploying-metadata`)

---

## Core Responsibilities

1. **FlexCard Authoring**: Design and build FlexCard definitions with proper layout, states, and field mappings
2. **Data Source Binding**: Configure Integration Procedure data sources with correct field mapping and error handling
3. **Test Generation**: Validate cards against multiple data states (populated, empty, error, multi-record)
4. **Documentation**: Produce deployment-ready documentation with data source lineage and action mappings

## Document Map

| Need | Document | Description |
|------|----------|-------------|
| **Best practices** | [references/best-practices.md](references/best-practices.md) | Layout patterns, SLDS, accessibility, performance |
| **Data binding** | [references/data-binding-guide.md](references/data-binding-guide.md) | IP sources, field mapping, conditional rendering |

---

## CRITICAL: Orchestration Order

FlexCards sit at the presentation layer of the OmniStudio stack. Ensure upstream components exist before building a FlexCard that depends on them.

```
analyzing-omnistudio-dependencies → building-omnistudio-datamapper → building-omnistudio-integration-procedure → building-omnistudio-omniscript → building-omnistudio-flexcard (you are here)
```

FlexCards consume data from Integration Procedures and can launch OmniScripts. Build the data layer first, then the presentation layer.

---

## Key Insights

| Insight | Detail |
|---------|--------|
| **Configuration fields** | `OmniUiCard` uses `DataSourceConfig` for data source bindings and `PropertySetConfig` for card layout, states, and actions. There is NO `Definition` field on `OmniUiCard` in Core namespace. |
| **Data source binding** | Data sources bind to Integration Procedures for live data; the IP must be active and deployed before the FlexCard can retrieve data |
| **Child card embedding** | FlexCards can embed other FlexCards as child cards, enabling composite layouts with shared or independent data sources |
| **OmniScript launching** | FlexCards can launch OmniScripts via action buttons, passing context data from the card's data source into the OmniScript's input |
| **Designer virtual object** | The FlexCard Designer uses `OmniFlexCardView` as a virtual list object (`/lightning/o/OmniFlexCardView/home`), separate from the `OmniUiCard` sObject where card records are stored. Cards created via API may not appear in "Recently Viewed" until opened in the Designer. |

---

## Workflow (5-Phase Pattern)

### Phase 1: Requirements Gathering

Before building, clarify these with the stakeholder:

| Question | Why It Matters |
|----------|---------------|
| What is the card's purpose? | Determines layout type and data density |
| Which data sources are needed? | Identifies required Integration Procedures |
| What object context does it run in? | Determines record-level vs. list-level display |
| What actions should the card expose? | Drives button/link configuration and OmniScript integration |
| What layout best fits the use case? | Single card, list, tabbed, or flyout |
| Are there conditional display rules? | Fields or sections that appear/hide based on data values |

### Phase 2: Design & Layout

Read `references/best-practices.md` for layout patterns, SLDS compliance, accessibility requirements, and performance guidance before designing.

#### Card Layout Options

| Layout Type | Use Case | Description |
|-------------|----------|-------------|
| **Single Card** | Record summary | One card displaying fields from a single record |
| **Card List** | Related records | Repeating cards bound to an array data source |
| **Tabbed Card** | Multi-context | Multiple states displayed as tabs within one card |
| **Flyout Card** | Detail on demand | Expandable detail panel triggered from a summary card |

#### Data Source Configuration

Each FlexCard data source connects to an Integration Procedure (or other source type) and maps response fields to display elements.

```
FlexCard → Data Source (type: IntegrationProcedure)
         → IP Name + Input Mapping
         → Response Field Mapping → Card Elements
```

- Map IP response fields to card display elements using `{datasource.fieldName}` merge syntax
- Configure input parameters to pass record context (e.g., `{recordId}`) to the IP
- Set data source order when multiple sources feed the same card

#### Action Button Design

| Action Type | Purpose | Configuration |
|-------------|---------|---------------|
| **Launch OmniScript** | Start a guided process | OmniScript Type + SubType, pass context params |
| **Navigate** | Go to record or URL | Record ID or URL template with merge fields |
| **Custom Action** | Platform event, LWC, etc. | Custom action handler with payload mapping |

#### Conditional Visibility

- Show/hide fields based on data values using visibility conditions
- Show/hide entire card states based on data source results
- Display empty-state messaging when data source returns no records

### Phase 3: Generation & Validation

Read `references/data-binding-guide.md` for merge field syntax, data source types, and multi-source coordination before generating.
Read `references/scoring-rubric.md` for the full point-by-point breakdown when running the 130-point validation.

1. Generate the FlexCard definition JSON
2. Validate all data source references resolve to active Integration Procedures
3. Run the 130-point scoring rubric (see Scoring section below)
4. Verify merge field syntax matches IP response structure
5. Check accessibility attributes on all interactive elements

### Phase 4: Deployment

1. Ensure all upstream Integration Procedures are deployed and active
2. Run a dry-run check: use the `deploying-metadata` skill with `--dry-run` before committing
3. Deploy the FlexCard metadata (`OmniUiCard`) — `sf project deploy start` is safe to re-run; it upserts existing records
4. Activate the FlexCard in the target org
5. Embed the FlexCard in the target Lightning page, OmniScript, or parent FlexCard
6. **If deploy fails**: check error output for specific cause — common issues: upstream IP not deployed (`Cannot find OmniIntegrationProcedure`), missing namespace prefix (`Entity not found`), or FlexCard still in Draft status (activate before retrieving)

### Phase 5: Testing

Test each FlexCard against multiple data scenarios:

| Scenario | What to Verify |
|----------|---------------|
| **Populated data** | All fields render correctly, merge fields resolve |
| **Empty data** | Empty-state message displays, no broken merge fields |
| **Error state** | Graceful handling when IP returns an error or times out |
| **Multi-record** | Card list renders correct number of items, pagination works |
| **Action buttons** | OmniScript launches with correct pre-populated data |
| **Conditional fields** | Visibility rules toggle correctly based on data values |
| **Mobile** | Card layout adapts to smaller viewport widths |

---

## Generation Guardrails

Avoid these patterns when generating FlexCard definitions:

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|---------------|-----------------|
| Referencing non-existent IP data sources | Card fails to load data at runtime | Verify IP exists and is active before binding |
| Hardcoded colors in styles | Breaks SLDS theming and dark mode | Use SLDS design tokens and CSS custom properties |
| Missing accessibility attributes | Fails WCAG compliance | Add `aria-label`, `role`, and keyboard handlers |
| Excessive nested child cards | Performance degrades with deep nesting | Limit to 2 levels of nesting; flatten where possible |
| Ignoring empty states | Broken UI when data source returns no records | Configure explicit empty-state messaging |
| Hardcoded record IDs | Card breaks across environments | Use merge fields and context-driven parameters |

---

## Scoring Rubric (130 Points)

All FlexCards are validated against 7 categories. **Thresholds**: ✅ 90+ (Deploy) | ⚠️ 67-89 (Review) | ❌ <67 (Block - fix required)

| Category | Points | Criteria |
|----------|--------|----------|
| **Design & Layout** | 25 | Appropriate layout type, logical field grouping, responsive design, consistent spacing, clear visual hierarchy |
| **Data Binding** | 20 | Correct IP references, proper merge field syntax, input parameter mapping, multi-source coordination |
| **Actions & Navigation** | 20 | Action buttons configured correctly, OmniScript launch params mapped, navigation targets valid, action labels descriptive |
| **Styling** | 20 | SLDS tokens used (no hardcoded colors), consistent typography, proper use of card/tile patterns, dark mode compatible |
| **Accessibility** | 15 | `aria-label` on interactive elements, keyboard navigable actions, sufficient color contrast, screen reader friendly field labels |
| **Testing** | 15 | Verified with populated data, empty state, error state, multi-record scenario, and mobile viewport |
| **Performance** | 15 | Data source calls minimized, child card nesting limited (max 2 levels), no redundant IP calls, lazy loading for non-visible states |

Read `references/scoring-rubric.md` for the full per-criterion breakdown of all 7 categories.

---

## CLI Commands

Read `scripts/flexcard-commands.sh` for all FlexCard CLI commands (query, retrieve, deploy). Replace `<org>` with your org alias and `<Name>` with the FlexCard API name.

---

## Data Source Binding

### FlexCard Data Source Configuration

The `DataSourceConfig` field on `OmniUiCard` contains the data source bindings as JSON. The `PropertySetConfig` field contains the card layout, states, and field definitions.

> **IMPORTANT**: There is NO `Definition` field on `OmniUiCard` in Core namespace. Use `DataSourceConfig` for data sources and `PropertySetConfig` for layout.

Read `assets/omni-ui-card.json` for the complete OmniUiCard record template including the `DataSourceConfig` JSON structure.

### Data Source Types

| Type | `dataSource.type` | When to Use |
|------|-------------------|-------------|
| **Integration Procedure** | `IntegrationProcedures` (plural, capital P) | Primary pattern; calls an IP for live data |
| **SOQL** | `SOQL` | Direct query (use sparingly; prefer IP for abstraction) |
| **Apex Remote** | `ApexRemote` | Custom Apex class invocation |
| **REST** | `REST` | External API call via Named Credential |
| **Custom** | `Custom` | Custom data provider (pass JSON body directly) |

### Field Mapping from IP Response

Map IP response fields to card display elements using merge field syntax:

```
IP Response:                    FlexCard Merge Field:
─────────────                   ─────────────────────
{ "Name": "Acme Corp" }   →    {Name}
{ "Account": {            →    {Account.Name}
    "Name": "Acme Corp"
  }
}
{ "records": [             →    {records[0].Name}  (single)
    { "Name": "Acme" }          or iterate with Card List layout
  ]
}
```

### Input Parameter Mapping

Pass context from the hosting page into the IP data source:

| Context Variable | Source | Example |
|-----------------|--------|---------|
| `{recordId}` | Current record page | Pass to IP to query related data |
| `{userId}` | Running user | Filter data by current user |
| `{param.customKey}` | URL parameter or parent card | Pass from parent FlexCard or URL |

---

## Cross-Skill Integration

| Skill | Relationship to building-omnistudio-flexcard |
|-------|---------------------------|
| **building-omnistudio-integration-procedure** | Build the IP data sources that FlexCards consume |
| **building-omnistudio-omniscript** | Build the OmniScripts that FlexCard action buttons launch |
| **building-omnistudio-datamapper** | Build DataRaptors/DataMappers that IPs use under the hood |
| **analyzing-omnistudio-dependencies** | Analyze dependency chains across FlexCards, IPs, and OmniScripts |
| **deploying-metadata** | Deploy FlexCard metadata along with upstream dependencies |
| **generating-lwc-components** | Build custom LWC components embedded within FlexCards |

---

## Gotchas

| Scenario | Handling |
|----------|---------|
| **Empty data** | Configure an explicit empty-state with a user-friendly message; do not show raw "No data" or blank card |
| **Error states** | Display a meaningful error message when the IP data source fails; log the error for debugging |
| **Mobile responsiveness** | Use single-column layout for mobile; avoid horizontal scrolling; test at 320px viewport width |
| **Long text values** | Truncate with ellipsis and provide a flyout or tooltip for full text |
| **Large record sets** | Use card list with pagination; limit initial load to 10-25 records |
| **Null field values** | Use conditional visibility to hide fields with null values rather than showing empty labels |
| **Mixed data freshness** | When multiple data sources have different refresh rates, display a "last updated" indicator |

---

## FlexCard vs LWC Decision Guide

| Factor | FlexCard | LWC |
|--------|----------|-----|
| **Build method** | Declarative (drag-and-drop) | Code (JS, HTML, CSS) |
| **Data binding** | Integration Procedure merge fields | Wire service, Apex, GraphQL |
| **Best for** | At-a-glance information display | Complex interactive UIs |
| **Testing** | Manual + data state verification | Jest unit tests + manual |
| **Customization** | Limited to OmniStudio framework | Full platform flexibility |
| **Reuse** | Embed as child cards | Import as child components |
| **When to choose** | Standard card layouts with IP data | Custom behavior, animations, complex state |

---

## Dependencies

**Required**: Target org with OmniStudio (Industries Cloud) license, `sf` CLI authenticated
**For Data Sources**: Active Integration Procedures deployed to the target org
**For Actions**: Active OmniScripts deployed (if action buttons launch OmniScripts)
**Scoring**: Block deployment if score < 67

**Idempotency**: `sf project deploy start` upserts metadata — safe to re-run without creating duplicates. Query first to confirm current state: see `scripts/flexcard-commands.sh`.

**Namespace handling**: In managed-package orgs, the metadata type may be prefixed (e.g., `omnistudio__OmniUiCard`). Check `sfdx-project.json` for the namespace. See `scripts/flexcard-commands.sh` for the namespaced deploy command.

**Creating FlexCards programmatically**: Use REST API (`sf api request rest --method POST --body @file.json`). Required fields: `Name`, `VersionNumber`, `OmniUiCardType` (e.g., `Child`). Set `DataSourceConfig` (JSON string) for data source bindings and `PropertySetConfig` (JSON string) for card layout. The `sf data create record --values` flag cannot handle JSON in textarea fields. Activate by updating `IsActive=true` after creation.

---

## Output Expectations

Deliverables produced by this skill:

- **FlexCard JSON definition** (`assets/omni-ui-card.json` template) — `OmniUiCard` record ready for REST API creation or metadata deployment
- **Data source binding block** — `DataSourceConfig` JSON mapping Integration Procedure inputs and response fields to card elements
- **Card layout config** — `PropertySetConfig` JSON defining card states, field display, conditional visibility, and action buttons
- **Validation report** — 130-point score across 7 categories with deploy/review/block threshold result
- **Deployment checklist** — confirms upstream IPs are active, FlexCard is activated, and embedded in target Lightning page or parent FlexCard

---

## External References

- **OmniStudio FlexCards** (Trailhead) — Official learning module for FlexCard fundamentals and guided setup
- **OmniStudio Developer Guide** — Technical reference for FlexCard metadata, data source configuration, and component properties
- **Salesforce Industries Documentation** — FlexCard configuration guide covering layout, states, and actions

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/omni-ui-card.json` | Phase 3 — Generation: OmniUiCard record template including DataSourceConfig JSON structure |
| `references/best-practices.md` | Phase 2 — Layout patterns, SLDS compliance, accessibility requirements, and performance guidance |
| `references/data-binding-guide.md` | Phase 2-3 — Data source types, merge field syntax, input parameter mapping, and multi-source coordination |
| `references/scoring-rubric.md` | Phase 3 — Full per-criterion breakdown of all 7 scoring categories (130 points) |
| `scripts/flexcard-commands.sh` | Phase 4 — All CLI commands for querying, retrieving, and deploying FlexCard metadata |

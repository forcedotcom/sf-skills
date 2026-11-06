# Aura Experience Site UI review

Read this reference during Phase 4a after selecting an entry with `status: "ready"`.

## Site source

Use the selected inventory entry's `uiRoots` and metadata evidence. Inspect its `experiences/<bundle>/routes` and `views` JSON files to identify rendered journeys and top-level component references.

The inventory identifies supported Aura view structure from `forceCommunity:` or `siteforce:` component references, or a view-referenced local Aura component. Legacy LWR view components in `community_builder:`, `community_layout:`, or `community_login:` are unsupported, as are DigitalExperienceBundle and UI-bundle source.

## Component and server-call tracing

Aura Experience Sites can use both LWC and Aura components.

Traverse standard layout and component nodes, including `forceCommunity:` and `siteforce:` references, through their regions and child components. Resolve referenced custom components from `lwc/` and `aura/` across the project's package directories, then follow their component composition, handlers, and data access. Skip unrelated components.

Review every UI flow, including initial data loading, searches, detail views, forms, and multi-step actions. In LWCs, inspect `@wire` adapters, reactive parameters, and imperative calls. In Aura components, follow markup event handlers, controllers, helpers, and server actions. Consult Salesforce documentation for unfamiliar adapters.

Trace every server operation and record its inputs, outputs, filters, and behavior in Phase 4a's UI operation inventory. Include simple data queries and writes without filtering by complexity.

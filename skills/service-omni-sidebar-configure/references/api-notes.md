# API notes — service-omni-sidebar-configure

## The setting

The Omni-Channel **sidebar** (the pinned Omni utility region docked to the side of a console
workspace) is controlled by a single boolean on the `CustomApplication` metadata:

```xml
<isOmniPinnedViewEnabled>true</isOmniPinnedViewEnabled>
```

- It is a **per-app** setting on a Lightning **console** app — not an org-level `OmniChannelSettings`
  flag. Enabling Omni-Channel org-wide (`service-omni-base-settings-configure`) is a prerequisite,
  but does not pin the sidebar on any app.
- When absent, the platform treats it as `false`. This skill therefore inserts the element when it
  is missing rather than assuming a default.

## XSD ordering

`CustomApplication` enforces element order. The `is*` booleans
(`isNavAutoTempTabsDisabled`, `isNavPersonalizationDisabled`, `isNavTabPersistenceDisabled`,
`isOmniPinnedViewEnabled`) precede `<label>`. The skill inserts `<isOmniPinnedViewEnabled>`
immediately before the first top-level `<label>`, which keeps the payload schema-valid whether or
not the other booleans are present. If a future release reorders the schema and the deploy fails
with an XSD-order error, adjust the insertion anchor here.

## Detecting console apps (auto-detect path)

When no app name is supplied, candidates come from the Tooling API:

```sql
SELECT DeveloperName, Label FROM AppDefinition WHERE UiType='Lightning' AND NavType='Console'
```

`AppDefinition.DeveloperName` matches the `CustomApplication` DeveloperName used for retrieve/deploy
for custom apps. The skill adopts a target automatically **only** when exactly one row is returned;
zero or many → `blocked` so it can never pin the wrong app. Standard apps surfaced by this query are
generally not deployable as `CustomApplication`; if one is named explicitly the retrieve returns no
`.app-meta.xml` and the skill blocks with a clear message.

## Retrieve / deploy

- Retrieve and deploy use explicit `--metadata "CustomApplication:<name>"` (never `--source-dir`) so
  no sibling metadata can piggyback.
- The deploy runs `--async` and polls `sf project deploy report` to a terminal state — a synchronous
  watched deploy can raise `ClientTimeoutError` under org load even when the server-side deploy
  succeeds (same false-red class handled by the other Omni leaves).
- Metadata deploys are atomic, so a failed deploy leaves the app unchanged; the skill then reports
  `blocked` and never claims partial success.
- Success is confirmed by a **re-retrieve** that reads `isOmniPinnedViewEnabled` back as `true`; a
  green deploy that does not round-trip the flag is reported `blocked`, not `enabled`.

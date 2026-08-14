# Search feature

Explains how this search feature is structured and how to customize it — which
files own configuration, how sObject and CMS sources differ, how CMS search is
wired end to end, and how to mount the UI. Read it before changing anything
under this directory.

## 1. What this feature is / where sources live

- `config.json` (co-located here) declares `sources: SourceConfig[]` — a
  discriminated union on `kind` — plus an optional `pagination` block. The
  shipped default has 3 `"sobject"` sources (`accounts`, `contacts`,
  `opportunities`) and one `"cms"` source (`key: "content"`).
- `loadConfig.ts` re-exports `config.json`, typed as `SearchConfig`. For a
  pure config change (add/remove a source, tweak fields), **edit
  `config.json` directly — no code changes required.**
- `types.ts` is the source of truth for `SourceConfig` (`SObjectSourceConfig |
CmsSourceConfig`) and `SearchConfig`.

## 2. Choosing sObject vs CMS per source

- **sObject source** (`kind: "sobject"`): requires `objectName`, `label`,
  `searchableFields`, `displayFields`. Optional: `labelSingular`, `idField`
  (defaults `"Id"`), `routePattern`, `filterBy`, `sortBy`, `defaultSort`,
  `whereTypeName`/`orderByTypeName`. Queried via the `uiapi` GraphQL bridge
  (`adapters/sobject`).
- **CMS source** (`kind: "cms"`): deliberately minimal — only `kind`, `key`,
  `label`, and optionally `labelSingular`/`routePattern`
  (`adapters/cms/types.ts`, `CmsSourceConfig`). No `channelId`, no content
  types, no `displayFields` — all of that is resolved at runtime. Routed via
  `adapters/registry.ts` to `cmsAdapter` (`adapters/cms/index.ts`).
- `adapters/registry.ts` maps `kind` → adapter (`sobject → sObjectAdapter`,
  `cms → cmsAdapter`). Adding a new backend `kind` means registering an
  adapter here plus extending the `SourceConfig` union in `types.ts` — out of
  scope for typical customization; most tasks only touch `config.json`.

## 3. Enabling sObject search

sObject sources work out of the box — no runtime id resolution and no gating.
They query the org's `uiapi` GraphQL bridge through `adapters/sobject`.

- **Declare the source** in `config.json`: `kind: "sobject"`, `objectName` (the
  API name, e.g. `"Account"`), `label`, `searchableFields` (the fields the
  free-text term matches against), and `displayFields` (what each result row
  shows). A `displayFields` entry is a plain field name (`"Name"`), a
  `{ name, raw }` (use the raw value, skip display formatting), or a
  `{ name, subfields }` for a parent relationship
  (`{ "name": "Owner", "subfields": ["Name"] }`).
- **Optional per-source knobs:** `labelSingular`, `idField` (defaults `"Id"`),
  `filterBy` (facets — `picklist` / `numeric` / `daterange`), `sortBy` +
  `defaultSort`, and `routePattern` (see §6). `whereTypeName` / `orderByTypeName`
  override the generated GraphQL input type names for objects whose where/orderBy
  types don't follow the default `<Object>` naming.
- **Query construction:** `buildSearchQuery` (`api/buildSearchQuery.ts`)
  assembles the GraphQL from the source config, `buildOrderBy` builds the sort
  clause, and picklist filter values come from `useDistinctValues` /
  `fetchDistinctValues`. The whole path runs through the platform data SDK — no
  enablement step beyond declaring the source.
- **FLS caveat:** a field the running user can't read is silently dropped by the
  platform, so an sObject source that "returns nothing" usually means the app's
  permission set is missing field access, not a config error.

## 4. Enabling CMS search

This is the part most likely to be missed — read all of it before assuming
CMS search "just works" after adding a `cms` source to `config.json`.

- **API version requirement.** Search on CMS content is supported only when the
  bundle is built against **API version 68.0 or greater**. The build-time
  version (`__SF_API_VERSION__`, injected from the resolved org's API version)
  is the version every SDK request is actually issued at, so it is the gate.
- **No static id in config.** The UIBundle id is resolved at runtime by
  `adapters/cms/searchChannel.ts::getUIBundleId()`, which calls
  `@salesforce/platform-sdk`'s `getCurrentApp()` and reads
  `identity.bundleId` — the UIBundle **record id** (a `9YE...` id). This is
  only populated when running on the WebApp surface (the runtime injects
  `SFDC_ENV`, per `packages/sdk/platform-sdk/src/core/app.ts`). Locally, or on
  any non-WebApp surface, `bundleId` is `undefined`/`""`, and the CMS source
  is skipped with no error — by design.
- **The gate:** `hooks/useSearch.ts` resolves `getUIBundleId()` **and**
  `getOrgSupportsCmsSearch()` once per fetch and, for the CMS source, includes
  the CMS request only when BOTH pass: `isConfiguredUIBundleId(uiBundleId)`
  (`adapters/cms/searchChannel.ts`) and the build API-version check (above).
  `isConfiguredUIBundleId` validates the `9YE` shape
  (`UI_BUNDLE_ID_PATTERN = /^9YE[a-zA-Z0-9]{12,15}$/`) — an empty or malformed
  id, or a build below v68, causes the CMS source to be silently dropped from
  the request (no per-source error banner), not sent to the server.
- **CMS UI surfaces hide on a gated build too.** When CMS search is skipped for
  the build-version reason, its scope entry and result section would only ever
  be empty, so both are hidden using the SAME gate as the fetch skip —
  `isCmsSearchSupported()` (the synchronous core of `getOrgSupportsCmsSearch()`,
  in `adapters/cms/api/orgApiVersionService.ts`). Two minimal guards read it:
  `ScopeSelector` skips the CMS `<SelectItem>` ("Content") and `SearchResults`
  skips the CMS `SourceSection` ("Content" heading + empty state). Both are safe
  during render because the gate reads only the build-time API version. (The
  runtime `bundleId` gate above is _not_ build-constant — it can differ per
  surface — so it stays a per-fetch skip and does not hide the UI; a CMS source
  skipped only for a missing `bundleId` still shows its section, empty.)
- **The query field:** `adapters/cms/cmsQueryFragment.ts` sends the resolved
  `$UIBundleId` into `searchIdentifiers.uibundleIds` (NOT `channelIds`) on
  `managed_content.search.searchContentInChannels`. Content-type filtering
  (`$cmsContentTypeFQNs`) is omitted on the bootstrap call and supplied once
  discovery completes.
  - **Why `uibundleIds` (evidence from core).** `ContentSearchIdentifiersInput`
    has three id-space fields — `channelIds` (`0ap` Managed Content channel ids),
    `siteIds`, and `uibundleIds` — and the `9YE` UIBundle **record id** belongs
    only in `uibundleIds`. In core (`core-2206/core-266-public`): the schema
    `ui-services-private/.../graphql-schemas/mcontent-search.graphqls` documents
    `uibundleIds` as _"Each UI bundle ID is resolved to its associated Managed
    Content channel(s)"_; the resolver
    `mcontent-impl/.../ManagedContentGraphQLSearchServiceImpl.resolveChannelIdsFromSitesAndUiBundles()`
    resolves each id via `getManagedContentChannelsByTarget(uibundleId)` (the id
    is the channel's **TargetEntityId**, i.e. a UIBundle record id); the UDD
    `lwr-udd/.../UIBundle.entity.xml` sets `keyPrefix="9YE"`; and the unit test
    `ManagedContentGraphQLSearchServiceImplTest.testUiBundleId_resolvesToChannelIds_andIsSearched()`
    passes a `9YE…` id into `uibundleIds` and asserts it resolves (W-23364628).
    `channelIds` values are validated as channel/site ids and never run through
    the target-entity resolver, so a `9YE` id sent there fails with
    `"9YE… isn't a valid managed content channel ID or a site ID"` — the exact
    error this wiring fixes. (Server-side, resolution of `uibundleIds`/`siteIds`
    is gated by the core feature flag `isAllowTargetEntityIdsEnabled()`.)
- **Content-type discovery:** after the first CMS result returns,
  `adapters/cms/channelResolver.ts::resolveChannelId()` extracts the `0ap`
  managed-content-channel id from
  `nodes[0].managedContentChannelDeliveryDetails[0].managedContentChannelDetails.id`.
  `adapters/cms/hooks/useSearchableContentTypes.ts` (session-cached) then
  fetches `GET /connect/cms/channels/{channelId}/searchable-content-types` to
  populate the scope dropdown's per-content-type entries. Note: this `0ap` id
  is a _different_ id space from the `9YE` UIBundle id above — don't confuse
  the two when debugging.
- **Seeding content:** the resolved `bundleId` only surfaces content published
  to the UIBundle's own channel (WebApp type), so CMS content must be published
  there — not to the Experience Site COMMUNITY channel. Content published to
  the wrong channel returns zero results even when the id/gate/query wiring is
  correct, so empty CMS results with everything else in place usually points at
  the publishing target rather than the code.
- **Mounting:** add a `{ "kind": "cms", "key": "...", "label": "..." }` entry
  to `config.sources` (in `config.json`, or a custom `SearchConfig` object at
  runtime), then render `<Search config={config} />` somewhere routed — see
  the next section.

## 5. Mounting `<Search>` — the routing caveat

- `GlobalSearchBox` (`components/GlobalSearchBox.tsx`) is a **pure
  launcher** — a text input + button that calls `navigate('/search?q=...')`
  on submit. **It renders no results itself.**
- **`GlobalSearchBox` only routes to `/search`; you must mount `<Search>` at
  that route for results to render.** In this template, `routes.tsx` does
  exactly that: `path: "search"` renders `<GlobalSearch config={config} .../>`
  (`GlobalSearch` is `Search` aliased on import). If an app drops in
  `GlobalSearchBox` without also mounting `<Search>` (or a custom results UI
  built on `useSearch`) at the route it navigates to, searches will appear to
  do nothing.
- `<Search>` itself (`components/Search.tsx`) is the batteries-included
  drop-in. For narrower customizations (e.g. a single-object search page),
  see its prop JSDoc for `restrictTo` (lock to one source), `renderResult` /
  `renderFilters` (per-source overrides), and `showScopeSelector`.

## 6. Adding a detail page (object detail / CMS content detail)

**By default, result cards are NOT clickable** — the feature renders each row as
plain (non-linked) text (see the final `return <div>…` branch in
`DefaultResultRow.tsx` / `CmsResultRow.tsx`). Making a card clickable is a
two-part change, and **both parts are required** — one without the other either
does nothing or 404s:

1. **In this feature** (`config.json`): give the source a `routePattern`. This is
   the _only_ thing that turns the row into a `<Link>`. Without it the row stays
   non-clickable no matter what routes the app defines.
2. **In the app** (`src/routes.tsx`): the detail page must actually exist and be
   registered at a matching dynamic route. The feature only builds the href
   (e.g. `/accounts/001…`); it does not own any route. If that route isn't in the
   app's `routes.tsx`, the (now-clickable) card navigates to a dead URL and 404s.

So: `routePattern` present **and** a matching detail route/page in the app →
clickable card that opens a detail page. `routePattern` absent → non-clickable
card (the default). `routePattern` present but no app route → clickable card that
404s.

- **How the link is built:** `routePattern` is a path template with `:token`
  placeholders resolved per result.
  - **sObject rows** (`components/results/DefaultResultRow.tsx`,
    `resolveRoute(routePattern, node, idField)`): `:fieldName` tokens are
    substituted from the record's field values, and a bare `:id` maps to the
    source's `idField` (default `Id`). The shipped `accounts` source uses
    `"/accounts/:id"`.
  - **CMS rows** (`components/results/CmsResultRow.tsx`): tokens are `:id`
    (the `managedContentId`) and `:key`; when no `routePattern` is set it falls
    back to `/content/:contentType/:id`.
- **Authoring the app-side route + page** (part 2 above): register the matching
  dynamic route in the app's `routes.tsx` (e.g. `path: "accounts/:id"` /
  `path: "content/:contentType/:id"`). That route's component reads the route
  param (`useParams`) and fetches the single record/content item — sObject
  detail: fetch the one record by id via the platform data SDK (see the
  `experience-ui-bundle-salesforce-data-access` skill — do not hand-roll
  `fetch`); CMS detail: fetch the content item by `managedContentId` through the
  CMS delivery API.
- **Generating the page:** whichever kind of detail page you need, nothing inside
  this search feature changes beyond setting `routePattern` — the page and route
  live in the app, not in this directory. Pick the skill by source type:
  - **sObject object-detail page** — a normal routed page; generate it with the
    `experience-ui-bundle-frontend-generate` skill (its page types include "detail
    view"; record data is fetched via the platform Data SDK per the
    `experience-ui-bundle-salesforce-data-access` skill).
  - **CMS content-detail page** — generate it with the
    `experience-cms-content-render` skill. That skill owns CMS content _fetch +
    render_ (the delivery API, `contentKey`/`contentType`, RichText, and image
    resolution) and **takes precedence** over `experience-ui-bundle-frontend-generate`
    for the rendering portion — the UI skill owns only the page/layout shell. Its
    Detail Page branch writes `src/pages/<type>/<PageName>.tsx` and inserts the
    route, so the app gets both the page and the matching route wired for you. (It
    is scoped to _rendering existing_ content — use this search feature, not that
    skill, for the search itself.)

## 7. Config knobs reference

| Knob                                      | Values / notes                                                                                                                                                                                                             |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pagination.mode`                         | `"per-source"` (default; one section per source) vs `"merged"` (one combined grid, single global pager) — `types.ts`                                                                                                       |
| `pagination.mergeOrder`                   | `"sequential" \| "interleaved" \| "proportional"` — merged mode only                                                                                                                                                       |
| `pagination.pageSize` / `pageSizeOptions` | shared across every source, every scope                                                                                                                                                                                    |
| Per-sobject-source                        | `objectName`, `label`/`labelSingular`, `idField`, `routePattern`, `searchableFields`, `displayFields` (`string \| {name,raw} \| {name,subfields}`), `filterBy`, `sortBy`, `defaultSort`, `whereTypeName`/`orderByTypeName` |
| Per-cms-source                            | `key`, `label`, `labelSingular?`, `routePattern?` — nothing else, by design                                                                                                                                                |
| `MIN_QUERY_LENGTH`                        | `constants.ts`, currently `3`. Both backends reject shorter terms server-side; gated client-side in `useSearch.ts` and `GlobalSearchBox.tsx` so the UI never shows a spurious failure for a too-short query                |

## 8. Public API pointers

Import from the barrel (`index.ts`) rather than reaching into internals. The
main extension points, grouped by concern:

- **Core (both source types):** `useSearch` — the hook (state, fetch,
  pagination) behind `<Search>`; `runSearch` — the underlying fetch;
  `buildSearchQuery` — assembles the query payload; `getAdapter` — resolves a
  source `kind` to its adapter; `config` — the loaded `SearchConfig`.
- **sObject sources:** `useDistinctValues` / `fetchDistinctValues` — picklist
  filter values; `buildOrderBy` — sort clause construction; the filter inputs
  (`TextFilter`, `SelectFilter`, `MultiSelectFilter`, `NumericRangeFilter`,
  `BooleanFilter`, `DateRangeFilter`) and `DefaultResultRow` for rendering.
- **CMS source:** `cmsAdapter`; `useSearchableContentTypes` — content-type
  discovery; `isValidCmsFqn` / `formatContentTypeLabel` — content-type FQN
  helpers; `CmsResultRow` for rendering.
- **Types:** `SearchConfig`, `SourceConfig`, `SObjectSourceConfig`,
  `CmsSourceConfig`, `SourceAdapter`, `SearchHandle`, and related runtime types.

See `index.ts` for the full exported surface (all components, filter inputs,
utils) — this list is intentionally short.

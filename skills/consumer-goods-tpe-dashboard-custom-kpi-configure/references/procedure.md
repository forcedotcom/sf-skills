# Full procedure

Implements Salesforce Help's "Customize Trade Promotion Effectiveness Analytics Dashboards" —
Customization Scenario 1 ("Use Custom KPIs with Standard Dashboards") — headlessly, driven entirely
by `sf` CLI + REST against an already-authenticated org.

## Namespace detection (run once, before Phase 0)

Same canonical procedure as sibling skills — never assume a namespace:

1. ```bash
   sf package installed list --target-org <username> --json
   ```
   Find the entry with `SubscriberPackageName == "Consumer Goods Cloud"`. If found, `NS` = its
   `SubscriberPackageNamespace`.
2. If no package is found inform the user and stop the process.

The REST paths used throughout this skill are all standard platform paths under
`/services/data/...` — **never namespaced**, regardless of `NS`. Namespace detection is still run
for consistency with sibling skills and in case a future phase needs `NS_FIELD`; do not apply `NS`
to any `/services/data/...` path below.

## Phase 0 — Preflight & discovery

1. Verify org connectivity and run namespace detection.
2. **API version is pinned to `v67.0` for every `/services/data/...` call below — per standing
   instruction, do not resolve it from the org's own `apiVersion`.** (Historical note: `v64.0` was
   found to return `DOWNGRADE_VERSION_ERROR` on visualization GETs — so if `v67.0` ever regresses
   similarly in a given org, surface the error rather than silently falling back to a different
   version.)
3. **Resolve real artifact ids by walking the installed app's asset list — never hardcode an id or
   api-name across orgs.**
   ```bash
   node ./scripts/sf-rest.js --target-org <username> \
     --path "/services/data/<apiVersion>/app-framework/apps?templateSourceId=sfdc_internal__Trade_Promotion_Effectiveness"
   ```
   Not present, or no entry with `applicationStatus` in `SuccessStatus`/`SuccessWithWarningsStatus`
   ⇒ **block**, point the user to `consumer-goods-tpe-dashboard-configure` to install prerequisites
   first.
   **If more than one entry matches** — never silently pick the first, the newest, or any other
   guessed tie-break. List every matching candidate's `id`, `name`/`label`, and `createdDate` and
   **stop and ask the user which app install to target**. Only continue automatically when exactly
   one `SuccessStatus`/`SuccessWithWarningsStatus` entry matches. Otherwise take that app's `id` and
   GET its asset list:
   ```bash
   node ./scripts/sf-rest.js --target-org <username> \
     --path "/services/data/<apiVersion>/app-framework/apps/<appId>/assets"
   ```
   From the returned `assets[]`, resolve by `type`/`templateAssetSourceName`:
   - `type: "SemanticModel"`, `templateAssetSourceName` starting with `Extended_Trade_Promotion_Management` → the Extended TPM Analytics model's `assetIdOrName`.
   - `type: "Dashboard"`, `templateAssetSourceName` == `PromotionAnalysis` / `TacticAnalysis` → each base dashboard's `assetIdOrName`.
   - `type: "Visualization"` entries → every base visualization's `assetIdOrName`; identify which
     ones the two dashboards actually use in step 5 below.
   If the Extended model or either dashboard asset is missing ⇒ **block**, point to
   `consumer-goods-tpe-dashboard-configure`.
4. **GET the Extended model — the whole model in one call, no working single-parameter GET
   confirmed:**
   ```bash
   node ./scripts/sf-rest.js --target-org <username> \
     --path "/services/data/<apiVersion>/ssot/semantic/models/<extendedModelId>"
   ```
   Index into `semanticParameters[]` and `semanticCalculatedMeasurements[]` by `apiName` to find all
   5 slots' parameter + calculated-measurement pairs — see `references/payload-shapes.md` for the
   confirmed apiNames and full JSON shape of both artifact types.
5. GET each base dashboard selected during Inputs collection, and every base visualization its
   `widgets[].source` (type `"visualization"`) points at:
   ```bash
   node ./scripts/sf-rest.js --target-org <username> \
     --path "/services/data/<apiVersion>/tableau/dashboards/<baseDashboardId>"
   node ./scripts/sf-rest.js --target-org <username> \
     --path "/services/data/<apiVersion>/tableau/visualizations/<baseVizId>"
   ```
6. Field shapes for parameters, calculated measurements, visualizations, and dashboard widgets are
   already documented in `references/payload-shapes.md` — use that file directly, no need to
   re-derive it from this org's live response. Only revisit it if a future package/template
   version changes these shapes.
7. Report Phase 0 pass/blocked, including the resolved apiVersion, model id, dashboard ids, and
   visualization ids.

## Phase 1 — Resolve the 5-slot plan

For each of the 5 known slots (Promotion Measure 1-3, Tactic Measure 1-2), using the real base
parameter + calculated-measurement JSON captured in Phase 0:

- If the customer supplied an override (always a full `{measureCode, displayName}` array collected
  during Inputs — a single-pair answer is still an array of length 1):
  - The new parameter = deep copy of the base parameter with `apiName` suffixed, `allowedValues`
    **replaced entirely** by the customer's array (each entry mapped to `{displayName, value:
    measureCode}` — base entries are discarded, not merged), and `defaultValue` set to the
    customer-specified default, or the first entry's `displayName` if none was specified. This is
    REPLACE mode (see Phases 2-4 below) — the customer's list is the whole menu, not a patch to it.
  - The new calculated measurement = deep copy of the base measurement with `apiName` suffixed and
    `expression` rewritten to reference the new parameter's suffixed `apiName` in place of the base
    one (`[Parameters].[<baseParamApiName>]` → `[Parameters].[<newParamApiName>]`).
- If no override was supplied: both the new parameter and new calculated measurement are exact
  deep copies of the base ones, with only `apiName` suffixed (and the measurement's `expression`
  still repointed at the sibling clone's new parameter `apiName`).

Print the resolved plan — slot → new parameter apiName → new measurement apiName → source
(override / base-copy) → resolved KPI (existing-entry / newly-appended) → values — and get explicit
confirmation before Phase 2 writes anything.

## Phases 2-4 — Clone parameters, measurements, visualizations, and dashboards

**Confirmed live and implemented by `scripts/clone-tpe-dashboards.js`** — a deterministic Node
driver that runs Phases 2-4 in one process. Prefer running it over hand-rolling the individual
`sf-rest.js` calls below; use the manual calls only for one-off debugging or to inspect a single
artifact.

```bash
node ./scripts/clone-tpe-dashboards.js --target-org <username> --suffix <Suffix> \
  [--overrides '{"Promotion_Measure_1":{"measureCode":"VOLU","displayName":"Volume"}}'] \
  [--max-vizs-per-dashboard N] [--dry-run]
```

`--overrides` supports two modes per slot, resolved by `slotOverride()` in the script:

- **APPEND mode** — `{"measureCode":"TARE","displayName":"My Custom KPI Name"}`. The customer's
  entry is upserted into the base's full `allowedValues` list by `value` (the measure code): if the
  code already exists in the base menu, its `displayName` is replaced in place (count stays the
  same); if it's a new code, it's appended (count grows by one). `defaultValue` is set to the
  resolved `displayName`. Confirmed live with suffix `Cust6`/`Dbg2`: overriding an existing code
  with a new display name leaves `allowedValues` count unchanged with exactly one entry for that
  code; overriding with a brand-new code grows the count by one.
- **REPLACE mode** — `{"allowedValues":[{"displayName":"...","value":"..."}, ...],
  "defaultValue":"..."}` (optional `defaultValue`; defaults to the first entry's `displayName` if
  omitted). The customer supplies the *complete* menu for that slot; base entries are discarded
  entirely rather than merged. `defaultValue` must match one of the supplied `displayName`s or the
  script throws before any writes happen.

A slot omitted from `--overrides` still gets a full clone via APPEND mode with no changes (base
measure code, base display name + suffix, full base `allowedValues` untouched).

**Inputs collection (above) always produces REPLACE-mode overrides** — the customer's array
replaces menu entries wholesale, per slot. APPEND mode still exists in the script and stays
available for hand-rolled/debug runs where only a single `{measureCode, displayName}` patch onto
the base menu is wanted, but the standard interactive flow never emits it.

**Both dashboards (Promotion + Tactic) are always cloned, regardless of which slots have
overrides** — `DASHBOARDS` in the script is a fixed constant, not derived from the override keys or
any selection input. There is currently no flag to clone only one dashboard.

`--max-vizs-per-dashboard N` is a **debug/iteration aid only** — caps how many distinct
visualizations get cloned per dashboard so a validation pass doesn't have to wait through all 9
(Promotion) / 7 (Tactic) real viz clones every time. Widgets beyond the cap are left pointing at
their base visualization — the dashboard still builds, just without full viz coverage. **Never use
this flag for an actual customer deliverable** — omit it for a real/complete run.

It resolves the app/assets/model exactly as Phase 0 describes, resolves both slots' calculated
measurements dynamically (never assuming `_value`-vs-`_clc` naming by symmetry), builds and prints
the Phase 1 plan, and — unless `--dry-run` — POSTs all 5 parameters, 5 measurements, every
visualization on either dashboard that references one of the 5 slot measurements, and both
dashboards, in the correct dependency order. See its header comment and
`references/payload-shapes.md` for the exact confirmed request-body shapes per endpoint.

### Real-write findings baked into the script (see `references/payload-shapes.md` for the full trace)

- **A cloned parameter's and measurement's `label` must be suffixed too, not just `apiName`** —
  `label` is uniqueness-checked; reusing the base label across enough clones fails with
  `CREATE_SEMANTIC_ENTITY_FAILED`.
- **The visualization POST body's `dataSource` ref must keep its `.type`** — the dashboard-only rule
  of stripping `.label`/`.type` from `Visualization`/`SemanticModel`-typed ref objects does **not**
  apply to a visualization's own body; applying it there strips `dataSource.type` and fails with
  `INVALID_INPUT: "Value required for [type]."`
- **Every visualization on a dashboard that references a slot measurement must be cloned — not just
  one "designated" viz per dashboard.** Confirmed live, **all 9** visualization widgets on
  `PromotionAnalysis1` and **all 7** on `TacticAnalysis1` reference at least one of the 5 slot
  measurements — top/bottom performers, trend charts, category/product breakdowns, not just the one
  obviously-named chart. The script discovers every `visualization`-type widget on the base
  dashboard directly and clones any whose viz JSON contains a slot measurement apiName; a viz with
  no such reference is correctly left pointing at base.
- **A cloned visualization's cosmetic `fields[].label` text embeds the base parameter's *label*, not
  its apiName** (e.g. `<[Parameters].[Promotion Measure 1]>`), so an apiName-only replace never
  touches it. The script also suffixes each parameter's label and replaces the exact
  `[Parameters].[<label>]` bracket pattern in every cloned visualization and dashboard body.
- **APPEND-mode overrides must upsert by measure code, not blindly push** — the script filters out
  any existing entry with the same `value` before appending the resolved entry, so reusing an
  existing measure code with a new display name produces exactly one entry for that code.

### Hand-rolling a single step (debug only)

If you must hand-roll a single step instead of running the script, the endpoints are:
`POST /services/data/<apiVersion>/ssot/semantic/models/<extendedModelApiName>/parameters`,
`POST /services/data/<apiVersion>/ssot/semantic/models/<extendedModelApiName>/calculated-measurements`,
`POST /services/data/<apiVersion>/tableau/visualizations`,
`POST /services/data/<apiVersion>/tableau/dashboards` — in that dependency order (parameter before
its measurement; both before any visualization that references the measurement; every affected
visualization before the dashboard that references it). Capture every new artifact's id/apiName,
keyed by slot (parameters/measurements) or base name (visualizations). This always produces 5 new
parameters + 5 new measurements — never fewer — regardless of how many slots have an actual
override, and a new visualization for **every** dashboard widget that referenced a slot
measurement, not a fixed count. Record pass/blocked per slot/artifact.

Re-running with a suffix that's already been used in that model **will fail** on the parameters
POST with `CREATE_SEMANTIC_ENTITY_FAILED` (apiName uniqueness is enforced) — always confirm the
chosen suffix hasn't been used before, or delete the prior clone set first.

## Phase 5 — Verify

GET every created parameter, calculated measurement, visualization, and dashboard back:

```bash
node ./scripts/sf-rest.js --target-org <username> \
  --path "/services/data/<apiVersion>/ssot/semantic/models/<extendedModelId>"
node ./scripts/sf-rest.js --target-org <username> \
  --path "/services/data/<apiVersion>/tableau/visualizations/<newVizId>"
node ./scripts/sf-rest.js --target-org <username> \
  --path "/services/data/<apiVersion>/tableau/dashboards/<newDashboardId>"
```

(Parameters/measurements are read back via the same whole-model GET as Phase 0 — index into
`semanticParameters[]`/`semanticCalculatedMeasurements[]` by the new suffixed apiNames.) Confirm
each new parameter resolves to the intended override (or exactly matches its base counterpart's
values, for un-overridden slots), each new measurement's `expression` references the new parameter
apiName (never a base one), each visualization references the correct new measurement apiName(s)
everywhere they appear, and each dashboard's widgets reference the correct new visualization(s) and
parameter(s). Record pass/blocked per artifact for the final report.

## Rules

- Never authenticate on the user's behalf — if `org-status` shows disconnected, stop and ask
  the user to log in themselves.
- Never run `sf org display --json` directly and read its output — always go through
  `scripts/sf-rest.js`'s `org-status` subcommand, which strips `accessToken` before printing.
- Never mutate a base-model parameter, calculated measurement, visualization, or dashboard — every
  write in this skill is a new POST of a suffixed copy. Never PATCH a base artifact.
- Never create a new parameter/measurement/visualization/dashboard without an explicit user
  go-ahead on the Phase 1 resolved plan first.
- Always produce all 5 slots' worth of clones (parameter + calculated measurement = 10 artifacts),
  even when 0 slots have an override — an unmentioned slot's new parameter/measurement must still
  be created as copies of its base counterparts, never skipped or left pointing at base artifacts.
- Never leave a cloned calculated measurement's `expression` referencing a base parameter apiName —
  once a parameter is cloned, every measurement that used it must be repointed at the clone.
- Always use API version `v67.0` for every `/services/data/...` call — pinned per standing
  instruction, not resolved from the target org's own `apiVersion`.
- Never hardcode an artifact id or api-name across orgs — resolve them per-org via the installed
  app's `assetUrl`/`assets[]` (Phase 0), never assume ids confirmed on one org apply elsewhere.
- Never guess a JSON field name for a measure-code binding or a parameter/visualization/dashboard
  reference — Phase 0's live-captured payload shapes are the only source of truth; if a needed
  field can't be identified from a real response, stop and ask the user rather than writing a
  guessed payload.
- Never hardcode the namespace in a REST path — `/services/data/...` paths in this skill are never
  namespaced regardless of `NS`.
- Never reuse a base-model API name for a new artifact — always apply the customer's suffix.
- Never assume only one "designated" visualization per dashboard needs cloning — discover every
  `visualization`-type widget on the base dashboard and clone any whose viz references a slot
  measurement; confirmed live, that is every visualization widget on both TPE dashboards.
- A poll timeout or a transient discovery gap is not a failure — report it as blocked/pending with
  the specific reason, not as a guessed success.

## Report

At the end of a run, give the user a structured status per phase (0-5): pass / blocked / pending,
with the specific blocking reason where applicable, and the final list of created artifacts (slot →
new parameter, base viz → new viz, base dashboard → new dashboard). Call out anything skipped due
to dry-run or a declined confirmation.

**When invoked via delegation** (the calling skill used the `Skill` tool to reach this file, rather
than the user directly — e.g. `consumer-goods-tpe-dashboard-configure`'s customization step): this
report is an intermediate result, not the end of the task. Return it to the calling skill and let it
continue with its own next phase (or finish its own overall report) — do not present this report to
the user as the final answer and stop. Only surface this report directly to the user when this
skill was invoked standalone.

# Data Mask API Surface Reference

The defining characteristic of Data Mask automation is that its entities live on **different API
surfaces**. Reaching for the wrong one is the primary cause of failed/stuck runs. This file is the
authoritative map.

## Per-entity surface

| Entity | Role | Surface | Reachable by |
|--------|------|---------|--------------|
| `DataMaskPolicy` | The masking policy shell (config) | Tooling API / Metadata API | `sf data query --use-tooling-api`, MDAPI deploy (thin shell only) |
| `DataMaskPolicyObject` | Object targeted by a policy (+ its optional row filter) | **Tooling API only** | Tooling query + insert |
| `DataMaskPolicyField` | Field + masking treatment | **Tooling API only** | Tooling query + insert |
| `DataMaskPolicyJobRun` | The job (a single run) | **Standard data API** | `sf data query` (plain SOQL) |
| `DataMaskPolicyJobRunDtl` | Per-object job detail (child) | **Standard data API** | `sf data query` (plain SOQL) |
| `DataMaskCustomValueLibrary` | Custom replacement-value library | **Standard data API** | `sf data query` (plain SOQL) |

`DataMaskPolicyJobRunDtl` is a child of `DataMaskPolicyJobRun` via the lookup
**`DataMaskPolicyJobRunId`**. `DataMaskPolicy` Ids carry the **`8dm`** key prefix.

> **`DataMaskPolicy` is a THIN Metadata API type.** `sf org list metadata-types` returns
> `DataMaskPolicy` (directory `dataMaskPolicies`) with **no child components** (`childXmlNames: []`).
> Only `<label>`, `<description>`, and `<runOnRefresh>` serialize into its metadata — object and
> field membership is **NOT** part of the Metadata API shape (there is no inline `<policyObjects>` /
> `<policyFields>`, and no standalone `DataMaskPolicyObject` / `DataMaskPolicyField` Metadata API
> type). Membership lives entirely in the Tooling entities `DataMaskPolicyObject` and
> `DataMaskPolicyField`, which you both **query and insert**. So authoring a complete policy is a
> **two-step** operation: (1) Metadata-deploy the thin shell (in **mdapi format** — `--metadata-dir`
> + `package.xml`; a source-format `--source-dir` deploy fails "Could not infer a metadata type"),
> then (2) Tooling-insert the object + field rows against it. The Metadata deploy must come first:
> it creates the policy with an active revision, without which the Tooling child insert fails
> `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`. See `policy-authoring.md` for the full recipe.
> `DataMaskPolicyField` treatment columns are `MaskingCategory` (`library` / `replaceRandom`) +
> `MaskValue` (a snake_case library token) — there is **no `MaskingRuleType` column**.

> **Schedule fields live ON the policy** — there is no separate schedule entity. `RunFrequency`
> (`once` / `daily` / `weekly` / `monthly`), `ScheduledStart`, and `RunOnRefresh` are fields on
> `DataMaskPolicy` (confirmed via Tooling describe), so scheduling folds into policy create/update.

> **Row-subset ("sample") filtering lives ON `DataMaskPolicyObject`, NOT on the policy.** There is
> **no `sampleSize` field** anywhere on `DataMaskPolicy`, and **no `LIMIT`** — Data Mask has no
> row-cap concept. To mask only a subset, set `FilterEnabled = true` and a **selective** predicate
> that genuinely matches fewer rows in `WhereCriteria` (a **40-char** SOQL-style predicate, e.g.
> `LastName LIKE '%son%'`); `RawFilterData` holds the structured form the engine actually executes.
> The masked count equals the number of rows the predicate matches. A `LIMIT` is **silently
> ignored** (`LastName != 'X' LIMIT 20` masks the whole table — 407 rows — because the predicate is
> always-true). Confirmed live. See `policy-authoring.md` → "Masking only a subset".
> **`RawFilterData`'s `operation` must be one of** `eq`, `ne`, `lt`, `gt`, `ge`, `le`, `contains`,
> `not_contains`, `in`, `not_in` — anything else (e.g. `startsWith`) fails the run with a `422`.
> **The predicate must also be valid SOQL** — Data Mask runs a planning `SELECT count() ... WHERE
> <predicate>`, so `Id != 'null'` fails the whole job (`invalid ID field: null`). Filter on a text
> field like `LastName`, not `Id`.

### What fails, and why

```bash
# WRONG — these are Tooling/MDAPI entities, not standard-data-API objects:
sf sobject describe --sobject DataMaskPolicy --target-org <alias>          # -> NOT_FOUND
sf data query --query "SELECT Id FROM DataMaskPolicy" --target-org <alias> # -> INVALID_TYPE

# RIGHT — policy config via Tooling API:
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id, DeveloperName, MasterLabel FROM DataMaskPolicy"

# RIGHT — job + job-detail via standard API:
sf data query --target-org <alias> \
  --query "SELECT Id, Status, Type, TotalRecords FROM DataMaskPolicyJobRun ORDER BY CreatedDate DESC LIMIT 5"
sf data query --target-org <alias> \
  --query "SELECT Id, DataMaskPolicyJobRunId, Status FROM DataMaskPolicyJobRunDtl WHERE DataMaskPolicyJobRunId = '<jobRunId>'"
```

## Status picklist values (`DataMaskPolicyJobRun.Status`)

```text
pending, scheduled, running, completed, completed_with_errors, failed, canceled
```

- **Mid-run (not terminal):** `pending`, `scheduled`, `running`
- **Terminal (success/failure):** `completed`, `completed_with_errors`, `failed`
- **Terminal after abort:** `canceled`  ← note the single "l"

`DataMaskPolicyJobRun.Type` picklist: `auto`, `manual`, `scheduled`.

Never report a mid-run value as the final status — poll until a terminal value appears.

> **Case differs by surface.** These SOQL picklist values are **lowercase**. The run/abort REST
> responses return the same states **UPPERCASE** (`RUNNING`, `CANCELED`). Poll for terminal state
> against the lowercase SOQL value — do not compare it to the run-API response string.

## Run / abort REST endpoints

Base: `/services/data/v67.0/platform/data-resilience/data-mask`

- Version must be **`v67.0` or later** (Core release 262, where these endpoints were added).
- There is **no `/connect/` segment** — the path is `/services/data/v67.0/platform/...`. A `connect`
  segment or a pre-v67 version returns `NOT_FOUND`. (This was the top failure mode — verified live.)
- The id is bound as a **path segment**, not a body field.

### Start a run
```text
POST /services/data/v67.0/platform/data-resilience/data-mask/policies/{policyId}/run
```
- Empty JSON body `{}` (`sf api request rest` requires `--body` on a POST; the API takes no payload).
- **`200`** → accepted; response `{ jobRunId, policyId, status: "RUNNING", message: "Job started successfully" }` (status UPPERCASE).
- `403` → org is production (Data Mask runs are sandbox-only; runtime sandbox guard).
- `409`/`CONFLICT` → a run is already in progress for that policy.

### Abort a run
```text
POST /services/data/v67.0/platform/data-resilience/data-mask/jobs/{jobRunId}/abort
```
- Empty JSON body `{}`.
- **`200`** → abort accepted, response `status: "CANCELED"`, `message: "Job abort requested"` (async — confirm with a SOQL re-query).
- `404` → unknown job run id.
- `409` → job is not in a `running` state (already terminal or still `scheduled`).
- After a successful abort, `DataMaskPolicyJobRun.Status` (SOQL, lowercase) becomes `canceled`.

### Calling the run API from the CLI
```bash
# Write an empty JSON object to a file, then pass it with an @ prefix:
printf '{}' > ./empty-body.json
sf api request rest \
  "/services/data/v67.0/platform/data-resilience/data-mask/policies/<policyId>/run" \
  --method POST --body @./empty-body.json --target-org <alias>
```
`sf api request rest` handles auth/session automatically — no need to extract a token by hand.
**A file body needs the `@` prefix** (`--body @./empty-body.json`) — without it the literal path
string is sent as the body and the API returns `JSON_PARSER_ERROR`. The file just needs `{}`.
If you must call it from Apex (`HttpRequest`), use `URL.getOrgDomainURL()` +
`UserInfo.getSessionId()` for the base URL and bearer token.

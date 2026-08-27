# Generic API Recipe (per config entry)

This skill does not carry a per-`ConfigurationName` mapping. It uses
one recipe for every entry, backed by a live describe probe that
verifies the derivation before any PATCH is planned. Read this file
alongside the "Generic per-entry procedure" section in `SKILL.md`.

All endpoints below use the Salesforce Tooling API
(`/services/data/vXX.0/tooling/...`). Substitute the org's current
API version for `vXX.0` (query `sf org display --json` and use
`result.apiVersion`).

---

## The 5-step recipe

### Step A — Derive the candidate Tooling API sobject

`ConfigurationName` in the config is (almost always) the Metadata API
type name, which is usually plural. The Tooling API sobject that
stores that metadata is usually the singular form, sometimes with a
prefix (`Workflow`-, or a `-Proxy` suffix for RSS-style records).

Use your Salesforce knowledge to propose one or two candidates. Do
not commit — Step B rules the wrong candidate out. Never fabricate a
candidate; if you have no plausible one, jump straight to
`API_NOT_IDENTIFIED`.

### Step B — Verify the candidate exists and supports Metadata writes

```bash
sf api request rest \
  "/services/data/v<apiVersion>/tooling/sobjects/<Candidate>/describe/"
```

Accept the candidate only if **both** are true:

- HTTP 200 — the sobject exists on this org's Tooling API.
- The response's `fields` array contains an entry whose `name` is
  `Metadata`. That compound field is what the PATCH writes through;
  without it, the write pattern this skill uses does not apply.

If no candidate passes, record `API_NOT_IDENTIFIED` for every entry
whose `ConfigurationName` derived to that candidate, and stop
attempting for that `ConfigurationName`. Do not guess a REST path.

Cache the verified sobject name per-`ConfigurationName` for the run —
do not re-describe on every entry.

### Step C — Resolve the record Id (SOQL-over-REST, Tooling API)

```bash
sf data query --use-tooling-api --json --query \
  "SELECT Id, FullName FROM <VerifiedSobject> WHERE <UniqueFilter>"
```

The `--use-tooling-api` flag routes the query through
`/services/data/vXX.0/tooling/query/?q=...` — it is a Tooling API
call, not a direct database query, and honors the authenticated
user's CRUD/FLS/sharing. No non-Salesforce SQL is ever issued.

Pick `<UniqueFilter>` from the describe response's `queryable`
fields. Common shapes:

- **Row exposes `FullName`**: filter by `EntityDefinition.QualifiedApiName`
  when the entry has `Fields.Object`, then pick the row whose
  `FullName == '<Object>.<Label>'` client-side. SOQL cannot filter on
  `FullName` directly.
- **Row exposes a queryable `SiteName` / `DeveloperName` / other
  unique field**: filter directly by that field = `<Label>`.

Outcomes:

- **Zero rows** → `NOT_FOUND` (never fall back to insert).
- **Multiple rows** after client-side filtering → `AMBIGUOUS`
  (surface every returned Id in the summary and skip; a wrong Id is
  worse than no Id).
- **Exactly one row** → proceed to Step D.

### Step D — GET + mutate + PATCH via compound `Metadata`

The `Metadata` field is replace-in-full — the entire block is
overwritten on PATCH, so any org-specific keys already in the block
must be preserved.

1. **GET** the record's current `Metadata`:

   ```bash
   sf api request rest \
     "/services/data/v<apiVersion>/tooling/sobjects/<VerifiedSobject>/<Id>" \
     | jq '.Metadata' > /tmp/entry-<Id>-meta.json
   ```

2. **Map** each `Fields.<Xxx>` from the config entry to a camelCase
   key inside the Metadata block.

   > **This decision is owned by `scripts/map-metadata-key.mjs`
   > (authoring standard A9).** Invoke it once per config field with
   > `<ConfigurationName>`, `<ConfigFieldName>`, and the current
   > Metadata JSON path; consume its `{status, key}` output verbatim
   > and do not re-derive the rule in prose.

   The rules the script encodes:

   - **Default rename**: lowercase the first character of the config
     field name — `EndpointUrl` → `endpointUrl`, `IsActive` →
     `isActive`, `Description` → `description`.
   - **Overrides**: some `ConfigurationName` types rename their
     fields between the customer-facing config shape and the Metadata
     API shape — e.g. `RemoteSiteSettings.Fields.RemoteSiteUrl` maps
     to `RemoteProxy.Metadata.url`, not `remoteSiteUrl`.
   - **Existence check**: the resolved key MUST be present in the
     current Metadata block from Step 1. Otherwise the script emits
     `FIELD_MAP_UNKNOWN` — mark the entry and stop. Silently patching
     a different key would either update the wrong field or add a
     phantom one. The customer must reconcile the config-field name
     against the metadata schema (a config-generator concern, not
     something the apply skill guesses at).

3. **PATCH** — the robust pattern: build the mutation object with a
   heredoc file (never inline `--arg` — that stringifies booleans /
   numbers and breaks on keys with special characters), merge it
   over the current Metadata with `jq`'s `+` operator (right-side
   wins, types preserved), then send the PATCH.

   ```bash
   # 3a. Build the mutation object (all camelCase-mapped keys from
   #     the entry's Fields, with correct JSON types).
   cat > /tmp/entry-<Id>-mutation.json <<'EOF'
   {"endpointUrl": "https://uat.example.com/services/account",
    "isActive": true}
   EOF

   # 3b. Merge mutation over current Metadata → wrap in {Metadata:}.
   jq --slurpfile m /tmp/entry-<Id>-mutation.json \
      '. + $m[0] | {Metadata: .}' \
      /tmp/entry-<Id>-meta.json > /tmp/entry-<Id>-patch.json

   # 3c. Send the PATCH.
   sf api request rest \
     "/services/data/v<apiVersion>/tooling/sobjects/<VerifiedSobject>/<Id>" \
     -X PATCH -H "Content-Type:application/json" \
     -b @/tmp/entry-<Id>-patch.json
   ```

Why heredoc + `--slurpfile` beat `--arg v "$val" '.<key> = $v'`:
- Values keep their JSON types (`true` stays boolean, `62.0` stays
  number). The `--arg` pattern stringifies everything.
- Multiple keys can be mutated in one merge — no per-key jq call.
- No shell escaping inside a jq expression — the most common source
  of quoting failures in this skill.
- Special characters in values (URLs with `&`, JSON with quotes)
  survive because they sit inside a heredoc literal, not a shell
  string.

**Classification is owned by `scripts/classify-patch-result.mjs`
(authoring standard A9).** After each PATCH attempt, invoke it with
the HTTP status code and (on non-204) the response body path. Exit 0
→ `SUCCESS`. Exit 2 → `FAILED` with a structured error message on
stdout. Do not re-implement the 204-vs-non-204 decision in prose.

**Retry-once on shell/jq quoting failure**: a single quoting bug
must not abort an apply run before any record is PATCHed. Wrap the
PATCH sequence in a `for attempt in 1 2; do <cmd> && break; done`
inline bash loop — if 3b or 3c fails with a non-zero exit *before*
the HTTP request goes out, heredoc-rebuild the mutation and retry
once. Only if the second attempt also fails is the entry recorded
`FAILED`.

### Step E — Verify the change landed

Re-read the record to confirm the effect:

- If the mutated field is a direct-queryable SOQL column on the
  sobject, a SELECT by Id is enough.
- Otherwise GET the record and inspect `.Metadata.<mappedKey>`.

If the read-back value does not match the requested value, record
`FAILED_VERIFY` — the PATCH returned 204 but the effect is not
visible (usually a naming or permission issue).

---

## Illustrative walkthroughs (not authoritative — always verify)

These are worked examples of the pattern, included to make the
recipe concrete. They are **not** a catalog — a real run must
re-derive and re-describe against the target org.

### Example 1 — `OutboundMessages`

- **Step A** — derive: `WorkflowOutboundMessage`.
- **Step B** — describe: `/services/data/v<apiVersion>/tooling/sobjects/WorkflowOutboundMessage/describe/`
  returns 200 and `fields[].name` includes `Metadata`. Verified.
- **Step C** — SOQL row exposes `FullName`:

  ```sql
  SELECT Id, FullName FROM WorkflowOutboundMessage
   WHERE EntityDefinition.QualifiedApiName = '<Fields.Object>'
  ```

  Pick the row where `FullName == '<Fields.Object>.<Label>'`.
- **Step D** — GET current Metadata, mutate
  `endpointUrl = <Fields.EndpointUrl>`, preserve every other
  Metadata key (`integrationUser`, `name`, `apiVersion`, `fields`,
  `protected`), PATCH.
- **Step E** — GET and confirm `.Metadata.endpointUrl` matches.

Notes:

- `Fields.Action = "Delete"` → `DELETE_NOT_SUPPORTED` (this skill
  updates only).
- OBM has no per-record `isActive` in its `Metadata` — the config's
  `IsActive` for OBM entries governs the parent `WorkflowRule`,
  which is out of scope. `IsActive:false` → `SKIPPED_INACTIVE` as
  the top-level rule (do not attempt to write `isActive` into the
  OBM Metadata).

### Example 2 — `RemoteSiteSettings`

- **Step A** — derive: `RemoteProxy`.
- **Step B** — describe verified.
- **Step C** — SOQL row exposes queryable `SiteName`:

  ```sql
  SELECT Id FROM RemoteProxy WHERE SiteName = '<Label>'
  ```

- **Step D** — GET current Metadata; note the field-name rename:
  config `Fields.RemoteSiteUrl` maps to `Metadata.url`, not
  `remoteSiteUrl`. Preserve every other Metadata key
  (`disableProtocolSecurity`, `isActive`, etc.), mutate `url`
  only, PATCH. `IsActive` at config root is a gate flag (see
  `SKILL.md` §IsActive semantics), not a field mapping — do not
  write it into `Metadata`.
- **Step E** — `RemoteProxy` exposes `EndpointUrl` and `IsActive` as
  direct SOQL columns — a SELECT by Id is enough to verify.

---

## Unsupported / unclear `ConfigurationName` values

If Step B fails for a candidate (or if there is no plausible
candidate to try), emit `API_NOT_IDENTIFIED` for the entry, list it
under Follow-ups in the summary, and continue. Never invent a REST
path. Types the config generator is known to still be scoping out
today — `NamedCredentials`, `SSO`, `CustomSettings`, `CustomLabels`,
`CustomMetadataTypes`, `ConnectedApps`, `FlowDeactivation`,
`ScheduledBatch` — should either pass Step B on the target org (in
which case the recipe applies unchanged) or fail it (in which case
they're flagged). This skill does not treat any type name as
inherently supported or unsupported; the live describe response is
the only authority.

---

## How to call the API

Two supported paths:

- **`sf api request rest`** (preferred — no manual token handling):

  ```bash
  sf api request rest \
    --method PATCH \
    "/services/data/v<apiVersion>/tooling/sobjects/<VerifiedSobject>/<Id>" \
    --body '<json-body>'
  ```

- **`curl` with the session token** (fallback when `sf api request
  rest` is unavailable): read `references/authentication.md` for the
  exact header set. Never log the `Authorization` header or its
  value.

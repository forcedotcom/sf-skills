# Domain & Feature Toggle Write Path (authoritative)

Education Cloud domain toggles — `enableEducationCloud`, `enableStudentSuccess`, `enableAcademicOperations`, `enableMentoring`, `enableCorporateRelations`, `enableStudentManagement`, `enableFinancialAid`, `enableFundraising`, `enableOutcomes`, `enableProgramCohorts`, `enableStudentGoals`, `enableAlumniRelations`, `enableRNADynamicApplications`, and ~28 similar — are **fields inside the `IndustriesSettings` settings file**. They are NOT in Core's `ORG_PREFERENCES` allowlist.

> **IRREVERSIBLE — one-way by design.** These toggles are `false → true` only. `true → false` is rejected/unsupported. **WARN the user before flipping any toggle. Do NOT promise a revert or rollback.**

## Endpoints that DO NOT work — never use these

| Attempt | Result |
|---------|--------|
| `PATCH setup/org/preferences/{name}` | 404 — name not in ORG_PREFERENCES allowlist |
| Tooling sObject `PATCH` on `IndustriesSettings` | 400 `JSON_PARSER_ERROR` (complexvalue fields) |
| SOAP `/services/Soap/m/XX.0` `updateMetadata` | `ROUTE_NOT_FOUND` through the gateway |
| `POST /services/data/vXX/metadata/deployRequest` (multipart zip) | `ROUTE_NOT_FOUND` through the gateway |

## What writes via this path, what does not

| Category | API-writable via metadata PUT? |
|----------|-------------------------------|
| Domain toggles (`enableStudentSuccess`, …) — **once foundation is ON** | Yes |
| Sub-feature toggles (`enableCarePlansPreference`, Support Programs, Scheduler org prefs) — **once foundation is ON** | Yes |
| **Education Cloud foundation** (`enableEducationCloud`) | No — via metadata PUT. **Confirmed silent no-op** for this specific field (`success:true`, stays `false`); the metadata PUT path itself is proven to route AND flip real sub-feature toggles (verified: `enableStudentGoals` `false→true`), so this is feature-specific, not a transport failure. Yes — via the dedicated invoke endpoint instead (see "Enabling the foundation" below). |

## Enabling the foundation (`enableEducationCloud`) — dedicated invoke endpoint

Root cause of the silent no-op: this toggle is AURA-IS-CANONICAL — the real enable action runs extra `ReleasableAction` provisioning wiring beyond a raw field flip, and only the dedicated controller endpoint below runs it. Do not attempt the metadata PUT for foundation.

Same `dispatch`/`dispatch_readonly` tools and headless-360 transport as the metadata path, different URL:
- READ: `GET /headless/invoke/platform/education-cloud-settings` (`dispatch_readonly` is fine) — inspect `educationCloudEnabled`.
- WRITE: `PATCH /headless/invoke/platform/education-cloud-settings/enable-education-cloud` (empty body, via the write-enabled `dispatch` tool).
- cold-VERIFY: repeat the GET above — confirm `educationCloudEnabled: true` on a fresh read. Also cold-check the `IndustriesSettings` tooling GET (`.Metadata.enableEducationCloud` / `IsEducationCloudEnabled`) as a secondary check — the invoke GET is authoritative if they disagree.
- If the invoke endpoint errors or cold-verify still shows `false`: fall back to manual UI — Setup → Quick Find → "Set Up Education Cloud" → Toggle "Enable Education Cloud" → Save. Warn this cannot be disabled after enabling. Wait for user confirmation, then cold-verify again.
| Person Accounts | No — manual UI only |
| License-gated features (Salesforce Scheduler master enable, Field Service) | No — manual UI only |

## The correct sequence: READ → WRITE → VERIFY (cold-verify is mandatory)

**Constants:** API version `v68.0` · `IndustriesSettings` `DurableId` = `bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=` (raw `=`, NOT url-encoded `%3D`).

**1. READ (pre-read current state)** — `dispatch_readonly` GET is fine here:
```http
GET /services/data/v68.0/tooling/sobjects/IndustriesSettings/bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=
```
Inspect `.Metadata.enable*` (and the flat `Is<X>Enabled` fields) for current state.

> `SELECT ... FROM IndustriesSettings` returns **only `Id` and `DurableId` — NO `Metadata`.** You MUST GET the record by `DurableId` to read toggle state. Do NOT use the placeholder Id `000000000000000AAA`.

**2. WRITE (flip the toggle)** — use the **write-enabled `dispatch` tool** (NOT `dispatch_readonly` — read-only *fakes* write success, returning `success:true` without writing). Synchronous, no polling:
```http
PUT /services/data/v68.0/headless/metadata
```
Structured JSON body — `type` is literally `IndustriesSettings`, `fullName` is `Industries`, `xmlRep` includes the XML declaration. One PUT can flip **multiple** elements at once:
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableStudentSuccess>true</enableStudentSuccess></IndustriesSettings>"
}
```

**3. VERIFY (cold read — REQUIRED)** — repeat step 1 and confirm `.Metadata.<element>` and/or the flat `Is<X>Enabled` field is now `true`.

> **`success:true` alone is unreliable — always cold-verify.** The foundation write returned `success:true` yet no-op'd. Only a fresh GET of the record confirms the toggle actually flipped.

> **Cold-verify fallback — the tooling GET can 500 org-wide.** Confirmed on a test org: `GET .../tooling/sobjects/IndustriesSettings/<DurableId>` returned HTTP 500 `UNKNOWN_EXCEPTION` on every value read (any field, any API version), root-caused to a null UDD `LogicalFieldDefinition` on one preference column in that org's data — an org-data defect, not a skill or transport bug (`describe` and `SELECT Id, DurableId` still returned 200). If this GET 500s on 3 consecutive attempts, stop retrying and ask the admin to confirm the toggle's state in Setup UI instead. Report it explicitly as "confirmed via Setup UI, not cold-verified via API" — never claim API cold-verify succeeded when it didn't.

> **License-gating on the write itself.** A toggle write can return `400 INSUFFICIENT_ACCESS_OR_READONLY` (nothing written) purely because the org lacks a license, not because the feature is unreachable via API — confirmed on a test org where the identical write failed, then succeeded after the admin added licenses with no other change. On this error, ask whether the org is fully licensed for the feature before concluding the API path doesn't work.

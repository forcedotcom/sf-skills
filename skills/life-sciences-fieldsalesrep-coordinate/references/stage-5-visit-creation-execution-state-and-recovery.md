# Visit Creation — Execution State & Recovery

Operational reference for Stage 5 (Visit Creation): the creation-state model to track throughout the run, the smoke-test-failure recovery protocol, the auto-diagnosis error table, and the gotchas table. Read this alongside the workflow in `SKILL.md`.

---

## State Tracking

Maintain a creation state throughout the workflow for smoke-test-failure recovery:

```text
State = {
  targetOrg: string,
  repUsername: string,
  repOrgAlias: string,
  steps: [
    { order: 1,  name: "LoginAsSalesRep",              ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 2,  name: "Account",                      ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 3,  name: "HealthcareProvider",           ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 4,  name: "ContactPointAddress",          ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 5,  name: "ObjectTerritory2Association",  ownedBy: "admin", status: "pending|done|failed", recordId?: string },
    { order: 6,  name: "ProviderAcctTerritoryInfo",    ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 7,  name: "Product2",                     ownedBy: "admin", status: "pending|done|failed", recordId?: string },
    { order: 8,  name: "LifeSciMarketableProduct",     ownedBy: "admin", status: "pending|done|failed", recordId?: string },
    { order: 9,  name: "ProductTerritoryAvailability", ownedBy: "admin", status: "pending|done|failed", recordId?: string },
    { order: 10, name: "Visit",                        ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 11, name: "ProviderVisit",                ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 12, name: "ProviderVisitProdDetailing",   ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 13, name: "ProviderVisitProdDiscussion",  ownedBy: "rep",   status: "pending|done|failed", recordId?: string },
    { order: 14, name: "MetadataRecordsSetup",         ownedBy: "admin", status: "pending|done|failed", parentId?: string, childId?: string },
    { order: 15, name: "GenerateMetadataCache",        ownedBy: "admin", status: "pending|done|failed", enqueued?: boolean },
    { order: 16, name: "MobileAppVisitValidation",     ownedBy: "rep (manual, iPad)", status: "pending|confirmed|issue" }
  ]
}
```

---

## Smoke-Test-Failure Recovery

If any step fails, immediately perform auto-diagnosis and display:

```text
Step <N>/16 FAILED: <StepName>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  What happened:
    <Exact error message from the CLI response>

  Why:
    <Interpretation — e.g. "The record type does not exist in the target org",
     "The field name is invalid for this API version", "Insufficient access">

  Possible causes:
    1. <Cause 1 — e.g. "Health_Care_Provider RecordType not deployed">
    2. <Cause 2 — e.g. "Sales rep user lacks object-level Create permission">
    3. <Cause 3 — e.g. "Required field missing or null">

  What I can do:
    A. Retry this step (if transient error)
    B. Skip this step and continue (if non-blocking)
    C. Attempt auto-fix: <describe specific fix if possible>
    D. Stop and report partial status

  Partial-success status:
    Completed: <N-1>/<16> steps
    Failed at: Step <N> (<StepName>)
    Records created so far:
      [done]    <list of successfully created records with IDs>
      [failed]  <failed step>
      [pending] <remaining pending steps>
```

**Wait for user choice before continuing.** Do NOT silently skip failed steps.

### Auto-diagnosis logic

| Error pattern | Diagnosis | Auto-fix |
|---|---|---|
| `INVALID_TYPE` or `sObject type not supported` | Object not available in org | None — tell user to verify LSC packages are installed |
| `INVALID_FIELD` | Field does not exist on this object | Check API version; try without the offending field |
| `REQUIRED_FIELD_MISSING` | A required field was not provided | Add the missing field with a sensible default and retry |
| `INSUFFICIENT_ACCESS_OR_READONLY` | User lacks permission | Check if using correct target-org (rep vs admin) |
| `DUPLICATE_VALUE` | Record already exists | Query existing record and reuse its ID; continue |
| `FIELD_INTEGRITY_EXCEPTION` | FK reference invalid (ID doesn't exist) | Re-query the parent record; if not found, report dependency failure |
| `UNABLE_TO_LOCK_ROW` | Concurrent lock conflict | Wait 5 seconds and retry (up to 3 times) |
| `NOT_FOUND` or `Session expired` | Auth issue | Re-authenticate and retry |
| `STRING_TOO_LONG` | Field value exceeds max length | Truncate and retry |
| `...parentMetadataRecordId parameter isn't ValidationCompleted` (Step 15) | Parent record Status not set | Set the **parent** record's Status to `ValidationCompleted` (the API requires the parent, not just the child), then retry |
| `JSON_PARSER_ERROR: Unrecognized field "generateStandardTranslations"` (Step 15) | Body has an unsupported field | Remove it — body accepts only `parentMetadataRecordId`, `apiVersion`, and `prefix` |
| `INVALID_AUTH_HEADER` (401) from Connect API (Step 15) | Used raw `curl` | Use `sf api request rest` — it builds the auth header correctly |
| HTTP 400/404 from Connect API (Step 15) | Invalid parentMetadataRecordId or endpoint unavailable | Re-query parent status; verify API version v65.0+ and LSC packages |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `sf org login web` opens browser but user can't access | Provide the instance URL from the admin org display; user may need to paste password manually |
| Account RecordType `Health_Care_Provider` not found | Query all Account RecordTypes and try `HealthCareProvider` (without underscore) or `Health_Care_Provider` |
| HealthcareProvider object not available | LSC packages not installed — direct user to `life-sciences-prerequisites-validate` |
| Territory query returns no results | Territory model may not be Active — direct user to `life-sciences-territory-configure` |
| `FIELD_INTEGRITY_EXCEPTION` on PlaceId in Visit | ContactPointAddress must be linked to the same Account; verify ParentId matches |
| `INSUFFICIENT_ACCESS` creating ObjectTerritory2Association | This object may require admin access — if rep fails, create this specific record as admin and document the exception |
| Account active flag | Use the standard `IsActive` (boolean), NOT `IsActive__c`. If the rep lacks FLS to it, omit and set as admin |
| `Unable to create/update fields: NationalProviderIdentifier` on HealthcareProvider | FLS — rep lacks access. Omit NPI and IsSpeaker (not needed for visit); admin can set later |
| `entity type cannot be inserted: Object Territory Association` (Step 5) | Rep lacks "Manage Territories"; create as admin (or skip — nothing downstream needs it) |
| `No such column 'ProductCode' on Product2` (Steps 7–8) | Rep has no create permission on product master data. Create Steps 7–9 as admin |
| Date format rejected | Use ISO 8601: `YYYY-MM-DDTHH:MM:SS.000+0000` for datetime, `YYYY-MM-DD` for date |
| `LifeSciMobileMetadataRecord` not found (Step 14) | LSC packages not installed or API version < 65.0 |
| `Profile 'LSC Custom Profile' not found` (Step 14) | Run Stage 2 (Starter Config Deploy) first — the child record needs the profile Id |
| Connect API errors (Step 15: `...isn't ValidationCompleted`, `INVALID_AUTH_HEADER`, `JSON_PARSER_ERROR`, HTTP 400/404) | See the auto-diagnosis table above for causes and fixes |
| `parse err: Expecting value` / `Unexpected token` when piping `--json` into `jq`/`python` | The command redirected stderr into stdout (`2>&1`) before the parser, so a CLI warning/deprecation notice contaminated the JSON. **Never pipe `sf ... --json 2>&1` into a parser.** Let stderr go to the terminal (drop `2>&1`), or discard it with `2>/dev/null`, so only clean JSON reaches the parser. This is a harness artifact, not an org error — the query itself succeeded; just re-run without merging stderr. |
| `INVALID_FIELD` querying `Visit` (e.g. `Subject`) | Don't guess field names. `Visit`'s label field is `Name` (auto-number, e.g. `00000001`), not `Subject`. To confirm the Visit, query `SELECT Id, Name FROM Visit WHERE Id='<visitId>'`. If unsure which fields exist, run `sf sobject describe --sobject Visit --target-org <org>` rather than guessing. |
| Records never leave their status (LastModifiedDate unchanged) | Async job didn't run — wait 30s and re-query; check Setup → Apex Jobs if still stuck |
| Records go to `Inactive` instead of `Active` (Step 15) | Generation ran but produced no cache — this is a failure. Check `IntegrationErrorMessage` and Setup → Apex Jobs for the cause |

---

## Phase 7 — Summary output template

After all records are created, display this block (substituting the actual IDs and values from the run):

```text
============================================================
  Life Sciences Visit Creation — Complete
============================================================

  ACCOUNT DETAILS
  ───────────────────────────────────────────────────────────
  Account Name:      Dr. Aaron Morita
  Record Type:       Health_Care_Provider
  Account ID:        <accountId>
  Provider Name:     Aaron Morita HP
  Provider Type:     Medical Doctor
  Address:           415 Mission St, San Francisco, CA 94105
  Territory:         <territoryName>

  VISIT DETAILS
  ───────────────────────────────────────────────────────────
  Visit ID:          <visitId>
  Status:            Planned
  Start Time:        <PlannedVisitStartTime>
  Account:           Dr. Aaron Morita
  Place:             415 Mission St
  Territory:         <territoryName>
  Provider Visit:    <providerVisitId>
  Product Detailed:  Immunexis 5mg
  Discussion Note:   Discussed Oncology treatments and patient care approaches

  RECORD CREATION SUMMARY
  ───────────────────────────────────────────────────────────
  [done] Step  1/16: Login as Sales Rep          (rep)   — done
  [done] Step  2/16: Account                     (rep)   — <accountId>
  [done] Step  3/16: HealthcareProvider          (rep)   — <hcpId>
  [done] Step  4/16: ContactPointAddress         (rep)   — <cpaId>
  [done] Step  5/16: ObjectTerritory2Association (admin) — <otaId>
  [done] Step  6/16: ProviderAcctTerritoryInfo   (rep)   — <patiId>
  [done] Step  7/16: Product2                    (admin) — <productId>
  [done] Step  8/16: LifeSciMarketableProduct    (admin) — <lmpId>
  [done] Step  9/16: ProductTerritoryAvailability (admin) — <ptaId>
  [done] Step 10/16: Visit                       (rep)   — <visitId>
  [done] Step 11/16: ProviderVisit               (rep)   — <pvId>
  [done] Step 12/16: ProviderVisitProdDetailing  (rep)   — <pvpdId>
  [done] Step 13/16: ProviderVisitProdDiscussion (rep)   — <pvpDiscId>
  [done] Step 14/16: MetadataRecordsSetup        (admin) — parent: <parentId> (ValidationCompleted), child: <childId> (ValidationCompleted)
  [done] Step 15/16: GenerateMetadataCache       (admin) — enqueued
  [done] Step 16/16: MobileAppVisitValidation    (rep)   — confirmed on iPad ('00000001' / Dr. Aaron Morita)

  Created as user: <repUsername>
  Visit confirmed on the iPad app — LSC setup in this org is complete.
============================================================
```

> **Keep the summary to the block above.** Do NOT append notes that describe the underlying data, its shape (row/record counts, hierarchy levels), specific product/record names or IDs, or commentary comparing the source data to the skill's examples. End at the summary; no "worth noting for future runs" addendum.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| **Require `.lsc-starter-config/LSStarterConfig/` to already be present in the CWD; do NOT download or delete it** | The shared folder's download/cleanup is owned by the coordinator (`life-sciences-fieldsalesrep-coordinate`) — one download at start, one delete at end |
| **Read the `.lsc-starter-config/LSStarterConfig/Data/` CSV for each object and use ONLY its values** — read at execution time, one record per row; never hardcode field values from this stage or reuse values from a prior run | The CSVs are the single source of truth and may change between runs; illustrative values in the steps can be stale |
| Create the **visit records** (Account, HealthcareProvider, ContactPointAddress, ProviderAcctTerritoryInfo, Visit, ProviderVisit, detailing, discussion) as the Sales Rep | Visit ownership must be the field rep for realistic field sales workflows |
| Create **territory associations (Step 5), product master data (Steps 7–9), and metadata cache (Steps 14–15) as the admin** | The LSC Custom Profile has no create permission on ObjectTerritory2Association, Product2, or LifeSciMarketableProduct; metadata cache records are admin-managed |
| Ask for rep credentials — never assume | Security; credentials vary per org |
| Use `--target-org lsc-rep` for the rep-owned steps (2, 3, 4, 6, 10–13); use `--target-org <admin>` for the admin-owned steps (5, 7, 8, 9, 14–15) | Ensures correct ownership and the right access level for each object |
| PlannedVisitStartTime must be NOW (current time) | Requirement: visit should reflect current scheduling |
| Create records in exact order 2→15, then run the manual iPad validation (Step 16) last | Later records reference earlier IDs (Account→Visit→ProviderVisit); the metadata cache (14–15) must exist before the app can sync the Visit |
| Step 16 (iPad validation) is **manual** — show the rep credentials (ask for the password if unknown; never use admin creds), give the instructions, and never claim it is done without the user's explicit "yes" | It requires a human with a physical iPad or simulator, logged in as the rep; the skill cannot verify app visibility programmatically |
| Treat a "yes" on the Step 16 prompt as the end of the LSC setup; on a reported issue, run the troubleshooting checks (territory assignment, ProviderAcctTerritoryInfo, metadata cache freshness) before re-asking | Confirms the end-to-end setup actually works on the device the rep uses |
| Product2 must NOT have a RecordType | Explicit requirement — no record type for Product2 |
| Show diagnosis on every failure | User needs to understand what went wrong without investigating CLI output |
| Wait for user decision on failure — no silent skips | User controls recovery path |

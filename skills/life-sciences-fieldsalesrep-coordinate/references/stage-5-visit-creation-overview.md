# Stage 5 — Visit Creation

Creates a sample Visit and all supporting records as the Field Sales Rep user (not the admin) in a Life Sciences Cloud org. This is the final stage (Stage 5) of the `life-sciences-fieldsalesrep-coordinate` workflow; the coordinator invokes it after the rep user (Stage 4) is provisioned.

## Stage Scope

- **In scope**: logging in as the sales rep; creating the full visit-chain records (Account → ProviderVisitProdDiscussion); generating the mobile metadata cache (LifeSciMobileMetadataRecord + Connect API); guiding a final manual iPad app validation; displaying a summary
- **Out of scope**: creating territories (Stage 3), provisioning users (Stage 4), package installation (Stage 1)

---

## Prerequisites

These must exist in the org before this stage runs (the coordinator sequences the earlier stages so they do):

| Prerequisite | Created by |
|---|---|
| Field Sales Rep user (with LSC Custom Profile) | Stage 4 (User Provisioning) |
| Active Territory Model with level-3 territory | Stage 3 (`life-sciences-territory-configure`) |
| Life Sciences Cloud packages installed | Stage 1 (`life-sciences-prerequisites-validate`) |

---

## Required Inputs

Gather before proceeding:

- **Target org** (admin alias): The org alias or username for the admin connection (from `sf config get target-org` or user-specified)
- **Sales Rep credentials**: Username and password for the Field Sales Rep user. **Ask the user** if not already known — do NOT assume or reuse admin credentials.

---

## Source Data (CSV-driven — read first, use only these)

**All record field values MUST come from the CSV files in `.lsc-starter-config/LSStarterConfig/Data/`** — read the corresponding CSV at execution time and use **only** the values it contains. Never hardcode values from this overview or carry them over from a prior run; the CSVs are the single source of truth and may change between runs.

> **The `.lsc-starter-config/LSStarterConfig/Data/` CSVs must already be present in the CWD** (from the public repo <https://github.com/SalesforceLabs/LSStarterConfig.git>). This embedded stage is a pure consumer of the folder and does NOT download or delete it — the coordinator (`life-sciences-fieldsalesrep-coordinate`) is the sole owner of the single download (at the start of the run) and the single delete (at the end). If `.lsc-starter-config/LSStarterConfig/` is absent when this stage runs, stop and report that it must be provisioned by the coordinator; do not download it here.

- Read each CSV (e.g. `cat .lsc-starter-config/LSStarterConfig/Data/<object>.csv`, named per the sobject — `account.csv`, `healthcareprovider.csv`, … `providervisitproddiscussion.csv`; the per-object mapping is in `references/stage-5-visit-creation-visit-creation-data.md`), parse header + rows, and create **one record per row** using exactly the columns present.
- CSV columns that hold **source-org IDs** (e.g. `ProductId`, `TerritoryId`, `ParentProductId`, `ProviderVisitId`, record-type IDs) will NOT exist in the target org — resolve the equivalent record in the target org and remap the ID. Never insert a raw source-org ID.
- The literal values shown in the workflow steps below and in `references/stage-5-visit-creation-visit-creation-data.md` are **illustrative of one CSV snapshot only** — the live CSV wins if they differ.

---

## State Tracking

Maintain a creation state throughout the workflow (target org, rep username/alias, and a per-step status list for steps 1–16) so a smoke-test failure can be diagnosed and resumed. See the full state model in `references/stage-5-visit-creation-execution-state-and-recovery.md`.

---

## Workflow

### Phase 1 — Login as Sales Rep

1. **Ask the user** for the Sales Rep credentials (username and password) if not already known.

2. **Authenticate as the Sales Rep** using the web login flow — **run the command yourself** (do not hand it to the user); it opens a browser on the user's machine for them to complete the login interactively, then returns:
   ```bash
   sf org login web --alias lsc-rep --instance-url <instanceUrl>
   ```
   Or use JWT/password flow if available:
   ```bash
   sf org login sfdx-url --sfdx-url-stdin <<< "<sfdxAuthUrl>"
   ```

   > Rep-owned steps (2, 3, 4, 6, 10–13) use `--target-org lsc-rep`; admin-owned steps (5, 7, 8, 9, 14–15) use `--target-org <admin>`. See the Phase 2/3 notes for the ownership split rationale.

3. **Verify the login** succeeded with `sf org display --target-org lsc-rep --json` and confirm the username matches the expected sales rep.

### Phase 2 — Create Account and Provider Records (Steps 2–6)

> **Rep vs. Admin ownership (important):** The LSC Custom Profile can create the Account, HealthcareProvider, ContactPointAddress, ProviderAcctTerritoryInfo, and the whole Visit chain (Steps 10–13) — but NOT territory associations (Step 5) or product master data (Steps 7–9). Create those as the admin (`--target-org <admin>`), then switch back to the rep. This split is expected: territory associations and products are admin-managed data.

**Step 2: Create Account (RecordType = Health_Care_Provider)**

First, query the RecordType ID:
```bash
sf data query --query "SELECT Id FROM RecordType WHERE SObjectType='Account' AND DeveloperName='Health_Care_Provider'" --target-org lsc-rep --json
```

Then create the Account:
```bash
sf data create record --sobject Account --values "FirstName='Aaron' LastName='Morita' Salutation='Dr.' RecordTypeId='<recordTypeId>' IsActive=true" --target-org lsc-rep --json
```

> Reference: `account.csv` — Name=Aaron Morita, Salutation=Dr., RecordType=Health_Care_Provider.
> The active flag is the standard `IsActive` field (boolean) — NOT `IsActive__c`. If the rep lacks FLS to it, omit it and have an admin set it afterward.

**Step 3: Create HealthcareProvider**

First, query the HealthcareProvider RecordType ID:
```bash
sf data query --query "SELECT Id FROM RecordType WHERE SObjectType='HealthcareProvider' AND DeveloperName != null LIMIT 1" --target-org lsc-rep --json
```

Then create:
```bash
sf data create record --sobject HealthcareProvider --values "AccountId='<accountId>' IsActive=true IsPrimaryProvider=true Name='Aaron Morita HP' ProviderType='Medical Doctor' Status='Active' RecordTypeId='<hcpRecordTypeId>'" --target-org lsc-rep --json
```

> Reference: `healthcareprovider.csv` — ProviderType=Medical Doctor, Status=Active. Do NOT set `NationalProviderIdentifier` or `IsSpeaker` — they (and `IsActive`) are FLS-gated on the LSC Custom Profile, so as the rep the create fails with `INVALID_FIELD`. Omit NPI/IsSpeaker (an admin can set them later).

**Step 4: Create ContactPointAddress**

```bash
sf data create record --sobject ContactPointAddress --values "ParentId='<accountId>' AddressType='Billing' Name='415 Mission St' Street='415 Mission St' City='San Francisco' State='California' StateCode='CA' PostalCode='94105' Country='United States' CountryCode='US' Latitude=37.789853 Longitude=-122.396806 IsActive=true IsPrimary=true UsageType='Work'" --target-org lsc-rep --json
```

> Reference: `contactpointaddress.csv` — 415 Mission St, San Francisco, CA 94105

**Step 5: Create ObjectTerritory2Association — as ADMIN**

First, query the level-3 territory ID:
```bash
sf data query --query "SELECT Id, Name FROM Territory2 WHERE Territory2Model.State='Active' AND ParentTerritory2.ParentTerritory2Id != null" --target-org <admin> --json
```

Then create it **as the admin** — the rep profile lacks "Manage Territories", so as the rep this fails with `entity type cannot be inserted: Object Territory Association` (describe reports `createable=false` for the rep). As the admin it is `createable=true`:
```bash
sf data create record --sobject ObjectTerritory2Association --values "ObjectId='<accountId>' Territory2Id='<territory2Id>' AssociationCause='Territory2Manual'" --target-org <admin> --json
```

> Reference: `objectterritory2association.csv` — AssociationCause=Territory2Manual. This is an admin-managed record, not referenced by any later record (the Visit gets its territory from its own `TerritoryId`, Step 10; the account↔territory link is carried by ProviderAcctTerritoryInfo, Step 6). If admin access is unavailable, it may be skipped without breaking the visit.

**Step 6: Create ProviderAcctTerritoryInfo**

```bash
sf data create record --sobject ProviderAcctTerritoryInfo --values "AccountId='<accountId>' Territory2Id='<territory2Id>' PreferredAddressId='<contactPointAddressId>' IsActive=true IsAvailableOffline=true IsTargetedAccount=true SourceType='Manual'" --target-org lsc-rep --json
```

> Reference: `provideracctterritoryinfo.csv` — IsTargetedAccount=true, SourceType=Manual

### Phase 3 — Create Product Records (Steps 7–9) — as ADMIN

Products are master data. The rep's LSC Custom Profile has NO create permission on `Product2` / `LifeSciMarketableProduct` (as the rep, even `Name` reports `createable=false` and `Product2.ProductCode` is not visible), and `ProductTerritoryAvailability` also fails as the rep. Create all three **as the admin** (`--target-org <admin>`). If your rep genuinely must own products, grant the profile Create + field access first — but the default and recommended path is admin.

**Step 7: Create Product2 (no RecordType) — as ADMIN**

```bash
sf data create record --sobject Product2 --values "Name='Immunexis 5mg' ProductCode='IM001-5' IsActive=true" --target-org <admin> --json
```

> Reference: `product2.csv` — Do NOT set a RecordType.

**Step 8: Create LifeSciMarketableProduct — as ADMIN**

```bash
sf data create record --sobject LifeSciMarketableProduct --values "Name='Immunexis 5mg' ProductId='<product2Id>' IsActive=true IsAvlForSamplingAllocation=true Manufacturer='Makana Health' DistributionMethod='Drop' SignatureRequirementLevel='Mandatory' SortOrder=100 StartDate=2026-07-01 Type='Product'" --target-org <admin> --json
```

> Reference: `lifescimarketableproduct.csv` — Manufacturer=Makana Health, DistributionMethod=Drop

**Step 9: Create ProductTerritoryAvailability — as ADMIN**

```bash
sf data create record --sobject ProductTerritoryAvailability --values "ProductId='<lifeSciMarketableProductId>' TerritoryId='<territory2Id>' AlignmentType='Territory Inclusion' Purpose='Visit' Status='Draft' UsageType='LifeSciences'" --target-org <admin> --json
```

> Reference: `productterritoryavailability.csv` — AlignmentType=Territory Inclusion, Purpose=Visit. After Step 9, switch back to the rep (`--target-org lsc-rep`) for the Visit chain (Steps 10–13) so the visit records are rep-owned.

### Phase 4 — Create Visit Records (Steps 10–13)

> **STOP-GATE (chain integrity).** Steps 10–13 are a strict dependency chain — each `sf data create record` returns an `id` that is a required input to the next step. After **every** create in this stage (Steps 2–13), confirm the response has `"success": true` and capture the real returned `id`. If any create fails, **STOP immediately** — do NOT continue with a null, empty, or placeholder ID (that produces an orphaned or mis-parented record chain that looks created but is broken). Report which step failed and its error. After Step 13, verify the full chain resolves: the ProviderVisitProdDiscussion → ProviderVisitProdDetailing → ProviderVisit → Visit → Account links must all be non-null.

**Step 10: Create Visit (PlannedVisitStartTime = NOW)**

```bash
sf data create record --sobject Visit --values "AccountId='<accountId>' PlaceId='<contactPointAddressId>' PlannedVisitStartTime='<NOW_ISO8601>' Status='Planned' TerritoryId='<territory2Id>'" --target-org lsc-rep --json
```

> `<NOW_ISO8601>` = current datetime in ISO 8601 (e.g. `2026-08-01T10:30:00.000+0000`), generated at execution time with `date -u +"%Y-%m-%dT%H:%M:%S.000+0000"`.
>
> Reference: `visit.csv` — Status=Planned, linked to Account, Place, and Territory

**Step 11: Create ProviderVisit**

First, query the territory name:
```bash
sf data query --query "SELECT Name FROM Territory2 WHERE Id='<territory2Id>'" --target-org lsc-rep --json
```

Then create:
```bash
sf data create record --sobject ProviderVisit --values "VisitId='<visitId>' TerritoryName='<territoryName>' IsConfirmed=false" --target-org lsc-rep --json
```


**Step 12: Create ProviderVisitProdDetailing**

```bash
sf data create record --sobject ProviderVisitProdDetailing --values "ProviderVisitId='<providerVisitId>' ProductId='<lifeSciMarketableProductId>' Priority=4 AdditionalInformation='Discussed Oncology products and treatments' IsGeneratedFromPresentation=false" --target-org lsc-rep --json
```

> Reference: `providervisitproddetailing.csv` — Priority=4, AdditionalInformation about Oncology products

**Step 13: Create ProviderVisitProdDiscussion**

```bash
sf data create record --sobject ProviderVisitProdDiscussion --values "ProviderVisitProductDtlId='<providerVisitProdDetailingId>' Note='Discussed Oncology treatments and patient care approaches'" --target-org lsc-rep --json
```

> Reference: `providervisitproddiscussion.csv` — Note about Oncology treatments

### Phase 5 — Generate Metadata Cache (Steps 14–15) — as ADMIN

This phase sets up a prerequisite metadata record and calls the Connect API to generate the metadata cache. No permission set is required — the generate Connect API bypasses the metadata validation itself, so validation-skip and generate permissions are not needed.

**Step 14: Create LifeSciMobileMetadataRecord Prerequisite**

Create a **parent** `LifeSciMobileMetadataRecord` record and a **child** record linked to the LSC Custom Profile (`ParentMobileMetadataRecId` + `ProfileId`). Set **both** to `Status = 'ValidationCompleted'` — the generate API rejects the call unless the **parent** is `ValidationCompleted`, not just the child. Extract the **parent** record ID — needed as `parentMetadataRecordId` in Step 15. Read `references/stage-5-visit-creation-metadata-cache-generation.md` for exact Apex and the schema-check command.

**Step 15: Call the Metadata Generate Connect API**

Use the CLI's own authenticated REST client — a hand-rolled `curl` fails with `INVALID_AUTH_HEADER`. The body accepts `parentMetadataRecordId`, `apiVersion`, and `prefix` (do NOT include `generateStandardTranslations` — it is rejected):

Write the request body to a **project-local** relative file (never `/tmp` or any path outside the project) and remove it right after:

```bash
cat > .lsc-mdgen-body.json <<'EOF'
{
  "parentMetadataRecordId": "<parentRecordId>",
  "apiVersion": "65.0",
  "prefix": "lsc4ce"
}
EOF
sf api request rest \
  "/services/data/v65.0/connect/life-sciences/commercial/metadata/actions/generate" \
  --method POST \
  --body @.lsc-mdgen-body.json \
  --target-org <admin>
rm -f .lsc-mdgen-body.json
```

> Expected: HTTP 200 with `{ "message": "Task enqueued for metadata cache generation." }`. This only confirms the task was accepted — it is NOT the final success signal. Generation runs asynchronously; the metadata records' `Status` then transitions to `Active`. **`Active` is the success state** — wait for it before treating generation as complete. A transition to `Inactive` (or records stuck unchanged) means the job failed or never ran — check `IntegrationErrorMessage` and Setup → Apex Jobs. Verify with a query on `Status`. See `references/stage-5-visit-creation-metadata-cache-generation.md` for full details.

---

### Phase 6 — Manual iPad Mobile-App Validation (Step 16) — as REP (manual)

The **final validation step (Step 16)** is **manual** — it can't be done programmatically. A tester installs the Life Sciences Cloud iPad app, logs in as the **rep**, and confirms the Visit is visible. Do this in order:

1. **Display the Sales Rep credentials** — `Username: <repUsername>`, `Password: use the password you created`, and (only if the app prompts for a custom domain) `Login URL: <instanceUrl>`. Use the actual username/URL from this run — never invent them. **Do NOT print the password value**; refer to the password created during user provisioning. If the user lacks it, an admin can reset it; never substitute admin credentials.

2. **Give the install/login/navigation instructions:** on the iPad, install "Life Sciences Cloud Mobile" from the App Store (<https://apps.apple.com/us/app/life-sciences-cloud-mobile/id6499238627>); open it and log in with the rep credentials; wait for the initial sync to finish (org data + metadata cache, 3–5 min on first login); then open the **Visits** tab and tap the Visit to view details.

3. **Ask the confirmation prompt** — substitute the actual Visit Name and Account Name (auto-generated here as Visit `00000001`, Account `Dr. Aaron Morita`): **"Do you see the Visit '00000001' for Account 'Dr. Aaron Morita' in the iPad app?"**

4. **Handle the response:** **YES** → mark Step 16 `confirmed`; this is the **end of the LSC setup in the org** — report success (Phase 7) and stop. **Issue reported** → mark `issue`, walk the troubleshooting steps below, then re-ask.

**Troubleshooting (only if the Visit is not visible):** verify each of these (`--target-org <admin>`), fix any that fail, have the tester force a re-sync (pull-to-refresh on the Visits list, or log out/in), then re-ask the prompt: (1) rep assigned to the level-3 territory (`UserTerritory2Association`) — else assign via Stage 4 (User Provisioning); (2) `ProviderAcctTerritoryInfo` exists for the Account + territory and `IsActive=true` — else (re)create Step 6; (3) `LifeSciMobileMetadataRecord` records are `Status='Active'` — else re-run Steps 14–15. Common root cause: the app synced **before** the territory assignment, ProviderAcctTerritoryInfo, or metadata cache existed. Exact queries/fixes are in `references/stage-5-visit-creation-visit-creation-data.md`.

---

## Phase 7 — Summary

After all records are created, display the completion summary — Account details, Visit details, and a 16-step record-creation summary with each record ID, ending with "Created as user: `<repUsername>`" and the iPad confirmation line. The exact ASCII template is in `references/stage-5-visit-creation-execution-state-and-recovery.md`; substitute the actual IDs and values from the run.

> **Keep the summary to that block.** Do NOT append notes that describe the underlying data, its shape (row/record counts, hierarchy levels), specific product/record names or IDs, or commentary comparing the source data to the skill's examples. End at the summary; no "worth noting for future runs" addendum.

---

## Smoke-Test-Failure Recovery

If any step fails, immediately perform auto-diagnosis: show **What happened** (exact CLI error), **Why**, **Possible causes**, **What I can do** (retry / skip / auto-fix / stop), and a **partial-success status** (completed N-1/16, failed step, records created so far). **Wait for user choice before continuing — do NOT silently skip failed steps.**

The failure-report template and the full auto-diagnosis error table (error pattern → diagnosis → auto-fix, covering `INVALID_TYPE`, `INVALID_FIELD`, `INSUFFICIENT_ACCESS_OR_READONLY`, `DUPLICATE_VALUE`, the Step 15 Connect API errors, etc.) are in `references/stage-5-visit-creation-execution-state-and-recovery.md`.

---

## Rules / Constraints

Load-bearing rules (full table with rationales in `references/stage-5-visit-creation-execution-state-and-recovery.md`):

- **`.lsc-starter-config/LSStarterConfig/` must already be present in the CWD — do NOT download or delete it.** That folder's download/cleanup is owned by `life-sciences-fieldsalesrep-coordinate`.
- **Read the `.lsc-starter-config/LSStarterConfig/Data/` CSV for each object and use ONLY its values** — at execution time, one record per row; never hardcode field values or reuse a prior run's. The CSVs are the single source of truth.
- **Ownership split:** create the **visit records** (Account, HealthcareProvider, ContactPointAddress, ProviderAcctTerritoryInfo, Visit, ProviderVisit, detailing, discussion) as the rep (`--target-org lsc-rep`); create **territory associations (Step 5), product master data (Steps 7–9), and metadata cache (Steps 14–15) as the admin** (`--target-org <admin>`) — the LSC Custom Profile can't create those.
- **Ask for rep credentials — never assume or reuse admin credentials.**
- Create records in exact order 2→15, then run the manual iPad validation (Step 16) last; earlier IDs feed later records and the metadata cache must exist before the app can sync the Visit.
- **Step 16 is manual** — show rep credentials (ask for the password if unknown; never use admin creds), give instructions, and never claim it's done without the user's explicit "yes"; on a reported issue, run the troubleshooting checks before re-asking.
- `PlannedVisitStartTime` must be NOW; Product2 must NOT have a RecordType.
- Show diagnosis on every failure and wait for the user's decision — no silent skips.

---

## Gotchas

Common failures and fixes — missing RecordTypes/objects, rep-vs-admin FLS on HealthcareProvider (NPI/IsSpeaker) and product master data, ISO 8601 date formats, the Step 14 profile/metadata prerequisites, and the Step 15 Connect API errors — are tabulated in `references/stage-5-visit-creation-execution-state-and-recovery.md`.

---

## Output Expectations

Deliverables:
- Authenticated as the Sales Rep (not admin); all 13 visit-chain records created in dependency order (Account → ProviderVisitProdDiscussion).
- LifeSciMobileMetadataRecord parent + child (child linked to the LSC Custom Profile), both `Status='ValidationCompleted'`; cache generation enqueued via Connect API and confirmed complete when the records reach `Status='Active'`.
- Manual iPad validation guided (rep creds shown, instructions given, confirmation prompt asked); a "yes" closes out setup, an issue triggers troubleshooting.
- Completion summary displayed (Account + Visit details, all record IDs). On failure: auto-diagnosis (What/Why/Causes/Actions) + partial-success status.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stage-5-visit-creation-visit-creation-data.md` | Default field values for all records (sourced from CSV files); also the Step 16 manual iPad validation checklist and troubleshooting queries |
| `references/stage-5-visit-creation-metadata-cache-generation.md` | During Phase 5 (Steps 14–15) — exact Apex and `sf api request rest` commands for metadata cache generation |
| `references/stage-5-visit-creation-execution-state-and-recovery.md` | The full creation-state model, the smoke-test-failure recovery template + auto-diagnosis error table, and the gotchas table |

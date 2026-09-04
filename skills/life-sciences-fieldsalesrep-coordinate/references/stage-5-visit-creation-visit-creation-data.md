# Visit Creation Data Reference

> **Read the CSVs — do not treat these tables as authoritative.** The values below are a **snapshot** of one export of the `.lsc-starter-config/LSStarterConfig/Data/` CSV files, kept for orientation only. At execution time you MUST read the actual CSV file for each object and use **only** the values it currently contains (one record per row). If a CSV differs from a table here — added/removed columns, changed values, extra rows — the **live CSV wins**. Never hardcode these values or reuse values from a previous run.
>
> **Do NOT narrate the difference to the user.** The example values here (e.g. `Immunexis 5mg`) are illustrative placeholders, not data — silently use whatever the live CSV contains and never tell the user that the live data differs from these examples, name a specific CSV row, or comment that the real product is a hierarchy rather than the sample product. Announcing the mismatch leaks internal data structure into user-facing output (against the "never mention the CSVs or underlying data in user-facing notes" rule) and adds noise. Just read the CSV and create the records.

Field values for all records, sourced from `.lsc-starter-config/LSStarterConfig/Data/` CSV files.

## Source folder & object→CSV mapping

The CSVs come from the public repo <https://github.com/SalesforceLabs/LSStarterConfig.git>. As an embedded Stage 5, this stage is a pure consumer of the `.lsc-starter-config/LSStarterConfig/` folder and MUST NOT download or delete it — the coordinator (`life-sciences-fieldsalesrep-coordinate`) is the sole owner of the single download (at the start of the run) and the single delete (at the end). If the folder is not present when this stage runs, stop and report that it must be provisioned by the coordinator; do not fetch it here.

Each object maps to a CSV named for the sobject (lowercased) under `.lsc-starter-config/LSStarterConfig/Data/`:

| Object | CSV file |
|---|---|
| Account | `account.csv` |
| HealthcareProvider | `healthcareprovider.csv` |
| ContactPointAddress | `contactpointaddress.csv` |
| ObjectTerritory2Association | `objectterritory2association.csv` |
| ProviderAcctTerritoryInfo | `provideracctterritoryinfo.csv` |
| Product2 | `product2.csv` |
| LifeSciMarketableProduct | `lifescimarketableproduct.csv` |
| ProductTerritoryAvailability | `productterritoryavailability.csv` |
| Visit | `visit.csv` |
| ProviderVisit | `providervisit.csv` |
| ProviderVisitProdDetailing | `providervisitproddetailing.csv` |
| ProviderVisitProdDiscussion | `providervisitproddiscussion.csv` |

## Account (RecordType: Health_Care_Provider)

| Field | Value | Source |
|-------|-------|--------|
| FirstName | Aaron | account.csv |
| LastName | Morita | account.csv |
| Salutation | Dr. | account.csv |
| RecordType DeveloperName | Health_Care_Provider | account.csv |
| IsActive | True | account.csv (standard `IsActive` boolean — NOT `IsActive__c`) |

> Created as the **rep** (`--target-org lsc-rep`). `IsActive` is the standard field; if the rep lacks FLS to it, omit and set as admin.

## HealthcareProvider

| Field | Value | Source |
|-------|-------|--------|
| Name | Aaron Morita HP | healthcareprovider.csv |
| IsActive | True | healthcareprovider.csv |
| IsPrimaryProvider | True | healthcareprovider.csv |
| ProviderType | Medical Doctor | healthcareprovider.csv |
| Status | Active | healthcareprovider.csv |
| AccountId | (from Step 2) | FK |

> Do NOT set `NationalProviderIdentifier` or `IsSpeaker` on creation. Both — along with `IsActive` — are gated by field-level security on the LSC Custom Profile; if the rep lacks FLS the create fails. `IsSpeaker` and `NationalProviderIdentifier` are not required for the visit, so omit them (an admin can set them later). The CSV lists them because it was exported from an org where the profile had FLS to those fields.

## ContactPointAddress

| Field | Value | Source |
|-------|-------|--------|
| Name | 415 Mission St | contactpointaddress.csv |
| AddressType | Billing | contactpointaddress.csv |
| Street | 415 Mission St | contactpointaddress.csv |
| City | San Francisco | contactpointaddress.csv |
| State | California | contactpointaddress.csv |
| StateCode | CA | contactpointaddress.csv |
| PostalCode | 94105 | contactpointaddress.csv |
| Country | United States | contactpointaddress.csv |
| CountryCode | US | contactpointaddress.csv |
| Latitude | 37.789853 | contactpointaddress.csv |
| Longitude | -122.396806 | contactpointaddress.csv |
| IsActive | True | contactpointaddress.csv |
| IsPrimary | True | contactpointaddress.csv |
| UsageType | Work | contactpointaddress.csv |
| ParentId | (from Step 2 — Account) | FK |

## ObjectTerritory2Association

| Field | Value | Source |
|-------|-------|--------|
| ObjectId | (from Step 2 — Account) | FK |
| Territory2Id | (queried — level-3 territory) | FK |
| AssociationCause | Territory2Manual | objectterritory2association.csv |

> Create as **admin** (`--target-org <admin>`) — the rep profile lacks "Manage Territories" so OT2A is `createable=false` for the rep. Not referenced by any later record; may be skipped if admin access is unavailable.

## ProviderAcctTerritoryInfo

| Field | Value | Source |
|-------|-------|--------|
| AccountId | (from Step 2) | FK |
| Territory2Id | (queried — level-3 territory) | FK |
| PreferredAddressId | (from Step 4 — ContactPointAddress) | FK |
| IsActive | True | provideracctterritoryinfo.csv |
| IsAvailableOffline | True | provideracctterritoryinfo.csv |
| IsTargetedAccount | True | provideracctterritoryinfo.csv |
| SourceType | Manual | provideracctterritoryinfo.csv |

## Product2 (NO RecordType)

| Field | Value | Source |
|-------|-------|--------|
| Name | Immunexis 5mg | product2.csv |
| ProductCode | IM001-5 | product2.csv |
| IsActive | True | product2.csv |

> Do NOT set RecordTypeId — this is an explicit requirement.
> Create as **admin** — the rep profile has no create permission on Product2 (`Name` is `createable=false`, `ProductCode` invisible for the rep). Steps 7–9 (Product2, LifeSciMarketableProduct, ProductTerritoryAvailability) are all admin-owned master data.

## LifeSciMarketableProduct

| Field | Value | Source |
|-------|-------|--------|
| Name | Immunexis 5mg | lifescimarketableproduct.csv |
| ProductId | (from Step 7 — Product2) | FK |
| IsActive | True | lifescimarketableproduct.csv |
| IsAvlForSamplingAllocation | True | lifescimarketableproduct.csv |
| Manufacturer | Makana Health | lifescimarketableproduct.csv |
| DistributionMethod | Drop | lifescimarketableproduct.csv |
| SignatureRequirementLevel | Mandatory | lifescimarketableproduct.csv |
| SortOrder | 100 | lifescimarketableproduct.csv |
| StartDate | 2026-07-01 | lifescimarketableproduct.csv |
| Type | Product | lifescimarketableproduct.csv |

## ProductTerritoryAvailability

| Field | Value | Source |
|-------|-------|--------|
| ProductId | (from Step 8 — LifeSciMarketableProduct) | FK |
| TerritoryId | (queried — level-3 territory) | FK |
| AlignmentType | Territory Inclusion | productterritoryavailability.csv |
| Purpose | Visit | productterritoryavailability.csv |
| Status | Draft | productterritoryavailability.csv |
| UsageType | LifeSciences | productterritoryavailability.csv |

## Visit

| Field | Value | Source |
|-------|-------|--------|
| AccountId | (from Step 2) | FK |
| PlaceId | (from Step 4 — ContactPointAddress) | FK |
| PlannedVisitStartTime | NOW (generated at runtime) | requirement |
| Status | Planned | visit.csv |
| TerritoryId | (queried — level-3 territory) | FK |

## ProviderVisit

| Field | Value | Source |
|-------|-------|--------|
| VisitId | (from Step 10) | FK |
| TerritoryName | (queried territory Name) | providervisit.csv |
| IsConfirmed | False | providervisit.csv |

## ProviderVisitProdDetailing

| Field | Value | Source |
|-------|-------|--------|
| ProviderVisitId | (from Step 11) | FK |
| ProductId | (from Step 8 — LifeSciMarketableProduct) | FK |
| Priority | 4 | providervisitproddetailing.csv |
| AdditionalInformation | Discussed Oncology products and treatments | providervisitproddetailing.csv |
| IsGeneratedFromPresentation | False | providervisitproddetailing.csv |

## ProviderVisitProdDiscussion

| Field | Value | Source |
|-------|-------|--------|
| ProviderVisitProductDtlId | (from Step 12) | FK |
| Note | Discussed Oncology treatments and patient care approaches | providervisitproddiscussion.csv |

---

## Manual iPad Mobile-App Validation (Step 16)

Final, **manual** step — a tester logs into the Life Sciences Cloud iPad app as the **rep** and confirms the Visit is visible.

- **App Store**: Life Sciences Cloud Mobile — <https://apps.apple.com/us/app/life-sciences-cloud-mobile/id6499238627>
- **Login**: open the app, log in with the rep credentials, wait for the initial sync (downloads org data + mobile metadata cache; 3-5 minutes on first login), then land on the Home page.
- **Navigate**: Home page → **Visits** tab (list of Visits) → tap the Visit name/row → Visit details.
- **Confirmation prompt**: "Do you see the Visit '00000001' for Account 'Dr. Aaron Morita' in the iPad app?" (substitute the actual Visit Name and Account Name from the run).

### Troubleshooting (Visit not visible)

| Check | How to verify | Fix |
|---|---|---|
| Rep is assigned to the level-3 territory | `SELECT Id, Territory2.Name FROM UserTerritory2Association WHERE UserId = '<repUserId>'` | If missing, assign via Stage 4 (User Provisioning) |
| `ProviderAcctTerritoryInfo` exists for the Account + territory | `SELECT Id, AccountId, Territory2Id, IsActive FROM ProviderAcctTerritoryInfo WHERE AccountId = '<accountId>'` | If missing/inactive, (re)create Step 6 with `IsActive=true`, `IsAvailableOffline=true` |
| Mobile sync metadata cache available and current | `SELECT Id, Status, LastModifiedDate FROM LifeSciMobileMetadataRecord ORDER BY LastModifiedDate DESC` | Records must be `Status='Active'`; if not, re-run Steps 14–15, then re-sync on the iPad |

> Common root cause: the app synced **before** the territory assignment, `ProviderAcctTerritoryInfo`, or metadata cache existed. After fixing the data, have the tester **force a re-sync** (pull-to-refresh on the Visits list, or log out and back in), then re-ask the confirmation prompt.

---

## Dependency Chain

```text
Account (Step 2)
├── HealthcareProvider (Step 3) — AccountId
├── ContactPointAddress (Step 4) — ParentId
├── ObjectTerritory2Association (Step 5) — ObjectId
├── ProviderAcctTerritoryInfo (Step 6) — AccountId, PreferredAddressId (Step 4)
└── Visit (Step 10) — AccountId, PlaceId (Step 4), TerritoryId

Product2 (Step 7)
└── LifeSciMarketableProduct (Step 8) — ProductId
    └── ProductTerritoryAvailability (Step 9) — ProductId (Step 8)
    └── ProviderVisitProdDetailing (Step 12) — ProductId (Step 8)

Visit (Step 10)
└── ProviderVisit (Step 11) — VisitId
    └── ProviderVisitProdDetailing (Step 12) — ProviderVisitId
        └── ProviderVisitProdDiscussion (Step 13) — ProviderVisitProductDtlId
```

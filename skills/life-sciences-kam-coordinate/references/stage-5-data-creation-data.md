# KAM Data Creation — Field Reference

> **Read the CSVs — do not treat these tables as authoritative.** The values below are a **snapshot** of one export of the `.lsc-starter-config/LSStarterConfig/Data/` CSV files, kept for orientation only. At execution time you MUST read the actual CSV for each object and use **only** the values it currently contains (one record per row). If a CSV differs from a table here — added/removed columns, changed values, extra rows — the **live CSV wins**. Never hardcode these values or reuse values from a previous run.
>
> **Do NOT narrate the difference to the user.** The example values here (e.g. `Immunexis 5mg`) are illustrative placeholders, not data — silently use whatever the live CSV contains and never tell the user that the live data differs from these examples, name a specific CSV row, or comment on the underlying data structure.

Field values for all KAM records, sourced from `.lsc-starter-config/LSStarterConfig/Data/` CSV files (plus the explicit HCO account bundle). **All records are created as the ADMIN** (`--target-org <admin>`) — in the KAM workflow the end user does not exist yet (Stage 6), so there is no rep/admin split and no login-as-rep step.

## Source folder & object→CSV mapping

The CSVs come from <https://github.com/SalesforceLabs/LSStarterConfig.git>. As an embedded Stage 5, this stage is a pure consumer of `.lsc-starter-config/LSStarterConfig/` and MUST NOT download or delete it — the coordinator (`life-sciences-kam-coordinate`) owns the single download (start) and single delete (end). If the folder is absent when this stage runs, stop and report it must be provisioned by the coordinator.

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

> **No Visit chain.** The KAM workflow does NOT create `Visit`, `ProviderVisit`, `ProviderVisitProdDetailing`, or `ProviderVisitProdDiscussion`. Ignore those CSVs.

## HCP Account (RecordType: Health_Care_Provider)

This is the CSV-driven **person** account (an individual provider). The HCO (organization) account is a separate bundle below.

| Field | Value | Source |
|-------|-------|--------|
| FirstName | Aaron | account.csv |
| LastName | Morita | account.csv |
| Salutation | Dr. | account.csv |
| RecordType DeveloperName | Health_Care_Provider | account.csv |
| IsActive | True | account.csv (standard `IsActive` boolean — NOT `IsActive__c`) |

## HealthcareProvider

| Field | Value | Source |
|-------|-------|--------|
| Name | Aaron Morita HP | healthcareprovider.csv |
| IsActive | True | healthcareprovider.csv |
| IsPrimaryProvider | True | healthcareprovider.csv |
| ProviderType | Medical Doctor | healthcareprovider.csv |
| Status | Active | healthcareprovider.csv |
| AccountId | (from Account) | FK |

> As admin you have FLS to all fields, so `NationalProviderIdentifier` and `IsSpeaker` may be set if the CSV lists them. If a create fails on a field, omit it and continue — those two are not required by any KAM downstream record.

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
| ParentId | (from HCP Account) | FK |

## HCO Account bundle — Partners Healthcare (explicit values, NOT from CSV)

In addition to the CSV-driven HCP account above, create a **Health Care Organization (HCO)** account and its provider and address. These three records use the **explicit values below** — they are **not** rows in any CSV (only the HCO ContactPointAddress reuses the CSV's address values). Both the Account and the HealthcareProvider use the **`Health_Care_Organization`** record type — look up each record type's Id by `DeveloperName` + `SobjectType` first (the DeveloperName is the same on both objects; the `SobjectType` differs):

```bash
# RecordTypeId for the HCO Account
sf data query --query "SELECT Id FROM RecordType WHERE SobjectType='Account' AND DeveloperName='Health_Care_Organization'" --target-org <admin> --json
# RecordTypeId for the HCO HealthcareProvider
sf data query --query "SELECT Id FROM RecordType WHERE SobjectType='HealthcareProvider' AND DeveloperName='Health_Care_Organization'" --target-org <admin> --json
```

### HCO Account (RecordType: Health_Care_Organization)

An **organization** account — use the `Name` field, not FirstName/LastName.

| Field | Value | Source |
|-------|-------|--------|
| Name | Partners Healthcare | explicit |
| IsActive | True | explicit |
| RecordTypeId | Id of Account RecordType `Health_Care_Organization` | RecordType query above |

```bash
sf data create record --sobject Account --target-org <admin> \
  --values "Name='Partners Healthcare' IsActive=true RecordTypeId=<hcoAccountRecordTypeId>" --json
```

Capture the returned **HCO Account Id** — the HCO HealthcareProvider (`AccountId`) and HCO ContactPointAddress (`ParentId`) both reference it.

### HCO HealthcareProvider

| Field | Value | Source |
|-------|-------|--------|
| Name | Partners Healthcare HP | explicit |
| AccountId | (from HCO Account) | FK — the `Partners Healthcare` Account Id |
| IsActive | True | explicit |
| IsPrimaryProvider | True | explicit |
| RecordTypeId | Id of HealthcareProvider RecordType `Health_Care_Organization` | RecordType query above |
| Status | Active | explicit |

```bash
sf data create record --sobject HealthcareProvider --target-org <admin> \
  --values "Name='Partners Healthcare HP' AccountId=<hcoAccountId> IsActive=true IsPrimaryProvider=true RecordTypeId=<hcoProviderRecordTypeId> Status=Active" --json
```

### HCO ContactPointAddress

Reuse the **exact same address values from `contactpointaddress.csv`** used for the HCP ContactPointAddress above (Name, AddressType, Street, City, State, StateCode, PostalCode, Country, CountryCode, Latitude, Longitude, IsActive, IsPrimary, UsageType) — changing **only** the parent.

| Field | Value | Source |
|-------|-------|--------|
| (all address fields) | same as the HCP `ContactPointAddress` (from `contactpointaddress.csv`) | contactpointaddress.csv |
| ParentId | (from HCO Account `Partners Healthcare`) | FK — the HCO Account, **not** the HCP Account |

```bash
# Same --values as the HCP ContactPointAddress, with ParentId pointing at the HCO Account instead.
sf data create record --sobject ContactPointAddress --target-org <admin> \
  --values "<same address fields as the HCP ContactPointAddress> ParentId=<hcoAccountId>" --json
```

Capture the returned **HCO ContactPointAddress Id** — the HCO `ProviderAcctTerritoryInfo` references it as `PreferredAddressId`.

### HCO ObjectTerritory2Association

Same field values as the HCP `ObjectTerritory2Association` below, pointing at the HCO Account and the **same Stage-3 level-3 territory**.

| Field | Value | Source |
|-------|-------|--------|
| ObjectId | (from HCO Account `Partners Healthcare`) | FK |
| Territory2Id | (Stage-3 level-3 territory) | FK |
| AssociationCause | Territory2Manual | objectterritory2association.csv |

```bash
sf data create record --sobject ObjectTerritory2Association --target-org <admin> \
  --values "ObjectId=<hcoAccountId> Territory2Id=<territoryId> AssociationCause=Territory2Manual" --json
```

### HCO ProviderAcctTerritoryInfo

Same field values as the HCP `ProviderAcctTerritoryInfo` below, pointing at the HCO Account, its ContactPointAddress, and the **same Stage-3 level-3 territory**.

| Field | Value | Source |
|-------|-------|--------|
| AccountId | (from HCO Account `Partners Healthcare`) | FK |
| Territory2Id | (Stage-3 level-3 territory) | FK |
| PreferredAddressId | (from HCO ContactPointAddress) | FK |
| IsActive | True | provideracctterritoryinfo.csv |
| IsAvailableOffline | True | provideracctterritoryinfo.csv |
| IsTargetedAccount | True | provideracctterritoryinfo.csv |
| SourceType | Manual | provideracctterritoryinfo.csv |

```bash
sf data create record --sobject ProviderAcctTerritoryInfo --target-org <admin> \
  --values "AccountId=<hcoAccountId> Territory2Id=<territoryId> PreferredAddressId=<hcoContactPointAddressId> IsActive=true IsAvailableOffline=true IsTargetedAccount=true SourceType=Manual" --json
```

## ObjectTerritory2Association

| Field | Value | Source |
|-------|-------|--------|
| ObjectId | (from Account) | FK |
| Territory2Id | (Stage-3 level-3 territory) | FK |
| AssociationCause | Territory2Manual | objectterritory2association.csv |

## ProviderAcctTerritoryInfo

| Field | Value | Source |
|-------|-------|--------|
| AccountId | (from Account) | FK |
| Territory2Id | (Stage-3 level-3 territory) | FK |
| PreferredAddressId | (from ContactPointAddress) | FK |
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

> Do NOT set RecordTypeId — explicit requirement.

## LifeSciMarketableProduct

| Field | Value | Source |
|-------|-------|--------|
| Name | Immunexis 5mg | lifescimarketableproduct.csv |
| ProductId | (from Product2) | FK |
| IsActive | True | lifescimarketableproduct.csv |
| IsAvlForSamplingAllocation | True | lifescimarketableproduct.csv |
| Manufacturer | Makana Health | lifescimarketableproduct.csv |
| DistributionMethod | Drop | lifescimarketableproduct.csv |
| SignatureRequirementLevel | Mandatory | lifescimarketableproduct.csv |
| SortOrder | 100 | lifescimarketableproduct.csv |
| StartDate | 2026-07-01 | lifescimarketableproduct.csv |
| Type | Product | lifescimarketableproduct.csv |

> Capture the resulting `LifeSciMarketableProduct` Id — Part B (plan templates) of this stage references it as the `GoalDefinitionProduct.ProductId`.

## ProductTerritoryAvailability

| Field | Value | Source |
|-------|-------|--------|
| ProductId | (from LifeSciMarketableProduct) | FK |
| TerritoryId | (Stage-3 level-3 territory) | FK |
| AlignmentType | Territory Inclusion | productterritoryavailability.csv |
| Purpose | Visit | productterritoryavailability.csv |
| Status | Draft | productterritoryavailability.csv |
| UsageType | LifeSciences | productterritoryavailability.csv |

> The `TerritoryId` MUST be the same Stage-3 level-3 territory later assigned to the KAM user (Stage 6). Otherwise the KAM user sees no product/account data.

---

## Dependency Chain

```text
HCP Account (person, Health_Care_Provider)
├── HealthcareProvider — AccountId
├── ContactPointAddress — ParentId
├── ObjectTerritory2Association — ObjectId, Territory2Id
└── ProviderAcctTerritoryInfo — AccountId, PreferredAddressId (ContactPointAddress), Territory2Id

HCO Account (organization, Health_Care_Organization — Partners Healthcare)
├── HealthcareProvider (Partners Healthcare HP) — AccountId
├── ContactPointAddress — ParentId (same CSV address values)
├── ObjectTerritory2Association — ObjectId, Territory2Id
└── ProviderAcctTerritoryInfo — AccountId, PreferredAddressId (HCO ContactPointAddress), Territory2Id

Product2
└── LifeSciMarketableProduct — ProductId
    └── ProductTerritoryAvailability — ProductId, TerritoryId
```

Create in the order: HCP Account → HealthcareProvider → ContactPointAddress → ObjectTerritory2Association → ProviderAcctTerritoryInfo → HCO Account → HCO HealthcareProvider → HCO ContactPointAddress → HCO ObjectTerritory2Association → HCO ProviderAcctTerritoryInfo → Product2 → LifeSciMarketableProduct → ProductTerritoryAvailability.

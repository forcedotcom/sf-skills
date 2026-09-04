# Prerequisite Checks — Org-Level Sharing and Data Settings

Covers the org-wide sharing and data-feature checks: OWD sharing, inventory count, sales account plans, care plans, chatter, data protection, multiple currencies, state/country picklists, and person accounts. For the user-access, managed-package, Life Sciences CE feature, and survey checks, see `checks-user-and-package.md`.

Each section contains: the sf CLI command to run, how to interpret the result, and the remediation steps if the check fails.

All Tooling API queries use `sf data query --target-org <org> --json --use-tooling-api`. Replace `<org>` with the target org alias.

---

## OWD Sharing

### Check 4 — Organization-Wide Defaults

Query OWD via `EntityDefinition` in the Tooling API:

```bash
sf data query --query "SELECT ExternalSharingModel, InternalSharingModel, QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName IN ('Account','Case')" --target-org <org> --json --use-tooling-api
```

**Status: this is a WARNING-level check, not a hard FAIL.** OWD values are org-configuration preferences that depend on how Life Sciences Cloud is deployed. When they differ from the expected values below, record the row as **WARNING** (with the recommended value in the remediation column), not FAIL — do not block on it.

**Expected values**:

| Object | Expected InternalSharingModel | Expected ExternalSharingModel |
|--------|-------------------------------|-------------------------------|
| Account | Private | Private |
| Case | Private | Private |

> Note: In the API response, `Private` means "Private" OWD and `ReadWrite` means "Public Read/Write".

**Remediation if the values differ (WARNING):**

1. Navigate to **Setup > Security > Sharing Settings**
2. Click **Edit** in the Organization-Wide Defaults section
3. Recommended values:
   - **Account**: Private
   - **Case**: Private
4. Click **Save**
5. Confirm the changes when prompted (recalculation may take time)

---

## Inventory Count

### Check 5 — Inventory Count Enabled

**Field** (from IndustriesSettings Metadata): `enableVisitInventoryEnabled`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Inventory Management > Inventory Count Settings**
2. Enable **Inventory Count**
3. Click **Save**

---

## Sales Account Plans

### Check 6 — Sales Account Plans Enabled

**Field** (from IndustriesSettings Metadata): `enableLSC4CEKeyAccountManagement`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Sales > Accounts > Account Plans > Sales Account Plans**
2. Toggle **Switch on Sales Account Plans** to enabled
3. Click **Save**

---

## Care Plans

### Check 7 — Care Plans Enabled

**Field** (from IndustriesSettings Metadata): `enableCarePlansPreference`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Program and Case Management > Care Plan Settings**
2. Enable **Care Plans**
3. Click **Save**

---

## Chatter Settings

### Check 8 — Chatter Enabled

```bash
sf data query --query "SELECT IsChatterEnabled FROM ChatterSettings" --target-org <org> --json --use-tooling-api
```

**Pass condition**: `IsChatterEnabled` is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Chatter > Chatter Settings**
2. Enable **Chatter Settings**
3. Click **Save**

---

## Data Protection and Privacy

### Check 9 — Data Protection and Privacy Enabled

```bash
sf data query --query "SELECT Metadata FROM PartyDataModelSettings" --target-org <org> --json --use-tooling-api
```

**Field** (from Metadata): `enableConsentManagement`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Company Settings > Data Protection and Privacy**
2. Enable **Data Protection and Privacy**
3. Click **Save**

---

## Multiple Currencies

### Check 10 — Multiple Currencies Activated

```bash
sf data query --query "SELECT Id FROM CurrencyType LIMIT 1" --target-org <org> --json
```

**Pass condition**: The query succeeds and returns at least one record. If the `CurrencyType` object is queryable, Multi-Currency is activated.

**Alternative check**: If the above fails with `INVALID_TYPE`, Multi-Currency is NOT activated.

**Remediation if failed**:

1. Navigate to **Setup > Company Settings > Company Information**
2. Click **Edit**
3. Check **Activate Multiple Currencies**
4. Click **Save**
5. Confirm the activation when prompted

> **Warning**: Activating Multiple Currencies is irreversible. Include this warning when presenting remediation steps.

---

## State and Country/Territory Picklists

### Check 11 — State and Country/Territory Picklists Enabled

```bash
sf data query --query "SELECT Metadata FROM AddressSettings" --target-org <org> --json --use-tooling-api
```

**Pass condition**: The `Metadata` response contains a `countriesAndStates` object with country data populated. If `countriesAndStates` is present and non-null, the feature is enabled.

**Remediation if failed**:

1. Navigate to **Setup > Data > State and Country/Territory Picklists**
2. Click **Enable** to enable state and country/territory picklists
3. Follow the wizard to configure your picklist values

> **Warning**: Enabling State and Country/Territory Picklists is irreversible. Include this warning when presenting remediation steps.

---

## Person Accounts

### Check 12 — Person Accounts Enabled

```bash
sf data query --query "SELECT Id FROM RecordType WHERE SobjectType = 'Account' AND IsPersonType = true LIMIT 1" --target-org <org> --json
```

**Pass condition**: At least one record returned (a person-type RecordType exists on Account).

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Sales > Accounts > Person Accounts**
2. Follow the steps to enable Person Accounts
3. This requires Record Types to be enabled on Account first

> **Warning**: Enabling Person Accounts is irreversible. Include this warning when presenting remediation steps.

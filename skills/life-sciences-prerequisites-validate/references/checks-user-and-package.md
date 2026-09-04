# Prerequisite Checks — User, Package, and Feature Setup

Covers the user-access, managed-package, Life Sciences CE feature, and survey checks. For the org-level sharing/data settings (OWD, inventory, account plans, care plans, chatter, data protection, currencies, picklists, person accounts), see `checks-org-settings.md`.

Each section contains: the sf CLI command to run, how to interpret the result, and the remediation steps if the check fails.

All Tooling API queries use `sf data query --target-org <org> --json --use-tooling-api`. Replace `<org>` with the target org alias.

---

## User Profile and Permission Sets

### Check 1a — System Administrator Profile

```bash
sf data query --query "SELECT Profile.Name FROM User WHERE Username = '<username>'" --target-org <org> --json
```

**Pass condition**: `Profile.Name` equals `System Administrator`.

**Remediation if failed**:

1. Navigate to **Setup > Users > Users**
2. Find the user and click **Edit**
3. Change **Profile** to `System Administrator`
4. Click **Save**

### Check 1b — LifeSciencesCommercialAdmin Permission Set

```bash
sf data query --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId IN (SELECT Id FROM User WHERE Username = '<username>') AND PermissionSet.Name = 'LifeSciencesCommercialAdmin'" --target-org <org> --json
```

**Pass condition**: At least one record returned.

**Remediation if failed**:

1. Navigate to **Setup > Users > Permission Sets**
2. Find `LifeSciencesCommercialAdmin` and click on it
3. Click **Manage Assignments**
4. Click **Add Assignment**
5. Select the admin user and click **Assign**

### Check 1c — HealthCloudStarter Permission Set

```bash
sf data query --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId IN (SELECT Id FROM User WHERE Username = '<username>') AND PermissionSet.Name = 'HealthCloudStarter'" --target-org <org> --json
```

**Pass condition**: At least one record returned.

**Remediation if failed**:

1. Navigate to **Setup > Users > Permission Sets**
2. Find `HealthCloudStarter` and click on it
3. Click **Manage Assignments**
4. Click **Add Assignment**
5. Select the admin user and click **Assign**

---

## Managed Package Check

### Check — lsc4ce Package Installed

Query the `InstalledSubscriberPackage` object via the Tooling API to list installed packages, then check client-side whether one has the namespace prefix `lsc4ce`:

```bash
sf data query --query "SELECT Id, SubscriberPackage.NamespacePrefix, SubscriberPackage.Name FROM InstalledSubscriberPackage" --target-org <org> --json --use-tooling-api
```

> **Do NOT add a `WHERE SubscriberPackage.NamespacePrefix = 'lsc4ce'` clause.** On `InstalledSubscriberPackage` the `SubscriberPackage.*` relationship fields are selectable but **not filterable** — a `WHERE` on them fails with `field 'SubscriberPackage' can not be filtered in query call`. Query all installed packages (there are only a handful) and inspect the results for the `lsc4ce` prefix in the agent, not in SOQL.

**Pass condition**: At least one returned record has `SubscriberPackage.NamespacePrefix == 'lsc4ce'` (the Life Sciences Cloud for Customer Engagement package is installed).

**If failed — STOP all remaining checks** and display:

> **BLOCKED: Life Sciences Cloud managed package not installed.**
>
> The managed package with namespace prefix `lsc4ce` (Life Sciences Cloud for Customer Engagement) is not installed in this org. All remaining prerequisite checks depend on this package.
>
> **Remediation:**
> 1. Obtain an org with the Life Sciences Cloud for Customer Engagement managed package installed
> 2. The package is typically provisioned through OrgFarm or installed by Salesforce as part of the Life Sciences Cloud license
> 3. Contact your Salesforce account team or provisioning admin to get an org with the `lsc4ce` package
>
> Re-run this validation after the package is installed.

**Do not proceed with any further checks if this fails.**

---

## Life Sciences Customer Engagement Setup

All Life Sciences CE settings are stored in `IndustriesSettings` via the Tooling API. Query once and check multiple fields:

```bash
sf data query --query "SELECT Metadata FROM IndustriesSettings" --target-org <org> --json --use-tooling-api
```

Parse the `Metadata` object from the first record in the response.

### Check 2a — Life Sciences Customer Engagement Enabled

**Field**: `enableLifeSciencesCustomerEngagementBase`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Toggle **Life Sciences Customer Engagement** to enabled
3. Click **Save**

### Check 2b — Enable Settings for Package Installation

**Field** (from IndustriesSettings Metadata): `enableLSC4CEPackage`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Under **Get Your Org Ready to Use Life Sciences Cloud for Customer Engagement**
3. Click the **Verify & Enable Settings** button under "Enable Settings for Package Installation"
4. Wait for the verification to complete

### Check 2c — Account-Based Sharing

**Field** (from IndustriesSettings Metadata): `enableAccountBasedSharing`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Under **Enable Life Sciences Cloud for Customer Engagement Features**
3. Enable **Account-Based Sharing**
4. Click **Save**

### Check 2d — Best Contact Time Custom Sharing

**Field** (from IndustriesSettings Metadata): `enableCPBestConTimeSharing`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Under **Enable Life Sciences Cloud for Customer Engagement Features**
3. Enable **Best Contact Time Custom Sharing**
4. Click **Save**

### Check 2e — Contact Point Social Custom Sharing

**Field** (from IndustriesSettings Metadata): `enableCPSocialCustomSharing`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Under **Enable Life Sciences Cloud for Customer Engagement Features**
3. Enable **Contact Point Social Custom Sharing**
4. Click **Save**

### Check 2f — Parent Territory Product Alignment

**Field** (from IndustriesSettings Metadata): `enablePATSTerritoryBasedSharing`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Under **Enable Life Sciences Cloud for Customer Engagement Features**
3. Enable **Parent Territory Product Alignment**
4. Click **Save**

### Check 2g — Product Hierarchy Business Group Filter

**Field** (from IndustriesSettings Metadata): `enableProdAdminBusinessGrpFilter`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Life Sciences > Life Sciences for Customer Engagement Setup**
2. Under **Enable Life Sciences Cloud for Customer Engagement Features**
3. Enable **Product Hierarchy Business Group Filter**
4. Click **Save**

---

## Surveys

### Check 3 — Surveys Enabled

```bash
sf data query --query "SELECT Metadata FROM SurveySettings" --target-org <org> --json --use-tooling-api
```

**Field** (from Metadata): `enableSurvey`

**Pass condition**: Value is `true`.

**Remediation if failed**:

1. Navigate to **Setup > Feature Settings > Survey > Survey Settings**
2. Toggle **Surveys** to enabled
3. Click **Save**

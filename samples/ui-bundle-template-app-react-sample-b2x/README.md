# Property Rental App

A property rental sample React UI Bundle for Salesforce Experience Cloud. Demonstrates property listings, maintenance requests, and a dashboard with an app shell designed for external-facing deployment. Built with React, Vite, TypeScript, and Tailwind/shadcn.

## Table of Contents

1. [What's Included](#whats-included)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Automated)](#quick-start-automated)
4. [Step-by-Step Setup](#step-by-step-setup)
   - [1. Install Dependencies](#1-install-dependencies)
   - [2. Authenticate Your Org](#2-authenticate-your-org)
   - [3. Deploy Metadata](#3-deploy-metadata)
   - [4. Assign Permission Sets](#4-assign-permission-sets)
   - [5. Import Sample Data](#5-import-sample-data)
   - [6. Generate GraphQL Types](#6-generate-graphql-types)
   - [7. Rebuild the UI Bundle](#7-rebuild-the-ui-bundle)
   - [8. Deploy the UI Bundle](#8-deploy-the-ui-bundle)
5. [Org Configuration](#org-configuration)
   - [Step 1: Assign a Role to Your Admin User](#step-1-assign-a-role-to-your-admin-user)
   - [Step 2: Create and Configure the Community Profile](#step-2-create-and-configure-the-community-profile)
   - [Step 3: Configure the Experience Cloud Site](#step-3-configure-the-experience-cloud-site)
   - [Step 4: Configure the Guest User Profile](#step-4-configure-the-guest-user-profile)
   - [Step 5: Create Criteria-Based Sharing Rules for Guest Access](#step-5-create-criteria-based-sharing-rules-for-guest-access)
6. [Local Development](#local-development)
7. [Resources](#resources)

---

## What's Included

```
force-app/main/default/
├── classes/                # Apex Logic: Triggers, Auth, and Registration
│   ├── MaintenanceRequestTriggerHandler.cls
│   ├── TenantTriggerHandler.cls
│   └── UIBundle (Auth, Login, Registration, etc.)
├── cspTrustedSites/        # External resource security (Maps, Fonts, Avatars)
├── data/                   # Sample JSON data for "sf data import tree"
├── digitalExperienceConfigs/ # Experience Cloud site configurations
├── digitalExperiences/      # Experience Cloud site definitions
├── layouts/                # Page layouts for all 17 custom objects
├── networks/               # Experience Cloud network metadata
├── objects/                # 17 Custom Objects (Property, Tenant, Lease, etc.)
├── permissionsets/         # Access: Property_Management (Admin) & Tenant (Scoped)
├── sites/                  # Salesforce Sites configuration
├── triggers/               # Apex Triggers: MaintenanceRequest & Tenant
└── uiBundles/
    └── propertyrentalapp/  # React UI Bundle (source, config, tests)
```

---

## Prerequisites

Before you begin, ensure the following are in place.

### Tools

| Tool                                                                          | Minimum Version    | Install                             |
| ----------------------------------------------------------------------------- | ------------------ | ----------------------------------- |
| [Salesforce CLI (`sf`)](https://developer.salesforce.com/tools/salesforcecli) | v2+                | `npm install -g @salesforce/cli`    |
| [Node.js](https://nodejs.org/)                                                | v22+               | [nodejs.org](https://nodejs.org/)   |
| [Git](https://git-scm.com/)                                                   | Any recent version | [git-scm.com](https://git-scm.com/) |

Verify your Salesforce CLI version with:

```bash
sf --version
```

### Salesforce Org Requirements

This project requires a Salesforce org with the following features and licenses. **Developer Edition orgs do not include these by default.** Use a sandbox, an org configured with add-ons, or request a pre-configured org from your Salesforce account team.

- **Digital Experiences (Experience Cloud) enabled** — required to deploy and run the Experience Cloud site. To verify, go to **Setup > Digital Experiences > Settings** and confirm "Enable Digital Experiences" is checked.
- **Customer Community** or **Customer Community Plus** user licenses — required to create community (portal) users. Customer Community Plus is recommended if you need record-level sharing via sharing rules.
- **Salesforce Sites enabled** — required for guest user access.

> **Note:** If Digital Experiences is not yet enabled in your org, go to **Setup > Digital Experiences > Settings**, check "Enable Digital Experiences", set a domain name, and save. This action cannot be undone.

---

## Quick Start (Automated)

Two npm scripts at the project root streamline getting started and deployment.

**`npm run sf-project-setup`** — installs the UI Bundle dependencies, builds the app, and starts the dev server (see [Local Development](#local-development)).

**`npm run setup`** — automates the full setup: login, deploy metadata, assign permission sets, import sample data, fetch the GraphQL schema, run codegen, build the UI Bundle, and optionally launch the dev server:

```bash
npm run setup -- --target-org <alias>
```

Replace `<alias>` with your target org alias or username. Running without flags presents an interactive step picker. Pass `--yes` to skip it and run all steps immediately:

```bash
npm run setup -- --target-org <alias> --yes
```

### Common Options

| Option                    | Description                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `--skip-login`            | Skip browser login (auto-skipped if org is already connected)                        |
| `--skip-deploy`           | Skip the metadata deploy step                                                        |
| `--skip-permset`          | Skip permission set assignment                                                       |
| `--skip-data`             | Skip data preparation and import                                                     |
| `--skip-graphql`          | Skip GraphQL schema fetch and codegen                                                |
| `--skip-ui-bundle-build`  | Skip `npm install` and UI Bundle build                                               |
| `--skip-dev`              | Do not launch the dev server at the end                                              |
| `--permset-name <name>`   | Assign only a specific permission set (repeatable). Default: all sets in the project |
| `--ui-bundle-name <name>` | UI Bundle folder name under `uiBundles/` (default: auto-detected)                    |
| `-y, --yes`               | Skip interactive step picker and run all enabled steps immediately                   |

For a full list of options:

```bash
npm run setup -- --help
```

> **After the automated setup completes**, proceed to [Org Configuration](#org-configuration) for the manual steps that cannot be automated via CLI (profile cloning, site member configuration, guest user setup, and publishing the Experience Cloud site).

---

## Step-by-Step Setup

Use this section if you prefer to run each step manually, or if the automated script is not available.

### 1. Install Dependencies

Install root-level project dependencies:

```bash
npm install
```

Install the UI Bundle dependencies and build it:

```bash
cd force-app/main/default/uiBundles/propertyrentalapp
npm install
npm run build
cd -
```

This produces the static bundle artifacts that are packaged into the Salesforce metadata. Having them built now means any deploy option in [Step 3](#3-deploy-metadata) is ready to run without an additional build step.

### 2. Authenticate Your Org

Log in to your target org using the Salesforce CLI. This opens a browser window for OAuth authentication:

```bash
sf org login web --alias <alias>
```

To verify the login was successful:

```bash
sf org display --target-org <alias>
```

If you are working with a sandbox, use:

```bash
sf org login web --alias <alias> --instance-url https://test.salesforce.com
```

### 3. Deploy Metadata

#### Option A: Deploy Everything (metadata + Experience Cloud site + UI Bundle)

Build the UI Bundle first, then deploy all source directories in a single command:

```bash
cd force-app/main/default/uiBundles/propertyrentalapp && npm run build && cd -
sf project deploy start --source-dir force-app --target-org <alias>
```

#### Option B: Deploy Metadata Only (objects, layouts, permission sets, Apex)

Use this approach for an initial deploy to verify metadata before deploying the Experience Cloud site:

```bash
sf project deploy start \
  --source-dir force-app/main/default/objects \
  --source-dir force-app/main/default/layouts \
  --source-dir force-app/main/default/permissionsets \
  --source-dir force-app/main/default/classes \
  --source-dir force-app/main/default/triggers \
  --source-dir force-app/main/default/cspTrustedSites \
  --target-org <alias>
```

#### Option C: Deploy Experience Cloud Site Only

```bash
sf project deploy start \
  --source-dir force-app/main/default/digitalExperienceConfigs \
  --source-dir force-app/main/default/digitalExperiences \
  --source-dir force-app/main/default/networks \
  --source-dir force-app/main/default/sites \
  --target-org <alias>
```

#### Option D: Deploy the UI Bundle Only

```bash
cd force-app/main/default/uiBundles/propertyrentalapp && npm run build && cd -
sf project deploy start --source-dir force-app/main/default/uiBundles --target-org <alias>
```

> **Deployment order matters.** Deploy metadata (Option B) before deploying the Experience Cloud site (Option C). The site configuration depends on the custom objects and classes being present in the org.

### 4. Assign Permission Sets

Two permission sets are included in this project:

| Permission Set               | Purpose                                                                                                 | Assign To                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `Property_Management_Access` | Full CRUD access to all custom objects. Intended for property managers and admin users.                 | Internal users managing the app |
| `Tenant_Maintenance_Access`  | Scoped read/write access for tenants. Allows creating and updating their own maintenance requests only. | Tenant community users          |

Assign permission sets using the CLI:

```bash
# Assign Property_Management_Access to a specific user
sf org assign permset --name Property_Management_Access --on-behalf-of <username> --target-org <alias>

# Assign Tenant_Maintenance_Access to a tenant user
sf org assign permset --name Tenant_Maintenance_Access --on-behalf-of <username> --target-org <alias>
```

To assign to multiple users, repeat the command for each user, or use the automated script which assigns all permission sets to the running user by default.

### 5. Import Sample Data

Once the metadata has been successfully deployed:

```bash
sf data import tree --plan force-app/main/default/data/data-plan.json --target-org <alias>
```

The data plan imports records in dependency order: Contacts, Agents, Maintenance Workers, Properties, Tenants, Applications, Maintenance Requests, Notifications, Property Management Companies, Property Owners, Leases, Property Sales, Property Costs, Payments, KPI Snapshots, Property Listings, Property Images, and Property Features.

> **Note:** If you re-run the import, duplicate records will be created. Wipe existing records first or use the `--upsert` flag if your plan supports it.

### 6. Generate GraphQL Types

After metadata is deployed, generate the GraphQL schema and TypeScript types for the UI Bundle. These are used to provide type-safe queries against the Salesforce GraphQL API.

```bash
cd force-app/main/default/uiBundles/propertyrentalapp
npm run graphql:schema   # Fetches schema from org → outputs schema.graphql
npm run graphql:codegen  # Generates TypeScript types → updates src/api/graphql-operations-types.ts
cd -
```

> **Prerequisite:** The org must be authenticated and metadata must already be deployed before running these commands, as the schema is generated from the org's live metadata.

### 7. Rebuild the UI Bundle

Step 6 updates the generated GraphQL types in the UI Bundle source. Rebuild the app to compile those changes into the bundle before deploying:

```bash
cd force-app/main/default/uiBundles/propertyrentalapp
npm run build
cd -
```

### 8. Deploy the UI Bundle

Once the build is complete, deploy the UI Bundle to your org:

```bash
sf project deploy start --source-dir force-app/main/default/uiBundles --target-org <alias>
```

---

## Org Configuration

The following steps must be completed manually in the Salesforce Setup UI. They configure Experience Cloud, user profiles, and data sharing for guest and community users. Complete these steps **after** the metadata and UI Bundle have been deployed.

> **License requirement:** Your org must have **Customer Community** or **Customer Community Plus** user licenses available before you can complete these steps. Customer Community Plus licenses are required if you need ownership-based record sharing (Private OWD with sharing rules). Verify available licenses at **Setup > Company Settings > Company Information**, in the "User Licenses" section.

---

### Step 1: Assign a Role to Your Admin User

Salesforce requires that the org's admin user has a role assigned before Experience Cloud sites can be created or managed. If your admin user already has a role, skip this step.

1. Go to **Setup > Users > Roles**.
2. Click **Set Up Roles**.
3. Click **Add Role**. Provide a label (e.g., `CEO`) and save.
4. From the role hierarchy, click the role you just created, then click **Assign Users to Role**.
5. Add your system administrator user and click **Save**.

> **Why this matters:** Salesforce prevents users without a role in the hierarchy from owning Experience Cloud sites. This is a platform-level requirement, not specific to this app.

---

### Step 2: Create and Configure the Community Profile

Community users require a profile that is based on one of the standard community profile templates. You will clone one of these templates and configure its permissions for this app.

#### 2a. Clone the Base Profile

1. Go to **Setup > Users > Profiles**.
2. Locate either **Customer Community User** or **Customer Community Plus User**.
   - Choose **Customer Community Plus User** if you need ownership-based record-level sharing (recommended).
3. Click **Clone** next to the profile. Give it a descriptive name such as `Property Rental Tenant`.
4. Click **Save**.

#### 2b. Edit the Cloned Profile

Open the newly cloned profile and configure the following settings.

**Administrative Permissions:**

| Permission  | Setting |
| ----------- | ------- |
| API Enabled | Checked |

**Custom Object Permissions:**

Set the following object-level access. After saving, also review field-level security for each object to ensure all relevant fields are readable.

| Object                                                           | Read | Create | Edit | Delete |
| :--------------------------------------------------------------- | :--: | :----: | :--: | :----: |
| Agents (`Agent__c`)                                              |  ✓   |        |      |        |
| Applications (`Application__c`)                                  |  ✓   |   ✓    |  ✓   |   ✓    |
| KPI Snapshots (`KPI_Snapshot__c`)                                |  ✓   |        |      |        |
| Leases (`Lease__c`)                                              |  ✓   |        |      |        |
| Maintenance Requests (`Maintenance_Request__c`)                  |  ✓   |   ✓    |  ✓   |   ✓    |
| Maintenance Workers (`Maintenance_Worker__c`)                    |  ✓   |        |  ✓   |        |
| Notifications (`Notification__c`)                                |  ✓   |        |      |        |
| Payments (`Payment__c`)                                          |  ✓   |        |      |        |
| Properties (`Property__c`)                                       |  ✓   |        |      |        |
| Property Costs (`Property_Cost__c`)                              |  ✓   |        |      |        |
| Property Features (`Property_Feature__c`)                        |  ✓   |        |      |        |
| Property Images (`Property_Image__c`)                            |  ✓   |        |      |        |
| Property Listings (`Property_Listing__c`)                        |  ✓   |        |      |        |
| Property Management Companies (`Property_Management_Company__c`) |  ✓   |        |      |        |
| Property Owners (`Property_Owner__c`)                            |  ✓   |        |      |        |
| Property Sales (`Property_Sale__c`)                              |  ✓   |        |      |        |
| Tenants (`Tenant__c`)                                            |  ✓   |        |      |        |

**Apex Class Access:**

Scroll to the **Enabled Apex Class Access** section and add the following classes. These classes handle authentication flows called by the UI Bundle:

- `UIBundleAuthUtils`
- `UIBundleChangePassword`
- `UIBundleForgotPassword`

> **Note:** `MaintenanceRequestTriggerHandler` and `TenantTriggerHandler` are trigger handler classes that run in system context when DML operations are performed. They do not need to be explicitly enabled in community profiles.

#### 2c. Configure View All for Property, Property Listing, Maintenance Worker

Tenants need to see all available properties and listings, not just records they own. Enable **View All** on these three objects for the community profile:

1. Go to **Setup > Object Manager**.
2. Search for and open **Property**.
3. Click **Object Access** in the left navigation.
4. Set the profile's access to allow viewing all records.
5. Repeat for **Property Listing** and **Maintenance Worker**.

- **Note**: the access for the **Maintenance Worker** is required for the `MaintenanceRequestTriggerHandler` to auto assign a worker on submission

#### 2d. Configure Field Level Security for the Application

1. Go to **Setup > Object Manager**.
2. Search for and open **Application**.
3. Click **Fields and Relationships** in the left navigation.
4. Select the `References__c` field, then click **Set Field-Level Security**.
5. Enable the field to be "Visible" to the community profile.
6. Click **Save**.
7. Repeat for the following fields:

- `Property__c`
- `Employment__c`
- `User__c`
- `Status__c`
- `Start_Date__c`

---

### Step 3: Configure the Experience Cloud Site

After deploying the Experience Cloud site metadata, configure its membership and self-registration settings.

1. In the App Launcher, open the **Digital Experiences** app (search for it if needed).
2. Find the **Property Rental App** site and click **Workspaces**.
3. Click the **Administration** tile.

#### Members

1. In the left navigation, click **Members**.
2. Under **Select Profiles**, add the cloned community profile (`Property Rental Tenant`) to the **Selected Profiles** list.
3. Click **Save**.

#### Login & Registration

1. In the left navigation, click **Login & Registration**.
2. Check **Allow customers and partners to self-register**.
3. Under **Registration**, set:
   - **Profile**: Select your cloned community profile (`Property Rental Tenant`).
   - **Account**: Select or create an account record to associate self-registered users with (e.g., a generic "Portal Account").
4. Click **Save**.

#### Guest User Profile

The site's guest user profile controls what unauthenticated visitors can see. You will configure this profile in [Step 4](#step-4-configure-the-guest-user-profile). To navigate to it:

1. In the **Administration** area, click **Preferences** in the left navigation.
2. Click the link next to **Guest user profile** to open it directly.

---

### Step 4: Configure the Guest User Profile

The guest user profile is auto-generated by Salesforce when an Experience Cloud site is created. It controls what unauthenticated visitors can access. Configure it to allow browsing of available properties only.

Open the guest user profile (linked from the site's Preferences page, as described above) and apply the following settings.

**Administrative Permissions:**

| Permission  | Setting |
| ----------- | ------- |
| API Enabled | Checked |

> **Security note:** Enabling API access for the guest profile is required for the UI Bundle to make GraphQL API calls on behalf of unauthenticated users. Ensure that object-level and field-level permissions are restrictive (as listed below) to avoid exposing sensitive data.

**Custom Object Permissions:**

Guest users can only browse available properties and listings. All other objects are restricted.

| Object                                    | Read | Create | Edit | Delete |
| :---------------------------------------- | :--: | :----: | :--: | :----: |
| Properties (`Property__c`)                |  ✓   |        |      |        |
| Property Costs (`Property_Cost__c`)       |  ✓   |        |      |        |
| Property Features (`Property_Feature__c`) |  ✓   |        |      |        |
| Property Images (`Property_Image__c`)     |  ✓   |        |      |        |
| Property Listings (`Property_Listing__c`) |  ✓   |        |      |        |
| All other objects                         |  —   |   —    |  —   |   —    |

**Apex Class Access:**

Add the following classes. These are required for the self-registration and login flows available to unauthenticated users:

- `UIBundleLogin`
- `UIBundleRegistration`

---

### Step 5: Create Criteria-Based Sharing Rules for Guest Access

By default, Salesforce does not expose any records to guest users. You must create **criteria-based sharing rules** to make available properties and listings visible to unauthenticated site visitors.

> **Organization-Wide Defaults (OWD):** Criteria-based sharing rules for guest users only work correctly when the object's OWD is set to **Public Read Only** or **Private**. Verify your OWD settings at **Setup > Sharing Settings** before proceeding.

#### Create a Sharing Rule for Properties

1. Go to **Setup > Sharing Settings**.
2. Scroll to the **Property Sharing Rules** section and click **New**.
3. Configure the rule:
   - **Label**: `Available Properties for Guest Users`
   - **Rule Type**: Select **Guest user access, based on criteria**
   - **Criteria**: `Status Equals Available` (adjust the field and value to match your data model)
   - **Share with**: Select **Guests of the Property Rental App site** (the guest user group for your Experience Cloud site)
   - **Access Level**: `Read Only`
4. Click **Save**.

#### Create a Sharing Rule for Property Listings

Repeat the same steps in the **Property Listing Sharing Rules** section:

- **Label**: `Available Property Listings for Guest Users`
- **Rule Type**: `Guest user access, based on criteria`
- **Criteria**: Match listings you want to expose (e.g., `Status Equals Active`)
- **Share with**: `Guests of the Property Rental App site`
- **Access Level**: `Read Only`

> **Note:** The "Guests of [site name]" option only appears in the sharing rule target list after the Experience Cloud site has been created and saved. If you do not see it, confirm the site metadata has been deployed and the site exists in the org.

---

## Local Development

Install project dependencies and start the dev server:

```bash
npm install
npm run sf-project-setup
```

This installs the UI Bundle dependencies, builds the app, and opens the dev server at `http://localhost:5173`. For manual build and test instructions, see the [UI Bundle README](force-app/main/default/uiBundles/propertyrentalapp/README.md).

---

## Resources

- [Salesforce Extensions Documentation](https://developer.salesforce.com/tools/vscode/)
- [Salesforce CLI Setup Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_intro.htm)
- [Salesforce DX Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_intro.htm)
- [Salesforce CLI Command Reference](https://developer.salesforce.com/docs/atlas.en-us.sfdx_cli_reference.meta/sfdx_cli_reference/cli_reference.htm)
- [Experience Cloud Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.communities_dev.meta/communities_dev/communities_dev_intro.htm)
- [Salesforce DX Project Configuration](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_ws_config.htm)

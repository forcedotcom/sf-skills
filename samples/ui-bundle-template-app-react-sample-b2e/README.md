# Property Management App

A property management sample React UI Bundle for the Salesforce platform. Demonstrates property management, maintenance requests, tenant applications, a dashboard, and an Agentforce conversation client. Built with React, Vite, TypeScript, and Tailwind/shadcn.

## Table of Contents

1. [What's Included](#whats-included)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Automated)](#quick-start-automated)
4. [Step-by-Step Setup](#step-by-step-setup)
   - [1. Install Dependencies](#1-install-dependencies)
   - [2. Authenticate Your Org](#2-authenticate-your-org)
   - [3. Deploy Metadata](#3-deploy-metadata)
   - [4. Assign Permission Set](#4-assign-permission-set)
   - [5. Import Sample Data](#5-import-sample-data)
   - [6. Generate GraphQL Types](#6-generate-graphql-types)
   - [7. Rebuild the UI Bundle](#7-rebuild-the-ui-bundle)
   - [8. Deploy the UI Bundle](#8-deploy-the-ui-bundle)
   - [9. Agentforce Conversation Client](#9-agentforce-conversation-client)
5. [Local Development](#local-development)
6. [Resources](#resources)

---

## What's Included

```
force-app/main/default/
├── uiBundles/            # React UI Bundle (source, config, tests)
├── objects/              # 17 Custom Objects (Property, Tenant, Lease, etc.)
├── layouts/              # Page layouts for all custom objects
├── permissionsets/       # Property_Management_Access (Full CRUD)
└── data/                 # Sample JSON data (use: sf data import tree)
```

---

## Prerequisites

Before you begin, ensure the following are in place.

| Tool                                                                          | Minimum Version    | Install                             |
| ----------------------------------------------------------------------------- | ------------------ | ----------------------------------- |
| [Salesforce CLI (`sf`)](https://developer.salesforce.com/tools/salesforcecli) | v2+                | `npm install -g @salesforce/cli`    |
| [Node.js](https://nodejs.org/)                                                | v22+               | [nodejs.org](https://nodejs.org/)   |
| [Git](https://git-scm.com/)                                                   | Any recent version | [git-scm.com](https://git-scm.com/) |

Verify your Salesforce CLI version with:

```bash
sf --version
```

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
cd force-app/main/default/uiBundles/propertymanagementapp
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

#### Option A: Deploy Everything (metadata + UI Bundle)

Build the UI Bundle first, then deploy all source in a single command:

```bash
cd force-app/main/default/uiBundles/propertymanagementapp && npm run build && cd -
sf project deploy start --source-dir force-app --target-org <alias>
```

#### Option B: Deploy Metadata Only (objects, layouts, permission sets)

```bash
sf project deploy start \
  --source-dir force-app/main/default/objects \
  --source-dir force-app/main/default/layouts \
  --source-dir force-app/main/default/permissionsets \
  --target-org <alias>
```

#### Option C: Deploy the UI Bundle Only

```bash
cd force-app/main/default/uiBundles/propertymanagementapp && npm run build && cd -
sf project deploy start --source-dir force-app/main/default/uiBundles --target-org <alias>
```

Replace `<alias>` with your target org alias.

### 4. Assign Permission Set

After deploying the metadata, assign the `Property_Management_Access` permission set to grant access to the custom objects and fields:

```bash
sf org assign permset --name Property_Management_Access --target-org <alias>
```

To assign to a specific user:

```bash
sf org assign permset --name Property_Management_Access --on-behalf-of <username> --target-org <alias>
```

Replace `<alias>` with your target org alias.

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
cd force-app/main/default/uiBundles/propertymanagementapp
npm run graphql:schema   # Fetches schema from org → outputs schema.graphql
npm run graphql:codegen  # Generates TypeScript types → updates src/api/graphql-operations-types.ts
cd -
```

> **Prerequisite:** The org must be authenticated and metadata must already be deployed before running these commands, as the schema is generated from the org's live metadata.

### 7. Rebuild the UI Bundle

Step 6 updates the generated GraphQL types in the UI Bundle source. Rebuild the app to compile those changes into the bundle before deploying:

```bash
cd force-app/main/default/uiBundles/propertymanagementapp
npm run build
cd -
```

### 8. Deploy the UI Bundle

Once the build is complete, deploy the UI Bundle to your org:

```bash
sf project deploy start --source-dir force-app/main/default/uiBundles --target-org <alias>
```

### 9. Agentforce Conversation Client

The sample app includes an Agentforce Conversation Client (ACC) placeholder component in `applayout.tsx`. The ACC component requires a valid `agentId` for an agent that exists in the org. The options to create an agent specific to this use-case are:

- **Agentforce Vibes:** Generate agent metadata with the extension, then deploy it to the org.
- **Agentforce Builder:** Create the agent in the UI. See [Set Up Your Agent](https://help.salesforce.com/s/articleView?id=ai.agent_parent_setup.htm&type=5).

---

## Local Development

Install project dependencies and start the dev server:

```bash
npm install
npm run sf-project-setup
```

This installs the UI Bundle dependencies, builds the app, and opens the dev server at `http://localhost:5173`. For manual build and test instructions, see the [UI Bundle README](force-app/main/default/uiBundles/propertymanagementapp/README.md).

---

## Resources

- [Salesforce Extensions Documentation](https://developer.salesforce.com/tools/vscode/)
- [Salesforce CLI Setup Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_intro.htm)
- [Salesforce DX Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_intro.htm)
- [Salesforce CLI Command Reference](https://developer.salesforce.com/docs/atlas.en-us.sfdx_cli_reference.meta/sfdx_cli_reference/cli_reference.htm)
- [Salesforce DX Project Configuration](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_ws_config.htm)

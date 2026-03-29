# Property Management App

A property management sample React UI Bundle for the Salesforce platform. Demonstrates property management, maintenance requests, tenant applications, a dashboard, and an Agentforce conversation client. Built with React, Vite, TypeScript, and Tailwind/shadcn.

## What's included

| Path                                                      | Description                                                                                                                                                                                                                                                                                                                                                       |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `force-app/main/default/uiBundles/propertymanagementapp/` | React UI Bundle (source, config, tests)                                                                                                                                                                                                                                                                                                                           |
| `force-app/main/default/objects/`                         | 17 custom objects — Agent\_\_c, Application\_\_c, KPI_Snapshot\_\_c, Lease\_\_c, Maintenance_Request\_\_c, Maintenance_Worker\_\_c, Notification\_\_c, Payment\_\_c, Property\_\_c, Property_Cost\_\_c, Property_Feature\_\_c, Property_Image\_\_c, Property_Listing\_\_c, Property_Management_Company\_\_c, Property_Owner\_\_c, Property_Sale\_\_c, Tenant\_\_c |
| `force-app/main/default/layouts/`                         | Page layouts for each custom object                                                                                                                                                                                                                                                                                                                               |
| `force-app/main/default/permissionsets/`                  | `Property_Management_Access` permission set                                                                                                                                                                                                                                                                                                                       |
| `force-app/main/default/data/`                            | Sample data (JSON) for all objects, importable via `sf data import tree`                                                                                                                                                                                                                                                                                          |

## Getting started

Navigate to the UI Bundle and install dependencies:

```bash
cd force-app/main/default/uiBundles/propertymanagementapp
npm install
npm run dev
```

Opens at http://localhost:5173 by default. For build and test instructions, see the [UI Bundle README](force-app/main/default/uiBundles/propertymanagementapp/README.md).

## Deploy

### Deploy everything (metadata + UI Bundle)

```bash
cd force-app/main/default/uiBundles/propertymanagementapp && npm install && npm run build && cd -
sf project deploy start --source-dir force-app --target-org <alias>
```

### Deploy the UI Bundle only

```bash
cd force-app/main/default/uiBundles/propertymanagementapp && npm install && npm run build && cd -
sf project deploy start --source-dir force-app/main/default/ui-bundles --target-org <alias>
```

### Deploy metadata only (objects, layouts, permission sets)

```bash
sf project deploy start \
  --source-dir force-app/main/default/objects \
  --source-dir force-app/main/default/layouts \
  --source-dir force-app/main/default/permissionsets \
  --target-org <alias>
```

Replace `<alias>` with your target org alias.

## Assign permset

After deploying the metadata, assign the `Property_Management_Access` permission set to your user to grant access to the custom objects and fields:

```bash
sf org assign permset -n Property_Management_Access --target-org <alias>
```

Replace `<alias>` with your target org alias.

## Import sample data

```bash
sf data import tree --plan force-app/main/default/data/data-plan.json --target-org <alias>
```

## Using setup-cli.mjs

When this app is built (e.g. from the monorepo or from a published package), a `setup-cli.mjs` script is included at the project root. It runs the full setup in one go: login (if needed), deploy metadata, assign the `Property_Management_Access` permission set, prepare and import sample data, fetch GraphQL schema and run codegen, build the UI Bundle, and optionally start the dev server.

Run from the **project root** (the directory that contains `force-app/`, `sfdx-project.json`, and `setup-cli.mjs`):

```bash
node setup-cli.mjs --target-org <alias>
```

Common options:

| Option                   | Description                                                      |
| ------------------------ | ---------------------------------------------------------------- |
| `--skip-login`           | Skip browser login (org already authenticated)                   |
| `--skip-data`            | Skip data preparation and import                                 |
| `--skip-graphql`         | Skip GraphQL schema fetch and codegen                            |
| `--skip-ui-bundle-build` | Skip `npm install` and UI Bundle build                           |
| `--skip-dev`             | Do not start the dev server at the end                           |
| `--permset <name>`       | Permission set to assign (default: `Property_Management_Access`) |
| `--app <name>`           | Web app folder name when multiple exist                          |

For all options: `node setup-cli.mjs --help`.

## Configure Your Salesforce DX Project

The `sfdx-project.json` file contains useful configuration information for your project. See [Salesforce DX Project Configuration](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_ws_config.htm) in the _Salesforce DX Developer Guide_ for details about this file.

## Read All About It

- [Salesforce Extensions Documentation](https://developer.salesforce.com/tools/vscode/)
- [Salesforce CLI Setup Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_intro.htm)
- [Salesforce DX Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_intro.htm)
- [Salesforce CLI Command Reference](https://developer.salesforce.com/docs/atlas.en-us.sfdx_cli_reference.meta/sfdx_cli_reference/cli_reference.htm)

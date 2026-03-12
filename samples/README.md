# Samples

Sample apps and templates synced into this repo for reference and reuse.

## webapp-template-app-react-sample-b2e-experimental

Source is synced from the npm package [@salesforce/webapp-template-app-react-sample-b2e-experimental](https://www.npmjs.com/package/@salesforce/webapp-template-app-react-sample-b2e-experimental). Only the package's source (no `node_modules`) is copied into `samples/webapp-template-app-react-sample-b2e-experimental/`.

### How it's updated

- **GitHub Action**: Runs nightly and can be triggered manually from the **Actions** tab ("Sync React samples from npm"). The workflow runs the same steps as below and opens a PR against `main` only when the npm package version has changed.
- **Local**: From the **repo root** you can run the same sync anytime:

  ```bash
  npm install
  npm run sync-react-b2e-sample
  ```

  This installs the package into root `node_modules` and copies its source into `samples/webapp-template-app-react-sample-b2e-experimental/`, and updates `.version` in that folder.

### Version tracking

The file `samples/webapp-template-app-react-sample-b2e-experimental/.version` stores the last-synced npm version. The Action compares it to the latest on npm and only creates a PR when they differ.

## webapp-template-app-react-sample-b2x-experimental

Source is synced from the npm package [@salesforce/webapp-template-app-react-sample-b2x-experimental](https://www.npmjs.com/package/@salesforce/webapp-template-app-react-sample-b2x-experimental). Only the package's source (no `node_modules`) is copied into `samples/webapp-template-app-react-sample-b2x-experimental/`.

### How it's updated

- **GitHub Action**: Runs nightly and can be triggered manually from the **Actions** tab ("Sync React samples from npm"). The workflow runs the same steps as below and opens a PR against `main` only when the npm package version has changed.
- **Local**: From the **repo root** you can run the same sync anytime:

  ```bash
  npm install
  npm run sync-react-b2x-sample
  ```

  This installs the package into root `node_modules` and copies its source into `samples/webapp-template-app-react-sample-b2x-experimental/`, and updates `.version` in that folder.

### Version tracking

The file `samples/webapp-template-app-react-sample-b2x-experimental/.version` stores the last-synced npm version. The Action compares it to the latest on npm and only creates a PR when they differ.

## native-mobile-rental-tenant-app

A sample Custom Agentic Mobile App (CAMA) for rental property tenants. This sample is maintained directly in this repository (not synced from npm). It includes:

- **digitalExperiences** metadata: CAMA app config (`experience__camaAppMetadata`), build metadata (`experience__camaBuildMetadata`), EC definition (`experience__camaECDefinition`), and screens (`experience__camaScreen`) with tabs (Home, Tenants, Properties), theme, and toolbar settings
- **Source**: Synced from [cama-mcp-server](https://git.soma.salesforce.com/khawkins/cama-mcp-server) (branch `apply_metadata_updates`)

### How it's used

The sample appears on the Agentforce Vibes welcome page under the **Mobile** app type. Users can clone it via the welcome page wizard or directly from this repo.

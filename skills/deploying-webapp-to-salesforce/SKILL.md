---
name: deploying-webapp-to-salesforce
description: "Enforces the correct order for deploying metadata, assigning permission sets, and fetching GraphQL schema. Use for ANY deployment to a Salesforce org — webapps, LWC, Aura, Apex, metadata, schema fetch, or org sync. Codifies setup-cli.mjs."
---

# Deploying to Salesforce

Guidance for AI agents deploying metadata to a Salesforce org or syncing with the org. **The order of operations is critical.** This skill codifies the exact sequence from `scripts/setup-cli.mjs` and documents **every Salesforce interaction**.

## When to Use

Invoke this skill whenever the task involves:

- Deploying metadata (objects, permission sets, layouts, Apex, web applications)
- Generating deploy commands or setup instructions
- Fetching the GraphQL schema (`npm run graphql:schema`)
- Running GraphQL codegen (`npm run graphql:codegen`)
- Full org setup (login, deploy, permset, data, schema, build)
- Any manual step that touches the Salesforce org

## Canonical Sequence (from setup-cli.mjs)

Execute steps in this **exact order**. Steps marked **(SF)** perform a Salesforce API or CLI interaction.

### Step 1: Login — org authentication

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Check if org is connected | **(SF)** | `sf org display --target-org <alias> --json` |
| If not connected: authenticate | **(SF)** | `sf org login web --alias <alias>` |

- **Run when:** Org is not connected. **Omit when:** Org is already authenticated (check via `sf org display`).
- All subsequent steps require an authenticated org.

### Step 2: Webapp build — pre-deploy (required for entity deployment)

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Install dependencies | No | `npm install` (in each webapp dir) |
| Build web app | No | `npm run build` (in each webapp dir) |

- Produces `dist/` so `sf project deploy start` can deploy web application entities. Run **before** deploy when deploying web apps.
- **Run when:** Deploying web apps AND (`dist/` does not exist OR webapp source has changed since last build). **Omit when:** Not deploying, or `dist/` is current and no source changes.

### Step 3: Deploy metadata

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Deploy metadata | **(SF)** | See below |

**Check for a manifest (package.xml) first.** Only use it if present:

- **If `manifest/package.xml` (or `package.xml`) exists:** Deploy using the manifest:
  ```bash
  sf project deploy start --manifest manifest/package.xml --target-org <alias>
  ```
- **If no manifest exists:** Deploy all metadata from the project (packageDirectories in sfdx-project.json):
  ```bash
  sf project deploy start --target-org <alias>
  ```

Do not assume a manifest exists. Check the project root and common locations (e.g., `manifest/`, `config/`) before choosing the deploy command.

- Deploys objects, layouts, permission sets, Apex classes, web applications, and all other metadata.
- **Must complete successfully before schema fetch** — the schema reflects org state; custom objects/fields appear only after deployment.
- **Run when:** Metadata has changed since last deploy, or never deployed. **Omit when:** No metadata changes and deploy has already run successfully.

### Step 4: Post-deployment configuration — assign permissions and configure

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Assign permission set or group | **(SF)** | `sf org assign permset --name <name> --target-org <alias>` (works for both permsets and permset groups) |
| Assign profile to user | **(SF)** | `sf data update record` or at user creation |
| Other post-deploy config | **(SF)** | Varies (e.g., named credentials, connected apps, custom settings) |

**Example commands:**

```bash
# Permission set (assigns to default user of target org)
sf org assign permset --name Property_Management_Access --target-org myorg

# Permission set group (same command; pass the group name)
sf org assign permset --name My_Permset_Group --target-org myorg

# Assign to a specific user
sf org assign permset --name Property_Management_Access --target-org myorg --on-behalf-of user@example.com

# Profile — update existing user's profile (requires ProfileId and User Id)
sf data update record --sobject User --record-id <userId> --values "ProfileId=<profileId>" --target-org myorg

# Profile — get ProfileId first
sf data query --query "SELECT Id, Name FROM Profile WHERE Name='Standard User'" --target-org myorg
```

- **Deploying does not mean assigning.** Even after permission sets, permission set groups, and profiles are deployed to the org, they must be explicitly assigned or configured for users. Deployment makes them available; assignment/configuration grants access.
- **Permission sets** — Assign to users so they have access to custom objects and fields. Required for GraphQL introspection to return the correct schema.
- **Permission set groups** — Assign to users when using grouped permission sets.
- **Profiles** — Ensure users have the correct profile; profile assignment may be done at user creation or via Setup.
- **Other post-deploy configuration** — Named credentials, connected apps, custom settings, flow activation, and any metadata that requires manual configuration after deploy.
- All of the above must exist in the org (deployed in Step 3).
- **Run when:** Any permission set, permission set group, profile, or other post-deploy config was deployed or changed and not yet assigned/configured. **Omit when:** All required assignments and configuration are already in place.

**Proactive behavior:** After a successful deploy, discover permission sets in the project (e.g., `force-app/main/default/permissionsets/*.permissionset-meta.xml`) and assign each one. Extract the API name from the filename (e.g., `Property_Management_Access.permissionset-meta.xml` → `Property_Management_Access`). If the user has not explicitly requested a full setup, you may ask: "Do you want me to assign the permission sets to your org?" — but do not skip this step silently; either run it or ask.

### Step 5: Data — prepare and import (optional)

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Prepare unique fields | No | `node scripts/prepare-import-unique-fields.js --data-dir <dataDir>` |
| Clean existing records | **(SF)** | `sf apex run --target-org <alias> --file <apex>` (per sobject, reverse plan order) |
| Import records | **(SF)** | `sf apex run --target-org <alias> --file <apex>` (per batch) |

- Only runs if `data/data-plan.json` and `data/` exist.
- Delete runs in reverse plan order (children before parents).
- Import uses Anonymous Apex with `Database.DMLOptions.duplicateRuleHeader.allowSave = true`.
- **Run when:** Data plan exists AND (never imported OR data files or plan changed). **Omit when:** No data plan, or data already imported and unchanged.

**Proactive behavior:** If `data/data-plan.json` and `data/` exist, you MUST ask the user: "Do you want me to import the sample data now? This will prepare unique fields, optionally clean existing records, and import data. Reply yes to proceed." Do not skip this step silently; either run it (after confirmation) or ask. Never import or clean without explicit user confirmation.

### Step 6: GraphQL schema and codegen

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Install webapp deps | No | `npm install` (in webapp dir) |
| Set default org | **(SF)** | `sf config set target-org <alias> --global` |
| Fetch schema (introspection) | **(SF)** | `npm run graphql:schema` (from webapp dir) |
| Generate types | No | `npm run graphql:codegen` (from webapp dir) |

- `graphql:schema` performs GraphQL introspection against the org — a **Salesforce API call**.
- Schema is written to `schema.graphql` at the SFDX project root.
- Codegen reads the schema file locally; no Salesforce interaction.
- **Run when:** Schema does not exist, OR metadata was deployed/changed since last schema fetch, OR permissions or post-deploy config was assigned since last schema fetch. **Omit when:** Schema exists and is current relative to org state.

### Step 7: Webapp build (if not done in Step 2)

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Build web app | No | `npm run build` (in webapp dir) |

- **Run when:** Build is needed (e.g., for dev server or deploy) AND (`dist/` does not exist OR webapp source has changed since last build). **Omit when:** `dist/` is current and no build needed.

### Step 8: Dev server (optional)

| Action | Salesforce interaction? | Command |
|--------|-------------------------|---------|
| Launch dev server | No | `npm run dev` (in webapp dir) |

- **Run when:** User requests to launch the dev server. **Omit when:** Not requested.

## Summary: All Salesforce Interactions (in order)

1. `sf org display` — check org connection
2. `sf org login web` — authenticate (if needed)
3. `sf project deploy start` — deploy metadata
4. `sf org assign permset` (permsets and permset groups) / profile assignment / other post-deploy config — assign permissions and configure
5. `sf apex run` — delete existing data (if data plan)
6. `sf apex run` — import data (if data plan)
7. `sf config set target-org` — set default org for schema
8. `npm run graphql:schema` — GraphQL introspection (Salesforce API)

## Post-Deploy Checklist (MUST NOT SKIP)

After **every successful metadata deploy**, the agent MUST address these before considering the task complete:

1. **Permission sets** — Discover `force-app/main/default/permissionsets/*.permissionset-meta.xml`, extract API names, and assign each via `sf org assign permset --name <name> --target-org <alias>`. If unsure, ask: "Do you want me to assign the permission sets (e.g., Property_Management_Access, Tenant_Maintenance_Access) to your org?"
2. **Data import** — If `data/data-plan.json` exists, ask: "Do you want me to import the sample data now? Reply yes to proceed." Do not import without confirmation.
3. **Schema refetch** — Run `npm run graphql:schema` and `npm run graphql:codegen` from the webapp dir (required after deploy).

Do not silently skip permission set assignment or data import. Either run them or ask the user.

## Agent Decision Criteria

Evaluate each step before running it. Ask:

- **Has this step ever run before?** If not, it is likely needed.
- **Have changes been made that require this step?** (e.g., metadata edits → deploy; deploy → schema refetch)
- **Is the current state sufficient?** (e.g., org connected, schema exists and is current, permissions and post-deploy config assigned)

Do not rely on CLI flags. Decide based on project state and what has changed.

## Evaluation: When Each Step Touches Salesforce

| Step | Salesforce interaction | Run when |
|------|------------------------|----------|
| 1. Login | Yes | Org not connected |
| 2. Webapp build | No | Deploying web apps AND dist missing or source changed |
| 3. Deploy | Yes | Metadata changed or never deployed |
| 4. Post-deploy config | Yes | Permission sets, permset groups, profiles, or other config deployed/changed and not assigned |
| 5. Data | Yes | Data plan exists AND (never imported OR data changed) |
| 6. GraphQL | Yes (schema only) | Schema missing or metadata/permissions changed since last fetch |
| 7. Webapp build | No | Build needed AND dist missing or source changed |
| 8. Dev | No | User requests dev server |

**Critical rule:** Steps 3 (deploy) and 4 (post-deploy config) must complete **before** step 6 (graphql:schema). The schema reflects the org state; running introspection too early yields an incomplete schema.

## Schema Refetch Rule (CRITICAL)

**After any metadata deployment**, you MUST re-run schema fetch and codegen:

- New custom objects
- New custom fields
- New or updated permission sets
- Any change to metadata that affects the GraphQL schema

```bash
# From webapp dir (force-app/main/default/webapplications/<appName>/)
npm run graphql:schema
npm run graphql:codegen
```

Do **not** assume the existing `schema.graphql` is current after metadata changes.

## One-Command Setup (Reference)

The project includes `scripts/setup-cli.mjs` which runs this sequence in batch. Use it when the user wants a full setup; otherwise, follow this skill and run only the steps that are needed based on current state.

## Prohibited Actions

- **Do not** run `npm run graphql:schema` before metadata is deployed — the schema will not include custom objects/fields
- **Do not** skip schema refetch after deploying new metadata — types and queries will be out of sync
- **Do not** assign permissions or configure before deploying — permission sets, permset groups, and profiles must exist in the org first
- **Do not** run GraphQL introspection before assigning permissions — the user may lack FLS for custom fields

## Related Skills

- **using-salesforce-data** — Full data access workflow (GraphQL queries/mutations, REST APIs, schema exploration, webapp integration)

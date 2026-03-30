---
name: deploying-ui-bundle
description: "Deploy a Salesforce UI bundle to an org — the full deployment sequence including org authentication, pre-deploy build, metadata deployment, permission set assignment, data import, GraphQL schema fetch, and codegen. Use whenever the user wants to deploy, push to org, assign permission sets, import data, fetch GraphQL schema, run codegen, or set up an org after development. Triggers on: deploy, push to org, deploy metadata, assign permission set, import data, schema fetch, codegen, org auth, authenticate org, build and deploy, post-deploy, org setup."
---

# Deploying a UI Bundle

The order of operations is critical when deploying to a Salesforce org. This sequence reflects the canonical flow.

## Step 1: Org Authentication

Check if the org is connected. If not, authenticate. All subsequent steps require an authenticated org.

## Step 2: Pre-deploy UI Bundle Build

Install dependencies and build the UI bundle to produce `dist/`. Required before deploying UI bundle entities.

Run when: deploying UI bundles and `dist/` is missing or source has changed.

## Step 3: Deploy Metadata

Check for a manifest (`manifest/package.xml` or `package.xml`) first. If present, deploy using the manifest. If not, deploy all metadata from the project.

Deploys objects, layouts, permission sets, Apex classes, UI bundles, and all other metadata. Must complete before schema fetch — the schema reflects org state.

## Step 4: Post-deploy Configuration

Deploying does not mean assigning. After deployment:

- **Permission sets / groups** — assign to users so they have access to custom objects and fields. Required for GraphQL introspection to return the correct schema.
- **Profiles** — ensure users have the correct profile.
- **Other config** — named credentials, connected apps, custom settings, flow activation.

Proactive behavior: after a successful deploy, discover permission sets in `force-app/main/default/permissionsets/` and assign each one (or ask the user).

## Step 5: Data Import (optional)

Only if `data/data-plan.json` exists. Delete runs in reverse plan order (children before parents). Import uses Anonymous Apex with duplicate rule save enabled.

Always ask the user before importing or cleaning data.

## Step 6: GraphQL Schema and Codegen

1. Set default org
2. Fetch schema (GraphQL introspection) — writes `schema.graphql` at project root
3. Generate types (codegen reads schema locally)

Run when: schema missing, or metadata/permissions changed since last fetch.

## Step 7: Final UI Bundle Build

Build the UI bundle if not already done in Step 2.

## Summary: Interaction Order

1. Check/authenticate org
2. Build UI bundle (if deploying UI bundles)
3. Deploy metadata
4. Assign permissions and configure
5. Import data (if data plan exists, with user confirmation)
6. Fetch GraphQL schema and run codegen
7. Build UI bundle (if needed)

## Critical Rules

- Deploy metadata **before** fetching schema — custom objects/fields appear only after deployment
- Assign permissions **before** schema fetch — the user may lack FLS for custom fields
- Re-run schema fetch and codegen **after every metadata deployment** that changes objects, fields, or permissions
- Never skip permission set assignment or data import silently — either run them or ask the user

## Post-deploy Checklist

After every successful metadata deploy:

1. Discover and assign permission sets (or ask the user)
2. If `data/data-plan.json` exists, ask the user about data import
3. Re-run schema fetch and codegen from the UI bundle directory

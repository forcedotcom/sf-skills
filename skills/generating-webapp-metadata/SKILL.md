---
name: generating-webapp-metadata
description: "Scaffold new Salesforce web applications and configure/deploy their metadata — sf webapp generate, WebApplication bundles (meta XML, webapplication.json with routing/headers/outputDir), CSP Trusted Sites for external domains, and the full deployment sequence (org auth, build, deploy, permset assign, data import, GraphQL schema fetch, codegen). Use whenever creating a new webapp, setting up webapp metadata structure, adding external domains that need CSP registration, deploying to a Salesforce org, assigning permission sets, fetching GraphQL schema, or running codegen. Triggers on: create webapp, new app, sf webapp generate, deploy, metadata, webapplication.json, CSP, trusted site, permission set, schema fetch, codegen, org setup, bundle configuration, meta XML, routing config, external domain."
---

# Web Application Metadata

## Scaffolding a New Webapp

Use `sf webapp generate` to create new apps — not create-react-app, Vite, or other generic scaffolds.

**Webapp name (`-n`):** Alphanumerical only — no spaces, hyphens, underscores, or special characters. Example: `CoffeeBoutique` (not `Coffee Boutique`).

After generation:
1. Replace all default boilerplate — "React App", "Vite + React", default `<title>`, placeholder text
2. Populate the home page with real content (landing section, banners, hero, navigation)
3. Update navigation and placeholders (see the `generating-webapp-ui` skill)

Always install dependencies before running any scripts in the webapp directory.

---

## WebApplication Bundle

A WebApplication bundle lives under `webapplications/<AppName>/` and must contain:

- `<AppName>.webapplication-meta.xml` — filename must exactly match the folder name
- A build output directory (default: `dist/`) with at least one file

### Meta XML

Required fields: `masterLabel`, `version` (max 20 chars), `isActive` (boolean).
Optional: `description` (max 255 chars).

### webapplication.json

Optional file. Allowed top-level keys: `outputDir`, `routing`, `headers`.

**Constraints:**
- Valid UTF-8 JSON, max 100 KB
- Root must be a non-empty object (never `{}`, arrays, or primitives)

**Path safety** (applies to `outputDir` and `routing.fallback`): Reject backslashes, leading `/` or `\`, `..` segments, null/control characters, globs (`*`, `?`, `**`), and `%`. All resolved paths must stay within the bundle.

#### outputDir
Non-empty string referencing a subdirectory (not `.` or `./`). Directory must exist and contain at least one file.

#### routing
If present, must be a non-empty object. Allowed keys: `rewrites`, `redirects`, `fallback`, `trailingSlash`, `fileBasedRouting`.

- **trailingSlash**: `"always"`, `"never"`, or `"auto"`
- **fileBasedRouting**: boolean
- **fallback**: non-empty string satisfying path safety; target file must exist
- **rewrites**: non-empty array of `{ route?, rewrite }` objects — e.g., `{ "route": "/app/:path*", "rewrite": "/index.html" }`
- **redirects**: non-empty array of `{ route?, redirect, statusCode? }` objects — statusCode must be 301, 302, 307, or 308

#### headers
Non-empty array of `{ source, headers: [{ key, value }] }` objects.

**Example:**
```json
{
  "routing": {
    "rewrites": [{ "route": "/app/:path*", "rewrite": "/index.html" }],
    "trailingSlash": "never"
  },
  "headers": [
    {
      "source": "/assets/**",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
    }
  ]
}
```

**Never suggest:** `{}` as root, empty `"routing": {}`, empty arrays, `[{}]`, `"outputDir": "."`, `"outputDir": "./"`.

---

## CSP Trusted Sites

Salesforce enforces Content Security Policy headers. Any external domain not registered as a CSP Trusted Site will be blocked (images won't load, API calls fail, fonts missing).

### When to Create

Whenever the app references a new external domain: CDN images, external fonts, third-party APIs, map tiles, iframes, external stylesheets.

### Steps

1. **Identify external domains** — extract the origin (scheme + host) from each external URL in the code
2. **Check existing registrations** — look in `force-app/main/default/cspTrustedSites/`
3. **Map resource type to CSP directive:**

| Resource Type | Directive Field |
|--------------|----------------|
| Images | `isApplicableToImgSrc` |
| API calls (fetch, XHR) | `isApplicableToConnectSrc` |
| Fonts | `isApplicableToFontSrc` |
| Stylesheets | `isApplicableToStyleSrc` |
| Video / audio | `isApplicableToMediaSrc` |
| Iframes | `isApplicableToFrameSrc` |

Always also set `isApplicableToConnectSrc` to `true` for preflight/redirect handling.

4. **Create the metadata file** — follow `implementation/csp-metadata-format.md` for the `.cspTrustedSite-meta.xml` format. Place in `force-app/main/default/cspTrustedSites/`.

---

## Deployment Sequence

The order of operations is critical when deploying to a Salesforce org. This sequence reflects the canonical flow.

### Step 1: Org Authentication

Check if the org is connected. If not, authenticate. All subsequent steps require an authenticated org.

### Step 2: Pre-deploy Webapp Build

Install dependencies and build the webapp to produce `dist/`. Required before deploying web application entities.

Run when: deploying web apps and `dist/` is missing or source has changed.

### Step 3: Deploy Metadata

Check for a manifest (`manifest/package.xml` or `package.xml`) first. If present, deploy using the manifest. If not, deploy all metadata from the project.

Deploys objects, layouts, permission sets, Apex classes, web applications, and all other metadata. Must complete before schema fetch — the schema reflects org state.

### Step 4: Post-deploy Configuration

Deploying does not mean assigning. After deployment:

- **Permission sets / groups** — assign to users so they have access to custom objects and fields. Required for GraphQL introspection to return the correct schema.
- **Profiles** — ensure users have the correct profile.
- **Other config** — named credentials, connected apps, custom settings, flow activation.

Proactive behavior: after a successful deploy, discover permission sets in `force-app/main/default/permissionsets/` and assign each one (or ask the user).

### Step 5: Data Import (optional)

Only if `data/data-plan.json` exists. Delete runs in reverse plan order (children before parents). Import uses Anonymous Apex with duplicate rule save enabled.

Always ask the user before importing or cleaning data.

### Step 6: GraphQL Schema and Codegen

1. Set default org
2. Fetch schema (GraphQL introspection) — writes `schema.graphql` at project root
3. Generate types (codegen reads schema locally)

Run when: schema missing, or metadata/permissions changed since last fetch.

### Step 7: Final Webapp Build

Build the webapp if not already done in Step 2.

### Summary: Interaction Order

1. Check/authenticate org
2. Build webapp (if deploying web apps)
3. Deploy metadata
4. Assign permissions and configure
5. Import data (if data plan exists, with user confirmation)
6. Fetch GraphQL schema and run codegen
7. Build webapp (if needed)

### Critical Rules

- Deploy metadata **before** fetching schema — custom objects/fields appear only after deployment
- Assign permissions **before** schema fetch — the user may lack FLS for custom fields
- Re-run schema fetch and codegen **after every metadata deployment** that changes objects, fields, or permissions
- Never skip permission set assignment or data import silently — either run them or ask the user

### Post-deploy Checklist

After every successful metadata deploy:

1. Discover and assign permission sets (or ask the user)
2. If `data/data-plan.json` exists, ask the user about data import
3. Re-run schema fetch and codegen from the webapp directory

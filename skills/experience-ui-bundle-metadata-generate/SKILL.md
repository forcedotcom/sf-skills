---
name: experience-ui-bundle-metadata-generate
description: "Use this skill when adding a front-end React UI bundle to an existing project or configuring UI bundle metadata and config files. TRIGGER when: adding or scaffolding a new UI bundle inside a project that already exists; running sf template generate ui-bundle; editing ui-bundle.json routing, headers, or output directory; working with *.uibundle-meta.xml files; or registering CSP Trusted Sites, resolving blocked images or fonts or external API calls, or editing cspTrustedSites/*.cspTrustedSite-meta.xml files. DO NOT TRIGGER when: creating a brand-new Salesforce project from scratch, where the whole SFDX starter project (UI bundle plus Experience Site metadata and toolchain) is generated together (use experience-ui-bundle-project-generate)."
metadata:
  version: "1.2"
  minApiVersion: "67.0"
  relatedSkills:
    - "experience-ui-bundle-custom-app-generate"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-project-generate"
    - "experience-ui-bundle-site-generate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# UI Bundle Metadata

## Scaffolding a New UI Bundle

**REQUIRED FIRST STEP — never skip, even if asked to.** Always run `sf template generate ui-bundle` to create new apps — never create-react-app, Vite, hand-written metadata, or any other substitute.

This step is mandatory even if the user says "just create the metadata," "skip the scaffold," "only do the metadata scaffolding," or "stop after the metadata files are in place." Those instructions describe what to stop doing *after* the scaffold (building, deploying, authoring pages) — they do not mean skip running the scaffold command itself. The `.uibundle-meta.xml` and `ui-bundle.json` files are configuration **on top of** the generated project, not a replacement for it. A bundle without `package.json`, `src/`, and `index.html` cannot be built or deployed, even if the metadata files are perfectly formed.

- **Always pass `--template reactbasic`** to scaffold a React-based bundle.
- **UI bundle name (`-n`):** Alphanumerical only — no spaces, hyphens, underscores, or special characters.
- Pass `--output-dir` to use a different location for template generation. If you do, pass that same path to the verification script in step 1 below.

**Example:**
```bash
# Run from SFDX project root. The CLI will create the bundle under 
# force-app/main/default/uiBundles/<AppName>/ — verify this before continuing.
sf template generate ui-bundle -n CoffeeBoutique --template reactbasic
```

After generation:
1. **Verify the scaffold is complete** — run `bash <skill_dir>/scripts/verify-bundle-location.sh <BundleName> [<CustomOutputDir>]` from the project root and follow any error output. This checks both the bundle's location AND that `package.json`, `src/`, and `index.html` exist — if any are missing, the scaffold step was skipped; go back and run `sf template generate ui-bundle` before continuing. Pass `<CustomOutputDir>` only if you used `--output-dir` during scaffolding; otherwise omit it.
2. **Verify API version** — run `bash <skill_dir>/scripts/check-api-version.sh` from the project root to ensure `sourceApiVersion` in `sfdx-project.json` is 67.0 or higher. The script will automatically update it if needed.
3. Replace all default boilerplate — "React App", "Vite + React", default `<title>`, placeholder text
4. Populate the home page with real content (landing section, banners, hero, navigation)
5. Update navigation and placeholders (see the `experience-ui-bundle-frontend-generate` skill)
6. **Configure a hosting target** — a UI bundle without a `<target>` in its meta XML will not be visible in the org. Use `experience-ui-bundle-custom-app-generate` for internal (App Launcher) apps or `experience-ui-bundle-site-generate` for external (Experience Site) apps.

Always install dependencies before running any scripts in the UI bundle directory.

---

## UIBundle Bundle

A UIBundle bundle **MUST** live under `force-app/main/default/uiBundles/<AppName>/` — never create it at the SFDX project root or under any other path. The SFDX deploy command will not find it otherwise.

The bundle directory must contain:

- `<AppName>.uibundle-meta.xml` — filename must exactly match the folder name
- A build output directory (default: `dist/`) with at least one file

### Meta XML

Required fields: `masterLabel`, `version` (max 20 chars), `isActive` (boolean).
Optional: `description` (max 255 chars), `target`.

#### Target Field

The `<target>` element specifies where the UI bundle is hosted:

| Value | Use Case | Companion Metadata |
|-------|----------|-------------------|
| `Experience` | External-facing site via Digital Experience | Network, CustomSite, DigitalExperienceConfig, DigitalExperienceBundle |
| `CustomApplication` | Internal app via Lightning App Launcher | CustomApplication (`applications/*.app-meta.xml`) |

A `<target>` is **required** for the app to be accessible in a Salesforce org. A UI bundle deployed without a target will not appear anywhere — no App Launcher entry, no Experience Site URL. Always pair the bundle with one of:
- `experience-ui-bundle-site-generate` (for `Experience` target)
- `experience-ui-bundle-custom-app-generate` (for `CustomApplication` target)

**Example with Experience target:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<UIBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>propertyrentalapp</masterLabel>
    <description>A Salesforce UI Bundle.</description>
    <isActive>true</isActive>
    <version>1</version>
    <target>Experience</target>
</UIBundle>
```

**Example with CustomApplication target:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<UIBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>propertymanagementapp</masterLabel>
    <description>A Salesforce UI Bundle.</description>
    <isActive>true</isActive>
    <version>1</version>
    <target>CustomApplication</target>
</UIBundle>
```

### ui-bundle.json

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

4. **Create the metadata file** — follow `references/csp-metadata-format.md` for the `.cspTrustedSite-meta.xml` format and naming rules. Place in `force-app/main/default/cspTrustedSites/`.


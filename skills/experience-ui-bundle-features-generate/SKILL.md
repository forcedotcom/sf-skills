---
name: experience-ui-bundle-features-generate
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the user wants to add a pre-built feature — such as authentication (login, logout, protected routes, session management) or search (global search across pages and content) — instead of building it from scratch. Always run list first to see the current feature catalog, since it can include more than authentication and search. Always use this skill for installing pre-built features rather than hand-building them. DO NOT TRIGGER for Agentforce conversational client or file-upload features — use experience-ui-bundle-agentforce-client-generate and experience-ui-bundle-file-upload-generate respectively."
metadata:
  version: "1.1"
  domains: ["Experience"]
  relatedSkills: ["experience-ui-bundle-agentforce-client-generate", "experience-ui-bundle-file-upload-generate"]
  cliTools:
    - tool: ["npx"]
      semver: ">=7.0.0"
    - tool: ["npm"]
      semver: ">=7.0.0"
  accessCheck:
    - type: "license"
      value: "Experience Cloud (Customer Community / Customer Community Plus)"
    - type: "orgPref"
      value: "Sites"
---

# UI Bundle Features

## Installing Pre-built Features

Always check for an existing feature before building something from scratch. The features CLI installs pre-built, tested packages into Salesforce UI bundles — from foundational UI libraries (shadcn/ui) to full-stack capabilities. Authentication and search are the most commonly used features today; run `list --verbose` for the full current catalog, since it can grow over time.

> **Ownership note:** Agentforce AI conversation clients and file-upload are owned by separate skills (`experience-ui-bundle-agentforce-client-generate`, `experience-ui-bundle-file-upload-generate`). If the catalog also lists an Agentforce or file-upload entry, do not install it from both places — confirm with the user which delivery path they want, and never install the same capability twice in one bundle.

> **Package name:** `@salesforce/ui-bundle-features` is the canonical package name. Some older templates/samples still reference the deprecated `@salesforce/ui-bundle-features-experimental` name — never use the `-experimental` suffix. If a command fails to resolve, confirm the published version with `npm view @salesforce/ui-bundle-features version` before assuming the package name is wrong.

### Workflow

0. **Confirm this is a React UI bundle** — this CLI copies into `src/features/` and expects `npm run build` to work. Non-React bundles are not supported and will fail late in the install.

   Run `scripts/verify-react-bundle.sh`. If it exits non-zero, stop — the bundle is not React-based and this skill cannot proceed.

1. **Search project code first** — check `src/` for existing implementations before installing anything. Scope searches to `src/` to avoid matching `node_modules/` or `dist/`.

2. **Search available features** — use `npx @salesforce/ui-bundle-features list` with `--search <query>` to filter by keyword. Use `--verbose` for full descriptions.

3. **Describe a feature** — use `npx @salesforce/ui-bundle-features describe <feature>` to see components, dependencies, copy operations, and example files.

4. **Install** — use `npx @salesforce/ui-bundle-features install <feature> --ui-bundle-dir <name>`. Key options:
   - `--dry-run` to preview changes
   - `--yes` for non-interactive mode (skips conflicts)
   - `--on-conflict error` to detect conflicts, then `--conflict-resolution <file>` to resolve them

   Install features **before** doing custom frontend/layout work in this bundle — features may rewrite `appLayout.tsx`/`routes.tsx`, and installing after hand-built layout changes risks collisions.

If no matching feature is found, ask the user before building a custom implementation — a relevant feature may exist under a different name.

### Conflict Handling

In non-interactive environments, use the two-pass approach:

1. Run install with `--on-conflict error` to detect conflicts without applying them.
2. Before writing the resolution file, read `references/conflict-resolution-schema.json` for the allowed keys and enum values.
3. Write a resolution file at `<ui-bundle-dir>/conflict-resolution.json` (path is relative to the UI bundle directory being installed into, not the repo root). Key it by the exact paths the CLI printed as conflicts in pass 1, verbatim:
   ```json
   {
     "src/appLayout.tsx": "overwrite",
     "src/routes.tsx": "skip"
   }
   ```
   Any conflicting path *not* listed in this file defaults to `skip` — the CLI will not overwrite a file you didn't explicitly mark `overwrite`.
4. Re-run install with `--conflict-resolution <path-to-that-file>`.

### Post-install: Integrating Example Files

Features may include example files under an `__examples__/` directory (plural) showing integration patterns. These are often full, working pages with concrete names (e.g. `AccountSearch.tsx`), not bare placeholder templates. For each:

1. Read the example file to understand the pattern — treat it as a working reference implementation, not necessarily a stub.
2. Read the target file (shown in `describe` output).
3. Apply the pattern from the example into the target.
4. **CRITICAL — verify before deleting:**
   ```bash
   # Verify the build passes with the integrated pattern
   npm run build || {
     echo "ERROR: Build failed after integration - do NOT delete __examples__/"
     exit 1
   }
   
   # Verify the pattern from the example is actually present in the target
   # (adjust grep pattern to match a key symbol/import/component from the example)
   # Example: for SearchInput pattern integrated into AccountSearch.tsx
   grep -q "SearchInput\|useSearch" src/pages/*.tsx src/components/*.tsx 2>/dev/null || {
     echo "ERROR: Pattern from example not found in target files - integration incomplete"
     echo "Do NOT delete __examples__/ until the pattern is confirmed present"
     exit 1
   }
   
   # Only delete after both checks pass
   rm -rf __examples__/
   ```

If either check fails, **do NOT delete `__examples__/`** — the integration is incomplete. Fix the integration first, then re-run the verification.

### Hint Placeholders

Some copy paths use `<descriptive-name>` placeholders (e.g., `<desired-page-with-search-input>`) that the CLI does not resolve. After installation, rename or relocate these files to the intended target, or integrate their patterns into an existing file. This is separate from the `__examples__/` convention above — a single copy path can use either mechanism.

### Auth Feature: Org-Side Prerequisites

Installing the authentication feature only copies files — it does not configure the org. Before telling the user auth is done, flag that these org-side steps still need to happen (outside this skill's scope, but required for the feature to actually work):

- Digital Experiences (Experience Cloud) must be enabled, with Customer Community / Customer Community Plus licenses assigned to the relevant users, and Salesforce Sites enabled.
- The community and guest profiles need explicit Apex class access granted for the auth utility, login/registration, and password-reset classes — the CLI does not grant this automatically.
- Guest-profile sharing rules / org-wide defaults for any objects the auth flow touches.
- **Known limitation:** logout has a documented CSRF-handling gap (tracked as W-21253864) — call this out to the user rather than presenting logout as fully solved.

### CRITICAL: Resolve `<sfdxRoot>` After Every Install

The CLI may copy files under a literal `<sfdxRoot>` folder — an unresolved placeholder for this project's Salesforce DX metadata root (from `sfdx-project.json`'s `packageDirectories[].path`, e.g. `force-app/main/default`). Files left there are undeployable.

**After every install:**
```bash
find uiBundles/<AppName> -type d -regex '.*/<[^/]+>$'
```
If found, move each file to `<metadata-root>/<same-relative-subpath>` (keep `-meta.xml` sidecars attached) and delete the emptied placeholder dir(s).

**Verification:**
- [ ] Re-run `find uiBundles/<AppName> -type d -regex '.*/<[^/]+>$'` — output must be empty before proceeding.



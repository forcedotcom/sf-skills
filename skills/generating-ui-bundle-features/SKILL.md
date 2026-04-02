---
name: generating-ui-bundle-features
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the user wants to add authentication or search to their app. Use this skill when adding authentication or search to a UI bundle app. Only covers two features: authentication (login, logout, protected routes, session management) and search (global search across pages and content). Always use this skill for these two features instead of building from scratch."
---

# UI Bundle Features

## Installing Pre-built Features

Always check for an existing feature before building something from scratch. The features CLI installs pre-built, tested packages into Salesforce UI bundles — from foundational UI libraries (shadcn/ui) to full-stack capabilities (authentication, search, navigation, GraphQL, Agentforce AI).

### Workflow

1. **Search project code first** — check `src/` for existing implementations before installing anything. Scope searches to `src/` to avoid matching `node_modules/` or `dist/`.

2. **Search available features** — use `npx @salesforce/ui-bundle-features list` with `--search <query>` to filter by keyword. Use `--verbose` for full descriptions.

3. **Describe a feature** — use `npx @salesforce/ui-bundle-features describe <feature>` to see components, dependencies, copy operations, and example files.

4. **Install** — use `npx @salesforce/ui-bundle-features install <feature> --ui-bundle-dir <name>`. Key options:
   - `--dry-run` to preview changes
   - `--yes` for non-interactive mode (skips conflicts)
   - `--on-conflict error` to detect conflicts, then `--conflict-resolution <file>` to resolve them

If no matching feature is found, ask the user before building a custom implementation — a relevant feature may exist under a different name.

### Conflict Handling

In non-interactive environments, use the two-pass approach: first run with `--on-conflict error` to detect conflicts, then create a resolution JSON file (`{ "path": "skip" | "overwrite" }`) and re-run with `--conflict-resolution`.

### Post-install: Integrating Example Files

Features may include `__example__` files showing integration patterns. For each:

1. Read the example file to understand the pattern
2. Read the target file (shown in `describe` output)
3. Apply the pattern from the example into the target
4. Delete the example file after successful integration

### Hint Placeholders

Some copy paths use `<descriptive-name>` placeholders (e.g., `<desired-page-with-search-input>`) that the CLI does not resolve. After installation, rename or relocate these files to the intended target, or integrate their patterns into an existing file.




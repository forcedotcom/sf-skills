---
name: installing-webapp-features
description: "Search, describe, and install pre-built UI features (authentication, shadcn components, navigation, search, GraphQL, Agentforce AI) into Salesforce webapps. Use this when the user wants to add functionality to a webapp, or when determining what salesforce-provided features are available — whether prompted by the user or on your own initiative. Always check for an existing feature before building from scratch."
---

# webapps-features-experimental CLI — Agent Reference

**Always check for an existing feature before building something yourself.** This CLI installs pre-built, tested feature packages into Salesforce webapps. Features range from foundational UI component libraries (shadcn/ui with Button, Card, Input, Table, etc.) to full-stack application capabilities like authentication (login, registration, password flows, session management, and Apex backend classes), global search, navigation menus, GraphQL integrations, and Agentforce AI conversation UIs. Each feature ships as a complete implementation — including React components, context providers, route guards, and any required Salesforce server-side code — that already handles platform-specific concerns like Salesforce API integration, session management, and SFDX metadata structure. Building these from scratch is error-prone and unnecessary when a feature exists. **If no existing feature is found, ask the user before proceeding with a custom implementation — a relevant feature may exist under a different name or keyword.**

```
npx @salesforce/webapps-features-experimental <command> [options]
```

## Workflow: Search Project → Search Features → Describe → Install

**MANDATORY**: When the user asks to add ANY webapp functionality, follow this entire workflow. Do not skip steps.

### 1. Search existing project code

Before installing anything, check whether the functionality already exists in the **project source code** (not dependencies).

- **Always scope searches to `src/`** to avoid matching files in `node_modules/`, `dist/`, or `build/` output
- Use Glob with a scoped path: e.g., `src/**/Button.tsx`, `src/**/*auth*.tsx`
- Use Grep with the `path` parameter set to the `src/` directory, or use `glob: "*.{ts,tsx}"` to restrict file types
- Check common directories: `src/components/`, `src/lib/`, `src/pages/`, `src/hooks/`
- **Never** search from the project root without a path or glob filter — this will crawl `node_modules` and produce massive, unhelpful output

**If existing code is found** — read the files, present them to the user, and ask if they want to reuse or extend what's there. If yes, use the existing code and stop. If no, proceed to step 2.

**If nothing is found** — proceed to step 2.

### 2. Search available features

```bash
npx @salesforce/webapps-features-experimental list [options]
```

Options:

- `-v, --verbose` — Show full descriptions, packages, and dependencies
- `--search <query>` — Filter features by keyword (ranked by relevance)

```bash
npx @salesforce/webapps-features-experimental list
npx @salesforce/webapps-features-experimental list --search "auth"
npx @salesforce/webapps-features-experimental list --search "button"
```

**If no matching feature is found** — ask the user before proceeding with a custom implementation. A relevant feature may exist under a different name or keyword.

### 3. Describe a feature

```bash
npx @salesforce/webapps-features-experimental describe <feature>
```

Shows description, package name, dependencies, components, copy operations, and example files.

```bash
npx @salesforce/webapps-features-experimental describe authentication
npx @salesforce/webapps-features-experimental describe shadcn
```

### 4. Install a feature

```bash
npx @salesforce/webapps-features-experimental install <feature> --webapp-dir <path> [options]
```

Resolves the feature name to an npm package, installs it and its dependencies (including transitive feature dependencies like `shadcn`), copies source files into your project, and reports any `__example__` files that require manual integration.

Options:

- `--webapp-dir <name>` (required) — Webapp name, resolves to `<sfdx-source>/webapplications/<name>`
- `--sfdx-source <path>` (default: `force-app/main/default`) — SFDX source directory
- `--dry-run` (default: `false`) — Preview changes without writing files
- `-v, --verbose` (default: `false`) — Enable verbose logging
- `-y, --yes` (default: `false`) — Skip all prompts (auto-skip conflicts)
- `--on-conflict <mode>` (default: `prompt`) — `prompt`, `error`, `skip`, or `overwrite`
- `--conflict-resolution <file>` — Path to JSON file with per-file resolutions

```bash
# Install authentication (also installs shadcn dependency)
npx @salesforce/webapps-features-experimental install authentication \
  --webapp-dir mywebapp

# Dry run to preview changes
npx @salesforce/webapps-features-experimental install shadcn \
  --webapp-dir mywebapp \
  --dry-run

# Non-interactive install (skip all file conflicts)
npx @salesforce/webapps-features-experimental install authentication \
  --webapp-dir mywebapp \
  --yes
```

## Conflict Handling

Since you are running in a non-interactive environment, you cannot use `--on-conflict prompt` directly. When conflicts are likely (e.g. installing into an existing project), you have two options:

**Option A — Let the user resolve conflicts interactively.** Suggest the user run the install command themselves with `--on-conflict prompt` so they can decide per-file.

**Option B — Two-pass automated resolution:**

```bash
# Pass 1: detect conflicts
npx @salesforce/webapps-features-experimental install authentication \
  --webapp-dir mywebapp \
  --on-conflict error

# The CLI will exit with an error listing every conflicting file path.

# Pass 2: create a resolution file and re-run
echo '{ "src/styles/global.css": "overwrite", "src/lib/utils.ts": "skip" }' > resolutions.json

npx @salesforce/webapps-features-experimental install authentication \
  --webapp-dir mywebapp \
  --conflict-resolution resolutions.json
```

Resolution values per file: `"skip"` (keep existing) or `"overwrite"` (replace). When unsure how to resolve a conflict, ask the user rather than guessing.

## Hint Placeholders in Copy Paths

Some copy operations use **hint placeholders** in the `"to"` path — descriptive segments like `<desired-page-with-search-input>` that are NOT resolved by the CLI. These are guidance for the user or LLM to choose an appropriate destination.

**How they work:** The file is copied with the literal placeholder name (e.g., `src/pages/<desired-page-with-search-input>.tsx`). After installation, you should:

1. Read the copied file to understand its purpose
2. Rename or relocate it to the intended target (e.g., `src/pages/Home.tsx`)
3. Or integrate its patterns into an existing file, then delete it

**How to identify them:** Hint placeholders use `<descriptive-name>` syntax but are NOT one of the system placeholders (`<sfdxSource>`, `<webappDir>`, `<webapp>`). They always appear in the middle or end of a path, never as the leading segment.

**Example from features.json:**

```json
{
  "to": "<webappDir>/src/pages/<desired-page-with-search-input>.tsx",
  "description": "Example home page showing GlobalSearchInput integration",
  "integrationTarget": "src/pages/Home.tsx"
}
```

The `integrationTarget` field tells you the suggested destination. Use your judgment — if the user already has a different page where search should go, integrate there instead.

**When `integrationTarget` itself is a placeholder:** Some features use a hint placeholder in the `integrationTarget` value (e.g., `"integrationTarget": "src/<path-to-desired-page-with-search-input>.tsx"`). This means there is no single default target — the user must decide which existing file to integrate into. When you encounter this:

1. Ask the user which page or file they want to integrate the feature into
2. Read the `__example__` file to understand the integration pattern
3. Read the user's chosen target file
4. Apply the pattern from the example into the target file

## Post Installation: Integrating **example** Files

Features may include `__example__` files (e.g., `__example__auth-app.tsx`) showing integration patterns.

**The describe command shows**:

- Which **example** files will be copied
- Target file to integrate into (e.g., `src/app.tsx`)
- What the example demonstrates

### How to Integrate Example Files (CRITICAL FOR LLMs)

⚠️ **ONLY USE Read AND Edit TOOLS - NO BASH COMMANDS** ⚠️

**DO NOT DO THIS**:

- ❌ `git status` or any git commands
- ❌ `ls`, `cat`, `sed`, `awk`, or ANY bash file commands
- ❌ Chaining bash commands to read multiple files
- ❌ Using bash to check directories or file existence

**DO THIS INSTEAD**:

- ✅ Use Read tool with `file_path` parameter to read each file
- ✅ Use Edit tool with `file_path`, `old_string`, `new_string` to modify files
- ✅ That's it! Just Read and Edit tools.

**Integration steps**:

1. **Read each example file** (use Read tool)
   - Example: Read tool with `file_path: "force-app/main/default/webapplications/mywebapp/src/__example__auth-app.tsx"`
   - Note the imports and patterns to integrate

2. **Read each target file** (use Read tool)
   - Example: Read tool with `file_path: "force-app/main/default/webapplications/mywebapp/src/app.tsx"`
   - Understand where the new code should go

3. **Edit each target file** (use Edit tool)
   - Add imports from the example
   - Add or modify code following the example's patterns
   - Preserve existing functionality

4. **Delete the example file after successful integration** (use Bash tool)
   - Example: `rm force-app/main/default/webapplications/mywebapp/src/__example__authentication-routes.tsx`
   - Only delete after you have successfully integrated the pattern
   - This keeps the codebase clean and removes temporary example files

## Troubleshooting

**Directory not found**: Check paths are correct, use absolute or correct relative paths

**Feature not found**: Use `npx @salesforce/webapps-features-experimental list` to see available feature names

**Conflicts in error mode**: Follow CLI instructions to create resolution file

**Need help?**: Run `npx @salesforce/webapps-features-experimental --help` to see all commands and options

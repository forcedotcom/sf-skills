---
name: commerce-b2b-open-code-components-replace
description: "Replace OOTB (out-of-the-box) B2B Commerce components with open source equivalents in site metadata content.json files, or look up the equivalent open code `site:` component for OOTB definitions. Use when users mention \"replace OOTB components\", \"replace commerce components with open code\", \"swap OOTB for open source\", \"replace commerce_builder:\", \"replace OOTB in site\", \"replace component in site metadata\", \"replace component definition\", \"find open code equivalent\", \"equivalent open code component\", \"OOTB to open code mapping\", \"what is the site component for\", components \"in this view\" or \"for a given view\", or a specific list of component names — and want to update or only discover mappings in their store metadata."
allowed-tools: Bash(grep:*) Bash(ls:*) Read Write
metadata:
  relatedSkills:
    - "commerce-b2b-open-code-components-integrate"
  version: "1.0"
---

# Replacing OOTB B2B Commerce Components with Open Code

This skill replaces OOTB (out-of-the-box) B2B Commerce component definitions in site metadata `content.json` files with their open source `site:` equivalents, or looks up the equivalent open code component for given OOTB definitions without making changes. It uses an authoritative mapping loaded from `assets/ootb-to-open-code-mapping.json`.

## Scope

**Modes:** **Full replace** runs the scan (Step 1), user selection if needed, then `content.json` updates (Step 2–3). **Lookup only** (user asks for equivalents but not to change files): apply the mapping-authority rule and report OOTB → `site:` for the named components or for definitions found in the scoped `content.json` — **do not** call Write unless the user confirms replacement. **View-scoped** work: limit file discovery and reads to `sfdc_cms__view/<ViewName>/` (or the path the user gives) instead of all views.

---

## Prerequisites

### Resolve `<package-dir>`

Read `sfdx-project.json` and pick the active package directory. Extract `packageDirectories[]` and use the entry with `"default": true`; if no entry is flagged default, use the first entry. Use this value as `<package-dir>` everywhere below. If `sfdx-project.json` is missing or has no `packageDirectories`, tell the user and abort.

### Delegate setup

Before replacing components, delegate to the **commerce-b2b-open-code-components-integrate** skill to ensure:

1. Open source repository is cloned at `.tmp/b2b-commerce-open-source-components`
2. Store is selected and site metadata is retrieved locally
3. Open code components are copied to the store's site metadata

The integrating skill owns the `.tmp/` clone lifecycle (it prompts the user to reuse or re-clone an existing checkout); this skill assumes the clone is already present.

Send a plain-text chat reply to the user (per Rule 1): "Before replacing components, I need to verify that the open code components are set up in your store. Let me check..."

If any prerequisite is not met, the integrating skill will handle it. Once all checks pass, proceed to the replacement workflow.

**Required state** after prerequisites:
- **Package dir** — the value resolved above (e.g., `force-app`)
- **Store name** — e.g., `My_B2B_Store1`
- **Site metadata path** — `<package-dir>/main/default/digitalExperiences/site/<store-name>/`

---

## Replacement Workflow

### Step 1: Scan Site and Cross-Reference Mapping

**This step is MANDATORY.** Always scan the site first before attempting any replacements.

Send a plain-text chat reply to the user (per Rule 1): "I'm scanning your store's site metadata to find all OOTB commerce components currently in use and checking which have open code equivalents."

**Step 1a — Find affected files** (one command, simple literal match):

```bash
grep -rl '"commerce' \
  <package-dir>/main/default/digitalExperiences/site/<store-name>/sfdc_cms__view/ \
  <package-dir>/main/default/digitalExperiences/site/<store-name>/sfdc_cms__themeLayout/ \
  --include="content.json"
```

**Step 1b — Read the mapping and parse the matched files.** Read `assets/ootb-to-open-code-mapping.json` once into memory. Then, using the **Read** tool, parse each matched file and extract all `"definition"` values that start with `commerce` (e.g., `commerce_builder:cartBadge`). Collect a deduplicated list of OOTB components across all files.

**Step 1c — List repo components** (one command):

```bash
ls .tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/
```

Using the parsed definitions, the `ls` output, and the mapping table, categorize every discovered OOTB component into three groups:

**Show the user a breakdown and a selectable list:**

First, inform the user about skipped and unmapped components:
```text
Found X OOTB components in your site:

In mapping table but NOT in repo (skipping):
  - commerce_builder:quoteSummary → site:quoteSummary (not found in repo)

No mapping available (not in mapping table):
  - commerce_builder:actionButtons
  - commerce_builder:layoutHeaderOne
  - commerce_builder:searchInputContainer
  - commerce_builder:myAccountMegaMenu
```

Then present the replaceable components as a **multi-select list** so the user can pick from checkboxes instead of typing. Include an "All of the above" option:

```text
Which components would you like to replace?

☐ commerce_builder:heading → site:productHeading
☐ commerce_builder:cartBadge → site:cartBadge
☐ commerce_builder:searchInput → site:searchInput
☐ All of the above
```

If user provided specific component name(s) in the original request, pre-filter to those and skip the selection prompt.

### Step 2: Replace in content.json

Send a plain-text chat reply to the user (per Rule 1): "I'm now replacing the selected OOTB component definitions with their open code equivalents in your site's content.json files."

The affected files are already known from Step 1. For each file that contains selected components:
1. Use the **Read** tool to read the file
2. For each selected OOTB component, confirm again that the mapped **`site:`** target exists in the open code repo. Only proceed with replacements that pass this check.
3. Replace all matching `"definition"` values with their mapped open code equivalents — **always** use the exact `site:<name>` string from the mapping table
   - Example: `"definition": "commerce_builder:heading"` → `"definition": "site:productHeading"`
4. Use the **Write** tool to save the updated file
5. Preserve all other JSON properties — only `"definition"` values change

**Batch efficiently:** if a file contains multiple OOTB components, apply ALL replacements in a single Read → modify → Write pass. Do NOT read and write the same file multiple times.

### Step 3: Report

```text
✅ Replacement Complete!

Replaced X components across Y files:
- commerce_builder:heading → site:productHeading (3 files)
- commerce_builder:cartBadge → site:cartBadge (2 files)
- commerce_builder:searchInput → site:searchInput (4 files)

Skipped (not in repo):
- commerce_builder:quoteSummary

No mapping available (left unchanged):
- commerce_builder:actionButtons
- commerce_builder:layoutHeaderOne
- commerce_builder:searchInputContainer

Modified files:
- sfdc_cms__view/Home/content.json
- sfdc_cms__view/Product_Detail/content.json
- sfdc_cms__themeLayout/DefaultTheme/content.json

Next Steps:
1. Deploy: sf project deploy start -d <package-dir>/main/default/digitalExperiences/site/<store-name>
2. Test the store thoroughly in Experience Builder
3. Publish your site when ready
```

---

## Example Interaction

**User:** "Replace OOTB components with open code versions"

**Agent:** "Before replacing components, I need to verify that the open code components are set up in your store. Let me check..."
- ✓ Open source repo cloned
- ✓ Store metadata available for My_B2B_Store1
- ✓ Open code components are integrated

**Agent:** "I'm scanning your store's site metadata to find all OOTB commerce components and checking which have open code equivalents."

_(Runs grep -rl to find files with commerce definitions, Reads those files to extract component names, runs ls to list repo components, then cross-references with mapping table)_

```text
Found 8 OOTB components in your site:

No mapping available (not in mapping table):
  - commerce_builder:searchInputContainer
  - commerce_builder:layoutHeaderOne
  - commerce_builder:myAccountMegaMenu
  - commerce_builder:actionButtons
```

**Agent** _(asks the user via a multi-select prompt):_
```text
Which components would you like to replace?

☐ commerce_builder:heading → site:productHeading
☐ commerce_builder:cartBadge → site:cartBadge
☐ commerce_builder:searchInput → site:searchInput
☐ commerce_builder:cartSummary → site:cartSummary
☐ All of the above
```

**User:** _(selects heading and cartBadge)_

**Agent:** "I'm now replacing the selected OOTB component definitions with their open code equivalents in your site's content.json files."

_(Files already known from scan — one Read/Write pass per affected file, all replacements batched)_

```text
✅ Replacement Complete!

Replaced 2 components across 5 files:
- commerce_builder:heading → site:productHeading (3 files)
- commerce_builder:cartBadge → site:cartBadge (2 files)

No mapping available (left unchanged):
- commerce_builder:searchInputContainer
- commerce_builder:layoutHeaderOne
- commerce_builder:myAccountMegaMenu
- commerce_builder:actionButtons

Modified files:
- sfdc_cms__view/Home/content.json
- sfdc_cms__view/Product_Detail/content.json
- sfdc_cms__themeLayout/DefaultTheme/content.json

Next Steps:
1. Deploy: sf project deploy start -d force-app/main/default/digitalExperiences/site/My_B2B_Store1
2. Test the store thoroughly in Experience Builder
```

---

## Rules

1. **Always explain in chat before executing.** Before every Bash or Write tool call, send a plain-text reply in the conversation that says what the command will do and why. The explanation MUST appear as a normal chat message preceding the tool call. Do NOT embed it inside the command itself (no `echo` lines, no `#` comments), do NOT prefix it to the command, and do NOT rely solely on the tool's `description` parameter — that field is not guaranteed to be visible to the user. After the explanation, issue the tool call and wait for the user to approve it before continuing.
2. **`assets/ootb-to-open-code-mapping.json` is the only source of truth.** Every OOTB → open-code mapping comes from that file; never guess, infer, or hallucinate component names. Each replacement's new `"definition"` MUST be the exact mapped value from the file, which always uses the `site:` namespace (e.g. `site:productHeading`). Before writing, verify the mapped target exists in the cloned open code components repo (under `.tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/`); if it is not present, skip the replacement and report it under "not in repo".
3. **Use Read and Write tools for JSON files.** Use the Read tool to parse `content.json` files and the Write tool to update them. Do NOT use bash to parse or edit JSON — no sed, awk, perl, or regex on JSON content. Bash is only for **simple file discovery** (`grep -rl`, `find`, `ls`) — never for extracting or modifying JSON values.
4. **Minimize commands.** Batch work into as few commands as possible. Use a single grep to scan all files, a single ls to verify the repo, and one Read/Write pass per file. Do NOT run a separate command for every component or every directory.

---

## Error Handling

| Error | Message | Action |
|-------|---------|--------|
| Prerequisites not met | "Open code components are not integrated yet." | Run integrating skill first |
| No mapping found | "No mapping found for '{component}'." | Show available mappings, report as unmapped |
| Component not in repo | "Open code component '{name}' not found in cloned repo." | Skip and inform user |
| No OOTB components in site | "No OOTB commerce components found in site metadata." | Inform user, nothing to replace |
| No replaceable components | "All OOTB components found are unmapped — none can be replaced." | Show the unmapped list, suggest checking for updated mappings |
| content.json parse error | "Failed to parse content.json: {file}" | Show error, skip file, continue with remaining files |

---

## Verification Checklist

- [ ] Prerequisites verified via integrating skill (repo, store, components)
- [ ] Site scanned + repo verified + mapping cross-referenced in minimal commands (Step 1)
- [ ] Each replacement uses the exact mapped `site:` definition and was verified present in the open code repo before write
- [ ] Breakdown shown to user with three categories before proceeding
- [ ] User selected components to replace (or provided names)
- [ ] Each `content.json` file updated in a single Read → modify → Write pass
- [ ] JSON structure preserved, no syntax errors introduced
- [ ] User informed of skipped and unmapped components
- [ ] Deployment command provided

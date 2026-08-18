---
name: dx-pkg-post-install-configure
description: "Use this skill to automate managed package post-install configuration. Package-agnostic — works with any managed package (LMA, FMA, work.com, Certinia, etc.). TRIGGER when: user installs a managed package and needs post-install configuration, mentions LMA/FMA/work.com post-install setup, asks to configure permission sets/FLS/page layouts for an installed package, says 'post-install', 'package setup', 'configure LMA', 'set up FMA', 'post-install steps'. DO NOT TRIGGER for: standalone permission set assignment (use dx-org-permission-set-assign), generating permission set metadata XML (use platform-permission-set-generate), package installation, or org switching."
metadata:
  version: "2.2"
  domains: ["Developer Experience"]
  minApiVersion: "67.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

## When to Use This Skill

Use when automating post-install configuration for any Salesforce managed package. This skill reads the package's post-install documentation, discovers available execution methods, and automates the configuration steps — including permission sets, object/field permissions, page layouts, Visualforce page access, and tab settings.

## Input

- **Required:** Package name (e.g., `LMA`, `FMA`, `work.com`)
- **Optional:** Path to post-install doc (PDF, markdown, URL)

If no doc is provided, ask the user to supply it.

## Workflow

Execute phases in order. Each phase must pass before proceeding.

---

### Phase 1: Discover Available Execution Methods

**Priority order:**
1. Org-native platform MCP servers (highest — direct org access via Headless 360)
2. Claude Code external MCP servers (sf-sobject-all, sf-sobject-all-sb, etc.)
3. sf CLI fallback (always available if authenticated)

#### Step 1A: Resolve org API version

Discover the org's current API version dynamically — never hardcode a version number:

```bash
sf org display --target-org <alias> --json
```

From the JSON response, read `result.apiVersion` (e.g., `"67.0"`). Store this value and use it as `v<apiVersion>` in all subsequent REST paths. If the command fails, fall back to the `minApiVersion` declared in this skill's metadata (`67.0`).

#### Step 1B: Check for org-native platform MCP servers

Query the Tooling API for MCP server availability:

```bash
sf api request rest "/services/data/v<apiVersion>/tooling/query?q=SELECT+Id,DeveloperName,MasterLabel+FROM+McpServerAccess" --target-org <alias>
```

#### Step 1C: Determine execution method

Check which Claude Code MCP tools are available and authenticated.

**MCP tool prefixes by org type:**

| Org Type | Tool Prefix |
|---|---|
| Production | `mcp__sf-sobject-all__` |
| Sandbox | `mcp__sf-sobject-all-sb__` |
| Falcon Test (pc-rnd) | `mcp__sf-sobject-all-falcon__` |

If MCP needs auth, call the authenticate tool. If auth fails, fall back to sf CLI.

---

### Phase 2: Verify Authentication & Org Identity

1. Run a lightweight test query (`SELECT Id, Name, IsSandbox FROM Organization`)
2. If MCP auth fails, automatically fall back to sf CLI
3. Display org info and ask user to confirm before proceeding

---

### Phase 3: Verify Package Installation

1. Determine the package namespace (ask user if unknown)
2. Check via Tooling API (`InstalledSubscriberPackage`) — do NOT use `PackageLicense`
3. If package not found, stop and inform user

---

### Phase 4: Read and Parse Post-Install Document

Read the provided document and extract discrete configuration steps.

**Supported formats:** PDF, markdown, URL (via WebFetch), pasted text.

**Parsing approach:**
1. Extract each numbered/bulleted step from the document
2. Present the extracted steps to the user for validation before proceeding

---

### Phase 5: Classify Steps & Interactive Plan Review

For each step extracted from the doc, classify as Automated or Manual.

#### Automation capabilities reference

**Via MCP (sobject-all) or sf CLI CRUD:**
- Record CRUD on any standard or custom object (PermissionSet, ObjectPermissions,
  FieldPermissions, SetupEntityAccess, PermissionSetTabSetting, PermissionSetAssignment, etc.)

**Via Metadata API retrieve/deploy (sf CLI):**
- Page layout modifications (add related lists, fields, sections)
- Profile settings
- Custom metadata type records

**Via sf CLI Tooling API:**
- Tooling queries (InstalledSubscriberPackage, ApexPage, ApexClass, etc.)
- Any REST-accessible Tooling operation

**Manual (no API path — requires Setup UI):**
- System permissions not exposed via REST
- Connected app OAuth configuration
- Environment Hub linkage

#### Interactive approval

Present the classified plan and let the user choose:
- **"Approve all"** — Execute all steps as planned
- **"Let me choose"** — Select which steps to approve/skip
- **"I have questions"** — Discuss specific steps before deciding

---

### Phase 6: Execute Approved Steps

For each approved step, use the resolved execution method.

#### Execution method reference

| Operation | Via MCP | Via sf CLI |
|---|---|---|
| SOQL query | `soqlQuery` tool | `sf data query --query "<SOQL>" --target-org <alias> --json` |
| Create record | `createSobjectRecord` tool | `sf data create record --sobject <Object> --values "..." --target-org <alias> --json` |
| Update record | `updateSobjectRecord` tool | `sf data update record --sobject <Object> --record-id <id> --values "..." --target-org <alias> --json` |
| Describe object | `getObjectSchema` tool | `sf api request rest "/services/data/v<apiVersion>/sobjects/<Object>/describe" --target-org <alias>` |
| Page layout | N/A | Metadata API retrieve/deploy |

#### Page layout modifications via Metadata API

Use `sf project retrieve start` → edit the layout XML → `sf project deploy start`.

#### Execution rules

- **Idempotency:** Before creating any record, query to check if it already exists. Skip if so.
- **Report after each step:** Show success count, skipped items, and reasons.
- **Automatic fallback:** If MCP fails mid-execution, retry via sf CLI.
- **On failure:** Report error, ask user to retry/skip/stop.

---

### Phase 7: Guide Manual Steps (if any)

If any steps could not be automated, present each with Setup navigation instructions.
Wait for user confirmation before proceeding to the next.

---

### Phase 8: Summary

Display final summary with step-by-step status, method used, and any skipped items.

---

## Error Handling

- **Auth failure mid-execution:** Stop, ask user to re-auth, offer to resume
- **Duplicate record errors:** Treat as "already configured", skip and continue
- **Permission errors:** Report which permission is missing, suggest resolution
- **Unknown step type:** Ask user to clarify, offer to mark as manual

## Notes

- **Priority: org-native MCP > Claude Code MCP > sf CLI > manual**
- sf CLI is always a valid fallback for all CRUD and Tooling API operations
- Page layout modifications are automated via Metadata API retrieve/deploy
- Always verify org identity before making changes
- All actions respect the authenticated user's permissions

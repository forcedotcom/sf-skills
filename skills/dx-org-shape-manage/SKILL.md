---
name: dx-org-shape-manage
description: "ALWAYS USE THIS SKILL to create, list, or delete org shapes. An org shape is a captured baseline configuration (features, limits, edition, and Metadata API settings) of a source org, without its data or metadata. Use when the user asks to create/make/take an org shape, capture or replicate an org's configuration/edition/limits, list/show/view existing org shapes (including INACTIVE/superseded ones) or their IDs and status, or delete/remove org shapes for a source org. Requires a source org with Dev Hub and Org Shape for Scratch Orgs enabled. DO NOT TRIGGER for creating snapshots or scratch orgs (use dx-org-manage)."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  relatedSkills:
    - "dx-org-manage"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "orgPref"
      value: "ScratchOrgManagementPref"
    - type: "orgPref"
      value: "ShapeExportPref"
---

# dx-org-shape-manage

Coordinates the full lifecycle of Salesforce org shapes — **create**, **list**, and **delete** — via `sf org create shape`, `sf org list shape`, and `sf org delete shape`. An org shape captures the baseline setup of a source org (features, limits, edition, and Metadata API settings) **without** its data or metadata.

---

## Tool Restrictions

**Use ONLY the Bash tool** to execute the `sf org ... shape` commands. Do NOT use MCP tools — ignore them completely.

**Output artifacts for eval/testing:** ALWAYS write the command's complete JSON response to a file when an output directory is available. Do NOT ask the user what file to write — this skill defines the filenames. After executing each command: (1) if the user specified an output path (e.g. "write all generated files into folder X"), write there immediately; (2) otherwise run `[ -d force-app/main/adk-eval-output/ ] && echo 'force-app/main/adk-eval-output'` to detect the eval directory; (3) write the command's full, unmodified JSON response (including the `status`/`result`/`warnings` wrapper) to `<output-dir>/<filename>` using these filenames: `create-shape-result.json` for shape creation, `list-shapes-result.json` for listing shapes, `list-shapes-inactive-result.json` for the inactive-shapes SOQL query, or `delete-shapes-result.json` for shape deletion. This is the generated output — write it without asking. Do NOT say "no files to generate" for these operations; the JSON result IS the output artifact.

---

## Scope

- **In scope**: Creating (`sf org create shape`), listing (`sf org list shape`), listing including inactive shapes for a specific source org (SOQL against `ShapeRepresentation`), and deleting (`sf org delete shape`) org shapes
- **Out of scope**: Creating snapshots, creating scratch orgs (use `dx-org-manage`)

---

## Required Inputs

Infer from the user's request:

- **Operation**: create, list, list-including-inactive, or delete (see Workflow step 1)
- **Source org** (create, delete, & list-including-inactive): Username or alias of the org to shape / whose shapes to delete or query. Passed via `--target-org`. Plain listing (Active/InProgress only) needs no source org.

Notes:
- There is **no** `--name` or `--description` flag — a shape is identified by the source org's ID, not a custom name.
- There is **no** `--target-dev-hub` flag — the shape commands operate on the source org directly, not a Dev Hub.

---

## Workflow

1. **Identify the operation** and match it to the command pattern below.
2. **For create/delete, confirm the source org** — identify the username/alias. If not provided, check the default with `sf config get target-org`.
3. **Execute via Bash tool** with the `--json` flag.
4. **Report the result** (see Output Expectations and the example files).

### Command Patterns

| Operation | User intent | Execute via Bash tool |
|-----------|-------------|------------------------|
| **Create** | Create shape from an org | `sf org create shape --target-org <alias> --json` |
| **Create** | Create shape from the default target org | `sf org create shape --json` |
| **List** | List all org shapes + IDs/status (Active/InProgress only) | `sf org list shape --json` |
| **List** | Save the list to a file | `sf org list shape --json > tmp/MyOrgShapeList.json` |
| **List (including inactive)** | List *all* shapes — including `Inactive` ones — for a specific source org | `sf data query --target-org <alias> --query "SELECT Id, Name, Status, CreatedDate, LastModifiedDate FROM ShapeRepresentation" --json` |
| **Delete** | Delete shapes for an org (with confirm prompt) | `sf org delete shape --target-org <alias> --json` |
| **Delete** | Delete shapes without prompting (scripts/CI) | `sf org delete shape --target-org <alias> --no-prompt --json` |

After creating a shape, run `sf org list shape --json` to get its **org ID**.

### Listing Inactive Shapes

`sf org list shape` has **no flag** to surface `Inactive` shapes and **no `--target-org`** flag (it always scans every locally authenticated org). To see a source org's full shape history — including shapes superseded by a later `sf org create shape` run — query `ShapeRepresentation` directly:

```bash
sf data query --target-org <alias> --query "SELECT Id, Name, Status, CreatedDate, LastModifiedDate FROM ShapeRepresentation" --json
```

Only use this query when the user explicitly asks for **inactive** or **all/historical** shapes for a named source org. For ordinary "list my org shapes" requests, keep using `sf org list shape` — it is the documented, cross-org command and matches the rest of this skill's behavior.

Notes:
- `ShapeRepresentation` has no `SourceOrgId`, `username`, or `alias` field — report the raw query fields (`Id`, `Name`, `Status`, `CreatedDate`, `LastModifiedDate`) as returned; do not invent an `orgId`/`username`/`alias` for these rows.
- Add `WHERE Status = 'Inactive'` to scope to only inactive shapes if the user asks for inactive shapes specifically (as opposed to "all"/"history").
- Requires the same `ShapeRepresentation` CRUD access as create/delete.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always use `--json` flag | Provides structured output for reliable parsing and error handling |
| Source org must have **Org Shape for Scratch Orgs** enabled | Without it, create/delete fail with a no-access error — enable via **Setup → Scratch Orgs → Enable Org Shape for Scratch Orgs** in the source org |
| User needs access to the `ShapeRepresentation` object | Without CRUD access, create fails with `NoCrudAccessCreateShape` — ask the org admin |
| `--target-org` is the SOURCE org, not a Dev Hub | Create/delete operate *on* this org; it is not a Dev Hub operation. List takes no `--target-org` |
| No `--name` / `--description` flags | A shape is keyed off the source org's ID, not a custom name |
| One active shape per source org | Re-running create replaces the prior shape (marks it inactive). `delete` removes **all** shapes for the org |
| `delete` prompts for confirmation by default | Use `--no-prompt` (`-p`) for non-interactive/CI use; declining the prompt aborts with no deletion |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `ShapeRepresentationNoAccess` — "The org needs to be enabled for org shape before one can be created" | Source org isn't enabled for org shape — in the source org go to **Setup → Scratch Orgs → Enable Org Shape for Scratch Orgs**, turn it on, then retry |
| `NoCrudAccessCreateShape` — "Can't create org shape. Contact the org admin..." | You lack access to the `ShapeRepresentation` object — ask the org admin to grant access, then retry |
| `ShapeCreateFailed` — "Error creating scratch definition file..." | Generic create failure — verify the source org is reachable/authenticated and retry; if it persists, contact Salesforce support |
| `UNKNOWN_EXCEPTION` on create (generic error with a support ErrorId, reproducible on retry) | The source org is not fully enabled for org shape even though `ShapeRepresentation` may be partially visible — confirm **Setup → Scratch Orgs → Enable Org Shape for Scratch Orgs** is on in the source org and that your user has CRUD on `ShapeRepresentation`, then retry |
| `sf org list shape` returns an empty list | No shapes exist yet (or none are `Active`/`InProgress`) — create one with `sf org create shape` |
| `sf org list shape` doesn't show a shape the user expects | It only surfaces `Active`/`InProgress` shapes and has no flag to change this — a prior `sf org create shape` run may have marked it `Inactive`. Use the SOQL query in "Listing Inactive Shapes" against that specific source org instead |
| Delete exits with code 68 (partial failure) | Some shapes failed to delete — inspect the `failures` array in the JSON for per-shape messages, then retry |
| Delete exits with code 1 (all failed) | Deletion failed entirely — confirm the org is enabled for org shape and you have access |
| `No org found for <alias>` / `NamedOrgNotFoundError` | Source org alias doesn't exist or isn't authenticated — verify with `sf org list` or re-auth with `sf org login web` |
| No default target org and `--target-org` omitted | Provide `--target-org <alias>` or set a default with `sf config set target-org=<alias>` |

---

## Output Expectations

All commands return JSON when `--json` is used:

- **Create** → `shapeId`, `success`, and `errors`.
- **List** → an array of shapes, each with `orgId`, `username`, `alias`, `shapeId`, `status` (`Active` or `InProgress`), `createdBy`, and `createdDate`.
- **List (including inactive)** → a SOQL query result (`records`, `totalSize`, `done`), each record with `Id`, `Name`, `Status` (`Active`, `InProgress`, or `Inactive`), `CreatedDate`, and `LastModifiedDate` — no `orgId`/`username`/`alias`, since `ShapeRepresentation` has no such fields.
- **Delete** → `orgId`, `shapeIds` (deleted), and `failures`. Returns no result if the user declines the confirmation prompt.

See the example files referenced below for full response structures.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Create a scratch org, or create/use a snapshot | `dx-org-manage` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `examples/create_success_output.json` | To understand the successful shape-creation response structure |
| `examples/create_error_output.json` | To handle common create error scenarios |
| `examples/list_output.json` | To understand the list response structure (org IDs, status) |
| `examples/list_inactive_output.json` | To understand the SOQL query response structure for listing shapes including `Inactive` ones |
| `examples/delete_output.json` | To understand the delete response structure (deleted IDs, failures) |
| `references/cli_flags.md` | For detailed explanation of all flags across create/list/delete |

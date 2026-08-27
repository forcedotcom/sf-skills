# Part 3 — Create a Fix Work Item

Creates a DevOps Center `WorkItem` to track a fix for a test failure or Code Analyzer violation. This is an **optional write**, triggered only when the user asks to create a fix work item, log a remediation, or assign a failure to a developer.

## Prerequisites

Run Prerequisites 1–4 (`references/prerequisite-checks.md`). You need `doce-org-alias`, a `DevopsProjectId` to file under, and an `OwnerId` (assignee). If no `DevopsProject` exists, surface that the work item cannot be created until a project exists — do NOT fabricate a project or work item.

## Inputs required before creating

| Input | How to obtain |
|---|---|
| `DevopsProjectId` | From the pipeline's associated project — query `DevopsProject WHERE Name = '<projectName>'` on the doce org if not already known |
| `Subject` | Derived from failure analysis — e.g. "Fix: Missing code-analyzer-v5.yml workflow in blitz-10-06 repository" |
| `OwnerId` | User ID of the developer to assign to — query `SELECT Id, Name FROM User WHERE Username = '<username>'` on the doce org if not known. Default to the requesting user when no assignee is specified; ask only if the username is unknown and no default applies. |
| `doce-org-alias` | Established in Prerequisites |

## Confirmation gate

Before creating the work item, show a summary and wait for explicit confirmation:

> "I'll create a fix work item with the following details:
> - **Subject:** `<subject>`
> - **Assigned to:** `<assigneeName>`
> - **Project:** `<projectName>`
>
> Shall I create it?"

Do not proceed until the user confirms.

## Creating the work item

```bash
sf data create record \
  --sobject WorkItem \
  --values "Subject='<subject>' DevopsProjectId='<DevopsProjectId>' OwnerId='<OwnerId>'" \
  --target-org <doce-org-alias> \
  --json
```

> **Important:** Use `WorkItem` (no namespace) — `DevopsWorkItem` is not a supported sObject in this org version.

## On success

Parse the returned `id` and confirm:

> "Fix work item created (`<id>`): `<subject>`. Assigned to `<assigneeName>` in the `<projectName>` project."

## Error handling

Never expose raw API error messages. Map errors to plain-language responses:

| Error | Response |
|---|---|
| `FIELD_INTEGRITY_EXCEPTION` | "The assignee ID is invalid. Let me look up the correct user ID — what's the developer's username?" |
| `REQUIRED_FIELD_MISSING` | "A required field is missing. Check that `Subject` and `DevopsProjectId` are both provided." |
| `INSUFFICIENT_ACCESS` | "Your user doesn't have permission to create work items in this project." |
| Any other error | "The work item could not be created. Error: `<plain summary>`. Try again or create it manually in DevOps Center." |

## No-project case

If the `DevopsProject` query returns 0 records, report clearly that no DevOps Center project exists and the work item cannot be created until one is set up. Do NOT fabricate a project name/ID, do NOT proceed to the confirmation gate or the create command.

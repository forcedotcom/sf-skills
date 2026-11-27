---
name: service-remove-agents-from-contact-center-assign
description: "Removes one or more agents (users) from a Contact Center (also known as Call Center). The action accepts user identifiers in multiple formats (User Id, Email, UserName, FirstName, LastName, or Alias) and a contact center identifier (CallCenter Id, Display name, or Internal name). Works with User, CallCenter metadata. Use this skill for remove agents from contact center, remove users from contact center, remove agents from call center, remove reps from contact center, remove reps from call center, remove users from call center, delete agents from contact center, delete users from contact center, delete agents from call center, delete users from call center, unassign agents from contact center, unassign users from contact center, unenroll agents from contact center, unenroll users from contact center."
metadata:
  version: "1.0"
  accessCheck: "(ServiceCloudVoice.userIsCCAdminScvOrBYOT) || (ServiceCloudVoice.userIsAdminUser)"
  tags:
  - "setup"
  domains:
  - "Service"
  utterances:
  - "Remove agents [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Remove agents [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Remove users [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Remove users [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Remove reps [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Remove reps [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Delete agents [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Delete agents [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Delete users [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Delete users [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Unassign agents [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Unassign agents [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Unassign users [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Unassign users [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Remove [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Remove [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Delete [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Delete [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Unassign [UserIdentifiers] from Contact Center [ContactCenterIdentifier]"
  - "Unassign [UserIdentifiers] from Call Center [ContactCenterIdentifier]"
  - "Remove [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Remove [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Delete [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Delete [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Unassign [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Unassign [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Remove agents [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Remove agents [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Remove users [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Remove users [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Delete agents [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Delete agents [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Delete users [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Delete users [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Unassign agents [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Unassign agents [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
  - "Unassign users [UserIdentifiers] from [ContactCenterIdentifier] Contact Center"
  - "Unassign users [UserIdentifiers] from [ContactCenterIdentifier] Call Center"
---


# Remove Agents from Contact Center

## When to Use This Skill

Use this skill when the user wants to remove, unassign, delete, or unenroll one
or more agents (users) from a Contact Center, also known as a Call Center. It
handles requests that identify the agents by User Id, email, username, first
or last name, or alias, and identify the contact center by its Id, display
name, or internal name.

## Workflow

1. Resolve every provided user identifier to a unique User ID.
2. Present the resolved users (with their User Ids) and the contact center as a
   draft, then stop and wait. Invoke the removal only after the user explicitly
   confirms in a later message — never in the same turn as the draft.
3. Remove the resolved agents from the specified contact center, passing only
   User Ids in userIdentifiers and the contact center identifier through
   unresolved.
4. Report the action's response as the result. The removal is asynchronous: an
   HTTP 200 with "We’re removing users from the contact center. Please give us a minute or two. We’ll send you an email when the process completes." certifies success — report it as a
   success and do not re-read User.CallCenterId or wait for the background job.

## Critical Constraints

**Preconditions:**
- One or more user identifiers for the agents to remove must be provided.
- A contact center identifier must be provided.
- The user must be a Contact Center admin or a Salesforce admin.
- The specified users must currently be associated with the specified contact
  center.

## Operations Reference

| Operation | Purpose | Call | Depends on |
|---|---|---|---|
| Resolve user identifiers | Resolve one or more user identifiers to unique User IDs | Resolve each user identifier (User Id, Email, UserName, FirstName, LastName, or Alias) to its User ID | - |
| Remove agents from contact center | Remove the resolved agents from the specified contact center | The Remove Agents from Contact Center action | Resolve user identifiers |

### Dependency graph

```mermaid
graph TD
    A[Resolve user identifiers] --> B[Remove agents from contact center]
```

### Read operations

**Resolve user identifiers**
Looks up each provided user identifier and returns its unique User ID.
- **Call:** resolve each User identifier to its User ID
- **Inputs:**
  - The entity type being resolved — `User`.
  - User identifiers (list) — each in one of: User Id, Email, UserName,
    FirstName, LastName, or Alias. Can be provided as a comma-separated list.
- **Output:** The resolved unique User IDs.

### Write operations

**Remove agents from contact center**
Removes the resolved agents from the specified contact center.
- **Call:** the Remove Agents from Contact Center action
- **Inputs:**
  - User IDs (list) — the User IDs resolved in the previous step.
  - Contact center identifier (string) — a CallCenter Id, display name, or
    internal name, passed through as provided without resolution.
- **Output:** A response describing the result of removing the agents from
  the contact center.
- **Depends on:** Resolve user identifiers.

## Notes

- User identifiers can be provided as a comma-separated list.
- Each identifier can be in any of these formats: User Id, Email, UserName,
  FirstName, LastName, or Alias.
- The contact center identifier can be a CallCenter Id, display name, or
  internal name.
- User identifiers are resolved to User IDs before being passed to the
  removal call; the contact center identifier is not resolved.

<!-- skill-validate: ignore-start -->
<!-- codey:operations start -->
## Operations Reference

Operations this skill uses — routing and dependency reference.

| Operation | Purpose | Status | Call | Depends on |
|-----------|---------|--------|------|------------|
| `resolve-user-identifiers` | read | implemented | `GET /services/data/v67.0/query` | — |
| `remove-agents-from-contact-center` | write | implemented | `POST /services/data/v67.0/headless/invocableaction` | `resolve-user-identifiers` |
| `verify-agents-removed-from-contact-center` | verify | implemented | `GET /services/data/v67.0/query` | `remove-agents-from-contact-center` |
<!-- codey:operations end -->
<!-- skill-validate: ignore-end -->

---
name: service-omni-queue-members-assign
description: "Use to bind agent users into a Salesforce Queue via GroupMember Data API POSTs, with SOQL-based idempotency (safe re-run — only inserts missing bindings). Binds either the generated demo agents (agent{1..N}.<suffix>@example.com) or an explicit list of real agents passed as usernames/User Ids. Triggers: add agents to a Case/Voice queue, assign agent users to a queue, populate queue membership for Omni routing. Do not use to create the queue (service-omni-queue-deploy), to create the agent users (service-omni-agent-users-create), or to assign permission sets (service-omni-permission-set-assign)."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-agent-users-create"
    - "service-omni-permission-set-assign"
    - "service-omni-queue-deploy"
    - "service-omni-queue-routing-config-deploy"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-queue-members-assign

Bind N agent users into a Salesforce Queue via `GroupMember` Data API POSTs. Without queue membership, Omni-Channel routing sees an empty pool for the queue and never assigns work. Detection is SOQL-based (the same detect-then-POST shape as `service-omni-queue-routing-config-deploy`), so only missing memberships are created and the skill is safe to re-run. Agent users come from `service-omni-agent-users-create`, the queue from `service-omni-queue-deploy`, and the users' Omni permissions from `service-omni-permission-set-assign`.

## Inputs

```bash
bash scripts/verify-and-bind.sh <org-alias> [queue-developer-name=CaseQueue] [count=3] [explicit-members-csv]
# demo agents (default):
bash scripts/verify-and-bind.sh myorg CaseQueue 3
# real agents by username/id:
bash scripts/verify-and-bind.sh myorg VoiceQueue "" "jdoe@acme.com,005XX000001abcd"
```

- `org-alias` (required).
- `queue-developer-name` (optional, default `CaseQueue`).
- `count` (optional, default `3`, range `1..10`) — must match the agent user count; ignored in explicit mode.
- `explicit-members-csv` (optional 4th positional, or `MEMBER_USERNAMES_CSV` / `MEMBER_USER_IDS_CSV`) — each token is a Username or a 15/18-char User Id; the count is derived from the list.

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL), Service Cloud license, `sf` CLI ≥ 2.139.6.
- The executing user has `PermissionsModifyAllData` (standard on System Administrator).
- The agent users exist (`service-omni-agent-users-create`) and the queue exists (`service-omni-queue-deploy`); a missing user set or queue blocks with a pointer to the right skill (queues cannot be created via the Data API).
- The three-way `safe_to_write` production guard applies — adding users to a production queue mis-routes real customer work, so it blocks with no override.

## Run

`verify-and-bind.sh` runs the whole cycle:

1. Compute `safe_to_write`; derive the 8-char org suffix.
2. Resolve the queue `Group.Id` by DeveloperName + `Type='Queue'`; block if missing.
3. Resolve the member set — generated mode queries `User` for `agent{1..N}.<suffix>@example.com` (block if any expected user is missing); explicit mode resolves each supplied token and requires every one to be an ACTIVE user.
4. Query existing `GroupMember` for the queue; compute the users not yet bound.
5. POST one `GroupMember` per missing user (individual POSTs, no `allOrNone`).
6. Re-query to confirm final membership and emit the report.

## Behavior

**Two member sources, never mixed.** The default generated pattern keeps the user-create → member-assign handoff deterministic; explicit mode is opt-in for real agents and takes over count derivation. In explicit mode, a token that does not resolve to an active user blocks the run — binding a typo'd or inactive user would silently under-populate the queue.

**Idempotency and honesty.** POSTs are individual so one failed binding (e.g. a race with another admin) never rolls back its successful siblings, and the skill re-queries after all POSTs — a 201 only means the write was accepted; a subsequent SOQL confirms the row is visible to the routing engine. The `before` snapshot includes members already present, even non-demo users added out-of-band, so the coordinator can see full membership state.

**Non-destructive.** Create-only; it never removes or reassigns existing members.

## Output contract

A single JSON object with `status` ∈ `bound` | `reused` | `partial` | `blocked`, the resolved `queue`, `org_suffix`, `member_source` (`generated_pattern` | `explicit`), `requested_count`, a `before` snapshot, `bound_this_run`/`bound_count`, `reused_count`, an `after` snapshot, `manual_actions`, and `blocking_issue`.

- `bound` — at least one new member created; final state matches the expected count.
- `reused` — all expected users were already members; nothing POSTed.
- `partial` — some POSTs failed; the re-query shows fewer members than requested (details in `blocking_issue`).
- `blocked` — precondition failed (production org, missing queue, missing users, missing permissions).

`bound_count + reused_count == requested_count` unless `partial`; `blocking_issue` is non-null only for `blocked`/`partial`.

## Limitations

- Generated and explicit modes are mutually exclusive per run.
- Create-only; removing or reassigning members is out of scope.
- Does not create the queue or the users, and does not assign permission sets or presence configs.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Before the detect/bind cycle — GroupMember schema, the queue-vs-public-group distinction, why `UserOrGroupId` is polymorphic, and common POST failures |
| `scripts/tests/test_queue_members_contracts.py` | When validating changes — run `python3 scripts/tests/test_queue_members_contracts.py` from this skill directory |

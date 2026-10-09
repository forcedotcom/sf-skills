---
name: service-omni-agent-users-create
description: "Create reusable agent users for Omni-Channel setup and routing validation. TRIGGER when users ask to create Omni agents, provision Omni test users, seed sandbox users for routing, create Omni-Channel routing agents, or repair missing demo agents. DO NOT TRIGGER for queue membership, permission-set assignment, or supervisor-user creation."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-permission-set-assign"
    - "service-omni-queue-members-assign"
    - "service-omni-supervisor-users-create"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.9"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-agent-users-create

Create N agent users on a Salesforce org via Anonymous Apex so Omni-Channel has agents to route work to. Usernames follow a deterministic per-org pattern, detection is SOQL-based, and the skill inserts only the users that are missing — so it is safe to re-run. It is invoked by `service-omni-channel-setup-coordinate` after `service-omni-base-settings-configure` enables Omni-Channel; assigning permission sets (`service-omni-permission-set-assign`) and adding users to queues (`service-omni-queue-members-assign`) are separate leaves. Supervisor users come from `service-omni-supervisor-users-create`.

## Inputs

Confirm once, up front:

- `org-alias` (required, no default) — must resolve via `sf org display`.
- User count (optional, default `3`, range `1..10`).
- Profile name (optional, default `Standard User` for portability). The coordinator overrides this to a Service Cloud profile so agents consume Service Cloud licenses; on many CDOs the Salesforce license pool is saturated while Service Cloud has free slots.

Usernames and passwords are never accepted from the operator — both are generated (usernames from the org suffix, passwords via Anonymous Apex). Operator-supplied credentials would break re-run detection and risk weak or leaked secrets.

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL, not `.lightning.force.com`), Service Cloud license present, `sf` CLI ≥ 2.139.6.
- The executing user has `PermissionsModifyAllData` and `PermissionsManagePasswordPolicies` (standard on System Administrator).
- **Production guardrail:** the detect script computes `safe_to_write` as `IsSandbox` OR `TrialExpirationDate != null` OR `OrganizationType` in {Developer Edition, Base Edition}, and the skill blocks with no override when it is false. CDOs, scratch orgs, and dev orgs are permitted.

**Password handling (fail-closed).** Passwords are set by Anonymous Apex `System.setPassword` (`sf user password generate` cannot target Apex-inserted users — it fails with `NamedOrgNotFoundError`). The password literal appears in the inline executeAnonymous debug log and, only when a debug-log TraceFlag is active for the running user, in a queryable `ApexLog`. The wrapper therefore fails closed *before* the first `System.setPassword`: it proves via a SOQL-filtered Tooling API query (`ExpirationDate > now`) that no active TraceFlag exists. If safety cannot be positively proven — the running user is unresolved, the query fails or is unparseable, or any active TraceFlag exists — it generates no password at all; the user is left ACTIVE, flagged `password_status:"reset_required"`, and a `security_warning` explains why. It never deletes logs, so no plaintext can reach an `ApexLog` and unrelated audit logs are untouched. If `System.setPassword` itself fails for a user, that user is kept ACTIVE and flagged for reset.

## Run

```bash
# read-only preview (never writes)
bash scripts/detect-and-create.sh plan <org-alias> [count] [profile-name]
# detect, enforce safe_to_write, then insert only the missing users
bash scripts/detect-and-create.sh run  <org-alias> [count=3] [profile-name="Standard User"]
```

`detect-and-create.sh` is the canonical entry point: it re-runs detection, enforces the production guard, and only then inserts. Do not call `scripts/run-create.sh` directly — it is internal and does not enforce the guard on its own.

## Behavior

**Detection.** The detector derives an 8-char suffix from `Organization.Id` (`substring(10,18)`, lowercased), resolves the profile by name, and queries `User` for `agent{i}.<suffix>@example.com` to find which of the `count` slot indexes are occupied. A stable, deterministic pattern is what makes re-runs idempotent — the suffix is never a timestamp or UUID.

**Insertion.** The Apex loads `assets/create-users.apex.template`, substitutes `__COUNT__`/`__PROFILE_ID__`/`__SUFFIX__`, and inserts only the missing indexes. It re-checks existing users inside the transaction, which prevents a single run from double-inserting; across *concurrent* runs the in-transaction check is not a guarantee (both can pass their pre-query before either commits), so duplicate protection there relies on the global username-uniqueness constraint plus the `DUPLICATE_USERNAME` retry (see references/apex-template-notes.md). It enables the Service Cloud feature (`UserPermissionsSupportUser=true`) so users can go online in Omni; if the profile's license does not allow it, the Apex strips the flag and retries (users are still created, but need a Service-Cloud-license profile for full Omni). Each created user is reported via `AGENT_USER_CREATED|<id>|<username>|<email>` (no password in the marker — passwords are set by the separate `System.setPassword` submission).

**Verification.** After insertion the detector re-runs and must show `missing_count == 0`; otherwise the skill fails (the Apex reported success but the users did not persist).

## Output contract

`detect-and-create.sh` emits a single JSON object with `status` ∈ `created` | `partial` | `reused` | `action_needed` | `blocked`, plus `detect` (mirrors the detector), `create` (mirrors the inserter, `null` when nothing was created), top-level `reused_users`, `created_count`, `reused_count`, `total_present_after`, `users_needing_password_reset`, `action_required`, and `safe_to_write`. The coordinator combines `reused_users` with newly created users so mixed runs configure presence and skills for the complete requested agent set.

- `created` — every missing index landed with a working password.
- `partial` — some landed but not all, or any user needs a manual password reset, or inactive occupants were found.
- `reused` — all requested users already existed; nothing created.
- `action_needed` — plan mode only; reports missing indexes without writing.
- `blocked` — precondition failed (`safe_to_write=false`, unresolved profile/suffix, or nothing inserted).

`create.created_users[].password` is populated only for users created this run whose `System.setPassword` succeeded; `password_status:"reset_required"` means the user is ACTIVE but has no working password yet. Exit code is 0 for `created`/`partial`/`action_needed`/`reused`, 1 for `blocked`.

Generated passwords are a secret: the returned JSON is the only place they appear. Any caller that persists stdout must write it only to a restricted `CREDENTIALS.json` (mode 0600), redact it from every other artifact, and delete it after distribution — the coordinator does this automatically; standalone callers own it. Reused users' passwords are not retrievable; recover via Setup → Users → Reset Password.

## Limitations

- Username pattern and org suffix are fixed and never operator-configurable — that determinism is what enables idempotent re-runs.
- Creates only agent users on the given profile; it never deletes, deactivates, or mutates existing users.
- Common User errors (`DUPLICATE_USERNAME`, `INVALID_EMAIL`, `LICENSE_LIMIT_EXCEEDED`) are translated into operator-friendly messages rather than surfaced raw.

## References

| File | When to read |
|---|---|
| `references/apex-patterns.md` | Before running the Apex — Apex structure, User field defaults, password policy, and the profile-localization risk |
| `references/apex-template-notes.md` | When user creation returns a duplicate, license, or password error — explains template substitutions and retry behavior |
| `assets/create-users.apex.template` | Loaded by `scripts/run-create.sh` when missing agent users must be inserted |
| `scripts/detect-existing.sh` | Loaded by the canonical entry point for the read-only org, profile, safety, and existing-user checks |
| `scripts/tests/test_user_create_security.py` | Run after changing the user-creation scripts to verify production refusal and password-handling contracts |

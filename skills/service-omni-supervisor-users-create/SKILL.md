---
name: service-omni-supervisor-users-create
description: "Use to create N Omni-Channel supervisor users on a Salesforce org via Anonymous Apex, using the supervisor{i}.<suffix>@example.com pattern with SOQL-based idempotency (re-runs skip existing usernames). Passwords are set via System.setPassword and handled fail-closed: the wrapper proves no active debug TraceFlag before setting a password, and otherwise leaves the user ACTIVE and reset_required. Triggers: create supervisor users, provision supervisor accounts, scaffold supervisor personas. Do not use on production customer orgs (blocked by the safe_to_write guard), to bind supervisors to OmniSupervisorConfig (service-omni-supervisor-config-deploy), or to assign the ContactCenterSupervisor permission set (service-omni-supervisor-permset-assign)."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-agent-users-create"
    - "service-omni-supervisor-config-deploy"
    - "service-omni-supervisor-permset-assign"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-supervisor-users-create

Create N supervisor users on a Salesforce org for the classic Omni-Channel Supervisor Configuration (`OmniSupervisorConfig`), which binds named user records via `OmniSupervisorConfigUser`. Users follow a deterministic `supervisor{i}.<suffix>@example.com` pattern so the coordinator can rediscover them across runs. It is the supervisor counterpart to `service-omni-agent-users-create` and shares its detection, password, and idempotency model; the only differences are the username/alias prefixes and the debug-log marker. Binding these users into a config (`service-omni-supervisor-config-deploy`) and granting them supervisor access (`service-omni-supervisor-permset-assign`) are separate leaves.

## Inputs

Confirm once, up front:

- `org-alias` (required, no default) — must resolve via `sf org display`.
- Supervisor count (optional, default `1`, range `1..5`; the coordinator typically requests 1).
- Profile name (optional, default `Standard User`). The coordinator overrides this to a Service Cloud profile so supervisors consume Service Cloud licenses; supervisor access itself comes from the standard `ContactCenterSupervisor` permission set assigned later.

Usernames and passwords are never accepted from the operator — both are generated (usernames from the org suffix, passwords via Anonymous Apex).

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL, not `.lightning.force.com`), Service Cloud license present, `sf` CLI ≥ 2.139.6.
- The executing user has `PermissionsModifyAllData` and `PermissionsManagePasswordPolicies` (standard on System Administrator).
- **Production guardrail:** the detect script computes `safe_to_write` as `IsSandbox` OR `TrialExpirationDate != null` OR `OrganizationType` in {Developer Edition, Base Edition}, and the skill blocks with no override when it is false. CDOs, scratch orgs, and dev orgs are permitted.

**Password handling (fail-closed).** Passwords are set by Anonymous Apex `System.setPassword` (`sf user password generate` cannot target Apex-inserted users). The literal appears in the inline executeAnonymous debug log and, only when a debug-log TraceFlag is active for the running user, in a queryable `ApexLog`. The wrapper therefore fails closed *before* the first `System.setPassword`: it proves via a SOQL-filtered Tooling API query (`ExpirationDate > now`) that no active TraceFlag exists. If safety cannot be positively proven, it sets no password at all; the user is left ACTIVE, flagged `password_status:"reset_required"`, and a `security_warning` explains why. It never deletes logs. A user whose password could not be set is kept ACTIVE and flagged for reset — never deactivated.

## Run

```bash
# read-only preview (never writes)
bash scripts/detect-and-create.sh plan <org-alias> [count] [profile-name]
# detect, enforce safe_to_write, then insert only the missing supervisors
bash scripts/detect-and-create.sh run  <org-alias> [count=1] [profile-name="Standard User"]
```

`detect-and-create.sh` is the canonical entry point: it re-runs detection, enforces the production guard, and only then inserts. Do not call `scripts/run-create.sh` directly — it is internal and does not enforce the guard.

## Behavior

**Detection.** The detector derives an 8-char suffix from `Organization.Id`, resolves the profile by name, and queries `User` for `supervisor{i}.<suffix>@example.com`, splitting occupied slots into active `existing_users` and `inactive_users`.

**Insertion.** The Apex loads `assets/create-supervisors.apex.template`, substitutes `__COUNT__`/`__PROFILE_ID__`/`__SUFFIX__`, and inserts only the missing indexes, re-checking inside the transaction to prevent a single run from double-inserting; across *concurrent* runs this check is not a guarantee (both can pass their pre-query before either commits), so duplicate protection there relies on the global username-uniqueness constraint plus the `DUPLICATE_USERNAME` retry (see references/apex-template-notes.md). Created users get the Service Cloud feature (`UserPermissionsSupportUser=true`); if the profile's license does not allow it, the Apex strips the flag and retries (the permset assign will then block until the user is on a suitable license). Each created user is reported via `SUPERVISOR_CREATED|<id>|<username>|<email>` (no password in the marker — it is set by the separate `System.setPassword` submission).

**Inactive occupants.** An inactive user occupying a supervisor slot is not a reusable supervisor and cannot be recreated (usernames are globally unique). It is surfaced as a required manual reactivation and never counted toward the requested slots — counting it would under-provision the config.

**Verification.** After insertion the detector re-runs and must show `missing_count == 0`.

## Output contract

`detect-and-create.sh` emits a single JSON object with `status` ∈ `created` | `partial` | `reused` | `action_needed` | `blocked`, plus `detect`, `create` (`null` when nothing was created), `created_count`, `reused_count`, `total_present_after`, `users_needing_password_reset`, `action_required`, and `safe_to_write`.

- `created` — every missing index landed with a working password.
- `partial` — some landed but not all, any `System.setPassword` failed (kept ACTIVE, listed in `users_needing_password_reset`), or a slot is occupied by an inactive user needing reactivation.
- `reused` — all requested slots already existed; no DML.
- `action_needed` — plan mode only.
- `blocked` — precondition failed.

`create.created_users[].password` is populated only for users created this run whose `System.setPassword` succeeded. `create.rolled_back_users` is always empty (this skill never deactivates a user). Generated passwords are a secret: the returned JSON is the only place they appear; a caller that persists stdout must write it only to a restricted `CREDENTIALS.json` (mode 0600), redact it elsewhere, and delete it after distribution — the coordinator does this automatically.

## Limitations

- Username pattern and org suffix are fixed and never operator-configurable — that determinism is what enables idempotent re-runs.
- Creates only supervisor users; it never deletes or deactivates users, including orphaned supervisors from prior runs.
- Common User errors (`DUPLICATE_USERNAME`, `INVALID_EMAIL`, `LICENSE_LIMIT_EXCEEDED`) are translated into operator-friendly messages rather than surfaced raw.

## References

| File | When to read |
|---|---|
| `references/apex-patterns.md` | Before running the Apex — Apex structure, User field defaults, password policy, and the profile-localization risk |
| `references/apex-template-notes.md` | When creation returns a duplicate, license, password, or trace-safety error |
| `assets/create-supervisors.apex.template` | Loaded by `scripts/run-create.sh` when missing supervisor users must be inserted |
| `scripts/detect-existing.sh` | Loaded by `scripts/detect-and-create.sh` for the read-only org, profile, safety, and existing-user checks |
| `scripts/run-create.sh` | Internal writer loaded by `scripts/detect-and-create.sh` only after guard checks pass |

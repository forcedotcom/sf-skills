# service-omni-supervisor-users-create — Apex patterns

Load this reference **only when the Apex template needs modification or debugging**. Under normal operation `run-create.sh` handles everything.

## Why Anonymous Apex over REST User POST

Two forcing constraints:


1. **`System.setPassword()` is Apex-only.** REST POST creates the user but requires an email-based password reset flow. That's a UX blocker for bootstrap scenarios.
2. **In-transaction re-check for concurrency.** If two operators run this skill simultaneously against the same org, REST POSTs race and one hits `DUPLICATE_USERNAME`. Apex re-queries inside the transaction and skips already-existing indexes atomically.

## Username pattern

`supervisor{i}.<orgsuffix>@example.com`

- `i` is 1..N (max 5 for supervisors)
- `orgsuffix` is deterministic — the last 8 chars of `Organization.Id`, lowercased
- `@example.com` is a reserved TLD, safe to use per RFC 2606

Deterministic pattern ⇒ any operator, any subsequent run, any skill can query for existing supervisors without shared state.

## Alias construction

Salesforce Alias field: **max 8 chars, alphanumeric**.

Format: `omsu{i}{last-3-of-suffix}`

- `omsu` prefix identifies these as Omni Supervisor agent users
- `i` is 1 char (1..9 max — 5 supervisors max ensures we never hit 10+)
- 3 trailing suffix chars give per-org uniqueness
- Total: 8 chars exactly

## Password pattern

`SuprV1<10-char-random-hex>` — 16 chars total.

Guaranteed to satisfy Salesforce's default password policy:
- ≥1 uppercase letter (`S`, `V`)
- ≥1 lowercase letter (from random)
- ≥1 digit (`1`)
- ≥1 special char (none required by default)
- ≥8 chars total (16)

Random source: `Crypto.generateAesKey(128)` → hex encode → first 10 chars.

## Standard User profile

**Why Standard User instead of a Supervisor-specific profile?**

1. **All standard editions ship it.** Custom profiles differ per org edition.
2. **Supervisor perms live in a PermissionSet** (`Omni_Supervisor`, assigned by `service-omni-supervisor-permset-assign`), not in the profile.
3. **Consistent with agent skill.** Same profile, different permset. Simpler mental model for reviewers.

## Debug log parsing

Each successful user creation emits exactly one line to the Apex debug log:

```text
SUPERVISOR_CREATED|<userId>|<username>|<password>|<email>
```

`run-create.sh` greps this pattern with a strict regex anchored on the User Id shape (`005` + 15 alphanumerics = 18 chars) to filter out source-code echoes and comment lines that might appear in the log.

## Failure modes surfaced to the skill-report

| Symptom | Cause | User-friendly translation |
|---------|-------|--------------------------|
| `LICENSE_LIMIT_EXCEEDED` | Org is out of user license slots | "Org has reached its user license limit. Free up a license slot or request a larger CDO." |
| `DUPLICATE_USERNAME` | Global collision (rare — deterministic suffix should prevent) | "Retry the skill; if it persists, escalate." |
| `INVALID_EMAIL_ADDRESS` | Should never happen with @example.com | "Bug in the skill template — escalate." |
| `INSUFFICIENT_ACCESS` | SF CLI user is not admin | "Ensure the authenticated user is System Administrator." |
| `INVALID_SESSION_ID` | Session expired | "Re-authenticate: sf org login web -a <alias>" |

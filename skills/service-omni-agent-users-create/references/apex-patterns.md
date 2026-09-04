# Apex patterns for agent user creation

Load this reference **only when the Apex block is actually going to run** (i.e., after `detect-existing.sh` returned `missing_count > 0`). It covers the Apex structure, `User` sObject required fields, password policy, profile-localization gotcha, and the emitted-log contract.

**Apex version verified:** v66 (Summer '26 baseline).
**Runtime:** Anonymous Apex via `sf apex run --target-org <alias> --file <resolved>.apex`.

---

## The Apex template shape

The template at `assets/create-users.apex.template` uses three tokens:

| Token | Type | Resolved by |
|---|---|---|
| `__COUNT__` | integer 1..10 | `run-create.sh` argument 2 (from operator input, default 3) |
| `__PROFILE_ID__` | 18-char Profile Id | `detect-existing.sh` from `SELECT Id FROM Profile WHERE Name = ?` |
| `__SUFFIX__` | 8-char lowercase hex | `detect-existing.sh` from `Organization.Id.substring(10, 18).toLowerCase()` |

Token substitution uses `sed` with **pipe (`|`) as the delimiter**, not `/`. This is not because Ids or names contain `/` (they do not) but because pipe is universally not-a-metacharacter in `sed`, avoiding future foot-guns if a token value ever contains a `/`.

---

## `User` sObject required fields

Salesforce enforces the following as required (non-nullable) when inserting a `User`:

| Field | Value used | Notes |
|---|---|---|
| `Username` | `agent{i}.{suffix}@example.com` | Must be globally unique across all Salesforce orgs. Our suffix strategy makes this per-org-unique; `@example.com` domain avoids sending real email |
| `Email` | same as `Username` | Salesforce enforces per-org email uniqueness (not global) — same suffix works |
| `LastName` | `Agent{i}` | Required, no default |
| `Alias` | `omag{i}{last-3-of-suffix}` (or `last-2` for i≥10) | Max 8 chars. Cross-org uniqueness NOT required |
| `ProfileId` | resolved from `Profile.Name` | See profile-localization note below |
| `TimeZoneSidKey` | `America/Los_Angeles` | Safe default for CDOs |
| `LocaleSidKey` | `en_US` | Safe default |
| `EmailEncodingKey` | `UTF-8` | Safe default |
| `LanguageLocaleKey` | `en_US` | Safe default; not all orgs enable all languages, but `en_US` is always available |

Optional but set for clarity: `FirstName = 'Omni'`, `IsActive = true`.

---

## Password policy & `System.setPassword`

Default org password policy on Enterprise Edition CDOs: min 8 chars, must contain at least 1 letter and 1 number. Our password format `AgntV1<10-hex>` satisfies this (contains `A`, `V` (upper), `g`, `n`, `t` (lower), `1` (digit), plus hex chars which contribute more letters+digits).

**`System.setPassword(Id, String)` requirements:**
- Executing user must have `PermissionsManagePasswordPolicies=true` (standard on System Administrator)
- Password must satisfy the org's password policy (`Setup → Password Policies`)
- On success, the user's password is set immediately; the user does NOT receive a verification email and is immediately usable
- On failure (policy violation), throws `System.NoAccessException` or a `System.InvalidPasswordException` — the skill's Apex catches these per-user and emits a `AGENT_USERS_PASSWORD_ERRORS` line without failing the whole run

**Note:** the skill's Apex sets passwords AFTER inserting users, not as a single atomic transaction. If a password-set fails for user N, the user still exists but has no password (Salesforce assigns a random one internally). The operator can then use "Reset Password" in Setup.

---

## Idempotency (belt + suspenders)

Two independent guards:

1. **Pre-check (in `detect-existing.sh`):** query `User` by username pattern → return `missing_indexes` array. If empty, skip Apex entirely.
2. **In-Apex re-check:** the Apex block queries `User WHERE Username IN :expectedByUsername.keySet()` inside its transaction, then builds `toInsert` from only the truly missing indexes. This handles two edge cases:
   - Concurrent skill runs (rare): two agents run this skill against the same org at nearly the same time
   - State drift between pre-check and Apex execution (very rare): another skill or manual UI action creates a matching user between the two SOQL queries

The in-Apex re-check makes the skill safe even if the pre-check is stale. In the concurrent-race case, the second run will find all users existing and emit `AGENT_USERS_ALL_EXIST` with no inserts.

---

## Profile-localization gotcha

`Profile.Name` is **not localized** for standard profiles (`Standard User`, `System Administrator`, `Marketing User`, etc.) as of v66 — verified on EPIC CDOs (English). But other Salesforce edition variants may localize these names (`Utilisateur standard` on French orgs?). Empirically we have not seen this, but the skill accepts the risk with a hardcoded default of `Standard User`.

**If a user overrides `--profile` to a custom profile**, they own the risk that the profile name is spelled correctly and matches exactly (case-sensitive). Custom profiles have a `DeveloperName` field (API-stable) but standard profiles do not — so this skill uses `Name` as the only universal lookup key.

A fallback query that also matches `DeveloperName` is possible:
```sql
SELECT Id FROM Profile WHERE Name = :profileName OR DeveloperName = :profileName LIMIT 1
```
The skill uses `Name` only, to keep the query simple and the error message clear.

---

## The emitted-log contract (parsed by `run-create.sh`)

The Apex block emits three kinds of `System.debug` lines that the shell script parses:

| Line prefix | When | Format |
|---|---|---|
| `AGENT_USER_CREATED` | One per newly-created user (never for reused users) | `AGENT_USER_CREATED\|<userId>\|<username>\|<password>\|<email>` |
| `AGENT_USERS_ALL_EXIST` | When `toInsert` is empty (all N users already existed at Apex transaction time) | Exactly the string `AGENT_USERS_ALL_EXIST — no inserts required` |
| `AGENT_USERS_PASSWORD_ERRORS` | When one or more `System.setPassword` calls failed | `AGENT_USERS_PASSWORD_ERRORS: <JSON-array of "username: error-message">` |

`run-create.sh` greps for these lines (they are the only lines starting with `AGENT_`), parses them, and constructs the return JSON.

---

## Failure modes

| Symptom in Apex output | Root cause | Skill behavior |
|---|---|---|
| `DUPLICATE_USERNAME` | Global-uniqueness violation — another org somewhere in Salesforce owns this username | Should not happen with the org-id suffix strategy. If it does, run detect again — likely a race with a concurrent run. Fail if it persists |
| `INVALID_EMAIL_ADDRESS` | Should not happen with `@example.com`. Would indicate a bug in username construction | Fail and escalate — skill logic error |
| `LICENSE_LIMIT_EXCEEDED` | Org's Salesforce license count is at max | Fail with an operator-friendly message: "Org has reached its user license limit — free up a license slot or ask Salesforce for more" |
| `System.NoAccessException` on `System.setPassword` | Executing user lacks `ManagePasswordPolicies` perm | Skill continues (per-user catch), emits `AGENT_USERS_PASSWORD_ERRORS`, operator uses Setup → Reset Password |
| `System.InvalidPasswordException` on `System.setPassword` | Org has a stricter password policy than our `AgntV1<10-hex>` satisfies | Should not happen with default policies. Skill continues, emits `AGENT_USERS_PASSWORD_ERRORS`, escalate to update the password generator |
| `UNABLE_TO_LOCK_ROW` | Concurrent transaction locked the `User` table | Retry the skill once. Rare on CDOs |

---

## Production-safety signal (three-way check)

**Discovery during on-org testing:** `IsSandbox` alone is insufficient to distinguish "safe to write demo data" from "real customer production". CDOs (Customer Demo Orgs, our primary target shape) have `IsSandbox=false` because they are not derived from a production org — they are standalone Enterprise Edition orgs with a trial expiration.

The correct three-way check:

```sql
SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1
```

`safe_to_write = true` if **any** of the following is true:

| Signal | Meaning |
|---|---|
| `IsSandbox = true` | Real sandbox — safe by construction |
| `TrialExpirationDate != null` | Trial org, CDO, or similar time-limited org — safe |
| `OrganizationType = 'Developer Edition'` | Dev org — safe |
| `OrganizationType = 'Base Edition'` | Scratch org — safe |

`safe_to_write = false` only when **all four** signals fail — i.e., `IsSandbox=false` AND `TrialExpirationDate=null` AND `OrganizationType NOT IN ('Developer Edition', 'Base Edition')`. That combination is definitionally a real customer production org.

**Example:** a CDO reporting `IsSandbox=false`, a non-null `TrialExpirationDate`, and `OrganizationType=Enterprise Edition` resolves to `safe_to_write=true` — the correct behavior for a demo/trial org.

**Other write-capable skills reuse this same three-way check.** A naive `IsSandbox=true` check would incorrectly block all CDOs, which are the primary target shape for these skills.

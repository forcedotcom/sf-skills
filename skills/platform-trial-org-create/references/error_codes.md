# SignupRequest Error Codes

There are **two distinct error systems** for `SignupRequest`:

1. **Synchronous field validation** — returned immediately on `sf data create record` (non-zero `status`; the CLI puts the code in `name`/`code` and flattens the underlying sObject `errors[]` into the `message` string, with `result: null`). **These are server-side rejections**: the record *is* sent to the org, and the platform rejects it at insert time — both the SignupRequest-specific validators (`missingEdition`, `redundantTemplateId`, `INVALID_EMAIL_ADDRESS`, `INVALID_SIGNUP_COUNTRY`) and the generic UDD field constraints enforced on any sObject write (`STRING_TOO_LONG` for a value over a field's max length, `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` for a bad `Edition` value). Do **not** describe these as "client-side" — the CLI does not enforce field length, picklist values, or email/country format locally; the server does. Source: validator classes under `core/signup-request/java/src/sfdc/signup/validation/` (SignupRequest-specific) plus core UDD field validation (generic). The client-side pre-checks are only those the create script itself performs before calling `sf` — a dependency check (`sf`/`jq` on PATH), required-field presence, the "exactly one of `TemplateId`/`Edition`" rule, and the both-quote-styles guard — all of which exit non-zero *without* contacting the org. None of them validate a value's **content** (length, picklist membership, email/country format); that is always server-side.
2. **Asynchronous provisioning failure** — surfaced only while polling, as `result.Status = Error` with a `result.ErrorCode` (max 8 chars, prefixed). Source: `core/signup-request-api/java/src/sfdc/signup/SignupRequestErrorCodes.java`. Human-readable messages come from `LabelRef`s in the `SignupRequestErrors` label section.

The prefix table below is the **async `ErrorCode`** (system 2). The common-failures table mixes both, labeled by when each surfaces.

## Error code prefixes

| Prefix | Category |
|---|---|
| `C-` | Org-creation failure |
| `S-` | Signup-data failure |
| `T-` | Template failure |
| `SH-` | Shape failure |
| `VR-` | Version-selection failure |
| `X-0001` / `X-0002` | Fatal "should never happen" errors |

## Common failures (surfaced at insert time in the create envelope's `name`/`message`)

| Symptom | Likely cause / fix |
|---|---|
| `NOT_FOUND` ("The requested resource does not exist") or `INVALID_TYPE` ("sObject type 'SignupRequest' is not supported") | The `SignupRequest` entity is not exposed → the org is not entitled to create trial orgs. Not retryable. Surface the **raw CLI error as-is** and tell the user to **reach out to Salesforce support** to get the org enabled — do not name or diagnose the missing permission. |
| `INSUFFICIENT_ACCESS_OR_READONLY` | Entity is exposed but the *user* lacks the access to create the record — a user-perm problem; fix the user's permissions and retry. |
| `missingEdition` (`INVALID_SIGNUP_OPTION`) | Neither `TemplateId` nor `Edition` supplied — send exactly one |
| `redundantTemplateId` (`INVALID_SIGNUP_OPTION`) | Both `TemplateId` and `Edition` supplied — send only one |
| `noPartnerAccess` (`NO_PARTNER_PERMISSION`) | A partner/Trialforce edition requested but host org lacks partner/TMC perm — use a generic edition |
| clone/source + template/edition | Clone (`CloneFromOrg`) or source-org signup must not also send `TemplateId`/`Edition` |
| Invalid username (`INVALID_EMAIL_ADDRESS`) | Username not email-format, or not globally unique (duplicate) — ask for a different one and retry |
| `INVALID_SIGNUP_COUNTRY` | `Country` not a valid/allowed ISO code (embargoed or malformed) — fix and retry |
| `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` | `Edition` is not an accepted value for the host org's restricted `Edition` picklist (e.g. `Ultimate`, or a partner value the org can't use) — pick a valid generic edition (`Developer`, `Enterprise`, …) and retry |
| `STRING_TOO_LONG` | A text field exceeds its max length (e.g. `LastName`/`Company`/`Username` over 80 chars) — the message names the field and `max length` — shorten it and retry. Server-side, **not** a client-side check. |
| Invalid / not-found `TemplateId` | `0TT` template id wrong or not visible to host org. **Note: this is validated asynchronously, not at insert** — a well-formed but nonexistent `0TT` inserts successfully (`status: 0`) and surfaces later on read-back as `Status = Error` with a `T-` `ErrorCode` (e.g. `T-0002`). Handle it in Step 2, not as a create-time rejection. |
| `subdomainInUse` / invalid subdomain | Requested `Subdomain` taken or malformed |
| `dailyLimitExceeded` / `activeScratchLimitExceeded` | Daily/active signup rate limit hit for the host org |

## Handling in the skill

- Insert-time validation failures come back from `sf data create record` as a non-zero `status` with the code in `name`/`code` and the detail flattened into `message` (`result: null`) — report the message and stop.
- Async provisioning failures show up on polling (`sf data get record`) as `result.Status = Error` with a `result.ErrorCode` — report the code + category and stop polling.

---
name: platform-trial-org-create
description: "Use this skill to create a Salesforce trial, developer, or Trialforce org against an already-authenticated host org, the same way a developer/Trialforce web signup form provisions one. INVOKE when the user asks to: create a trial org, sign up a new trial or developer org, provision a Trialforce org from a template, or check the status of a trial-org signup they started. Trigger phrases: 'create a trial org', 'sign up a trial org', 'spin up a dev org', 'Trialforce signup', 'provision trial from template', 'check my trial org signup status'. Do NOT use for scratch orgs (use dx-org-manage) or for checking trial expiration dates of existing orgs (use dx-org-trial-expiration-check)."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "60.0"
  relatedSkills:
    - "dx-org-manage"
    - "dx-org-trial-expiration-check"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

## What this skill does

Creates a Salesforce **trial org** by inserting a `SignupRequest` sObject with the `sf` CLI — the same request the Trialforce/developer **web signup form** issues under the hood. There is no bespoke signup endpoint: signup = inserting a `SignupRequest` (key prefix `0SR`) against an authenticated **host org** (a Trialforce Source Org / Env Hub / partner org that is entitled to create trial orgs).

The flow is **two CLI calls**: (1) create the `SignupRequest`, (2) read it back to pick up the assigned org id (creation is asynchronous — the org id appears shortly after the insert).

## Prerequisites — confirm before executing

1. **Authenticated host org — always confirm which one, explicitly.** You are signing up *from* an authenticated host org, not anonymously. The `sf` CLI operates against an org you have already logged into once (`sf org login web`, or `sf org login`).

   **Always pass an explicit `--target-org` (`-o`) with the host org's alias or username on every command, and confirm the target with the user before creating** — even if a default org is configured. Creating a `SignupRequest` is a real provisioning action; do not let it run against whatever org happens to be the default.

   - **Do not rely on the default-org fallback.** With no `-o`, the CLI resolves the target from `--target-org` → `SF_TARGET_ORG` env var → local then global `target-org` config, and **errors (`NoDefaultEnvError`) if none is set** — it never auto-picks among your connected orgs. That default may be an unrelated dev/scratch org, so an omitted `-o` is either wrong-org or a hard failure. Never omit it.
   - **The user may have many authenticated orgs.** Run `sf org list` and, if the intended host org is ambiguous or not provided, ask the user which alias/username to use. Do not guess.
   - **Verify the chosen org is `Connected`** in `sf org list` before creating (stale refresh tokens / expired certs show as error states, not `Connected`).
   - Never invent credentials.
2. **Host org must be entitled to create trial orgs**, and the invoking user must have sufficient access on it. The skill does **not** run a separate permission check — the `sf data create record` call (Step 1) is the definitive gate, and the same API enforcement is what a check would rely on. If the org is not entitled, the `SignupRequest` entity is not exposed and the create fails with a non-zero `status` and `name`/`code` of `NOT_FOUND` ("The requested resource does not exist") or `INVALID_TYPE` ("sObject type 'SignupRequest' is not supported"). This case is handled in Step 1's error table.

   When it happens, **stop** (it is not retryable from the CLI) and report to the user: (a) the **raw CLI error as-is** — the exact `name`/`errorCode` and `message` the CLI returned, verbatim — and (b) that they should **reach out to Salesforce support** to get the org enabled for trial-org creation, then try again. **Do NOT diagnose or name which permission is missing** — just surface the raw error and point them to support.

## Required Inputs — collect from the invoking user before any create

Prompt the user for these and do NOT proceed until all are provided. Do not invent values. **Ask for each one; if the user is unsure about a field, guide them using the "If the user is unsure" column before moving on.**

**Always required (5)** — these are `required="true"` on the `SignupRequest` entity (`FirstName` is listed here for prompting convenience but is **optional**):

| Input | Notes | If the user is unsure |
|-------|-------|-----------------------|
| `LastName` | Admin user's last name. Max 80 chars. | Any surname for the new org's admin user; it's just the admin contact name, use theirs. |
| `FirstName` | **Optional.** Admin user's first name. Ask for it, but proceed without it if the user doesn't provide one. | Optional — leave blank if unsure; only `LastName` is required for the admin user. |
| `Username` | Admin login username. Must be **email-format** and **globally unique** across all Salesforce orgs. Max 80 chars. Lowercased on save. | It does not have to be a real inbox — it just has to look like an email and be unique. Suggest a pattern like `admin@<company>-<something-unique>.com`. If it collides, you'll get a duplicate-username error on create; pick another. |
| `SignupEmail` | Admin user's **real** email address (welcome/login mail goes here). | This one must be a working inbox they can access — unlike `Username`, it should be a real address. |
| `Company` | Company / org name. Max 80 chars. | The organization name to show in the trial org; any descriptive name is fine. |
| `Country` | **ISO country code**, max 3 chars, e.g. `US`, `GB`, `IN`, `DE`. Validated at runtime against allowed codes (embargoed/invalid codes are rejected). | Use the 2-letter ISO code for their country (e.g. `US` for United States, `GB` for United Kingdom). Not a free-text country name. |

**Exactly one of (required, pick one — NOT both):**

| Input | Notes | If the user is unsure |
|-------|-------|-----------------------|
| `TemplateId` | Trialforce template ID (key prefix `0TT`, 15 chars) — defines the trial org's product/content. | Use a template when they want a specific pre-built product/content set. To find available templates, query the host org: `sf data query -o <HOST_ORG> -q "SELECT Id, TemplateName FROM TrialforceTemplate" --json`. If they just want a plain trial org, use `Edition` instead. |
| `Edition` | Org edition for a generic (non-template) trial. Generic values: `Developer`, `Group`, `Professional`, `Enterprise` (also `ServiceProfessional`, `SalesEnterprise`). Partner/Trialforce editions are perm-gated. | If they just want "a dev org to try things," use `Developer`. Partner editions (`PARTNER_*`, `TRIALFORCE_*`) only work if the host org has partner/TMC perms — using one without the perm returns a `noPartnerAccess` error. |

Ask the user to choose **either** a `TemplateId` **or** an `Edition`, not both:
- **Neither supplied** → stop and ask. A create with no template and no edition fails validation with `missingEdition` (`ApiErrorCodes.INVALID_SIGNUP_OPTION`).
- **Both supplied** → ask them to pick one; send only the chosen field. Combining them fails with `redundantTemplateId`. Neither may be combined with clone/source-org fields either.

This skill intentionally scopes user-collected input to the fields above (the 5 always-required plus optional `FirstName`). Do **not** prompt for or surface other fields. The `SignupRequest` entity supports additional optional and perm-gated fields (`TrialDays`, `Subdomain`, `PreferredLanguage`, `SignupSource`, the OAuth-return pair, etc.); these are **out of scope here** and left to server defaults. They are documented in `references/signup_request_fields.md` for reference only — do not send them from this skill.

## Step 1 — Create the SignupRequest

Invoke the create script with the collected inputs. It enforces the "exactly one of `TemplateId`/`Edition`" rule, assembles and quotes the `--values` payload, runs the insert, and prints the assigned `0SR…` id on success. Reference the script by its **absolute path** from the skill directory (`<skill_dir>/scripts/…`) — never `./scripts/`, which resolves against the user's working directory.

**With a template:**
```bash
SR_ID=$(bash "<skill_dir>/scripts/create_signup_request.sh" \
  --target-org <HOST_ORG> \
  --last-name <LAST_NAME> --email <EMAIL> --username <UNIQUE_USERNAME> \
  --company "<COMPANY>" --country <ISO> --template-id 0TT... \
  --output-dir force-app/main/adk-eval-output)
```

**With an edition (generic trial, no template):** replace `--template-id 0TT...` with `--edition Developer` (or `Enterprise`, etc.). Add `--first-name <NAME>` only if the user supplied it — no other optional fields are sent by this skill. The script rejects supplying both `--template-id` and `--edition`, or neither.

Pass `--output-dir` (use `force-app/main/adk-eval-output` when it exists) so that if the create is **rejected**, the script still writes `<output-dir>/signup-request-result.json` capturing the create-rejected outcome and the raw error verbatim — the run's output artifact even when no org is created. On success this write is done by the Step 2 read-back instead.

On success the script prints the `0SR…` SignupRequest id (capture it as `SR_ID`). Pass `--json` instead to get the raw `sf` create envelope, which wraps a **handle**, not the org:
```json
{ "status": 0, "result": { "id": "0SRxx0000000000", "success": true, "errors": [] } }
```

**Handle create errors (synchronous field validation).** On a rejected create the script exits non-zero and prints the **raw CLI error** (`name`/`code` + `message`) to stderr — surface it verbatim and act per the table below. When `--output-dir` was given, the script also writes the create-rejected artifact (`{ "outcome": "create-rejected", "error": {…}, "CreatedOrgId": null, "Status": null }`) to `<output-dir>/signup-request-result.json`; do not hand-author this file. This is field validation, returned *immediately* — distinct from the async `ErrorCode` in Step 2. These are **server-side** rejections (the record reaches the org and the platform rejects it at insert time) — do not describe them to the user as "client-side"; the CLI does not validate email/country format, picklist values, or field length locally. Do NOT poll a create that failed, and do NOT proceed to Step 2.

| Failure | Meaning → what to tell the user |
|---------|---------------------------------|
| `missingEdition` / `INVALID_SIGNUP_OPTION` | Neither `TemplateId` nor `Edition` was sent — ask for one and retry. |
| `redundantTemplateId` | Both `TemplateId` and `Edition` were sent — drop one and retry. |
| `noPartnerAccess` / `NO_PARTNER_PERMISSION` | A partner/TSO edition was requested but the host org lacks the perm — use a generic edition (`Developer`, etc.) or get the perm. |
| duplicate / invalid `Username` (`INVALID_EMAIL_ADDRESS`) | `Username` is not email-format or not globally unique — ask for a different one and retry. |
| `INVALID_SIGNUP_COUNTRY` | `Country` is not a valid/allowed ISO code — fix and retry. |
| `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` | `Edition` is not an accepted value for the host org's restricted picklist (e.g. `Ultimate`) — pick a valid generic edition and retry. |
| `STRING_TOO_LONG` | A field value exceeds its max length (the message names the field + `max length`, e.g. `LastName` over 80) — shorten it and retry. |
| `subdomainInUse` / invalid subdomain | Chosen `Subdomain` is taken or invalid — pick another. |
| `NOT_FOUND` ("The requested resource does not exist") or `INVALID_TYPE` ("sObject type 'SignupRequest' is not supported") | The `SignupRequest` entity is not exposed → the org is not entitled to create trial orgs. **Not** retryable. Stop and surface the **raw CLI error as-is** (`name`/`errorCode` + `message`), then tell the user to **reach out to Salesforce support** to get the org enabled. **Do not name or diagnose the missing permission.** |
| `INSUFFICIENT_ACCESS_OR_READONLY` | The entity is exposed but the *user* lacks the access to create the record — a user-permission problem, distinct from the org-entitlement failure above. Fix the user's permissions and retry. |

For the full catalog and prefixes → `references/error_codes.md`.

- For the full required/optional field list, types, and perm-gated fields → load `references/signup_request_fields.md`.
- Do NOT send `TemplateId` together with clone/source-org fields (`redundantTemplateId` error). Do NOT request a partner/Trialforce edition without the host org's partner/TMC perm.

## Step 2 — Read the request once the org id is available (creation is async)

Provisioning happens asynchronously after the insert, so re-read the record to pick up the assigned org id. Invoke the read script — it applies a fixed, bounded read-back policy internally (stopping as soon as `CreatedOrgId` is populated or the status is terminal, and never polling indefinitely), prints the record as JSON, and writes the output artifact when `--output-dir` is given. Then act on the script's **exit code** (below) — the retry count and delay are the script's own deterministic logic; you do not re-implement or re-count them in prose. If the org id is not yet available, the script exits `3` so you can hand the request id back to the user:

```bash
bash "<skill_dir>/scripts/get_signup_request.sh" \
  --target-org <HOST_ORG> --id "$SR_ID" [--output-dir <DIR>]
```

The script prints the `SignupRequest` record (the `sf` envelope's `result`) as JSON. Read these fields from it:
- `CreatedOrgId` — the new trial org id (`00D…`, 15 chars). Populated as soon as the org is allocated (often while `Status` is still `InProgress`); this is the script's stop signal.
- `CreatedOrgInstance` — instance hosting the new org (target follow-up calls here).
- `Username` — the admin login username on the record. Report the value **read back from the record**, not the raw input — it is lowercased on save, so the stored value is the accurate one to hand the user.
- `Status` — lifecycle `New` → `InProgress` → `Success` | `Error` (match case-insensitively).
- `LoginUrl` — present only if `IsSyncLogin` was set on create (perm-gated).
- `AuthCode` — present only if `ConnectedAppConsumerKey` + `ConnectedAppCallbackUrl` were set.
- `ErrorCode` — populated **only when `Status = Error`**. This is the *async provisioning* error (distinct from the synchronous create-time validation in Step 1), prefixed:
  - `C-` org creation error · `S-` signup data error · `T-` template error (e.g. `T-0002` = template not found) · `SH-` org-shape error · `VR-` version-selection error · `X-0001`/`X-0002` fatal/should-never-happen.

Act on the script's exit code. **The org id lookup runs first — do not report anything to the user until the script returns.** Report only what is actually on the record; never invent or relabel the `Status`:
- **`0`** — `CreatedOrgId` is populated. Proceed to Step 3 and report the org id together with the record's real `Status` and the `Username`.
- **`3` — no org id available yet (not an error).** The org has not been allocated. The script has already exhausted its bounded read-back — **do NOT re-invoke it in a loop to keep polling.** Report the **SignupRequest id (`0SR…`)**, the record's **`Status` exactly as returned**, and the `Username`; tell the user the org id is not available yet, and let them re-check later (see Step 3).
- **`1`** — `Status = Error` (stop and report the `ErrorCode` and its prefix meaning via `references/error_codes.md`; the org was not created), or the read itself failed (auth expired, `0SR` id not found) — surface the raw CLI error and stop.

## Step 3 — Report details and hand off status checks

Report **after** the Step 2 lookup returns — not before. When the user asks to create (or re-check) the org, run the read-back first and wait for it, then report all available details to the user in one go. Report **only what is on the record**; never fabricate or relabel a value — especially `Status`, which must be the exact string the response object carries:
- **SignupRequest id** — the `0SR…` request id (from Step 1). **Always report this** — it is the handle the user (or a later check) uses to look the request up again, and it is the primary thing to hand back if the org id is not yet available.
- **CreatedOrgId** — the new trial org id (`00D…`), when populated. If the read returned exit `3` (org id not yet available), say so plainly: the request was accepted and the org is still being provisioned; there is no org id to share *yet*.
- **CreatedOrgInstance** — the instance hosting it, if present.
- **Username** — the admin login username **as stored on the record** (lowercased on save). Always report this — it is what the user logs in with once the org is ready.
- **Status** — the `Status` value **exactly as it appears on the record**. Echo whatever string the response carries; do not map, translate, infer, or pick from a fixed list. A still-pending status is normal at this point — provisioning finishes in the background.
- **LoginUrl** / **AuthCode** — only if present.

Also tell the user that **login details for the new org arrive by email** — once provisioning completes, a welcome/login email is sent to the `SignupEmail` address, so they should watch that inbox to finish logging in. (This is why `SignupEmail` must be a real, accessible address.)

Then suggest, in plain language, how the user can re-check status later — provisioning may still be completing. Tell them they can just ask (the skill re-reads the record), for example:
- "Check the status of my trial org **`00D…`**" (by the org id), or
- "Check the status of signup request **`0SR…`**" (by the SignupRequest id).

Both resolve to a re-run of the Step 2 read script against the same `SignupRequest` record (the org id is looked up on that record). A later check should report the current `Status` **exactly as returned** on the record. If the record comes back with an error status, also report the `ErrorCode` and its prefix meaning via `references/error_codes.md`.

**Output artifact.** Write the current `SignupRequest` record as the run's output artifact by passing `--output-dir` to the Step 2 read script — the script writes `<output-dir>/signup-request-result.json` (creating the directory if needed). Use `force-app/main/adk-eval-output` as the output directory when it exists:

```bash
bash "<skill_dir>/scripts/get_signup_request.sh" \
  --target-org <HOST_ORG> --id "$SR_ID" \
  --output-dir force-app/main/adk-eval-output
```

This is the run's defined output — do not ask permission before writing it.

## Reference File Index

| File | When to read |
|------|-------------|
| `references/signup_request_fields.md` | Full field reference — required/optional fields, types, defaults, perm-gated fields, editions |
| `references/error_codes.md` | Interpreting `ErrorCode` prefixes and common validation failures |

## Example Files

Load these only when you need to see the concrete shape of a payload or response — they are illustrative samples with placeholder ids (`0SRxx…`, `00Dxx…`), not values to send.

| File | When to read |
|------|-------------|
| `examples/create_request.json` | When assembling the create — to confirm the field names/shape of the `SignupRequest` create payload |
| `examples/success_response.json` | When interpreting a successful create + read-back — shows the record once `CreatedOrgId` is populated |
| `examples/error_response.json` | When interpreting a rejected create — shows the shape of common validation/error responses |

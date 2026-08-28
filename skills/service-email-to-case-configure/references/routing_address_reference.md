# EmailToCaseRoutingAddress — Field & Surface Reference

Each routing address is one `<routingAddresses>` element inside `CaseSettings.emailToCase`.

## Prerequisites (before routing addresses can be created)

`apply-casesettings.py` applies these in Phase A, before adding any routing address in Phase B. The two `emailToCase` switches are required. On-Demand Email-to-Case requires a Default Case Owner and an Automated Case User to be set: write the values the user names into the source file (the scored, versionable artifact); the script also accepts them as flags and preserves any the org already has (see below).

| Field | Level | Notes |
|-------|-------|-------|
| `defaultCaseOwner` | `CaseSettings` | Fallback owner for cases assignment rules can't route. **Preserved if the org already has it.** When not configured, the script requires an explicit, org-validated value: a Username (`defaultCaseOwnerType=User`) or a Queue DeveloperName (`defaultCaseOwnerType=Queue`). Never assumed. |
| `defaultCaseOwnerType` | `CaseSettings` | `User` or `Queue`. Selects how `defaultCaseOwner` is resolved (Username vs Queue DeveloperName). No silent default — supplied with the owner value. |
| `defaultCaseUser` | `CaseSettings` | The **Automated Case User** recorded in Case History for automated Email-to-Case changes. A specific active Username. Mutually exclusive with `useSystemUserAsDefaultCaseUser`. |
| `useSystemUserAsDefaultCaseUser` | `CaseSettings` | Set `true` to use the org's **System** (automated process) user as the Automated Case User instead of a named user. Do **not** also set `defaultCaseUser` (platform error). API 67.0+. |
| `systemUserEmail` | `CaseSettings` | Email for the automated process user, required with `useSystemUserAsDefaultCaseUser=true` only when the org's automated case user doesn't exist yet. |
| `enableEmailToCase` | `emailToCase` | Master switch. Cannot be disabled once enabled. |
| `enableOnDemandEmailToCase` | `emailToCase` | Must be `true` before the org accepts routing addresses. Requires the Default Case Owner + Automated Case User above. |

**Support-settings resolution (Phase A).** The script reads current settings first. If the Default Case Owner or Automated Case User is already configured in the org, it is **preserved** untouched (pass `--overwrite-support-settings` to replace it). For a field the user names, write the value into the source file — `defaultCaseOwner` + `defaultCaseOwnerType`; `defaultCaseUser`, or `useSystemUserAsDefaultCaseUser` (+ optional `systemUserEmail`) — since the file is the scored, versionable artifact; the script also accepts the same values as flags (`--owner-type`/`--owner-value`, `--automated-type`/`--automated-value`, `--system-user-email`). Each value is validated against the org — an unknown user or queue, or an invalid type, fails the run with an actionable message so the caller can re-prompt. For a field that is unset **and** unnamed, ask; the authenticated CLI user is used **only** with `--use-authenticated-user`.

## Surface selection by `addressType`

`addressType` is the gating decision — it determines whether the address can be created via the Metadata API at all.

| `addressType` | Surface | Notes |
|---------------|---------|-------|
| `EmailToCase` | **Metadata API** | The standard case. Requires out-of-band verification of the Salesforce-generated forwarding address before it receives production mail. |
| `Outlook` | **Metadata API** | Used with Salesforce for Outlook. Requires On-Demand Email-to-Case enabled. |
| `GmailOAuth` | **Metadata API** | Gmail connector. Only one GmailOAuth connector is supported — do not stack a second. |
| `E2cEasy` | **Service Easy Setup wizard ONLY** | The wizard binds the address to the prebuilt `service_case` queue and completes email round-trip verification. Neither the queue binding nor `isVerified` can be reproduced by a Metadata API deploy. Do not emit Metadata for this type. |

## Writable fields

| Field | Type | Notes |
|-------|------|-------|
| `addressType` | enum | Required. One of `EmailToCase`, `Outlook`, `GmailOAuth` (see surface table for `E2cEasy`). |
| `routingName` | string | Required. Unique label for the routing address. The platform rewrites this to equal the email address for `EmailToCase` addresses. |
| `caseOrigin` | string | **Required.** Default Case Origin for cases from this address. The operation fails with "Missing caseOrigin" if omitted. |
| `casePriority` | string | **Required.** Default Case Priority. The operation fails with "Missing casePriority" if omitted. |
| `caseOwner` | string | **Optional, opt-in per address.** Default owner for cases from this address — an active Username or a Queue DeveloperName. Omit it (the default) to fall back to the org Default Case Owner / assignment rules; set it only when the user chooses a specific owner for this address. **Must** be paired with `caseOwnerType` — the platform rejects `caseOwner` without it. `apply-casesettings.py` validates the value against the org (active user / real queue) and fails closed if it doesn't exist. |
| `caseOwnerType` | string | `User` or `Queue` — how `caseOwner` is resolved (Username vs Queue DeveloperName). Required whenever `caseOwner` is set; not written on its own. |
| `createTask` | boolean | If `true`, a task is auto-assigned to the case owner on case creation. |
| `taskStatus` | string | Default status for the auto-created task. Applies only when `createTask` is `true`. |
| `authorizedSenders` | string | Comma-separated addresses/domains allowed to submit email (On-Demand E2C). |
| `saveEmailHeaders` | boolean | Whether routing/envelope headers are saved. |
| `newEntityRecordType` | string | Case Record Type for cases from this address; defaults to the org's default Case Record Type. Must exist and be active on Case. |
| `routingFlow` | string | Omni-Channel flow that routes generated cases (API 56.0+). |
| `fallbackQueue` | string | Queue used when the Omni-Channel flow can't route; must use Case as the service channel object (API 56.0+). |
| `isPermsetControlled` | boolean | If `true`, only users granted access via a permission set can use the address (API 61.0+). |

## Supplied at apply time — never in the source file

| Field | Why |
|-------|-----|
| `emailAddress` | The customer-facing address that routes email into cases. Supplied via `--routing-email` (one per address, in document order), never written in the source file — this keeps the address explicit user input and out of a reusable artifact. The validator rejects a source file that sets it. |

## Read-only fields — never write values for these

| Field | Why |
|-------|-----|
| `emailServicesAddress` | Salesforce-generated forwarding address. Read-only; set by the platform. |
| `isVerified` | Set by the customer's verification flow (clicking the confirmation email). Read-only; cannot be flipped by an apply. |

## Optional org-level `emailToCase` toggles

Set these only when the user asks. `enableEmailToCase` and `enableOnDemandEmailToCase` are the required ones (see Prerequisites).

| Field | Type | Notes |
|-------|------|-------|
| `enableHtmlEmail` | boolean | Enables HTML email. |
| `enableE2CSourceTracking` | boolean | Sets Case Source to Email for E2C-originated cases. |
| `overEmailLimitAction` | enum | `Bounce` \| `Discard` \| `Requeue` — action when the daily E2C limit is exceeded. |
| `unauthorizedSenderAction` | enum | `Bounce` \| `Discard` — action for email from invalid senders. |

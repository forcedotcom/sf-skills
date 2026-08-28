---
name: service-de-channel-create
description: "**INTERNAL USE ONLY — invoked by `service-de-headless-channel-configure` orchestrator.** Insert an Enhanced messaging `MessagingChannel` record (plus its child `MessagingChannelUsage` as a free server-side side-effect) of any supported type — WhatsApp, LINE, Apple Business Chat, Facebook, or SMS (Text). Given a `{MESSAGE_TYPE}` and the corresponding type-specific inputs, runs the shared preflight → Connect-insert → verify flow and branches only where a type genuinely differs (request body, prerequisites, error classes). Uses the sanctioned `POST /services/data/v{V}/connect/livemessage/channels` Connect REST endpoint — no Aura session, no token extracted into shell state. **Users should always invoke `service-de-headless-channel-configure` instead — it handles insert → route → activate in one flow.** Use this skill when inserting a messaging channel of any type; it replaces the four former per-type creation skills."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-activate"
    - "service-de-channel-consent-configure"
    - "service-de-channel-routing-configure"
    - "service-de-headless-channel-configure"
    - "service-de-waba-integrate"
---

# Inserting Messaging Channels

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/whatsapp.md` | `MESSAGE_TYPE=WhatsApp` — WABA partnership (Stage 2) + SF-side manage-WABA (Stage 3) prereqs, request body, WhatsApp gotchas. |
| `references/line.md` | `MESSAGE_TYPE=Line` — optional token verify, `authDetails` body shape, LINE gotchas. |
| `references/apple.md` | `MESSAGE_TYPE=AppleBusinessChat` — empty-config body, Apple-precondition errors, Apple gotchas. |
| `references/facebook.md` | `MESSAGE_TYPE=Facebook` — browser OAuth → page-selection flow, Facebook gotchas. |
| `references/sms.md` | `MESSAGE_TYPE=Text` — phone-number platform key, present-but-unvalidated `smsProvider`, number-provisioning prerequisite (caller's), SMS gotchas. |
| `references/connect-insert.md` | Shared authProviderId lookup + Connect POST + response-classification detail (Stage 4). |
| `references/worked-examples.md` | End-to-end traces per type (fresh insert, preflight short-circuit, OAuth). |

## What this skill does

Given a `{MESSAGE_TYPE}` and its inputs, creates a `MessagingChannel` record with
`PlatformType=Enhanced`, `IsActive=false`. The same server-side path
(`LiveMessageSetupServiceImpl.addChannel` → `LiveMessageChannelsUtil.findOrCreateCsotMessagingChannel`)
also inserts a `MessagingChannelUsage` row (`DeploymentType=Conversation`, `DeploymentStatus=New`
on fresh insert — `Disabled` on a channel that was previously activated then deactivated) — we get
it for free.

**One primary path for every type: Connect REST API.**
`POST /services/data/v{V}/connect/livemessage/channels` with an org OAuth session managed by
`sf api request rest`. Public, sanctioned, live since API v66+. No Aura session, no token extracted
into shell state.

**Idempotent** on `(MessagingPlatformKey, MessageType)` — re-firing with the same platform key
returns the existing channel's id. This matters because `MessagingChannel` records are not deletable
via standard means, so the preflight (Stage 1) is the practical idempotency guard.

All types return the **same envelope shape**, so callers don't branch on type after insert:
`{ok, channelId, mcuId, developerName, isActive:false, messageType, messagingPlatformKey, path, created, durationMs}`.

### Supported types (the only branch point)

| `{MESSAGE_TYPE}` | Platform key (`messagingPlatformKey`) | Prerequisite (caller supplies) | Body extras | Ref |
| --- | --- | --- | --- | --- |
| `WhatsApp` | Phone Number ID | `service-de-waba-integrate` (run in Stage 2-3) | `externalAccountId`, `isoCountryCode` | `whatsapp.md` |
| `Line` | LINE channel id | LINE id + secret + token (LINE Developers Console) | `authDetails.{client_secret,access_token}` | `line.md` |
| `AppleBusinessChat` | Apple BC Account ID (GUID) | Apple BC Account ID (register.apple.com/business-chat) | *(none — empty config)* | `apple.md` |
| `Facebook` | Facebook Page ID | *OAuth handled internally* | `authDetails: {}` (OAuth-derived) | `facebook.md` |
| `Text` | Phone number / short code | number already provisioned (caller supplies) | `smsProvider` (key required, value may be `""`), `isoCountryCode` | `sms.md` |

Unsupported (would need their own leaf logic, not yet built): `WeChat`, `MsCopilot`, `Alexa`.
For these, emit the `unsupported-type` envelope (Stage 0).

## When NOT to use this skill

- **End-to-end setup.** If the user wants insert → route → activate, invoke
  `service-de-headless-channel-configure` — it orchestrates this skill plus routing, consent, and
  activation. This skill only handles the insertion step (see Stage 0).
- **The channel already exists and you only want to re-route / activate it.** Skip insertion;
  call `service-de-channel-routing-configure` / `service-de-channel-activate` with the existing
  `channelId`.

## Inputs (from caller)

- `{MESSAGE_TYPE}` — one of `WhatsApp`, `Line`, `AppleBusinessChat`, `Facebook`, `Text`.
  Case-sensitive (matches the SF picklist). `Text` is the enum value for SMS — there is no `SMS` type.
- `{ORG_ALIAS}` — optional; `sf` CLI target-org alias. Default: `sf config get target-org`.
- `{API_VERSION}` — optional; Connect API version. Default: the org's current API version
  (`sf org display --json | jq -r '.result.apiVersion'`). Always use the org's native version to
  avoid 404s.
- `{CHANNEL_NAME}` — display name shown in Setup → Messaging Settings. Required for
  `AppleBusinessChat` (no phone/screen-name fallback); prompted if omitted for others.

Type-specific inputs:

- **WhatsApp:** `{WABA_ID}` (sent as `externalAccountId`), `{PHONE_NUMBER_ID}` (the platform
  key — **must differ from WABA_ID**), `{ISO_COUNTRY_CODE}` (optional, default `US`).
- **Line:** `{LINE_CHANNEL_ID}` (platform key), `{LINE_CHANNEL_SECRET}`, `{LINE_ACCESS_TOKEN}`,
  `{VERIFY_TOKEN_FIRST}` (optional, default `true`).
- **AppleBusinessChat:** `{APPLE_BC_ID}` (platform key, GUID).
- **Facebook:** `{PAGE_ID}` (optional — OAuth fetches/prompts if absent).
- **Text (SMS):** `{SMS_NUMBER}` (the platform key — the phone number / short code string, already
  provisioned to the org), `{SMS_PROVIDER}` (sent as `smsProvider` — the `smsProvider` **key must be
  present** in the body or the insert 400s with "SMS provider is missing", but its **value is not
  validated or stored**, so an empty string `""` works; default to `""` when the caller doesn't supply
  a provider), `{ISO_COUNTRY_CODE}` (optional, default `US`). This skill does not provision the
  number — the caller must already know their number.

## Output (to caller)

**Success:**
```json
{"ok": true, "channelId": "0Mj...", "mcuId": "0gL...", "developerName": "...",
 "isActive": false, "messageType": "{MESSAGE_TYPE}", "messagingPlatformKey": "...",
 "path": "connect" | "preflight", "created": true | false, "durationMs": 1234}
```
`created: false` + `path: "preflight"` means the row already existed and was returned idempotently.

**Failure (shared):**
```json
{"ok": false, "kind": "wrong-skill", "correctSkill": "service-de-headless-channel-configure", "hint": "..."}
{"ok": false, "kind": "unsupported-type", "supportedTypes": ["WhatsApp","Line","AppleBusinessChat","Facebook","Text"], "hint": "..."}
{"ok": false, "kind": "missing-input", "missing": ["..."], "hint": "caller must provide all required inputs for this type"}
{"ok": false, "kind": "auth",     "hint": "OAuth token invalid / expired — run 'sf org login web'"}
{"ok": false, "kind": "business", "message": "...", "errorCode": "..."}
{"ok": false, "kind": "transport","status": 500, "message": "..."}
{"ok": false, "kind": "verify-failed", "hint": "Connect returned 201 but follow-up SOQL shows no matching channel"}
```
Type-specific failure kinds (`partnership-blocked`, `user-declined`, `waba-manage-failed`,
`meta-precondition` for WhatsApp; `line-token-invalid` for LINE; `apple-precondition` for Apple;
`oauth-not-complete`, `oauth-failed` for Facebook) are documented in the per-type reference files.

---

## Stage 0: Enforce orchestrator-only invocation

**This skill is INTERNAL USE ONLY.** It should only be invoked by the
`service-de-headless-channel-configure` orchestrator.

If the user's original request was to "install", "set up", "create", or "activate" a messaging
channel (or any phrasing that implies end-to-end setup), immediately return:

```json
{
  "ok": false,
  "kind": "wrong-skill",
  "hint": "This is an internal insertion skill. For end-to-end channel setup (insert → route → activate), invoke 'service-de-headless-channel-configure' instead with the desired MESSAGE_TYPE.",
  "correctSkill": "service-de-headless-channel-configure"
}
```

And render to the user:
```text
Error: Wrong skill invoked.

This skill (service-de-channel-create) only handles the insertion step.
For complete channel setup, use: /service-de-headless-channel-configure

That orchestrator runs: insert → configure routing → activate in one flow.
```

**Only proceed to Stage 0.1 if:**
- This skill was invoked programmatically by `service-de-headless-channel-configure`
- The user explicitly stated they ONLY want insertion (not routing or activation)
- This is a retry/resume scenario where routing/activation already succeeded

When in doubt, redirect to the orchestrator.

### Stage 0.1: Validate type and required inputs

Look up `{MESSAGE_TYPE}` in the supported-types table. If absent, emit the `unsupported-type`
envelope and return.

Validate the type's required inputs are present (**Facebook is the exception** — no required
inputs; OAuth → page selection → prompts happen inside the Facebook flow). If any are missing,
emit `missing-input` with the list and return.

**WhatsApp only:** additionally assert `{WABA_ID} != {PHONE_NUMBER_ID}` — they are distinct Meta
entities and reusing one value for both causes cryptic activation failures. If equal, emit
`{ok:false, kind:"invalid-input", hint:"WABA_ID and PHONE_NUMBER_ID must differ — WABA_ID is the WhatsApp Business Account ID; PHONE_NUMBER_ID is a specific phone number within it. Find both in Meta Business Manager → WhatsApp Accounts."}`.

Capture `{T0} = Date.now()` for `durationMs`.

### Stage 0.2: Establish the scratch directory

Every transient artifact this skill writes (preflight query results, request bodies, Connect
responses) goes into a per-run scratch directory rooted inside the harness working area — never a
bare absolute `/tmp` path, which is world-writable and non-portable. Establish it once:

```bash
SCRATCH_DIR="$(mktemp -d "${outputDir:-${TMPDIR:-/tmp}}/icc.XXXXXX")"
```

The base dir is the harness-provided `${outputDir}` when set, else the private user-scoped
`${TMPDIR}`, else `/tmp` only as a last resort. All later stages (and the reference flows) write
under `${SCRATCH_DIR}/`; the durable report stays under `${outputDir}`.

---

## Stage 1: Preflight — is the channel already here?

SOQL-probe for an existing row **first**; a hit lets us skip all prerequisites and the insert.

**For Facebook without a `{PAGE_ID}`, skip this stage** — the page id isn't known until OAuth →
page selection completes (see `references/facebook.md`). Run the preflight after page selection.

**Two queries, not a subquery.** The `(SELECT ... FROM MessagingChannelUsages)` child subquery
fails with `INVALID_TYPE` on orgs where the child relationship is unnameable (verified on
`wadtesting` / PRODDEBUG). The FK-keyed form works everywhere.

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MasterLabel, IsActive, MessagingPlatformKey FROM MessagingChannel WHERE MessagingPlatformKey = '{PLATFORM_KEY}' AND MessageType = '{MESSAGE_TYPE}'" \
  --json > "${SCRATCH_DIR}/preflight.json"
```

If `records.length === 1`:
- Record `{CHANNEL_ID}`, `{DEVELOPER_NAME}`, `{IS_ACTIVE}`.
- Second query for the MCU by FK:
  ```bash
  sf data query --target-org '{ORG_ALIAS}' \
    --query "SELECT Id, DeploymentStatus FROM MessagingChannelUsage WHERE MessagingChannelId = '{CHANNEL_ID}'" \
    --json > "${SCRATCH_DIR}/preflight-mcu.json"
  ```
  Record `{MCU_ID}` (empty MCU: flag, don't fail — the activation skill handles it).
- Emit the success envelope with `path: "preflight", created: false`. Return.

If `records.length > 1`: ambiguous (uniqueness should prevent this) — proceed with the first,
note a warning in the envelope.

If `records.length === 0`: proceed to Stage 2.

---

## Stage 2-3: Type-specific prerequisites

Most types have **no** prerequisite here — go straight to Stage 4.

- **WhatsApp:** requires the Meta WABA↔Salesforce partnership (Stage 2, via
  `service-de-waba-integrate`) and the SF-side webhook subscription + credit-line share
  (Stage 3, `POST /connect/livemessage/whatsapp/business-account`). **Load `references/whatsapp.md`
  and follow it** before inserting.
- **Line:** optional token preflight against `https://api.line.me/v2/bot/info` if
  `{VERIFY_TOKEN_FIRST}` is true. **See `references/line.md`.**
- **Facebook:** browser-based OAuth authorization + page-list fetch + page selection happen here,
  before the insert. **Load `references/facebook.md` and follow it.**
- **Apple:** none. (Apple's certificate handshake is provisioned on Apple's side and is per-message
  at runtime, not at channel insert — see `references/apple.md`.)
- **Text (SMS):** none at insert. The number must already be provisioned to the org and the caller
  must know its `smsProvider`, but this skill performs no provisioning step — it inserts the record for
  a number the caller already has. (ESP registration runs at activation, not insert — see
  `references/sms.md`.)

---

## Stage 4: Insert via Connect REST API

Shared across all types. The only per-type difference is the **request body**; the authProviderId
lookup, the POST invocation, and the response-classification table are identical.

### Stage 4.1: authProviderId (org-global; required for every type except Text)

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id FROM AuthProvider WHERE DeveloperName = 'LiveMessageSetup'" \
  --json > "${SCRATCH_DIR}/authprovider.json"
```

One row → `{AUTH_PROVIDER_ID}`. Zero rows → **branch on type:**
- **`Text`** — non-fatal. Text's Connect signature doesn't take `authProviderId`, so leave
  `{AUTH_PROVIDER_ID}` unset and continue to Stage 4.2; the POST omits the parameter entirely (see
  below). Do **not** emit the business error for Text — an org that has never run LiveMessage setup
  is exactly where the Text-only path matters, and blocking here would make the advertised SMS insert
  unreachable on those orgs.
- **every other type** (`WhatsApp`, `Line`, `AppleBusinessChat`, `Facebook`) — the org has never run
  LiveMessage setup and the insert can't proceed; emit
  `{ok:false, kind:"business", message:"No AuthProvider 'LiveMessageSetup' found — run the Messaging Setup wizard once on this org first"}`.

The Connect endpoint rejects the POST with `400 ILLEGAL_QUERY_PARAMETER_VALUE "Missing argument
authProviderId"` if this URL parameter is absent — verified for every type **except `Text`**, Apple
included. (`Text` has its own Connect signature that doesn't require it.) When the lookup finds a row,
send `authProviderId` for every type including Text (harmless there); when it finds none, only Text may
proceed, and it proceeds **without** the parameter. `authProviderId` goes in the URL query string,
never the body (body → `400 JSON_PARSER_ERROR "Unrecognized field 'authProviderId'"`).

### Stage 4.2: Build the type-specific body and POST

Resolve `{CHANNEL_NAME}` first (prompt if required and absent — see per-type ref). Then build the
body from the supported-types table and POST. **Write the body to a file** (`--body @...`) — LINE
tokens are long and can contain shell-hostile characters.

Append the `authProviderId` query parameter only when Stage 4.1 resolved one — otherwise (the
Text-with-no-AuthProvider case) POST to the bare endpoint, since an empty `?authProviderId=` would
trip the same `ILLEGAL_QUERY_PARAMETER_VALUE`:

```bash
URL="/services/data/v{API_VERSION}/connect/livemessage/channels"
[ -n "${AUTH_PROVIDER_ID:-}" ] && URL="${URL}?authProviderId=${AUTH_PROVIDER_ID}"

sf api request rest "${URL}" \
  --method POST --target-org '{ORG_ALIAS}' \
  --header 'Content-Type: application/json' --header 'Accept: application/json' \
  --body @"${SCRATCH_DIR}/body.json" --include > "${SCRATCH_DIR}/connect-response.txt" 2>&1
```

`--include` prints the HTTP status/header block before the body — read the status from there, not
a trailing `-w` marker. `sf api request rest` manages OAuth internally.

**For the exact per-type body shape and the full response-classification table (including the
`DUPLICATE_VALUE` race back to Stage 1, the Facebook `AUTH_PROVIDER_NEEDS_AUTH` 401-vs-400
disambiguation, and per-type precondition errors), load `references/connect-insert.md` plus the
per-type ref.**

---

## Stage 5: Verify the insert

Two queries (same no-subquery reason as Stage 1). Keep to the universal field set —
`ExternalAccountId` and `MessagingPlatform` don't exist on all orgs.

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MasterLabel, MessageType, IsActive, MessagingPlatformKey FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" --json

sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeploymentStatus, DeploymentType FROM MessagingChannelUsage WHERE MessagingChannelId = '{CHANNEL_ID}'" --json
```

Expected: channel `IsActive=false`; exactly one MCU, `DeploymentType=Conversation`,
`DeploymentStatus` in `{New, Disabled}` (fresh inserts land in `New`; `Disabled` is a
previously-activated-then-deactivated channel — both are valid starting states for activation).
Empty MCU query → `{ok:false, kind:"verify-failed", hint:"Connect returned {CHANNEL_ID} but no
child MessagingChannelUsage was created"}`.

**Trust the DB, not the Connect response body**, for `MasterLabel` / `DeveloperName` — the 201 body
carries stale input-rep projections (see per-type gotchas).

---

## Stage 6: Report to caller

```json
{"ok": true, "channelId": "{CHANNEL_ID}", "mcuId": "<from Stage 5>",
 "developerName": "<authoritative, from Stage 5>", "isActive": false,
 "messageType": "{MESSAGE_TYPE}", "messagingPlatformKey": "{PLATFORM_KEY}",
 "path": "connect", "created": true, "durationMs": <Date.now() - T0>}
```

Rendered (when invoked directly rather than by the orchestrator):
- `Success — MessagingChannel {CHANNEL_ID} ({developerName}) created via {path}. MCU {mcuId} auto-created. IsActive=false — run routing, then consent, then activate next.`
- `Info: Channel already exists — {CHANNEL_ID} ({developerName}). Proceed to routing/activation.`
- `Error: {kind}: {message or hint}`

On success the caller can immediately invoke `service-de-channel-routing-configure` with the
returned `channelId`, then `service-de-channel-consent-configure`, then
`service-de-channel-activate`. Those three are message-type-agnostic (they operate on
`MessagingChannel.Id` + `MessagingChannelUsage.Id`), so there's no downstream dispatch concern.

---

## Gotchas (shared)

1. **Case-sensitive type names.** `"whatsapp"` ≠ `"WhatsApp"` — the SF picklist, SOQL filters,
   and Connect enum all match exactly. Normalize upstream; don't make Stage 0.1 case-insensitive.
2. **Preflight is the idempotency guard.** `MessagingChannel` rows aren't deletable via standard
   means, so re-runs rely on Stage 1 finding the existing row.
3. **Envelope shape is a tight coupling with callers.** If a field is renamed here, every caller
   (especially `service-de-headless-channel-configure`) silently sees the change — break loudly
   in tests rather than remap field names.
4. **Per-type gotchas live in the reference files.** WABA/phone-id confusion, LINE long-lived vs
   short-lived tokens, Apple's empty-config body + no-provisioning-callout, Facebook OAuth page
   selection + 401 disambiguation — load the matching `references/<type>.md` when debugging that type.

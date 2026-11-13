# WhatsApp — prerequisites, request body, gotchas

`MESSAGE_TYPE=WhatsApp`. Platform key is the **Phone Number ID** (not the WABA ID, not the display
number). WABA ID is sent separately as `externalAccountId`.

## Inputs

- `{WABA_ID}` — WhatsApp Business Account ID. Numeric string, ~15 digits. Sent as
  `externalAccountId`. **NOT the same as Phone Number ID** — a WABA can contain multiple phone
  numbers. Meta Business Manager → WhatsApp Accounts → (your account) → Account ID at top.
- `{PHONE_NUMBER_ID}` — Meta phone number ID. Numeric string, ~15 digits. Sent as
  `messagingPlatformKey`. (NOT the display phone number like `+1 650-555-0199`.) **Must differ from
  WABA_ID.** Meta Business Manager → WhatsApp Accounts → (your WABA) → Phone Numbers tab → Phone
  number ID column.
- `{CHANNEL_NAME}` — display name (`messagingChannelName`), shown as "Channel Name" in Setup →
  Messaging Settings. Required — prompt if not supplied. Never auto-default to the phone number id:
  the id is opaque and produces a confusing UI (both columns show the same digits).
- `{ISO_COUNTRY_CODE}` — optional, two-letter ISO-3166 alpha-2 (e.g. `US`). Default `US`. Passed as
  `isoCountryCode`.

## Stage 2-3: WABA partnership + SF-side management (prereq)

Runs only when Stage 1 preflight found no existing channel. Execution order on a fresh run:
Stage 1 → Stage 2 (linking) → Stage 3 (manage-WABA) → Stage 4 (insert). On a preflight-hit resume,
these never run — the partnership and the SF-side webhook/credit-line share are both in place by
definition (the prior insert couldn't have succeeded otherwise).

**Stage 2 — customer-side partnership.** Confirm the WABA is shared with Salesforce in Meta Business
Suite. There's no Graph API to probe this without a customer Meta token, so invoke
`service-de-waba-integrate` and handle its envelope:
- success → proceed to Stage 3
- `{ok:false, kind:"partnership-blocked"}` → propagate; resolve on Meta side and retry
- `{ok:false, kind:"user-declined"}` → propagate; re-run when ready

**Stage 3 — SF-side management.** The customer-side share from Stage 2 alone does not subscribe SF's
webhook or share SF's Meta line of credit. Call the sanctioned Connect endpoint. It needs
`{AUTH_PROVIDER_ID}`, so **run the Stage 4.1 AuthProvider lookup (SKILL.md) first** — on a fresh run
Stage 3 executes before Stage 4. **The WABA id (and phone id) go in the URL query string, NOT the
JSON body** — the endpoint reads `wabaId`/`phoneId` from the query and ignores a body
`externalAccountId`. The body is empty, but **pass `--body '{}'` explicitly**: current `sf` CLI
versions reject a body-less POST locally with `No 'mode' found in 'body'` before anything reaches the
server.

```bash
sf api request rest \
  "/services/data/v{API_VERSION}/connect/livemessage/whatsapp/business-account?authProviderId=${AUTH_PROVIDER_ID}&wabaId=${WABA_ID}&phoneId=${PHONE_NUMBER_ID}" \
  --method POST --target-org '{ORG_ALIAS}' \
  --header 'Content-Type: application/json' --header 'Accept: application/json' \
  --body '{}' --include > "${SCRATCH_DIR}/waba-manage.txt" 2>&1
```

**Classify by the response body's `success` field, not the HTTP status** (gotcha #7). This endpoint
returns **HTTP 201 even when it fails**, with `{"success":false,"errorMessage":"..."}` in the body.
- `success:true` → proceed to Stage 4.
- `success:false` with `errorMessage` containing `DE Unlimited Access orgs must create Unified Messaging channels`
  → emit `{ok:false, kind:"unified-messaging-required", message:"<errorMessage>", hint:"This org's Digital Engagement license (DE Unlimited Access) only allows Unified Messaging WhatsApp channels; these skills create Enhanced WhatsApp channels, so WhatsApp can't be set up headlessly here. Set WhatsApp up in Setup → Messaging Settings instead. Other channel types aren't affected."}`. Stop — don't
  attempt the insert; it fails on the same gate with a less readable error.
- any other `success:false`, or a non-2xx status → emit
  `{ok:false, kind:"waba-manage-failed", hint:"manageWhatsAppBusinessAccount failed — SF could not subscribe its webhook / share credit line with this WABA. Most likely: WABA not actually shared yet (partnership landed Meta-side but hasn't propagated), or the WABA id is wrong.", message:"<errorMessage or response body>"}`.

> **Do NOT put the WABA id in the body** (gotcha #6). A body of `{"externalAccountId":"<WABA_ID>"}` —
> or even `{"wabaId":"<WABA_ID>"}` — returns `400 INVALID_API_INPUT "wabaId is required"`, because the
> endpoint only reads `wabaId`/`phoneId` from the query string. Pass both as query params with an empty
> body. (Verified live: documented body shape → `"wabaId is required"` on sdb6; query-param shape → 201
> on projectCodeyDemo, 2026-08-26.)

Together Stage 2 + Stage 3 produce a WABA fully ready for the Stage 4 channel insert.

## Stage 4.2: request body

```json
{"messageType":"WhatsApp","platformType":"Enhanced",
 "messagingPlatformKey":"{PHONE_NUMBER_ID}",
 "messagingChannelName":"{CHANNEL_NAME}",
 "externalAccountId":"{WABA_ID}",
 "isoCountryCode":"{ISO_COUNTRY_CODE}"}
```

The MCU lands in a pre-activation `DeploymentStatus` (observed as both `Disabled` and `New` on fresh
WhatsApp inserts across orgs; Facebook lands as `New`). Any pre-activation value is a valid
`→ Provisioning` source state — don't assert a specific one; just confirm the MCU exists.

## Type-specific failure kinds

- `partnership-blocked` — from Stage 2 (`service-de-waba-integrate`).
- `user-declined` — user cancelled the WABA-linking prompt.
- `waba-manage-failed` — from Stage 3 (SF-side `manageWhatsAppBusinessAccount`).
- `unified-messaging-required` — from Stage 3; the org's license only allows Unified Messaging
  WhatsApp channels (gotcha #8).
- `meta-precondition` — Connect rejected the insert (WABA not shared, phone not OTP'd on Meta side,
  etc.); hint `"Connect API rejected the request — WABA not shared, phone not OTP'd on Meta side"`.

## Gotchas

1. **WABA_ID ≠ PHONE_NUMBER_ID.** A WABA can contain multiple phone numbers. Same value for both →
   cryptic activation failures ("WhatsApp number registration failed"). Stage 0.1 asserts they differ.
2. **PATCH activation is synchronous with Meta `/register`** — WhatsApp channels take 15-30s to
   activate (vs ~1s for Apple/LINE, which have no external callout). Not this skill's concern, but
   explains the downstream latency difference in `service-de-channel-activate`.
3. **`developerName` follows the server-side format** (e.g. `WHATSAPP_US_<phoneNumberId>`), NOT the
   Connect response's pre-DB projection. Trust the DB (Stage 5 verify), not the 201 body.
4. **Fresh-insert MCU `DeploymentStatus` varies** — observed as both `Disabled` and `New` on WhatsApp
   across orgs (`New` for Facebook). Don't assert a specific starting status in Stage 5 — just that the
   MCU exists; any pre-activation value is a valid `→ Provisioning` source.
5. **Field/relationship-name variance across orgs.** Use the two-query FK form (never the
   `MessagingChannelUsages` child subquery), and the trimmed universal field set — `ExternalAccountId`
   and `MessagingPlatform` are absent on some orgs (`INVALID_FIELD` on `wadtesting`).
6. **WABA-management call takes `wabaId`/`phoneId` in the URL query, not the body.** The documented
   body shape `{"externalAccountId":"<WABA_ID>"}` returns `400 INVALID_API_INPUT "wabaId is required"`
   (as does `{"wabaId":...}` in the body). Pass `?...&wabaId=<WABA_ID>&phoneId=<PHONE_NUMBER_ID>` with an
   empty body — see Stage 3.
7. **WABA-manage reports failure inside a 201.** A failed call returns HTTP 201 with
   `{"success":false,"errorMessage":"..."}`. Classifying by status alone treats it as success and
   pushes the run into an insert that fails anyway. Always read `success`.
8. **DE Unlimited Access orgs can't create Enhanced WhatsApp channels.** On orgs licensed "DE
   Unlimited Access" (Messaging Unlimited), both WhatsApp Connect calls are blocked by the same
   server-side check: `DE Unlimited Access orgs must create Unified Messaging channels.` WABA-manage
   returns it readably (201 + `success:false`). The insert returns it as
   `400 CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY`, or on some builds as an opaque `500 UNKNOWN_EXCEPTION`
   ("Error creating a new Messaging Channel"), which is why Stage 3 stops on it. Setting
   `platformType:"Unified"` in the insert body isn't a workaround — it's rejected with
   `Invalid value for platform type`. The check fires before the WABA partnership matters, and it
   only affects WhatsApp: Facebook, MIAW and Voice channels on the same org stay Enhanced. There's no
   headless Unified Messaging path in these skills, so the user has to set up WhatsApp in Setup.
   (Verified on a 264 DE Unlimited Access org, 2026-10-05, and a local 266 org, 2026-09-23.)

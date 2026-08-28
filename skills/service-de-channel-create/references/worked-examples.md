---
name: service-de-channel-create-worked-examples
description: "Load for end-to-end traces of a channel insert per type — a fresh Connect-path insert (Apple, verified on wadtesting), a preflight short-circuit re-run, and the Facebook interactive OAuth → page-selection path. Illustrative only; the authoritative flow is the parent SKILL.md stages."
metadata:
  version: "1.0"
  related-skills: service-de-channel-create
---

# Worked examples (per type)

## Apple Business Chat — fresh insert (real trace, wadtesting 2026-04-30)

`messagingcore-wadtesting2.test1.my.pc-rnd.salesforce.com`. Inputs:
`APPLE_BC_ID=c02e9350-f526-42dc-9e8d-cec2edf59487`, `CHANNEL_NAME=Apple Channel`.

- **Stage 1** — preflight SOQL (two-query FK form) returns 0 rows. Proceed.
- **Stage 4.1** — `SELECT Id FROM AuthProvider WHERE DeveloperName='LiveMessageSetup'` → one row,
  captured as `{AUTH_PROVIDER_ID}` (org-specific).
- **Stage 4.2** — body `{"messageType":"AppleBusinessChat","platformType":"Enhanced","messagingPlatformKey":"c02e9350-...","messagingChannelName":"Apple Channel"}`;
  POST to `.../connect/livemessage/channels?authProviderId=${AUTH_PROVIDER_ID}`. Response 201:
  ```json
  {"id":"0MjSG000000MNUD0A4","developerName":"AppleBusinessChat_c02e9350_...",
   "isActive":false,"masterLabel":"c02e9350-...","messageType":"AppleBusinessChat",
   "messagingPlatformKey":"c02e9350-..."}
  ```
  The `masterLabel`/`developerName` in the body are **stale input-rep projections** — the DB row uses
  `MasterLabel="Apple Channel"` and the canonical `APPLEBUSINESSCHAT_US_c02e9350_...`.
- **Stage 5** — verify SOQL confirms `MasterLabel="Apple Channel"`,
  `DeveloperName="APPLEBUSINESSCHAT_US_c02e9350_..."`, `IsActive=false`; MCU `0gLSG0000003Kjl2AE`,
  `DeploymentType=Conversation`, `DeploymentStatus=New`.
- **Stage 6** — success envelope, `path:"connect"`, `created:true`.

Downstream chain ran immediately after: routing PATCH → 204; activation PATCH
(`DeploymentStatus="Provisioning"`) → 204 in ~1s (Apple hits the observer's `default` branch — no
external callout).

**Gotcha surfaced:** the first POST omitted `?authProviderId=` (based on an older skill version
claiming "Apple doesn't use authProviderId") → `400 ILLEGAL_QUERY_PARAMETER_VALUE`. Corrected:
`authProviderId` is universally required.

## LINE — fresh insert (illustrative)

Inputs: `LINE_CHANNEL_ID=2001234567`, secret + long-lived token, `CHANNEL_NAME=Support LINE Channel`.

- **Stage 1** preflight → 0 rows.
- **Stage 2-3** (optional token verify) → `GET https://api.line.me/v2/bot/info` returns 200. Valid.
- **Stage 4.2** body includes `authDetails:{client_secret, access_token}`. Response 201 →
  `{id:"0MjSG000000Fd2m0AD", developerName:"LINE_2001234567", ...}`.
- **Stage 5** verify → channel + one MCU `DeploymentType=Conversation`. Success `path:"connect"`.

## Preflight short-circuit (any type)

Re-running an insert for a channel that already exists:
- **Stage 1** preflight SOQL finds `records.length === 1`. Records `{CHANNEL_ID}`, `{DEVELOPER_NAME}`,
  `{IS_ACTIVE}`; second query picks up `{MCU_ID}`.
- Emits success envelope with `path:"preflight", created:false`. Stages 2-5 never run. This is the
  idempotency guard (`MessagingChannel` rows aren't deletable via standard means).

## Facebook — interactive OAuth → page selection (illustrative)

`PAGE_ID` not supplied.
- **Stage 1** skipped (no page id yet).
- **Stage 2-3** — look up `{AUTH_PROVIDER_ID}`; the stored FB token is stale, so open the OAuth URL
  in a browser, wait for the user to authorize, then fetch the page list. Render all pages sorted by
  `masterLabel`, annotated with connected status, untruncated. User selects one → `{PAGE_ID}`. Prompt
  for `{CHANNEL_NAME}`. Now run the Stage 1 preflight for the chosen page id.
- **Stage 4.2** body `{..., messagingPlatformKey:"{PAGE_ID}", authDetails:{}}`. If the response
  errorCode is `AUTH_PROVIDER_NEEDS_AUTH` (may arrive as 400 OR 401), emit `oauth-not-complete` and
  re-run OAuth — do NOT tell the user to run `sf org login web` (the SF session is fine).
- **Stage 5** verify → MCU `DeploymentStatus=New` (Facebook lands as `New`, not `Disabled`). Success.

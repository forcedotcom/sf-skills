# LINE — token verify, request body, gotchas

`MESSAGE_TYPE=Line`. Platform key is the **LINE channel id** (numeric, from the LINE Developers
Console — not the LINE user id). Channel secret + access token go in `authDetails`.

## Inputs

- `{LINE_CHANNEL_ID}` — LINE channel id. Numeric string. Sent as `messagingPlatformKey`.
- `{LINE_CHANNEL_SECRET}` — LINE channel secret (webhook verification secret). Sent in
  `authDetails.client_secret`.
- `{LINE_ACCESS_TOKEN}` — LINE long-lived channel access token. Sent in `authDetails.access_token`.
- `{CHANNEL_NAME}` — optional. Defaults to `LINE_{LINE_CHANNEL_ID}` if not provided.
- `{VERIFY_TOKEN_FIRST}` — optional boolean, default `true`. When `true`, validate the token against
  LINE's public API before insert.

## Stage 2-3: optional token preflight

If `{VERIFY_TOKEN_FIRST}` is `true`, validate the token before paying the full insert cost. This is
a **third-party** call to LINE, so it uses `curl` (not `sf api request rest`) — the LINE token is
not a Salesforce credential:

```bash
curl -sS -o "${SCRATCH_DIR}/line-token.json" -w '\n%{http_code}' \
  -H "Authorization: Bearer ${LINE_ACCESS_TOKEN}" \
  "https://api.line.me/v2/bot/info"
```

- HTTP 200 → token valid, proceed.
- HTTP 401 / non-200 → `{ok:false, kind:"line-token-invalid", hint:"LINE access token rejected — regenerate in LINE Developers Console and retry"}`.

If `VERIFY_TOKEN_FIRST=false`, skip — the Connect POST will surface a token error later, with less
clear signal.

(`${SCRATCH_DIR}` is the per-run scratch dir established in SKILL.md Stage 0.2 — under
`${outputDir}`/`${TMPDIR}`, never a bare `/tmp` path.)

## Stage 4.2: request body

```json
{"messageType":"Line","platformType":"Enhanced",
 "messagingPlatformKey":"{LINE_CHANNEL_ID}",
 "messagingChannelName":"{CHANNEL_NAME}",
 "authDetails":{"client_secret":"{LINE_CHANNEL_SECRET}","access_token":"{LINE_ACCESS_TOKEN}"}}
```

**Write the body to a file** — the access token is long and can contain shell-hostile characters.

Response classification: same as the shared table (see `connect-insert.md`), plus — on `400` whose
message contains "access token" / "channel secret" / "Line" — emit
`{ok:false, kind:"line-token-invalid", message, hint:"LINE creds rejected — verify channel secret + access token in LINE Developers Console"}`.

## Gotchas

1. **`messagingPlatformKey` is the LINE channel id**, not the LINE user id — the numeric id shown in
   the Developers Console for the Messaging API channel.
2. **`authDetails` keys are exactly `client_secret` + `access_token`.** Don't rename them;
   `LiveMessageSetupServiceImpl.addChannel` looks for exactly those strings.
3. **Long-lived vs short-lived tokens.** The Setup wizard assumes long-lived (Developers Console).
   Short-lived tokens (Channel Access Token v2.1 API) insert fine but expire, silently stopping the
   channel. Use long-lived for production.
4. **No third-party registration at activation.** Unlike WhatsApp, LINE has no `/register` call —
   `service-de-channel-activate` transitions MCU→Active without any external callout, so
   `Provisioning` is essentially invisible (~1s).
5. **`sf api request rest` manages the SF OAuth session** — no `ACCESS_TOKEN`/`INSTANCE_URL` shell
   variables. The LINE token is the only credential handled by `curl`, and only for the Stage 2-3
   verify.

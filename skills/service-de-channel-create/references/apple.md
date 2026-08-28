# Apple Business Chat — empty config, precondition errors, gotchas

`MESSAGE_TYPE=AppleBusinessChat`. Platform key is the **Apple Business Chat Account ID** (a GUID,
`00000000-0000-0000-0000-000000000000`, from register.apple.com/business-chat).

Apple BC has **no third-party credentials** (no client secret, no access token). Authentication with
Apple's servers is certificate-based and provisioned when the Apple BC account is created on Apple's
Register a Business side. That's why the Setup UI's `liveMessageAppleBusinessChatHelper.js` sends
`messagingChannelProperties: {}` and never asks for any secret beyond the account id itself.

## Inputs

- `{APPLE_BC_ID}` — Apple Business Chat Account ID (GUID). Sent as `messagingPlatformKey`.
- `{CHANNEL_NAME}` — **required**. Apple BC has no phone number / screen name to fall back on, so the
  caller must supply a display name (`messagingChannelName`). Don't synthesize `APPLE_{id}` — the
  user sees this name in the UI.

## Stage 2-3: none

Apple has no insert-time prerequisite. The certificate handshake with Apple's servers is per-message
at runtime, separate from channel activation — there is no external provisioning callout at activation
either (Apple hits the `default` branch in the observer's external-callout switch; activation is ~1s).

## Stage 4.2: request body

```json
{"messageType":"AppleBusinessChat","platformType":"Enhanced",
 "messagingPlatformKey":"{APPLE_BC_ID}",
 "messagingChannelName":"{CHANNEL_NAME}"}
```

**No `authDetails` / `externalAccountId` / `isoCountryCode`.** Apple BC uses none of those; the
Connect input rep treats unset fields as absent (not `null`). `authProviderId` still goes in the URL
query string (Apple is NOT exempt — verified: omitting it yields `400 ILLEGAL_QUERY_PARAMETER_VALUE
"Missing argument authProviderId"`).

Response classification: same as the shared table (see `connect-insert.md`), plus — on `400` whose
message mentions "Apple" / "account" / "not registered" — emit
`{ok:false, kind:"apple-precondition", hint:"Apple BC Account ID not recognized — confirm the business is registered at register.apple.com/business-chat", message}`.

## Gotchas

1. **`messagingChannelProperties` / `authDetails` MUST be empty or omitted for Apple.** Populating
   the map with placeholder values can make the server reject the insert with an unclear error.
2. **`MessagingPlatformKey` is the GUID**, not a display string. Don't paste the URL-encoded or
   capitalized form.
3. **No external provisioning callout at activation** — Apple hits the `default` branch in
   `ConversationChannelUsageDeploymentStatusService.runProvisioning`; the terminal
   `DeploymentStatus=Active` write happens immediately (~1s, vs 15-21s for WhatsApp).
4. **`CHANNEL_NAME` is required** — no display phone number to fall back on.
5. **Apple BC onboarding is slow outside SF.** Registering at register.apple.com/business-chat can
   take days for Apple to approve. A precondition error at insert most likely means the business
   isn't live on Apple's side yet.
6. **Connect response echoes are not authoritative.** The 201 body comes back with
   `masterLabel = messagingPlatformKey` (the GUID) and a non-canonical short `developerName`
   (`AppleBusinessChat_<guid>`). The DB row uses the supplied `messagingChannelName` and the
   canonical `APPLEBUSINESSCHAT_US_<guid>`. Trust Stage 5's verify SOQL, not the POST body.
7. **Fresh MCUs start in `DeploymentStatus=New`** (`Disabled` is the post-deactivation state). Both
   are valid `→ Provisioning` sources — don't assert a specific starting status in Stage 5.

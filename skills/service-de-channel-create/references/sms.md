# SMS (Text) — phone-number platform key, accepted-but-ignored smsProvider, gotchas

`MESSAGE_TYPE=Text`. There is **no `"SMS"` enum value** — SMS channels are `Text` everywhere in the
platform (the `MessageTypeEnum` API value is `"Text"`; the DB value is `0`). Send `"messageType":"Text"`.

Platform key is the **phone number / SMS code itself** — the literal long code, toll-free number, or
short code string the caller wants to send from (e.g. `18005551234`). It is stored verbatim into
`MessagingChannel.MessagingPlatformKey` and used as-is for the activation-time ESP lookup, so it must
match exactly what was provisioned for that code. Don't reformat it; send whatever the caller gives.

**Prerequisite (caller's responsibility, NOT handled by this skill):** the phone number / code must
already be provisioned to the org through the SMS code-request flow. This skill does **not** allocate a
number, request a short code, or run any code-provisioning step — it only inserts the channel record for
a number the caller already has. If the number isn't provisioned yet, the insert may still succeed (the
record is created inactive) but activation will later fail at the ESP registration step.

## Inputs

- `{SMS_NUMBER}` — the phone number / short code / toll-free number, as a plain string. Sent as
  `messagingPlatformKey`. **Required.**
- `{SMS_PROVIDER}` — the code-provider identifier for this number (the "messaging provider" / SMS
  provider). Sent as `smsProvider`. The `smsProvider` **key must be present in the body**, but the
  Connect endpoint only checks that the field *exists* — it does not check the **value** against any
  provider registry, and it does not persist the value anywhere. Sending an **empty string**
  (`"smsProvider":""`) inserts the channel successfully; **omitting the key entirely** fails with
  errorCode `ILLEGAL_QUERY_PARAMETER_VALUE`, message `"SMS provider is missing "`. Tested against
  `sdb6` (API v69.0): an empty-provider channel and a real-provider channel are byte-identical across
  every queryable `MessagingChannel` field — there is no `ExternalChannelConfigJson` /
  `codeProviderDetails` field on the object (the only provider/config-adjacent fields are
  `IsoCountryCode` and `RoutingConfigurationId`), so the value has no storage location and leaves no
  observable trace. Pass the real provider when the caller knows it, else default to `""` — never omit
  the key.
- `{CHANNEL_NAME}` — display name (`messagingChannelName`). Recommended; falls back to the number if
  omitted, but supplying it keeps the Setup UI label meaningful. Note: the insert **response** echoes
  `masterLabel` as the bare number, but the **persisted** `MessagingChannel.MasterLabel` holds the
  supplied `messagingChannelName` (tested against `sdb6`, API v69.0). Read the stored record — not the
  POST response — if you need the display label back.
- `{ISO_COUNTRY_CODE}` — optional, default `US`. Participates in the dedupe query and the generated
  `DeveloperName`, so pass the real country if the number is non-US.

## Stage 2-3: none

SMS has no insert-time third-party prerequisite that this skill performs. The number-provisioning /
code-request step is upstream and out of scope (see the prerequisite note above). The ESP registration
(`registerCsotSms` → Admin API ESP-ID lookup keyed by the platform key) runs at **activation**, not
insert — so an unprovisioned number surfaces as an activation-time `provisioning-error`, not an insert
failure.

## Stage 4.2: request body

```json
{"messageType":"Text","platformType":"Enhanced",
 "messagingPlatformKey":"{SMS_NUMBER}",
 "messagingChannelName":"{CHANNEL_NAME}",
 "smsProvider":"{SMS_PROVIDER}",
 "isoCountryCode":"{ISO_COUNTRY_CODE}"}
```

**`smsProvider` is the Text-specific field the body must always carry** — no other type sends it, and
Text cannot be inserted if the key is missing. Its value is not validated or stored (see Inputs), so
default to `""` when the caller didn't supply a provider — but **always include the key**. **No
`authDetails` / `externalAccountId` / auth tokens** — Text uses none of those (`authDetails` is read
only by MsCopilot / GoogleChat / Slack / Line). `authProviderId` in the URL query string is **optional
for Text** (the v258 Connect signature added a Text-only path that doesn't require it) — this is the
whole reason Stage 4.1 treats a missing `LiveMessageSetup` AuthProvider as terminal for every other type
but non-fatal for `Text`. Send `authProviderId` only when Stage 4.1 actually resolved one (harmless for
Text); when it didn't, `Text` proceeds and the POST omits the parameter entirely. **Do not append an
empty `?authProviderId=`** — a blank value is rejected with `ILLEGAL_QUERY_PARAMETER_VALUE`, so a Text
insert on an org with no LiveMessage setup must hit the bare endpoint.

Response classification: same as the shared table (see `connect-insert.md`), plus — on an error whose
message mentions "SMS provider" / "provider is missing" (observed errorCode
`ILLEGAL_QUERY_PARAMETER_VALUE`) — the body dropped the `smsProvider` key entirely; re-send with the
key present (an empty string `""` is fine). This shouldn't happen if the body is built from the shape
above, which always includes the key.

## Gotchas

1. **The enum is `Text`, not `SMS`.** `"messageType":"SMS"` is rejected — the picklist / SOQL / Connect
   enum value is `Text`. The user-facing concept "SMS" maps to `Text` in every API surface.
2. **`smsProvider` key is mandatory; its value is not.** The Connect endpoint checks only that the
   field is present — omitting it fails with errorCode `ILLEGAL_QUERY_PARAMETER_VALUE`, message
   `"SMS provider is missing "`, but an empty string (`"smsProvider":""`) inserts fine, and the
   endpoint neither checks the value against a provider registry nor stores it anywhere (no
   `ExternalChannelConfigJson`/`codeProviderDetails` field exists on `MessagingChannel`; tested
   against `sdb6`, API v69.0). Always send the key; default the value to `""` when unknown. It is a
   code-provider label, not an auth secret.
3. **`MessagingPlatformKey` is the number/code string itself**, stored verbatim. There's no separate
   phone-number ID (contrast WhatsApp, where the platform key is a Phone Number ID distinct from the
   WABA ID). Send the exact provisioned code string; this skill doesn't normalize to E.164.
4. **This skill doesn't provision the number.** It inserts a channel record for a number the caller
   already has. Number allocation / short-code requests are a separate upstream flow, intentionally out
   of scope here — the caller must already know their number and its provider.
5. **Activation, not insert, is where an unprovisioned number bites.** `registerCsotSms` does the Admin
   API ESP-ID lookup keyed by the platform key at activation time. Insert only creates the inactive
   record + its MCU.
6. **Fresh MCUs start in `DeploymentStatus=New`** (`Disabled` is the post-deactivation state) — same as
   every other type. Don't assert a specific starting status in Stage 5.

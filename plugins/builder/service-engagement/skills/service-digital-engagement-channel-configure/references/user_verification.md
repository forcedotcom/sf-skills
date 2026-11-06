# User verification (Auth mode)

Applies when the user turns user verification on (step 8).

- Set `embeddedConfig.authMode` to `Auth` and use `verifiedUserJwtExpirationTime` (60-240); omit `anonymousUserJwtExpirationTime`.
- Include `<messagingAuthorizations>` inside `<embeddedConfig>` only when the user gave an existing keyset name: `authorizationType` `PublicKeyCertificateSet`, `enabled` `true`, `publicKeyCertificateSetName` (the keyset's API name) and `authIdentifier` (free-form label; default the file name, not the JWT `sub` claim). Do not emit `authProviderName`. Shape: `references/channel_settings.md` → Messaging Authorizations; example: `examples/auth_queue_channel.xml`.
- Never invent a keyset name, reuse the example's `Support_Keyset`, or write key or keyset files; the deploy fails with "Required fields are missing: [AuthorizationConfigId]" when the keyset doesn't exist.
- No keyset name given (standalone or delegated): do not ask or fail. Set `authMode` `Auth` with `verifiedUserJwtExpirationTime` and omit `<messagingAuthorizations>`, then tell the user verification is not active until a keyset is attached.
- Creating keys or keysets is a separate setup and not part of this skill.

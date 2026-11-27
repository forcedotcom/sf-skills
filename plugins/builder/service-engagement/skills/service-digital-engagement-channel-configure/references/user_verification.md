# User verification (Auth mode)

Applies when the user turns user verification on (step 8).

- Set `embeddedConfig.authMode` to `Auth` and use `verifiedUserJwtExpirationTime` (60-240); omit `anonymousUserJwtExpirationTime`.
- Include `<messagingAuthorizations>` inside `<embeddedConfig>` only for a keyset name the user gave, or one just created or chosen through `references/keyset_setup.md`: `authorizationType` `PublicKeyCertificateSet`, `enabled` `true`, `publicKeyCertificateSetName` (the keyset's API name) and `authIdentifier` (free-form label; default the file name, not the JWT `sub` claim). Do not emit `authProviderName`. Shape: `references/channel_settings.md` → Messaging Authorizations; example: `examples/auth_queue_channel.xml`.
- Never invent a keyset name or reuse the example's `Support_Keyset`; the deploy fails with "Required fields are missing: [AuthorizationConfigId]" when the keyset doesn't exist.
- No keyset named (standalone, or delegated with `verificationKeyset` absent): never block or fail. Set `authMode` `Auth` with `verifiedUserJwtExpirationTime` and omit `<messagingAuthorizations>`, then ask once after activation whether to create a keyset, use an existing one, or skip (`references/keyset_setup.md` → After the channel exists). Only `keyset_setup.md` writes key or keyset files.

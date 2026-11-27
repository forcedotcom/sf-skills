# Client Integration Contract (customer-side)

This keyset only *verifies* JWTs. Minting and signing them is the **customer's**
responsibility, on their **backend**. This file documents the contract the customer
must meet so their tokens validate against the keyset this skill creates.

---

## Who signs what, and where

- The **private** key lives on the customer's backend (or an HSM / secrets manager)
  and **never** touches the browser or mobile app.
- The customer's backend signs a short-lived JWT (RS256 or RS512) with that private key.
- Salesforce validates the signature using the **public** key registered in this keyset,
  matched by `kid`.
- The `key-command-line-utility`
  (`github.com/Salesforce-Async-Messaging/key-command-line-utility`) is an **offline,
  test-only** tool for generating demo keys/JWTs — it is NOT a production signer.

## The token

**Header**
| Field | Requirement |
|-------|-------------|
| `alg` | `RS256` or `RS512` |
| `kid` | Must match a `kid` in this keyset's JWKS — else runtime `JWK corresponding to kid in customer JWT not found` (422) |

**Claims**
| Claim | Requirement |
|-------|-------------|
| `iss` | Must equal the keyset's `jwtIssuer` |
| `sub` | Stable user identifier. Salesforce maps the verified user from this. (Note: only `sub` is used for identity — additional custom claims are not read; use hidden pre-chat fields to convey extra data.) |
| `exp` / `iat` | Short-lived. See session renewal below. |

## Delivering the token to Salesforce (SDK)

- **Web (Messaging for Web):** after the embedded messaging bootstrap is ready, call
  `embeddedservice_bootstrap.userVerificationAPI.setIdentityToken({ identityTokenType: 'JWT', identityToken: <jwt> })`.
  On user logout call `clearSession()` — Salesforce cannot know when the customer's own
  site session ends, so the customer must clear it (this revokes the internal session JWT).
- **Mobile (In-App SDK, iOS/Android):** supply the token through the SDK's
  user-verification configuration at conversation creation. A mobile deployment must be
  designed for verified users OR unverified users, not both.

## Two tokens (don't confuse them)

1. **User-verification JWT** — the customer mints/signs this; it's the identity assertion
   this keyset verifies.
2. **Session JWT** — Salesforce mints this internally after verification; the SDK stores it
   to resume conversations. The customer neither generates nor should read it. `clearSession()`
   is what invalidates it on logout.

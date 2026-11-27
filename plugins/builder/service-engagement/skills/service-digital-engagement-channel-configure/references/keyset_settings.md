# Keyset Settings Reference

The org-side keyset for MIAW token-based user verification. Two metadata types. Templates: `assets/public_key_certificate*.xml`; examples: `examples/jwks_*.xml`.

---

## `PublicKeyCertificate` (JWKS / uploaded-keys mode only)

Dir `PublicKeyCertificate/`, suffix `.PublicKeyCertificate-meta.xml`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `masterLabel` | String | Yes | Display name of the key |
| `isActive` | Boolean | Yes | Whether the key is active |
| `jsonWebKey` | String (escaped JSON) | Yes | The PUBLIC JWK, one JSON object, XML-escaped |

`jsonWebKey` JSON fields (public JWK):

| Field | Notes |
|-------|-------|
| `kty` | `RSA` |
| `kid` | Key id — MUST match the JWT header `kid` |
| `alg` | `RS256` or `RS512` |
| `use` | `sig` |
| `n`, `e` | RSA public modulus / exponent (base64url) |
| `x5c` | Optional cert chain |

> Do NOT include a real private exponent (`d`). A public JWK for upload has `n`/`e`
> (and optionally `x5c`) only. On a live retrieve, private-only slots come back as
> placeholder literals (e.g. `"d":"d"`) — Salesforce stores only the public half.

---

## `PublicKeyCertificateSet`

Dir `PublicKeyCertificateSet/`, suffix `.PublicKeyCertificateSet-meta.xml` (casing is load-bearing).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `masterLabel` | String | Yes | Display name of the keyset |
| `jwtIssuer` | StringOrURI | Yes | Matches the JWT `iss` claim exactly. Bare strings (no colon, e.g. `testIssuer`) are valid and deploy fine; only a value containing a `:` must be a well-formed URI (RFC 7519 StringOrURI) |
| `type` | Enum | Yes | `JWKS` (uploaded keys) or `JWKS_URL` (endpoint). All caps |
| `publicKeyCertificateSetKeys` | List | JWKS only | One entry per key; child `<publicKeyCertificate>` = the key's API name |
| `jwksEndPoint` | String (URL) | JWKS_URL only | JWKS endpoint hosted outside Salesforce. Required when `type=JWKS_URL` — a null/invalid endpoint is rejected on create/update |

`JWKS_URL` suits large or rotating key sets: Salesforce re-fetches keys from the endpoint, so no re-upload on rotation. The endpoint must be outside Salesforce and serve RS256/RS512 keys. A `JWKS_URL` set cannot hold keys.

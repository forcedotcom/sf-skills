# Keyset setup (creating the verification keyset)

Applies when user verification is on (step 8) and the user gives a key source, asks to create a keyset, or answers "create" to the question below. Delegated mode reaches it only when `verificationKeyset` is absent and the user answers "create"; a given `verificationKeyset` is used as is.

The keyset is what Salesforce uses to verify customer-signed JWTs. It is a `PublicKeyCertificateSet`, plus one `PublicKeyCertificate` per key in uploaded-keys mode. Fields: `references/keyset_settings.md`. Customer-side signing contract: `references/user_verification_client.md`.

## Rules

- Public keys only. Never accept a private key or PEM (a JWK with a meaningful `d`); stop and ask for the public JWKS. A pasted public JWKS (only `n`, `e`, `kid` and similar public fields) is fine. If a private key was pasted in chat, stop and tell the user to treat that key as exposed and rotate it.
- Never `Read`/`cat` a customer's key file: a JWKS export can carry private fields. Extract only the public fields with a script (e.g. `jq`), and refuse the file if any key has a real `d`, `p`, `q`, `dp`, `dq` or `qi` (test without printing values). Ignore the placeholder literals an org retrieve returns (`"d":"d"`, `"y":"y"`, `"k":"k"`, `"crv":"crv"`) and drop them. Never echo `n`/`e` back beyond the generated file.
- Never generate keys. The private key lives on the customer's backend. Only if the user explicitly asks for throwaway test keys for a dev org, point them to the offline `key-command-line-utility` and say the material is disposable.
- Deploy each `PublicKeyCertificate` before the set that references it.
- `jwtIssuer` must equal the `iss` the customer's JWTs carry exactly; do not force a URI (field rules in `keyset_settings.md`).

## Ask first

1. Mode: uploaded keys (`type` `JWKS`) or endpoint URL (`type` `JWKS_URL`).
2. Key source, the main input. Uploaded keys: the path to the customer's `jwks.json`, or pasted JWK/JWKS JSON. Extract `kid`, `alg`, `kty`, `use`, `n`, `e`, optional `x5c` from it as above; never ask the user to type them. Endpoint URL: the JWKS URL, hosted outside Salesforce. Use the keys URL, not the `.well-known/openid-configuration` URL.
3. Keyset API name and label, and the JWT issuer.

## Generate

Folder and suffix casing is load-bearing: `PublicKeyCertificate/` and `PublicKeyCertificateSet/` with `.PublicKeyCertificate-meta.xml` and `.PublicKeyCertificateSet-meta.xml`. Not `publicKeyCertificateSets/`; the CLI cannot infer the type.

- Uploaded keys: per JWK, `PublicKeyCertificate/<KeyName>.PublicKeyCertificate-meta.xml` from `assets/public_key_certificate_template.xml` (`isActive` `true`, `masterLabel`, `jsonWebKey` as the XML-escaped single-key JSON; default `<KeyName>` from the `kid`). Then `PublicKeyCertificateSet/<KeysetName>.PublicKeyCertificateSet-meta.xml` from `assets/public_key_certificate_set_jwks_template.xml`, one `publicKeyCertificateSetKeys` entry per key.
- Endpoint URL: only the set, from `assets/public_key_certificate_set_jwks_url_template.xml`, with `jwksEndPoint`. No key components; a `JWKS_URL` set cannot hold keys.

## Deploy and verify

Use the transport rules in `references/onboarding_contract.md` §2: probe a read per type (`PublicKeyCertificate`, `PublicKeyCertificateSet`), use `/headless/metadata` where the probe allows it (POST create, PUT full `xmlRep` on re-run, built from the generated file), otherwise `sf project deploy start --metadata "PublicKeyCertificate:<KeyName>"` then `"PublicKeyCertificateSet:<KeysetName>"`. Read it back (GET, or `sf project retrieve start`) and confirm `jwtIssuer`, `type` and each key's `kid`.

## Hand off to the channel

Use the keyset API name as `publicKeyCertificateSetName` in `references/user_verification.md`. Three values must line up at runtime: the JWT header `kid` is in the keyset's JWKS, the JWT `iss` equals `jwtIssuer`, and the channel's `publicKeyCertificateSetName` equals the keyset's API name. A `kid` already used by another key in the org fails the deploy, so before deploying retrieve the org's existing `PublicKeyCertificate` keys and compare their `kid`s with the new ones. On a match, reference the existing key in the new set instead of duplicating it.

## After the channel exists

No keyset named (standalone, or delegated without `verificationKeyset`): the channel is already created and activated as `Auth` without `messagingAuthorizations`. Ask one question right after step 15 and before step 16: create a new keyset, use an existing one, or skip. The answer is consent for the follow-up update of the channel this skill just created, and sets `keysetChoice` in the delegated result.

- **Create**: run Ask first, Generate and Deploy above, then add `messagingAuthorizations` to the channel with a full-document update (step 14).
- **Use existing**: list the org's `PublicKeyCertificateSet` records (name, label, `type`, `jwtIssuer`) and let the user pick; never choose for them. Then add `messagingAuthorizations` the same way. No keyset files are written.
- **Skip**: change nothing and say verification is not active until a keyset is attached.

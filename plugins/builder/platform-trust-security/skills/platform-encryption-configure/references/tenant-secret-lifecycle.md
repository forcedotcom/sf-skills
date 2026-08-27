# Tenant Secret Lifecycle

A **tenant secret** is the per-org root from which Shield derives (or wraps) data encryption keys. Its lifecycle operations are **UI/REST-only** — there is no `*.settings-meta.xml` for rotating, destroying, or uploading a tenant secret. When a user asks about these, return guidance and point them at Setup or the REST/Tooling API, not a metadata file.

## Operations

| Operation | What it does | Surface |
|-----------|--------------|---------|
| Generate | Creates a new active tenant secret for a key type | Setup → Key Management, or REST |
| Rotate | Generates a new tenant secret; existing data stays readable under prior secrets | Setup / REST |
| Destroy | Permanently destroys key material; data encrypted under it becomes unrecoverable | Setup (destructive, requires confirmation) |
| BYOK upload | Uploads customer-supplied key material as the tenant secret | Setup / REST |
| Cache-Only callout setup | Configures the named credential / callout endpoint the key service is fetched from | Setup (Named Credentials) |

## Rotation semantics

Rotating a tenant secret makes a new secret **active**; prior secrets are retained as **archived** so existing ciphertext stays readable. New writes use the active secret. To move existing data onto the new secret, run **background encryption** (a.k.a. the sync/re-encrypt process) — rotation alone does not re-encrypt existing rows.

For BYOK specifically, the sequence is: rotate to (upload) the new key material, then run background encryption to apply it. Uploading new material does not retroactively re-encrypt existing data on its own.

## Destruction semantics

Destroying a tenant secret is **irreversible**. Any data whose keys derive from that secret and has not been re-encrypted under another active secret becomes permanently unreadable. This is intentional (right-to-be-forgotten / crypto-shredding) but must be surfaced as a hard warning — there is no recovery path.

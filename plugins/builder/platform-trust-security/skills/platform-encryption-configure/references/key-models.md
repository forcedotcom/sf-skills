# Key Management Models

Shield Platform Encryption supports several ways to source and control the key material that protects encrypted data. They differ in *where the key material lives* and *who controls it*.

## The models

| Model | Where key material lives | Who controls it | Metadata / setting |
|-------|--------------------------|-----------------|--------------------|
| Salesforce-derived (default) | Salesforce, derived from a tenant secret | Salesforce derivation | none — default |
| **BYOK** (Bring Your Own Key) | Salesforce, but from *customer-supplied* material | Customer uploads key material; Salesforce stores it | `canOptOutOfDerivationWithBYOK` controls per-key derivation opt-out |
| **BYOKMS / EKM** (External Key Management) | An *external* key store the customer runs | Customer; Salesforce calls out to the KMS | `canExternalKeyManagement` (API 63.0+) |
| **Cache-Only Keys** | Outside Salesforce entirely; fetched on demand per callout | Customer hosts a key service; Salesforce caches, never persists | `enableCacheOnlyKeys`, `enableReplayDetection` |
| **Data 360 keys** | Salesforce, dedicated Data 360 root key | Customer-managed root key | `canManageDataCloudKeys` (API 63.0+) |
| **Transactional DB** | Salesforce | Org policy | `canEncryptTransactionalDatabase` (API 63.0+) |

## BYOK vs BYOKMS/EKM — the distinction users get wrong

- **BYOK**: you generate key material and *upload* it. Salesforce stores it and uses it like a derived key. The trust boundary still includes Salesforce storing the material.
- **BYOKMS / EKM**: key material *never leaves your external KMS*. Salesforce makes a callout to the KMS to wrap/unwrap. This keeps the material entirely under your control.

## Cache-Only Keys and replay detection

Cache-Only Keys go further than EKM: Salesforce fetches key material on every use and never persists it — only caches it transiently.

`enableReplayDetection` protects those callouts against replay attacks using a nonce. The contract is a **one-way dependency**:

> *Requires `enableCacheOnlyKeys=true` before setting `enableReplayDetection` to true.*

Two consequences the agent must respect:

1. Enabling Cache-Only Keys does **not** auto-enable replay detection. You must set `enableReplayDetection=true` explicitly.
2. An org can validly run Cache-Only Keys with replay detection **off**. It is not required.

Setting `enableReplayDetection=true` without `enableCacheOnlyKeys=true` is an invalid combination and will be rejected.

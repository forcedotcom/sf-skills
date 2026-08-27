# Encryption Schemes

Shield Platform Encryption offers two families of scheme, exposed on `CustomField.encryptionScheme` (Metadata API 44.0+). Choosing between them is a trade-off between cryptographic strength and queryability.

## Valid `encryptionScheme` values

| Value | Filterable / sortable / groupable | When to use |
|-------|:--:|-------------|
| `ProbabilisticEncryption` | **No** | Default and strongest. Same plaintext encrypts to different ciphertext each time, so no two values are comparable. Use unless the field must be queried. |
| `CaseSensitiveDeterministicEncryption` | Yes | Same plaintext always encrypts to the same ciphertext, preserving exact case. Use for exact-match filters where case matters (e.g. codes, tokens). |
| `CaseInsensitiveDeterministicEncryption` | Yes | Deterministic with case normalized before encryption. Use for equality filters on human-entered text (names, emails) where case should not matter. |
| `None` | n/a | Removes encryption from the field. |

Only these four strings are accepted. Any other value fails deployment.

## Deterministic vs Probabilistic — the decision

- **Need to filter, sort, group, or use the field in a WHERE clause?** → a deterministic scheme. Deterministic encryption preserves equality so the index can be used.
- **No query requirement?** → probabilistic. It is cryptographically stronger because identical plaintexts produce different ciphertexts, defeating frequency analysis.
- **Case matters in matching?** → `CaseSensitive...`. Otherwise `CaseInsensitive...`.

Enabling the deterministic scheme at the org level also requires `enableDeterministicEncryption=true` in `PlatformEncryptionSettings`.

## Query behavior of encrypted fields — the failure mode

A common misconception is that filtering or sorting on a **probabilistically**-encrypted field silently drops the clause or returns zero rows. It does not.

The platform **rejects the query** with an `INVALID_FIELD` error:

```text
INVALID_FIELD: field '<FieldName>' can not be sorted / filtered / grouped in a query call
```

This is enforced server-side (see the platform's `QueryBlockingTest` coverage). The correct guidance to a user hitting this is: the query failed because the field is probabilistically encrypted — re-encrypt it with a deterministic scheme if it must be queryable, or remove the field from the filter/sort/group clause. Never tell the user the query "returns nothing" — it errors.

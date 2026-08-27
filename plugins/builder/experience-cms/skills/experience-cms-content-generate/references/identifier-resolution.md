# Identifier resolution — content key / managedContentId / variantId

Shared by **Step 0-U** (UPDATE entry) and **Step 0-P** (PUBLISH entry). Both `update_cms_content_variant` and `publish_content` act on a `managedContentVariantId`; every direct-entry path must validate + resolve the user-supplied identifier to one via a `content-readonly` read BEFORE touching the write tool. The read also confirms the record exists.

**Precondition:** the hard identifier gate in Step 0-U / 0-P has already run. This resolution only executes once an identifier is in hand (session registry, or a user-typed value). The name-only / no-identifier case is STOPPED at the gate — never search the org to turn a name into an ID.

## Classify by prefix, pick the read tool

| Prefix | Identifier | Validate + resolve with | Yields |
|--------|-----------|-------------------------|--------|
| `9Ps` | `managedContentVariantId` | `get_content_variant` — param `variantId` (pattern `^(9Ps)\w*`) | the same `managedContentVariantId` (confirmed to exist) |
| `MC…` | content key | `get_content` — accepts a content key | the record's `managedContentVariantId` |
| `20Y…` | `managedContentId` | `get_content` — accepts an ID | the record's `managedContentVariantId` |

Both read tools live on `content-readonly`. `get_content` does **not** accept a variant ID — a `9Ps` value MUST go to `get_content_variant`, never `get_content` (sending a `9Ps` to `get_content` returns `INVALID_ID_FIELD`). Both reads return the variant's current field values and `contentBody` — retain that body (Step 0-U displays it before asking for edits).

## On the read result

- **Read fails** (`INVALID_ID_FIELD`, not-found, empty) → the ID is invalid. STOP and tell the user the identifier did not resolve; ask via `ask_user_tool` for a valid content key / `managedContentId` / `managedContentVariantId`. Do NOT edit or publish blindly.
- **`9Ps` fails its pattern, or the prefix matches none of the three rows** → unrecognized. Ask via `ask_user_tool` for a valid identifier; do NOT guess or dispatch.
- **Success** → take the `managedContentVariantId` (for `9Ps`, the ID the user gave, now confirmed valid) and continue: Step 0-U → Step 8c; Step 0-P → Step 9b.

## Hard rules

- **Never run SOQL / `sf data query`** to look one up — these reads are the only resolution path.
- If the required read tool is unavailable on this bridge, apply the No-drift STOP rule (Step 0).

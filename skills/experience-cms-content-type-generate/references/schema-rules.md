# Schema rules (validator truth)

The CMS deploy validator is the source of truth — not the per-type metaschemas.

## Bundle root (`schema.json`)

- **MUST include**: `"title"`, `"description"`, `"lightning:type": "lightning__objectType"`, `"lightning:mixinTypes": { "sfdc_cms:metadataContent": {} }`, `"properties"`, `"required"`, `"unevaluatedProperties": false` (root only — do NOT set `unevaluatedProperties` on individual field entries inside `properties`).
- **MUST NOT include**: `"$schema"` at root.

## Per-field rules

**Allowed top-level keys per field**: `title`, `description`, `lightning:type`, `lightning:uiOptions`, plus the type-specific keys in the table below. **Nothing else.**

**Forbidden top-level keys on any field** (validator rejects under `unevaluatedProperties: false`):
- `type` (the JSON Schema `"type": "string"` etc — never write it; `lightning:type` is the only type marker)
- `format` (e.g. `"format": "date"` on a date field)
- `default`
- Any other JSON Schema keyword not in this skill

**`lightning:uiOptions` rules (sharp edge — caused multi-attempt auto-fix loops):**
- If you write `lightning:uiOptions`, it **MUST** contain a non-empty `placeholderText` string. Empty `{}` fails validation with `placeholderText: is missing but it is required`.
- The default-minimal rule means: **omit `lightning:uiOptions` entirely** unless the user asked for placeholders. Do NOT write `"lightning:uiOptions": {}`.
- All-or-nothing: include `lightning:uiOptions` with a real `placeholderText`, or omit the key completely.

`lightning:uiOptions` (with a real `placeholderText`) is accepted on **every** type. The columns below are the *additional* type-specific keys allowed alongside `lightning:type`.

| `lightning:type` | Accepted keys |
|---|---|
| `lightning__textType` | `minLength`, `maxLength`, `lightning:textIndexed`, `lightning:localizable`, `enum`, `const` |
| `lightning__multilineTextType` | `minLength`, `maxLength`, `lightning:textIndexed`, `lightning:localizable` |
| `lightning__richTextType` | `minLength`, `maxLength`, `lightning:textIndexed`, `lightning:localizable` |
| `lightning__urlType` | `lightning:allowedUrlSchemes` (required), `lightning:localizable`, `readOnly` |
| `lightning__dateType` | `lightning:localizable` |
| `lightning__dateTimeType` | `lightning:localizable` |
| `lightning__booleanType` | (none) |
| `lightning__integerType` | `minimum`, `maximum`, `const` |
| `lightning__numberType` | `minimum`, `maximum`, `const` |
| `lightning__imageType` | (none — do NOT add `type`, `format`, or any other key) |

Default-minimal: only set type-specific keys when the user explicitly asks. The columns above are validator-accepted; they are not defaults to apply automatically.

## Validator quirks

- `lightning:mixinTypes` accepts ONLY `sfdc_cms:metadataContent`. Any other mixin fails.
- `enum` is only valid for `lightning__textType`.
- `required` referencing a missing property is not deploy-enforced — but keep it consistent.
- No `default` values anywhere — validator rejects them.

## Default-minimal rule (step 3a)

Do NOT add `lightning:textIndexed`, `lightning:localizable`, length/range bounds, `enum`, `const`, or `placeholderText` unless the user asked. Match the request, nothing more. The user can request additions in step 3b.

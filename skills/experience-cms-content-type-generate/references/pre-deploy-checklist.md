# Pre-deploy schema checklist (agent-internal)

Run this check between step 4 (write files) and step 5 (dry-run). Do NOT print to chat. Fix in place and re-check before dispatching step 5a. Following this on the first write avoids spending auto-fix attempts in step 6.

Verify against `references/schema-rules.md`:

**Root of `schema.json`**
- Has `title`, `description`, `lightning:type: "lightning__objectType"`, `lightning:mixinTypes: { "sfdc_cms:metadataContent": {} }` (nothing else in mixins), `properties`, `required`, `unevaluatedProperties: false`.
- Does NOT have `$schema` or `default` at root.

**Per field**
- Every `required` entry matches a `properties` key.
- Every field has a supported `lightning:type`.
- No bare `type`, `format`, or `default` keys.
- Type-specific keys match the per-field rules table in `references/schema-rules.md`.
- `lightning:uiOptions` is either omitted or has a non-empty `placeholderText` (never `{}`).
- `lightning__urlType` fields include `lightning:allowedUrlSchemes`.

**Naming**
- Folder name, meta-XML filename prefix, and `<masterLabel>` all match `<contentTypeName>`.
- All `apiName` property keys are camelCase.

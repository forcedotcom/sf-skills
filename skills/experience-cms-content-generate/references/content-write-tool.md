# `create_cms_content` — content-write MCP tool reference

The CMS content-creation capability is exposed as a tool on the `content-write` MCP server. The canonical tool id is `create_cms_content`; the underlying Connect API operation is `createManagedContent` → `POST /connect/cms/contents`. IDE-specific namespace prefixes vary (e.g. `mcp__content-write__create_cms_content` in some surfaces) — refer to it by capability and the canonical id, not by a single hardcoded full name.

## Authoritative source: the JSON input schema

The tool's prose description sometimes lists `contentBody` and `title` as required. **The JSON input schema is authoritative — the prose is not.** The schema declares only `contentType` and `contentSpaceOrFolderId` as required, and offers two mutually exclusive body channels (`prompt` xor `contentBody`).

**This skill uses the `prompt` channel exclusively for both `create_cms_content` and `update_cms_content_variant`.** The user's goal (create) or edit instruction (update) is passed to the tool as `prompt`; the tool's server-side pipeline (Vibes MC content pipeline) owns generation / edit application and schema validation. The agent generates only the `title` on the create path, and only re-emits `title` on the edit path when the edit clearly targets the title. This skill does not use `contentBody` on any dispatch. `update_cms_content_variant` accepts `prompt` and reads the existing `contentBody` for the target `variantId`; the server applies the edit and persists the result.

## Inputs

The tool accepts an `inputs` array; each element persists one content record. **This skill sends exactly ONE element per call** — for bulk creation of N items, it dispatches N separate `create_cms_content` calls in parallel, each carrying a 1-element `inputs` array. See "Dispatch policy" below.

## Dispatch policy — one call per item, parallel fan-out (HARD RULE)

For any N ≥ 1, dispatch N `create_cms_content` calls, each with a 1-element `inputs` array, all fanned out in parallel in a single turn. Enforced by SKILL.md Step 5b and detailed in `references/bulk-batching.md`.

**Why one call per item:**

- **Matches the server-side generation model.** Each `create_cms_content` runs the Vibes MC content pipeline for one record; 1:1 calls-to-records is how the pipeline is tuned.
- **Blast radius = 1.** A dropped connection loses exactly one record. Retry is trivial — the same 1-element payload, redispatched.
- **Trivial partial-failure handling.** Each call's success or failure is independent and known individually.
- **Simpler mental model.** No batch-size math, no balancing, no re-batching on retry.

**Anti-patterns:**

- Any `inputs` array with more than 1 element — violates the hard rule. Split into N parallel 1-element calls.
- Serialized calls (dispatch call 1, await, dispatch call 2, …) — defeats the parallelism this rule enables.
- Combining failed retries into a multi-item `inputs` array — retry each failed item as its own 1-element parallel call.

### Required per element

| Key | Type | Notes |
|-----|------|-------|
| `contentType` | string | Fully qualified type name. Standard: `sfdc_cms__article`. Custom: `<namespace>__<TypeName>`, e.g. `c__PressRelease`. The masterLabel is **not** accepted here. The FQN must come from the `experience-cms-content-type-generate` sibling — never copy from this doc. |
| `contentSpaceOrFolderId` | string | Salesforce ID of the target content space (workspace) or a folder within one. Org-specific — do not reuse across orgs. Always asked from the user (see SKILL.md Step 3). Never inferred from `ui-bundle.json` or any local file. |
| `title` | string | Agent-generated — reflects `[USER GOAL]`. |
| `prompt` | string | **The body channel this skill uses.** `[USER GOAL]` verbatim. The server-side pipeline generates and validates the body against the type's schema. Mutually exclusive with `contentBody`. |

### Body channel policy

This skill emits `prompt` only. `contentBody` (caller-supplied JSON body serialized to a string) is a valid tool input but is not used here — the server-side pipeline owns generation quality end-to-end.

**Mutual exclusion.** `prompt` and `contentBody` cannot both be set on the same `inputs[]` element. Sending both fails; sending neither fails.

### Optional per element

| Key | Type | When to set |
|-----|------|-------------|
| `urlName` | string | URL-friendly slug within the org. Set when you want a deterministic URL; default to lowercase-kebab-case derived from `title`. |
| `contentKey` | string | Specific content key to assign. The tool auto-generates one if omitted — prefer omission unless the user has a key in hand. |
| `externalId` | string | External-system correlation id. Pass through only when the user supplies it. |
| `apiName` | string | API name of the content. Rarely needed — let the tool pick a default. |

## Consuming the outcome from `experience-cms-content-type-generate`

The sibling skill returns a structured outcome. This skill consumes only `{ status, fqn, message }`. The sibling may also emit `schema`, but this skill ignores it — server-side generation does not need it. See SKILL.md Step 2b/2c for the routing table.

## Response shape

A successful call returns a nested object on the matching `outputs` element. Key fields the skill surfaces:

| Field | What it is |
|-------|------------|
| `managedContentId` | The record's primary id — pass this to any follow-up tooling. |
| `managedContentVersionId` | Version-specific id (a record may have multiple versions). |
| `managedContentVariantId` | Variant id (language/locale variant). |
| `contentKey` | Stable key the user references in URLs and other content. |
| `contentFqn` | Echo of the `contentType` FQN. |
| `title` | Final title. |
| `urlName` | Final url-friendly slug. |
| `contentSpace` | Object with `id` and `label` of the parent workspace. |
| `folder` | Object with `id` and `label` if a folder was used. |
| `createdBy`, `createdDate`, `lastModifiedBy`, `lastModifiedDate` | Standard audit fields. |
| `contentBody` | The persisted body (echoes back what was stored). |
| `contentVersion` | Version-related metadata. |

Optional fields are omitted when not applicable — do not assume every key is present.

## Out-of-scope siblings on `content-write`

The same MCP server exposes other tools — of these, `update_cms_content_variant` and `publish_content` are used by this skill (see SKILL.md Steps 8 and 9). The rest are out of scope:

| Tool id | What it does | Where it belongs |
|---------|--------------|------------------|
| `unpublish_content` | Unpublishes from channels | Out of scope |
| `clone_content` | Clones an existing record | Out of scope |
| `create_workspace` | Creates a content space | Out of scope (workspace tooling) |
| `update_workspace` | Updates a workspace | Out of scope |
| `update_workspace_channels` | Sets workspace channel mapping | Out of scope |
| `create_channel` | Creates a delivery channel | Out of scope |
| `update_channel` | Updates a channel | Out of scope |

If the user asks for any of these, exit this skill cleanly and point them at the appropriate tool or the CMS UI.

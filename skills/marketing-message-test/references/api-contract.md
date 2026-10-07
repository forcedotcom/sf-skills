# E360 Message Preview & Test-Send — API Contract

Full operation tables, request bodies, response-field rules, per-resource version floors, and the end-to-end recipe for all six E360 channels (Email, SMS, WhatsApp, Push, In-App, RCS). This is the detailed reference behind [../SKILL.md](../SKILL.md).

**Operations are referenced by their step id** (e.g. `preview-email-personalized`, `send-test-sms`, `sender-email-dkim-valid`). The exact instance-relative path for each step — the LWR-Apex or Connect REST address you actually call — is on that step's **Call** line in the skill's Operations Reference. Read the path there; the tables below give you the step id, verb category, and body shape.

## Two transports

| Purpose | Transport | Instance-relative path |
|---|---|---|
| Render preview · test send · sender lookups | **LWR Apex** | `lwr/apex/v68.0/…` (exact path on each step's **Call** line) |
| Managed content · data space · DMO · segment · profile | **Connect REST** | `services/data/vXX.0/…` (per-resource minimums below; v62.0+ covers every REST-derivation resource) |

**Call everything through `sf api request rest`, never `curl`.** The CLI attaches the org's bearer token internally — do **not** extract the org's access token (e.g. via `sf org display --json`) or put a token in a header, because that emits a live credential into tool output and your context. Pass the **instance-relative path** (no host); the CLI prepends the org's instance URL, and it accepts both transports (the LWR-Apex paths are not under `services/data/`, but the CLI does not restrict the path).

**One step is the exception** — `whatsapp-template-fetch` (Part 1, WhatsApp) is a headless **dispatch** route (`/headless/invoke/…`), invoked through the `dispatch` tool rather than `sf api request rest`. Every other operation in this reference uses `sf api request rest`.

```bash
# GET (default method)
sf api request rest '<instance-relative path from the step's Call line>' --target-org <org>

# POST with a flat JSON body (content-type: application/json is sent by default)
sf api request rest '<instance-relative path from the step's Call line>' --target-org <org> --method POST --body @body.json
#   --body @file.json  → read the body from a file (recommended for the flat payloads below)
#   --body '{"contentKey":"…"}'  → inline body, also fine for short payloads
```

**LWR Apex verb rule**: an operation's caching flag fixes its verb. Preview and test-send operations are **POST** (`--method POST`) with a flat JSON body whose keys are exactly the parameter names (no envelope). Sender/permission lookups are **GET** (default) with args packed into a single `methodParams` query param as a URL-encoded JSON string appended to the path; no-arg lookups omit it.

**Versions:**
- **LWR-Apex** — not version-gated (resolves down to ~v20.0); pin `v68.0` so the path carries a well-formed `vXX.0` segment (the examples use it consistently).
- **Connect REST** — real per-resource floors (noted at each call, v51–v62). Highest is `ssot/data-spaces` at **v62.0**, so **v62.0+** covers every REST-derivation resource; the rest are lower.

---

## Part 1 — Render a preview

LWR-Apex, all **POST**, body keys = parameter names. Read each operation's path from its **Call** line.

- **Unpersonalized** — content only, keyed by `contentKey` alone (plus `locale` for Email's locale variant).
- **Personalized** — rendered against one real recipient; needs `segmentId`, `recipientDataModelObjectName`, `contentKey`, `profileId`.

| Channel | Operation (step) | Body |
|---|---|---|
| Email | `preview-email-unpersonalized` | `{ contentKey }` |
| Email | `preview-email-unpersonalized-by-locale` | `{ contentKey, locale }` |
| Email | `preview-email-personalized` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, isContentBlock, recipientAttributesJson }` |
| Email | `preview-email-personalized-by-locale` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, isContentBlock, locale, recipientAttributesJson }` |
| SMS | `preview-sms-unpersonalized` | `{ contentKey }` |
| SMS | `preview-sms-personalized` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, recipientAttributesJson }` |
| WhatsApp | `preview-whatsapp-unpersonalized` | `{ contentKey }` |
| WhatsApp | `preview-whatsapp-personalized` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, recipientAttributesJson }` |
| Push | `preview-push-unpersonalized` | `{ contentKey }` |
| Push | `preview-push-personalized` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId }` |
| In-App | `preview-inapp-unpersonalized` | `{ contentKey }` |
| In-App | `preview-inapp-personalized` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId }` |
| RCS | `preview-rcs-unpersonalized` | `{ contentKey }` |
| RCS | `preview-rcs-personalized` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, recipientAttributesJson }` |

Only Email has locale-variant operations (the `…-by-locale` steps) and carries the extra `isContentBlock` field.

**Example — Email personalized** (write the flat body to a file, then POST it against the `preview-email-personalized-by-locale` step's Call path):

```bash
cat > body.json <<'JSON'
{
  "segmentId": "1sgSG000000EXAMPLE",
  "recipientDataModelObjectName": "UnifiedIndividual__dlm",
  "contentKey": "MCKEXAMPLECONTENTKEY00000000",
  "profileId": "00000000000000000000000000000000",
  "isContentBlock": false,
  "locale": null,
  "recipientAttributesJson": null
}
JSON

sf api request rest '<preview-email-personalized-by-locale Call path>' \
  --target-org <org> --method POST --body @body.json
```

**Example — SMS unpersonalized (minimal, inline body, against the `preview-sms-unpersonalized` step's Call path):**

```bash
sf api request rest '<preview-sms-unpersonalized Call path>' \
  --target-org <org> --method POST --body '{ "contentKey": "MCKEXAMPLECONTENTKEY00000000" }'
```

### Reading rendered output per channel

- **Email** — flat JSON object of string fields (`subject`, `preheader`, `body`, `nonAggregateHtmlBody`, `textBody`, …). Rendered HTML is in `body` for personalized calls, `nonAggregateHtmlBody` for unpersonalized — **read `body` first, fall back to `nonAggregateHtmlBody`**.
- **SMS** — rendered message is the plain **`content`** string; MMS also carries **`mediaUrl`** and **`isLinkShorteningEnabled`**.
- **WhatsApp** — returns `{ content, metadata }` where **both are JSON strings**. `content` is an ordered, positional list of parameter values per component. The template (with `{{1}} {{2}}` slots) is NOT in the preview response — fetch it (below) and reassemble.
- **Push / In-App / RCS** — read the returned rendered fields.

**Fetch media from the rendered `<img src>`, not the content definition.** Rendered srcs are public-CDN URLs (`…salesforce-experience.com/_scs/cms/<orgId>/<spaceId>/<fileHash>/<file>`) that fetch unauthenticated. The `contentBody` refs from §4.2 (`/cms/media/<mediaKey>?fileName=…&fileHash=…`) are session-gated — unauthenticated they return an HTML login page (HTTP 200, no error), not image bytes.

### WhatsApp — reconstructing the visible message text

Fetch the template via the **`whatsapp-template-fetch`** step. Unlike every other operation in this reference, this is **not** an `sf api request rest` call — it's a headless **dispatch** route (`/headless/invoke/…`, **GET**; inputs `templateId` + `wabaId`), so invoke it through the `dispatch` tool with the step's Call path and `templateId` + `wabaId` as query params. Both values come from the content body in §4.2 — content-body fields `wabaId` / `wabaTemplateId`, or parse `sfdc_cms:template.definition` = `@meta/{wabaId}/{lang}/{templateId}`; pass the `wabaTemplateId` value as the `templateId` input. Read the exact Call path from the Operations Reference:

```text
# whatsapp-template-fetch — a headless dispatch route (/headless/invoke/…), GET.
# NOT an `sf api request rest` call: /headless/invoke paths resolve to an invoke
# envelope on the platform, so route them through the dispatch tool, not the REST CLI.
#
#   dispatch  method=GET  path=<whatsapp-template-fetch Call path>
#             query params: { templateId, wabaId }
```

The **`json` field is HTML-entity-escaped** (`&quot;`) — unescape, then parse; it holds the Meta template definition. **Reassemble**: for each component, `{{k}}` is **1-indexed** into that same component's `parameters[]` from the preview `content`. Replace `{{k}}` with `parameters[k-1].text`. Match components by `type` (BODY↔body, HEADER↔header). A component with no placeholders (e.g. a static HEADER) is omitted from `content` — use its template `text` verbatim. Personalized preview yields final text; unpersonalized leaves mapping expressions in the slots.

---

## Part 2 — Send a test message

**Permission gate — check first, every time.** Before firing a test send, call the channel's permission check. LWR-Apex, all **GET**, no args, returns `Boolean`. If it returns `false`, surface a permission error and **stop** — do not attempt the send. Read each operation's path from its **Call** line.

| Channel | Operation (step) | Params | Returns |
|---|---|---|---|
| Email | `perm-can-send-test-email` | *(none)* | `Boolean` — `canUserSendTestEmail` |
| SMS | `perm-can-send-test-sms` | *(none)* | `Boolean` — `canUserSendTestSms` |
| Push | `perm-can-send-test-push` | *(none)* | `Boolean` — `canUserSendTestPush` |
| In-App | `perm-can-send-test-inapp` | *(none)* | `Boolean` — `canUserSendTestInApp` |
| RCS | `perm-can-send-test-rcs` | *(none)* | `Boolean` — `canUserSendTestRcs` |

Then the send itself — LWR-Apex, all **POST**. Email returns a `Map`; others return a `String` result id. Read each operation's path from its **Call** line.

| Channel | Operation (step) | Body |
|---|---|---|
| Email | `send-test-email` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, fromAddress, toAddresses }` |
| Email | `send-test-email-by-locale` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, fromAddress, toAddresses, locale, recipientAttributesJson }` |
| SMS | `send-test-sms` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, senderId, toPhoneNumbers, recipientAttributesJson }` |
| WhatsApp | `send-test-whatsapp` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, senderId, toPhoneNumbers, recipientAttributesJson }` |
| Push | `send-test-push` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, senderId, toIndividualIds }` |
| In-App | `send-test-inapp` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, senderId, toIndividualIds }` |
| RCS | `send-test-rcs` | `{ segmentId, recipientDataModelObjectName, contentKey, profileId, senderId, toPhoneNumbers, recipientAttributesJson }` |

- **Destination field differs by channel**: Email → `toAddresses`, SMS/WhatsApp/RCS → `toPhoneNumbers`, Push/In-App → `toIndividualIds`. All are JSON string arrays — the tester's own destinations, supplied by the user, never derived.
- **`fromAddress` (Email) / `senderId` (everyone else)** identify the sending identity — derive via Part 3.
- Core message inputs (`segmentId`, `recipientDataModelObjectName`, `contentKey`, `profileId`) are identical to the personalized-preview inputs — derive once, reuse.
- **A test send is a real send.** Only call these when the user explicitly asked to test-send and supplied their own destinations.

---

## Part 3 — Sender / from-address inputs (test send only)

LWR-Apex, all **GET** — args via `methodParams`, or omit for no-arg. Read each operation's path from its **Call** line.

| Channel | Operation (step) | Params | Returns |
|---|---|---|---|
| Email | `sender-email-from-addresses` | *(none)* | available from-addresses → pick one for `fromAddress` |
| Email | `sender-email-dkim-valid` | `{ fromAddress }` | `Boolean` — validate before sending |
| SMS | `sender-sms-codes` | *(none)* | sender codes → pick `senderId` |
| RCS | `sender-rcs-agents` | *(none)* | RCS agents → pick `senderId` |
| WhatsApp | `sender-whatsapp-numbers` | *(none)* | WhatsApp numbers → pick `senderId` |
| WhatsApp | `sender-whatsapp-waba-ids` | *(none)* | WABA ids/names |

```bash
# list SMS sender codes (no-arg → no methodParams) — against the sender-sms-codes step's Call path
sf api request rest '<sender-sms-codes Call path>' --target-org <org>

# validate an Email from-address (step sender-email-dkim-valid) — methodParams is a URL-encoded
# JSON string appended to the path as ?methodParams=… (there is no --data-urlencode; encode it
# into the query string). Here {"fromAddress":"noreply@example.com"} encodes to
# %7B%22fromAddress%22%3A%22noreply%40example.com%22%7D
sf api request rest '<sender-email-dkim-valid Call path>?methodParams=%7B%22fromAddress%22%3A%22noreply%40example.com%22%7D' \
  --target-org <org>
```

Preview needs **no** sender — skip Part 3 unless test-sending. On Business-Unit-enabled orgs, sender lists are scoped by BU — use the Business-Unit-scoped variants of these lookups and pass `businessUnitId` (§4.7).

---

## Part 4 — Deriving the inputs

Everything above needs, at most, these values, all chained from the **`contentKey`**.

| Input | Required for | Where it comes from |
|---|---|---|
| `contentKey` | every call | given (the message you're previewing) |
| `locale` | Email `…-by-locale` | caller (`null` = default) |
| `recipientDataModelObjectName` (DMO) | personalized / send | parsed from the content (§4.3) |
| `segmentId` | personalized / send | segment list (§4.5) |
| `profileId` | personalized / send | segment member (§4.6) — must be a member of `segmentId` |
| `isContentBlock` | Email personalized | caller flag (`false` default) |
| `recipientAttributesJson` | Email, SMS, WhatsApp, RCS personalized / send | caller (`null` default); not Push/In-App |

### 4.1 `contentKey` — the seed

Identifies the authored message. Given up front; not derivable. Everything below flows from it.

### 4.2 Fetch the managed content

Use the CMS **Authoring** API — keyed directly by `contentKey`, returns drafts (what preview renders):

```bash
# GET /connect/cms/contents/{contentKeyOrId} — v57+  (step cms-content-fetch)
sf api request rest \
  'services/data/vXX.0/connect/cms/contents/{contentKeyOrId}' \
  --target-org <org>
```

Accepts either `contentKey` or the `20Y…` managed-content id. Optional query params `language`, `version`, `variantVersion`, `contentVersion`. Response carries `contentKey`, `managedContentId`, `contentBody`.

### 4.3 Determine the recipient DMO → `recipientDataModelObjectName`

Resolve the DMO **first** — the data space (§4.4) is derived from its name. Read it from `contentBody['lightning:dataProviders']` (from §4.2):
- a provider with `attributes.objectApiName` → that value **is** the DMO;
- a provider with `attributes.dataGraphApiName` → resolve the graph's primary object via
  `GET /services/data/vXX.0/ssot/data-graphs/{dataGraphApiName}` (v58+, step `data-graph-primary-object`) — read
  **`primaryObjectName`** (that is the DMO). The same response also carries
  **`dataspaceName`**, which you can use directly for §4.4 instead of deriving the data
  space from the DMO-name prefix. (The graph name goes in the **path**, not a query param —
  `?dataGraphApiName=`/`?dataGraphName=` both error `"Empty Data Graph Name"`.)

**Org fallback — content declares no DMO:** there is no name to derive a data space from, so pick the data space first (§4.4 — explicitly, or `default` on a single-space org), then call the org-fallback lookup (step `messaging-selected-uma-dmo`), an LWR-Apex **POST** with a flat body:

```bash
sf api request rest '<messaging-selected-uma-dmo Call path>' \
  --target-org <org> --method POST --body '{ "dataSpaceName": "<dataSpaceName>" }'
```

Returns the admin-configured Unified Individual DMO. Returns **`null`** if neither a Customer Engagement Data Graph nor an Identity Resolution ruleset is configured — treat as "no personalized preview available for this org," not a retryable error.

### 4.4 Identify the data space

```bash
# GET /ssot/data-spaces — v62+  (step data-spaces-list)
sf api request rest \
  'services/data/vXX.0/ssot/data-spaces' \
  --target-org <org>
```

Each entry has `name`, `label`, **`prefix`**. Use the matching entry's **`name`** as `dataspace`; `default` if the org has only one space. **Deterministic match from the DMO name** (§4.3):

- Begins with `ssot__` (e.g. `ssot__UnifiedIndividual__dlm`) → **`default`**, no lookup needed.
- Carries a recognized `<prefix>_` token (e.g. `EM1_UnifiedIndividual__dlm` → prefix `EM1`) — match against `/ssot/data-spaces`' `prefix` field and take the entry's `name`.
- No `ssot__` and no leading token matching any listed `prefix` (e.g. plain `UnifiedIndividual__dlm`) → **`default`** (the space with no `prefix`).

In the org-fallback case (§4.3, no DMO) there's no prefix to parse — pick the space explicitly, or `default` on a single-space org, **before** calling the fallback.

### 4.5 Pick a published segment → `segmentId`

```bash
# GET /ssot/segments — v55+  (step segments-list)
sf api request rest \
  'services/data/vXX.0/ssot/segments?dataspace=<dataSpaceName>' \
  --target-org <org>
```

Ask the user which segment to use and validate it has data. Keep the segment's **`apiName`** (fetches members, §4.6) and the `1sg…` **`marketSegmentId`** (the **`segmentId`** preview/send calls take).

### 4.6 Pick a recipient → `profileId`

Need one member of the chosen segment in the content's data space. **The recipient comes only from the segment's member list** — the `profileId` must be a member of the `segmentId` you pass to the render, or the render rejects it with an opaque error.

```bash
# segment members — GET /ssot/segments/{segmentApiName}/members — v58+  (step segment-members-list)
sf api request rest \
  'services/data/vXX.0/ssot/segments/{segmentApiName}/members?limit=10&dataspace=<dataSpaceName>' \
  --target-org <org>
```

- **The member `id` is your `profileId`.** Each row's profile key (e.g. `a1b2c3d4…` — **not** a `1sg…` segment id or a `003…` CRM id) is returned under **`id`**, and it is a member of the segment, so the render accepts it.
- **Empty member list → personalization cannot be performed.** An empty response (the segment has no members), or no segment in the content's data space, means there is no valid recipient: report `cannot personalize — no valid segment member` and stop. It is **not** a retryable error, and there is no fallback recipient source — do **not** list individuals from the DMO to manufacture a `profileId`; one that isn't a member of the passed `segmentId` is rejected by the render.
- The unpersonalized preview (`contentKey` only, §4.8/Part 5) does not need a recipient — offer it when personalization can't be performed.

*(To confirm a specific `profileId` exists (step `profile-fetch-by-id`):* `GET /services/data/vXX.0/ssot/profile/{dmoName}/{profileId}?dataspace=<dataSpaceName>` *— 200 = confirmed.)*

### 4.7 Get `businessUnitId` (BU-enabled orgs, test send only)

```bash
# GET /connect/cms/spaces — v53+  (step cms-spaces-list)
sf api request rest \
  'services/data/vXX.0/connect/cms/spaces' \
  --target-org <org>
```

Match the entry whose `id` equals the content's `contentSpace.id` (from §4.2) and read its **`businessUnit.id`** → `businessUnitId`. Preview never needs it.

### 4.8 The remaining flags

- **`locale`** — `null` for default; a locale code (e.g. `en_US`) only to force one. Email `…-by-locale` only.
- **`isContentBlock`** (Email) — `false` for a full message, `true` for a reusable content block. Default `false`.
- **`recipientAttributesJson`** (Email, SMS, WhatsApp, RCS) — `null` unless specifying content variables (§4.9), serialized as a JSON string. Not accepted by Push/In-App.

### 4.9 Content variables — you must supply values

Content variables (e.g. `{{$content.Input}}`) are author-left blanks with no data behind them — they render empty unless you pass a value. Find them under **`sfdc_cms:schema.properties`** in the content (§4.2); each key is one variable. Get a value for each **before** previewing (ask the user; don't invent one), and supply via `recipientAttributesJson` (Email, SMS, WhatsApp, RCS) as a JSON **string**: `"{\"$content\": { \"<variable>\": <value>, … }}"`.

**Push and In-App personalized previews do not support content variables.** If any are declared in the content definition for one of those channels, inform the user it's not supported — do not troubleshoot.

---

## Part 5 — End-to-end recipe

**Personalized preview, given only `contentKey`:**

1. `GET /connect/cms/contents/{contentKey}` (v57+, step `cms-content-fetch`) → `managedContentId`, `contentBody`.
2. Parse `contentBody` → **DMO** (`objectApiName` / `dataGraphApiName`, §4.3). If the content declares none, leave it for step 3's fallback.
3. **dataSpaceName** (§4.4) — scopes every `/ssot/…` call below. DMO declared: derive it from the DMO name via `GET /ssot/data-spaces` (step `data-spaces-list`). No DMO declared: pick the space explicitly (or `default` on a single-space org), then call the org-fallback lookup (step `messaging-selected-uma-dmo`) with `{ dataSpaceName }` → **DMO** (`null` → no personalized preview available for this org).
4. `GET /ssot/segments?dataspace={dataSpaceName}` (step `segments-list`) → pick a segment; keep `segmentApiName` and `1sg…` id (**segmentId**).
5. Get **profileId** from the segment's members (§4.6, the only valid source): `GET /ssot/segments/{segmentApiName}/members?limit=10&dataspace={dataSpaceName}` (step `segment-members-list`) → member `id`. If the member list is empty (or no segment exists in the data space), **stop** — report `cannot personalize — no valid segment member` and offer the unpersonalized preview; the `profileId` must be a member of the segment, so there is no fallback recipient source.
6. Call the channel's personalized-preview operation (step `preview-<channel>-personalized`, or the `…-by-locale` variant) with `{ segmentId, recipientDataModelObjectName, contentKey, profileId, … }`.

**Unpersonalized preview** short-circuits after step 1: call the channel's unpersonalized-preview operation (step `preview-<channel>-unpersonalized`) with `{ contentKey }` (add `locale` for Email's locale variant).

**Test send** = the channel's permission check (step `perm-can-send-test-<channel>`, Part 2; stop if `false`), then steps 1–6, then a Part 3 sender lookup for `fromAddress`/`senderId`, then the channel's test-send operation (step `send-test-<channel>`) with your supplied destination array.

---

## Field glossary

| Field | Type | Meaning |
|---|---|---|
| `contentKey` | String | Identifier of the authored message. Keys every preview/send call. |
| `managedContentId` | String | The content's record id (`20Y…`). Returned alongside `contentKey`. |
| `dataSpaceName` | String | Data Cloud data space name; the `dataspace` query param scoping the `/ssot/…` lookups. Must match the content. |
| `recipientDataModelObjectName` | String | The **table** — the DMO the recipient is looked up in, e.g. `UnifiedIndividual__dlm`. |
| `segmentId` | String | The segment **record** id (`1sg…`) passed to preview/send. |
| `segmentApiName` | String | The segment **developer** name used to fetch members over REST. |
| `profileId` | String | The **person** — a Data Cloud profile key, **not** a CRM id. |
| `isContentBlock` | Boolean | Email only — reusable content block vs. full message. |
| `locale` | String | Email `…-by-locale` only — locale override; `null` = default. |
| `recipientAttributesJson` | String | Email, SMS, WhatsApp, RCS — JSON string of content-variable overrides; `null` = none. Not Push/In-App. |
| `fromAddress` / `senderId` | String | Sending identity for a test send (Email vs. all other channels). |
| `toAddresses` / `toPhoneNumbers` / `toIndividualIds` | String[] | Your tester's own destinations for a test send (channel-dependent). |

**The identifier trio**: `segmentId` (`1sg…`) = *which audience*; `recipientDataModelObjectName` (`…__dlm`) = *which table the members live in*; `profileId` (profile key) = *which person*. DMO + `profileId` together identify one individual — neither alone suffices.

## Version floors (verified on a v69.0 org)

LWR-Apex not gated (works to v20; pin `v68.0` so the path segment is well-formed). REST derivation resources: `/connect/cms/spaces` v53, segments v55, contents v57, members v58, data-graphs v58, data-spaces v62; profile v51 (docs) but requires a `filters=[field=value]` param. Highest REST floor is data-spaces at v62 — target **v62.0+** for full six-channel coverage (this is why `minApiVersion` is `62.0`).

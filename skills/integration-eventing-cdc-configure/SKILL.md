---
name: integration-eventing-cdc-configure
description: "Use to enable Salesforce Change Data Capture (CDC) on a standard or custom object, configure a custom event channel, set a filter expression, or add enrichment fields. TRIGGER broadly on any of: 'enable CDC', 'enable Change Data Capture', 'turn on CDC', 'subscribe X to change events', 'only emit events for', 'filter change events', 'enrich change events', 'create a custom event channel'; or any mention of CDC, change events, PlatformEventChannel, PlatformEventChannelMember, EnrichedField, ChangeEvents channel, enrichment fields, change event filter; or when the user wants a downstream system to receive Salesforce data changes; or when the user touches .platformEventChannelMember-meta.xml / .platformEventChannel-meta.xml files. SKIP when publishing platform events, Pub/Sub API or REST/SOAP (use integration-connectivity-generate), or ManagedEventSubscription (out of scope for CDC). Always use this skill for CDC channel-membership metadata."
metadata:
  version: "1.0"
---

# Managing Change Data Capture Enablement

Generate the metadata that subscribes Salesforce objects to Change Data Capture: `PlatformEventChannelMember` files for the default `ChangeEvents` channel or a custom channel, and `PlatformEventChannel` files for new custom channels. Covers enrichment fields, filter expressions, and the canonical naming and value formats that the Metadata API actually accepts (which differ from values that appear in many internal test fixtures and code-search hits).

## Scope

- **In scope**: Generating `PlatformEventChannelMember` and `PlatformEventChannel` metadata for CDC. Subscribing standard objects, custom objects, or both. Configuring enrichment fields. Configuring filter expressions. Defining custom data channels.
- **Out of scope**: Publishing custom platform events (PE) — that's a different metadata type (`PlatformEvent`). Pub/Sub API or external Kafka/Bayeux configuration. Pricing/limits guidance — refer the user to the [CDC Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.change_data_capture.meta/change_data_capture/). Programmatic event-bus subscribers in Apex.

---

## Clarifying Questions

Before generating, confirm with the user if not already clear:

- Which entity (or entities) need CDC enablement? Standard, custom, or both?
- Default channel (`ChangeEvents`) or a custom channel? If custom, what's the channel label?
- Any enrichment fields needed? (Lookup IDs that the consumer needs even when they didn't change.)
- Any filter expression needed? (A SOQL-WHERE-clause body that gates which change events emit.)

---

## Required Inputs

Gather or infer before proceeding:

- **Source entity API name(s)** — e.g. `Account`, `Lead`, `Order__c`. The skill internally translates this to the **ChangeEvent entity name** (see Workflow step 2).
- **Channel** — either `ChangeEvents` (default) or the developer name of a custom channel ending in `__chn`.
- **Enrichment fields (optional)** — list of field API names on the source object whose values should be included in every change event.
- **Filter expression (optional)** — a predicate over fields on the change event payload (e.g. `Status__c != null`).

Defaults unless specified:
- Channel: `ChangeEvents` (the default CDC channel — no path prefix).
- Enrichment fields: none.
- Filter expression: none.

If the user provides a clear, complete request, generate immediately without unnecessary back-and-forth.

---

## Workflow

All steps are sequential. Do not skip or reorder.

**Before generating anything, know the only valid CDC metadata types:** CDC is expressed entirely through `PlatformEventChannelMember` (one per subscribed entity) and `PlatformEventChannel` (only for custom channels). Do NOT use `<ChangeDataCapture>`, `.changeDataCapture-meta.xml`, `changeDataCapture/` directories, `EnableChangeDataCapture`, or `ManagedEventSubscription` — these are not in scope for CDC. If you find yourself writing any of them, stop and use a `PlatformEventChannelMember` file instead.

1. **Identify the channel** — if the user names a custom channel, you'll generate a `PlatformEventChannel` file (see step 4). Otherwise use the literal value `ChangeEvents` for the default channel.

2. **Translate source entity to ChangeEvent entity name** — `<selectedEntity>` is the **ChangeEvent** type, NOT the source object:

   | Source object | `<selectedEntity>` value |
   |---|---|
   | `Account` | `AccountChangeEvent` |
   | `Lead` | `LeadChangeEvent` |
   | `Contact` | `ContactChangeEvent` |
   | `Order__c` (custom) | `Order__ChangeEvent` |
   | `MyThing__c` (custom) | `MyThing__ChangeEvent` |

   For standard objects: append `ChangeEvent`. For custom objects: replace the trailing `__c` with `__ChangeEvent` (the double-underscore is preserved).

3. **Generate the channel-member file** — one file per `(entity, channel)` pair. **The filename and fullName always use a SINGLE underscore between the entity stem and `ChangeEvent`** — this is independent of how `selectedEntity` is formatted in the XML body. For custom objects, drop the `__c` from the source name when forming the filename:

   | Source object | Filename (and fullName) | `<selectedEntity>` (in XML) |
   |---|---|---|
   | `Account` | `Account_ChangeEvent.platformEventChannelMember-meta.xml` | `AccountChangeEvent` |
   | `Lead` | `Lead_ChangeEvent.platformEventChannelMember-meta.xml` | `LeadChangeEvent` |
   | `Order__c` | `Order_ChangeEvent.platformEventChannelMember-meta.xml` (NOT `Order__ChangeEvent`) | `Order__ChangeEvent` |
   | `MyThing__c` | `MyThing_ChangeEvent.platformEventChannelMember-meta.xml` (NOT `MyThing__ChangeEvent`) | `MyThing__ChangeEvent` |

   The custom-object case is the easiest place to slip — the filename uses single underscore, the `selectedEntity` keeps its double underscore. Read `assets/PlatformEventChannelMember-template.xml` as the structural template.

4. **For a custom channel**, generate a `PlatformEventChannel` file — required if any member references a non-default channel. Derive a DeveloperName from the user's label: strip spaces and non-alphanumeric characters, convert to CamelCase, then **always** append the literal suffix `__chn`. The filename and the channel's `<eventChannel>` reference must use this exact form, otherwise the deploy fails with `Invalid channel name`:

   | User says | DeveloperName | Filename |
   |---|---|---|
   | `Partner Sync` | `PartnerSync__chn` | `PartnerSync__chn.platformEventChannel-meta.xml` (NOT `Partner_Sync...` or `PartnerSync...`) |
   | `Order Updates` | `OrderUpdates__chn` | `OrderUpdates__chn.platformEventChannel-meta.xml` |
   | `data sync` | `DataSync__chn` | `DataSync__chn.platformEventChannel-meta.xml` |

   Members on this channel reference it by the same DeveloperName: `<eventChannel>PartnerSync__chn</eventChannel>`. Read `assets/PlatformEventChannel-template.xml`.

5. **Add enrichment fields** if requested — repeat the `<enrichedFields><name>FIELD_API_NAME</name></enrichedFields>` block for each field. The name must be a **single-hop API name on the source entity** — verified working with: standard lookup IDs (`OwnerId`, `ParentId`), custom lookup fields (`MyLookup__c`), and custom non-relationship fields (`Region__c`, `Status__c`). Relationship traversals like `Owner.Name` or `Parent.Account.Industry` are rejected by deploy with "The selected field, X.Y, isn't valid".

6. **Add a filter expression** if requested — wrap the predicate in `<filterExpression>...</filterExpression>`. The body is a WHERE-clause body without the `WHERE` keyword (e.g. `Status__c != null`, not `WHERE Status__c != null`). For supported operators, field types, and pitfalls, read `references/filter-expressions.md`.

---

## Rules / Constraints

| Constraint | Rationale |
|---|---|
| `<selectedEntity>` is the ChangeEvent type name, not the source object name | The Metadata API binds the member to a ChangeEvent entity — passing `Account` directly fails with "invalid event in selectedEntity". |
| Member fullName uses **single** underscore: `Account_ChangeEvent` | The double-underscore form (`Account__ChangeEvent`) is parsed as `<namespace>__<name>` and rejected: "Cannot create a new component with the namespace: Account". |
| Default channel value is exactly `ChangeEvents` — no path prefix | Older fixtures and some docs show `data/ChangeEvents`; the deploy returns "Unable to find the specified channel" for that value. |
| Enrichment field names are single-hop API names on the source entity | Standard (`OwnerId`), custom lookup (`MyLookup__c`), and custom non-relationship (`Region__c`) all validate. Traversals like `Owner.Name` are rejected: "The selected field, X.Y, isn't valid". |
| `<filterExpression>` body has no `WHERE` keyword | Deploy returns "filter expression has syntax errors: unexpected token: 'WHERE'". |
| Filter cannot reference `IsDeleted` or do relationship traversal (`Owner.Username`) | Deploy rejects with "field is invalid". |
| DateTime fields support **only equality** in filters (`=`, `!=`) — not `<` / `>` | Deploy returns "Only equality operators are supported for this field type or value". Use a named date literal: `LastModifiedDate = TODAY`. |
| Filter RHS must be a literal — no field-to-field comparison | `BillingCity = ShippingCity` returns "unexpected token: 'ShippingCity'". |
| Compound fields (e.g. `BillingAddress`) require dotted component access in filter | `BillingAddress.City = 'X'` deploys; flat `BillingCity` is rejected as "field is invalid"; raw `BillingAddress` is rejected as "has to be used with a component field". Note this is the OPPOSITE of `<enrichedFields>`, which uses flat names. |
| Custom channel filename ends with `__chn` before the meta-xml suffix | Salesforce's MDAPI naming convention; mismatch causes deploy ambiguity. |
| Custom channel XML must include `<channelType>data</channelType>` | Without `data`, the channel is rejected for CDC (other types exist for streaming/event channels). |
| Source custom objects must already exist (or be deployed in the same transaction) | The ChangeEvent entity for `Foo__c` doesn't exist until `Foo__c` does; member deploy fails otherwise. |
| Never generate a `PlatformEventChannel` file for the default `ChangeEvents` channel | The default channel is system-provided. Reference it via `<eventChannel>ChangeEvents</eventChannel>` on members, but only custom (`__chn`) channels need a channel-meta file. |
| `PlatformEventChannelMember` accepts ONLY four elements: `<enrichedFields>`, `<eventChannel>`, `<filterExpression>`, `<selectedEntity>` | Adding `<description>`, `<isActive>`, `<masterLabel>`, or any other element fails XML schema validation: "Element {...} invalid at this location". Stick to the four documented elements. |
| `PlatformEventChannel` accepts ONLY two elements: `<channelType>` and `<label>` | Adding `<masterLabel>`, `<description>`, etc. produces "Element {...}masterLabel invalid at this location in type PlatformEventChannel". Use `<label>`, not `<masterLabel>`. |
| Generated metadata files only — never run `sf project deploy start` from this skill | This skill produces artifacts; deployment is a separate lifecycle concern. |

---

## Gotchas

| Issue | Resolution |
|---|---|
| `Unable to find the specified channel` | Set `<eventChannel>ChangeEvents</eventChannel>` (no `data/` prefix). |
| `The PlatformEventChannelMember can't be created because it references an invalid event in the "selectedEntity" field` | Use the ChangeEvent name, not the source object: `AccountChangeEvent`, not `Account`. |
| `Cannot create a new component with the namespace: <Object>` | Rename the file to use a single underscore: `Account_ChangeEvent...`, not `Account__ChangeEvent...`. |
| `The selected field, X.Y, isn't valid` (in `<enrichedFields>`) | Replace `Owner.Name` with `OwnerId`. CDC enriches the lookup automatically; only single-hop field API names validate. |
| `filter expression has syntax errors: unexpected token: 'WHERE'` | Remove the `WHERE` keyword. The body is the predicate only. |
| `The BillingCity field in the filter expression is invalid` (or any flat Address component) | Use the compound dotted form: `BillingAddress.City`, not `BillingCity`. See `references/filter-expressions.md` for the full compound-field matrix. |
| Custom-object member fails with "ChangeEvent doesn't exist" | The source object isn't deployed yet. Ensure the `Foo__c` object metadata is in the same deploy or already in the org. |
| `DUPLICATE_VALUE` on second deploy | The member is already subscribed. Either delete first or skip — CDC doesn't support upsert on members directly. |
| `sf infra error (TypeInferenceError, DeployMetadata): Could not infer a metadata type` for a `.changeDataCapture-meta.xml` file | That file extension and metadata type don't exist. Replace the `changeDataCapture/<Entity>.changeDataCapture-meta.xml` file with a `platformEventChannelMembers/<Entity>_ChangeEvent.platformEventChannelMember-meta.xml` file. |
| User says "subscribe Order__c" but means standard `Order` | Confirm — `OrderChangeEvent` (standard) and `Order__ChangeEvent` (custom) are different entities. |

---

## Output Expectations

Deliverables:
- One `force-app/.../platformEventChannelMembers/<Entity>_ChangeEvent.platformEventChannelMember-meta.xml` per subscribed entity.
- One `force-app/.../platformEventChannels/<DevName>__chn.platformEventChannel-meta.xml` per custom channel (if any).

File structure follows the templates in `assets/`.

After receiving the generated files, the user can verify them with `sf project deploy start --dry-run -d <path> --target-org <alias>` before deploying. If a dry-run surfaces an unfamiliar error, `references/deploy-troubleshooting.md` maps the common deploy errors to their metadata-side fixes.

---

## Cross-Skill Integration

| Need | Delegate to |
|---|---|
| Generate the source custom object | `platform-custom-object-generate` skill |
| Generate custom fields referenced by enrichment or filter | `platform-custom-field-generate` skill |
| Build a permission set for users who consume change events | `platform-permission-set-generate` skill |

---

## Reference File Index

| File | When to read |
|---|---|
| `assets/PlatformEventChannelMember-template.xml` | Step 3 — starting structure for a channel member |
| `assets/PlatformEventChannel-template.xml` | Step 4 — starting structure for a custom channel |
| `references/filter-expressions.md` | Step 6 — for the supported operators and field-type matrix when writing a filter expression |
| `references/deploy-troubleshooting.md` | When a user reports a dry-run deploy error and asks for help diagnosing it |

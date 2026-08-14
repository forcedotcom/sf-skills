# Example: list payload fields, discovered from the IA describe

A complete walkthrough for the two **list** shapes where an Invocable Action output resolves to a list
of another Apex class — a **top-level list** (`maxOccurs > 1`) and a **list nested inside a wrapper
object** (the describe returns one `maxOccurs: 1` `apexClass` output and hides the interior list).
**The Invocable Action (IA) describe is the source of truth**; the Apex class is read only to enumerate
a referenced class's own fields (and to find lists the describe does not surface). The **single
nested-object** shape (`maxOccurs: 1`, no list) is the companion example
`nested-object-single-source-prompt.md`. Read `references/mcp-tool-output-discovery.md`
("Nested-object and list payload fields") and `references/two-clt-modeling.md` ("Top-level list vs
list-inside-wrapper") first.

> **The skill never modifies the Apex.** The describe's `apexClass` + `maxOccurs` tell you the shape;
> reading the referenced class is a read-only enumeration step, not a reshape. There is no case that
> requires adding a wrapper class or changing a return type — a top-level list binds directly.

---

## Case A — top-level list output (`maxOccurs > 1`)

The describe surfaces the **list itself** as an output with `maxOccurs > 1`. The `GetLeadsList` action
returns a list of lead summaries plus a count.

### Phase 2 — Payload discovery (from the describe)

```jsonc
// GET /services/data/v67.0/actions/custom/apex/GetLeadsList  →  .outputs[]
[
  { "name": "leadCount", "type": "INTEGER", "maxOccurs": 1 },
  { "name": "leads",     "type": null, "apexClass": "GetLeadsList$LeadSummary", "maxOccurs": 2000 },
  { "name": "status",    "type": "STRING",  "maxOccurs": 1 }
]
```

- `leads`: `type: null` + `apexClass` set + **`maxOccurs: 2000` (> 1)** = a **top-level list**
  output whose element type is `GetLeadsList$LeadSummary`. Do NOT ignore it because it is a list.
- Read `GetLeadsList.LeadSummary` to enumerate the row leaves (`name`, `company`, `status`, `email`,
  `phone`).
- `leadCount`, `status` are top-level scalars (rendered alongside the list).

### Modeling

- **Response CLT** `getLeadsListResponse` — type the list property **directly** as the element class;
  the CLT never carries a `lightning__listType`/`items` (rejected by the CLT metaschema):

  ```json
  {
    "type": "object",
    "lightning:type": "lightning__objectType",
    "lightning:tags": ["mcp"],
    "unevaluatedProperties": false,
    "properties": {
      "leadCount": { "title": "Lead Count", "lightning:type": "lightning__integerType" },
      "leads":     { "title": "Leads", "lightning:type": "@apexClassType/c__GetLeadsList$LeadSummary" },
      "status":    { "title": "Status", "lightning:type": "lightning__textType" }
    }
  }
  ```

- **Widget** `getLeadsListWidget` — the list surfaces here as a `lightning__listType` property with
  an `items.lightning:type` of `@apexClassType/c__GetLeadsList$LeadSummary`; the body iterates it with
  `forEach`/`forItem` (`{!$item.name}`, …) or a `tile/table` `rows`.

- **Envelope renderer** — bind the top-level list at **two segments**, scalars likewise:

  ```json
  {
    "renderer": {
      "componentOverrides": {
        "$": {
          "definition": "@widget/c/getLeadsListWidget",
          "attributes": {
            "leadCount": "{!$attrs.outputValues.leadCount}",
            "leads":     "{!$attrs.outputValues.leads}"
          }
        }
      }
    }
  }
  ```

This shape binds and renders with no wrapper class, no `List<Wrapper>` return-type change, and no Apex
edit of any kind.

---

## Case B — list nested inside a wrapper object (describe does NOT surface it)

When the describe returns ONE `apexClass` output with `maxOccurs: 1`, the list is a field **inside**
that class and the describe never shows it — the only way to find it is to read the wrapper class.

### Phase 2 — Payload discovery

```jsonc
// GET /services/data/v67.0/actions/custom/apex/GetShipmentDetails  →  .outputs[]
[
  { "name": "shipmentDetailsResponse", "type": null,
    "apexClass": "GetShipmentDetails$GetShipmentDetailsResponse", "maxOccurs": 1 }
]
```

- One output, `maxOccurs: 1` → a single wrapper object. Read
  `GetShipmentDetails.GetShipmentDetailsResponse` to enumerate its fields. One of them is
  `List<StatusUpdateResponse> statusUpdates` — **a nested list the describe never surfaced.** You
  MUST read the inner class to find it, then recurse into `StatusUpdateResponse` for the row leaves
  (`id`, `status`, `location`, `notes`, `updateTime`). **Never ignore such a property.**

The inner classes are annotated `@AuraEnabled`, **not** `@InvocableVariable` — a `grep '@InvocableVariable'`
here matches nothing and enumerates zero leaves (an empty CLT + widget). Enumerate the inner classes by
their public/`@AuraEnabled` members (per SKILL.md Hard Rule 6):

```apex
global class GetShipmentDetailsResponse {
    @AuraEnabled global String shipmentId;
    @AuraEnabled global String trackingNumber;
    @AuraEnabled global String carrierName;
    @AuraEnabled global String status;
    @AuraEnabled global Date   eta;
    @AuraEnabled global Decimal weight;
    @AuraEnabled global Integer pieceCount;
    @AuraEnabled global String origin;
    @AuraEnabled global String destination;
    @AuraEnabled global Decimal totalCharges;
    @AuraEnabled global List<StatusUpdateResponse> statusUpdates;   // nested list — not in the describe
}

global class StatusUpdateResponse {
    @AuraEnabled global String   id;
    @AuraEnabled global String   status;
    @AuraEnabled global String   location;
    @AuraEnabled global String   notes;
    @AuraEnabled global Datetime updateTime;
}
```

(The top-level `@InvocableMethod` response wrapper is still `@InvocableVariable`-gated — that is what
lets the describe surface the one `shipmentDetailsResponse` output above. The split is by class role,
per SKILL.md Hard Rule 6.)

### Modeling

- **Response CLT** — one property `shipmentDetailsResponse` →
  `@apexClassType/c__GetShipmentDetails$GetShipmentDetailsResponse` (the wrapper class). The
  `statusUpdates` list is NOT a CLT property; it surfaces in the widget schema as a
  `lightning__listType` with `items.lightning:type` = `@apexClassType/c__GetShipmentDetails$StatusUpdateResponse`.
- **Renderer** — bind the list at **three segments**:
  `{!$attrs.outputValues.shipmentDetailsResponse.statusUpdates}`; scalar fields inside the wrapper
  bind `{!$attrs.outputValues.shipmentDetailsResponse.<leaf>}`.

---

## Notes

- **Binding depth = the list's position in the describe, never a transform.** Two segments for a
  top-level list output (Case A), three segments for a list inside a wrapper object (Case B). The
  skill reads the depth off the describe; it never reshapes the Apex to change it.
- **A response CLT list property is always a plain `@apexClassType/...` reference.** Typing it as
  `lightning__listType` + `items` is rejected by the CLT metaschema
  (*"You can't add the items property … because the `unevaluatedProperties` keyword value is set to
  false"*). `items`/`lightning__listType` belong to the **widget** schema only.
- **Never drop a list.** A `List<ApexClass>` field — whether a top-level output or nested inside a
  wrapper — is domain data and is always rendered. "List rendering not supported" / "out of scope"
  are not valid rationales; see the hard `nested-list-coverage` gate in `references/validation-gates.md`.

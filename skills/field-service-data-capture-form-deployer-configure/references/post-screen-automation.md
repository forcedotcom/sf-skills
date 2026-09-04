# Post-screen automation: decision → lookup → loop → createRecord

The Inventory_Transfer flow in the demo org shows the canonical "do something with the captured data" chain. After the last screen, the flow:

1. **Decides** which branch to take based on a Radio answer (Truck vs Work Order).
2. **Looks up** a record per branch (the truck Location for the user, or the WorkOrder).
3. **Stores** the resulting Id into a private variable (`Transfer_Destination`).
4. **Loops** over the Repeater's `AddedItems` collection.
5. **Creates** one Salesforce record per row, mapping the row's child-field values onto the target object.

This file documents the spec shape that drives that XML.

## Spec extension

Add a top-level `postScreen` block:

```json
{
  "formTitle": "Inventory Transfer",
  "formType": "Inventory",
  "screens": { ... },
  "postScreen": {
    "variables": [
      { "name": "Transfer_Destination", "type": "String" }
    ],
    "decision": {
      "name": "Transfer_Location_Decision",
      "label": "Transfer Location Decision",
      "defaultLabel": "Error",
      "branches": [
        {
          "name": "Truck_Decision",
          "label": "Truck",
          "when": { "field": "To", "operator": "EqualTo", "value": "Truck" },
          "then": "Get_Truck"
        },
        {
          "name": "Work_Order_Decision",
          "label": "Work Order",
          "when": { "field": "To", "operator": "EqualTo", "value": "Work Order" },
          "then": "Get_WO"
        }
      ]
    },
    "recordLookups": [
      {
        "name": "Get_Truck",
        "label": "Get Truck",
        "object": "Location",
        "filters": [
          { "field": "Service_Resource__c", "operator": "EqualTo", "valueRef": "$User.Id" }
        ],
        "outputAssignments": [
          { "assignTo": "Transfer_Destination", "field": "Id" }
        ],
        "next": "Part_Transfers"
      },
      {
        "name": "Get_WO",
        "label": "Get WO",
        "object": "WorkOrder",
        "filters": [
          { "field": "Id", "operator": "EqualTo", "valueRef": "Work_Order_Number.value" }
        ],
        "outputAssignments": [
          { "assignTo": "Transfer_Destination", "field": "LocationId" }
        ],
        "next": "Part_Transfers"
      }
    ],
    "loop": {
      "name": "Part_Transfers",
      "label": "Part Transfers",
      "collection": "Part.AddedItems",
      "next": "Transfer_Part"
    },
    "recordCreates": [
      {
        "name": "Transfer_Part",
        "label": "Transfer Part",
        "object": "ProductTransfer",
        "next": "Part_Transfers",
        "inputAssignments": [
          { "field": "DestinationLocationId", "valueRef": "Transfer_Destination" },
          { "field": "IsReceived", "boolean": true },
          { "field": "OwnerId", "valueRef": "$User.Id" },
          { "field": "Product2Id", "valueRef": "Part_Transfers.Part_Number.value" },
          { "field": "QuantityReceived", "valueRef": "Part_Transfers.Quantity.value" },
          { "field": "QuantitySent", "valueRef": "Part_Transfers.Quantity.value" },
          { "field": "ReceivedById", "valueRef": "$User.Id" }
        ]
      }
    ]
  }
}
```

## How the converter wires it up

When `postScreen` is present:

- The **last screen's connector** points to the decision's `name` (or, if no decision, the first lookup, or the loop, or the first recordCreate — whichever is first in the chain).
- The decision emits `<decisions>` with one `<rules>` per branch. Each rule's `connector` targets `then`. The `defaultConnectorLabel` becomes the catch-all branch label (no connector means the flow ends on the default path).
- Each `recordLookups` emits its filter list, output assignments, and a `connector` to its `next`.
- The `loop` emits `<loops>` with `collectionReference`, `nextValueConnector` to its `next`. The "no more items" path falls through (no connector).
- Each `recordCreates` emits its input assignments and a `connector` back to the loop (so iteration continues). The loop's "default" (after items finish) is what naturally terminates the flow.
- All non-input variables in `postScreen.variables` are emitted alongside the three required `parentObjectType` / `parentRecordId` / `recordId` variables.

## Spec → XML reference card

| Spec key | Emits |
|---|---|
| `valueRef` | `<elementReference>...</elementReference>` |
| `value` (string) | `<stringValue>...</stringValue>` |
| `boolean` | `<booleanValue>true|false</booleanValue>` |
| `number` | `<numberValue>...</numberValue>` |

Filter / decision-condition operators that have been seen in real flows: `EqualTo`, `NotEqualTo`, `GreaterThan`, `LessThan`, `IsNull`, `Contains`. The converter passes them through as-is — Salesforce will reject anything invalid.

## Limitations

- Only one decision, one loop, and one chain of lookups+creates per spec. Real flows can have many; that's not in scope here.
- No `assignments` element (the Inventory_Transfer flow uses `recordLookups` outputAssignments instead, which we replicate).
- No formula resources or text templates.
- No nested loops, no decisions inside loops.

If you need any of the above, deploy what the skill produces and finish wiring in Flow Builder.

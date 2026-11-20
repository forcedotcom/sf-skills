# Apex-Backed CLT as an Agentforce Action Output

## Overview

An Apex-backed Custom Lightning Type (`@apexClassType/c__<Payload>`) renders an Agentforce action's output only when the action exposes **an output property whose type is that Apex class**. The Output Rendering picker in Agent Builder offers a CLT per output property; it offers `c__<CLTName>` only for a property typed `@apexClassType/c__<Payload>` (or a list property whose items are that type). Primitive outputs (`Integer`, `Decimal`, `String`, ...) are only ever offered primitive renderers.

Neither the CLT deploy nor the `GenAiFunction` deploy checks this. A wrong shape deploys cleanly and then renders nothing — the agent shows plain text or the default renderer.

## How `@InvocableMethod` outputs are built

When `@InvocableMethod` returns `List<T>`, **each non-static `@InvocableVariable` field of `T` becomes a separate action output**. `T` itself is never an output, and fields of `T` without `@InvocableVariable` (for example `@AuraEnabled`-only fields) are dropped.

So returning the payload class directly does not work:

```apex
// BROKEN — outputs are `totalCount` (Integer) and `totalAmount` (Decimal); `opportunities` is lost.
public with sharing class OpportunityList {
    @InvocableVariable @AuraEnabled public Integer totalCount;
    @InvocableVariable @AuraEnabled public Decimal totalAmount;
    @AuraEnabled public List<Row> opportunities;

    @InvocableMethod(label='Get Opportunities')
    public static List<OpportunityList> getOpportunityList(List<Request> requests) { /* ... */ }
}
```

Adding `@InvocableVariable` to the payload's fields to fix a deploy error (`InvocableMethod methods do not support return type of List<X>`) produces exactly this broken shape.

## Required shape: wrapper Response

Keep the payload class as a plain data class and return a separate `Response` wrapper that has one `@InvocableVariable` **typed to the payload class**:

```apex
// Payload — the class the CLT points at. Fields are @AuraEnabled.
public with sharing class OpportunityList {
    @AuraEnabled public Integer totalCount;
    @AuraEnabled public Decimal totalAmount;
    @AuraEnabled public List<Row> opportunities;

    public class Row {
        @AuraEnabled public String name;
        @AuraEnabled public Decimal amount;
    }
}
```

```apex
// Action — separate class, returns the wrapper.
public with sharing class GetOpportunityListAction {
    public class Request {
        @InvocableVariable(required=true) public Id accountId;
    }

    public class Response {
        @InvocableVariable(label='Opportunity List') public OpportunityList result;
        @InvocableVariable public Boolean isSuccess;
        @InvocableVariable public String errorMessage;
    }

    @InvocableMethod(label='Get Opportunity List')
    public static List<Response> run(List<Request> requests) { /* ... */ }
}
```

CLT `schema.json`:

```json
{
  "title": "Opportunity List",
  "lightning:type": "@apexClassType/c__OpportunityList"
}
```

The action now has an output `result` typed `@apexClassType/c__OpportunityList`. In Agent Builder, choose the CLT as the Output Rendering for `result`; this sets the output property's `lightning:type` to `c__<CLTName>` in the `GenAiFunction` `output/schema.json`:

```json
"result": {
  "title": "result",
  "lightning:type": "c__OpportunityListType",
  "lightning:isPII": false,
  "copilotAction:isDisplayable": true,
  "copilotAction:isUsedByPlanner": true
}
```

## Rules

- At least one output must be typed to the CLT's Apex class. Status outputs alongside it (`isSuccess`, `errorMessage`) are fine.
- The payload may also be an inner class (`@apexClassType/c__Outer$Inner`).
- Payload fields may be `@AuraEnabled`, `@InvocableVariable`, or both; `@AuraEnabled`-only is the recommended form. Do **not** put `@InvocableMethod` on the payload class.
- For a list of records, the output can be `@InvocableVariable public List<Row> rows;` with the CLT on `@apexClassType/c__<Action>$Row`. The CLT then renders each item.
- A CLT can't be bound to the action output as a whole — only to one output property.
- Widget renditions go in the root `renderer.json` (`@widget/c/<name>`). `lightningDesktopGenAi/renderer.json` rejects `@widget` references.

## Diagnosing "the widget doesn't render"

1. Describe the action with REST `GET /services/data/v<NN>.0/actions/custom/apex/<ActionClass>` and check `outputs[]`. One entry must have `apexClass` equal to the CLT's class. If every output is a primitive, the Apex shape is wrong — apply the wrapper.
2. Check the picker candidates with REST `GET /services/data/v<NN>.0/connect/genAiCandidateTypes?esDataTypes=%40apexClassType%2Fc__<Payload>`. The response must list `c__<CLTName>`. If it doesn't, the CLT isn't deployed against that class, or the widget isn't deployed.
3. Check the `GenAiFunction` `output/schema.json`. The property typed to the class must have `"lightning:type": "c__<CLTName>"`.

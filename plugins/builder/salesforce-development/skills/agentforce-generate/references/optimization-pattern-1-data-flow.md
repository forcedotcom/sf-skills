# Optimization Pattern 1: Wire Required Outputs to Deterministic Consumers

Do not treat every `...` input as missing wiring. `...` is the correct binding
when the model should extract the latest value from the current turn or
conversation history.

## Detection Logic

Scan systematically across ALL subagents:

1. **Identify deterministic consumers**: Find later actions, guards, or
   transitions that require an exact machine value rather than conversational
   slot filling.

2. **Identify trusted producers**: Find the action output that establishes that
   exact value. Matching names or types alone are not proof of data flow.

3. **Check scope**: Persist the output only when the deterministic consumer runs
   after `@outputs` leaves scope. If the consumer should use the user's latest
   wording instead, keep `...`.

4. **Match the stored shape to the consumer**: If the later consumer needs the
   exact identifier, store that identifier. If it needs only a trusted
   complete/incomplete gate, store the trusted boolean outcome and leave a
   display-only receipt or identifier in the action result and surviving
   history. Do not persist a richer value merely because the action returns it.
   Match semantics as well as the declared primitive type: a scalar category is
   not a JSON record just because both are strings. Do not rename or store a
   partial output to disguise a producer/consumer contract gap. Surface the
   mismatch, or change the stub contract only when that change is approved.

## How to Fix

When an exact producer-consumer dependency is established, complete all three
steps:

### Step A — Variable Creation (MANDATORY)

Name the later deterministic consumer in the Agent Spec. Reuse an existing
single-purpose variable or add one with the producer's exact type and a default
value.

### Step B — Store Output (MANDATORY)

Add `set @variables.X = @outputs.Y` immediately after the producing action.

### Step C — Use Variable (MANDATORY)

Bind only the established deterministic consumer to `@variables.X`. Do not
replace unrelated conversational slot-filled inputs.

## Example

**Before:**
```agentscript
variables:
    customerId: linked string
        source: @MessagingSession.MessagingEndUserId

subagent OrderManagement:
    reasoning:
        instructions: ->
            | When updating an order status, first retrieve the order details, confirm the new status, then update it.
        actions:
            GetOrderDetails: @actions.GetOrderByNumber
                with customerId = @variables.customerId
                with orderNumber = ...
            UpdateStatus: @actions.UpdateOrderStatus
                with orderRecord = ...
                with status = ...
    actions:
        GetOrderByNumber:
            inputs:
                "customerId": string
                "orderNumber": string
            outputs:
                "orderRecord": object
        UpdateOrderStatus:
            inputs:
                "orderRecord": object
                "status": string
```

**After:**
```agentscript
variables:
    customerId: linked string
        source: @MessagingSession.MessagingEndUserId
    orderRecord: mutable object = None

subagent OrderManagement:
    reasoning:
        instructions: ->
            | When updating an order status, first retrieve the order details with {!@actions.GetOrderDetails}, confirm the new status, then update it with {!@actions.UpdateStatus}.
        actions:
            GetOrderDetails: @actions.GetOrderByNumber
                with customerId = @variables.customerId
                with orderNumber = ...
                set @variables.orderRecord = @outputs.orderRecord
            UpdateStatus: @actions.UpdateOrderStatus
                with orderRecord = @variables.orderRecord
                with status = ...
    actions:
        GetOrderByNumber:
            inputs:
                "customerId": string
                "orderNumber": string
            outputs:
                "orderRecord": object
        UpdateOrderStatus:
            inputs:
                "orderRecord": object
                "status": string
```

**Key improvements:**
1. Identified data producer: GetOrderByNumber has `outputs: "orderRecord"`
2. Identified data consumer: UpdateStatus has `...` placeholder for `orderRecord` input
3. Matched producer/consumer: "orderRecord" output matches "orderRecord" input
4. Wired only the proven exact data flow:
   - Step A: Created new variable `orderRecord: mutable object = None`
   - Step B: Added `set @variables.orderRecord = @outputs.orderRecord` after GetOrderDetails
   - Step C: Replaced `...` with `@variables.orderRecord` in UpdateStatus action

# Optimization Pattern 2: Extract Deterministic Logic from Natural Language

## Detection Logic

Scan instruction blocks for logic that may need deterministic enforcement:

1. **Material action ordering**: Instructions saying "first do X" or "do X
   before Y" where regulation, authorization, irreversible consequence, or an
   external protocol requires the order.

2. **Machine-known gates**: Authorization, confirmation, eligibility, and
   trusted action-result conditions that control tool visibility or routing.

3. **Post-action invariants**: Success/failure outcomes that must enable,
   disable, or route later execution.

Do not extract current intent, remembered preferences, question progress, or
other unstructured conversational judgment into mutable state merely because
it can be phrased as “if X.”

## How to Fix

Move requirement-backed procedural logic to explicit `if`, `run`, `set`,
`available when`, or `transition` constructs.

Create a mutable variable only when a named later deterministic consumer needs
an action output after `@outputs` leaves scope. Then:
1. Create a new mutable variable with matching type if it doesn't exist
2. Add `set @variables.X = @outputs.Y` to store the output
3. Use `@variables.X` only in that consumer

When the decision is immediate in the producing action's post-action scope, use
`@outputs.X` directly instead of copying it to state.

**Ordering**: Deterministic checks should happen BEFORE natural language instructions, not embedded within them.

## Example

**Before:**
```agentscript
subagent hotel_booking:
    reasoning:
        instructions: ->
            | If user is not known, always ask for their username and get their User record before making any booking. Help user check room availability with {!@actions.CheckAvailability}. If room is available, transition to payment.
        actions:
            IdentifyUserByUsername: @actions.identify_user_by_username
                with username = ...
            CheckAvailability: @actions.check_room_availability
                with roomType = ...
                with userRecord = ...
    actions:
        identify_user_by_username:
            description: "Get user tier"
            inputs:
                "username": string
            outputs:
                "userRecord": object
        check_room_availability:
            inputs:
                "roomType": string
                "userRecord": object
            outputs:
                "available": boolean
```

**After:**
```agentscript
variables:
    userRecord: mutable object = None

subagent hotel_booking:
    reasoning:
        instructions: ->
            if @variables.userRecord is None:
                | Ask for the username needed to identify the user, then use
                  {!@actions.IdentifyUserByUsername}.
            else:
                | Help the user check room availability with
                  {!@actions.CheckAvailability}.
        actions:
            IdentifyUserByUsername: @actions.identify_user_by_username
                with username = ...
                set @variables.userRecord = @outputs.userRecord
            CheckAvailability: @actions.check_room_availability
                with roomType = ...
                with userRecord = @variables.userRecord
                available when @variables.userRecord != None
                if @outputs.available == True:
                    transition to @subagent.payment
    actions:
        identify_user_by_username:
            description: "Get user tier"
            inputs:
                "username": string
            outputs:
                "userRecord": object
        check_room_availability:
            inputs:
                "roomType": string
                "userRecord": object
            outputs:
                "available": boolean
```

**Key improvements:**
- Persisted only `userRecord`, because the later availability action requires
  that exact identified record
- Kept username and room type as conversational slot-filled inputs
- Hid availability until identification succeeds
- Used immediate `@outputs.available` instead of duplicating it in a variable
- Kept natural-language instructions focused on the current user-facing task

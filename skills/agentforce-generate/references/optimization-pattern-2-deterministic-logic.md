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

4. **Exact comparisons in prompt text**: Instructions such as
   `If {!@variables.status} == "blocked"` that expose a runtime value but ask
   the model to perform a machine-known branch.

Do not extract current intent, remembered preferences, question progress, or
other unstructured conversational judgment into mutable state merely because
it can be phrased as “if X.”

## Decision Test

Put on the author's thinking hat; do not rewrite conditions mechanically.

- **Keep model-facing:** “If the user wants to speak with a human…” The model
  must interpret the user's intent from natural language.
- **Make deterministic when material:** “If account status equals blocked…”
  The runtime already knows the exact value and the branch must not drift.
- **Use mixed control when needed:** Let the model identify intent, but gate a
  consequential action with `available when` over trusted state.

Interpolation and determinism are separate decisions. A merge field gives the
model a value; it does not make the model's comparison or sequence reliable.

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

### Focused example

```agentscript
# BAD: exact runtime comparison delegated to the model
| If {!@variables.account_status} == "blocked", use account recovery.

# GOOD: runtime owns the exact comparison
if @variables.account_status == "blocked":
    | Help the customer recover access to the blocked account.

# ALSO GOOD: model owns semantic intent
| If the user asks to speak with a human, use
  {!@actions.escalate_to_support}.
```

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

# Optimization Pattern 3: Fix Variable and Action Reference Syntax

## Detection Logic

Scan all `reasoning.instructions` blocks for two categories of issues:

### 1. Incorrect reference syntax

- Model instructions require a stored value but contain bare `@variables.X`,
  which is only literal text
- Actions/tools mentioned by name without using `{!@actions.X}` syntax

### 2. Missing action references

- Scan all actions in `reasoning.actions` and their definitions in `actions:` section
- Identify what use case each action serves based on its name, description, inputs/outputs
- Check if `reasoning.instructions` mentions those use cases without explicit `{!@actions.X}` references
- Match phrases like "retrieve details", "get contact", "update status", "look up", "search for" to action names

## How to Fix

Classify each reference before editing:

1. If the model must read the current value, change bare `@variables.X` to
   `{!@variables.X}`.
2. If the text merely names an action parameter or state concept, keep it
   literal. For example, `Set next_destination to "self_service"` does not need
   the current value of `next_destination`.
3. If the text performs an exact comparison over a trusted value, do not stop
   at interpolation. Move the comparison into an AgentScript `if` when the
   branch must be deterministic.
4. Add `{!@actions.X}` when model instructions need to identify an available
   action by its use case.

Do not auto-fix every interpolation lint hint. The question is whether the
model needs the value, not whether a variable-like name appears in prose.

## Example

**Before:**
```agentscript
subagent CustomerService:
    reasoning:
        instructions: ->
            | Address user as @variables.userName. Help customers by looking up their account information and answering their questions.
        actions:
            GetAccount: @actions.GetCustomerAccount
                with email = @variables.customerEmail
            AnswerQuestion: @actions.AnswerWithKnowledge
                with query = ...
    actions:
        GetCustomerAccount:
            description: "Retrieves customer account details"
            inputs:
                "email": string
            outputs:
                "accountInfo": object
        AnswerWithKnowledge:
            description: "Answers questions using knowledge base"
            inputs:
                "query": string
```

**After:**
```agentscript
subagent CustomerService:
    reasoning:
        instructions: ->
            | Address user as {!@variables.userName}. Help customers by looking up their account information with {!@actions.GetAccount} and answering their questions with {!@actions.AnswerQuestion}.
        actions:
            GetAccount: @actions.GetCustomerAccount
                with email = @variables.customerEmail
            AnswerQuestion: @actions.AnswerWithKnowledge
                with query = ...
    actions:
        GetCustomerAccount:
            description: "Retrieves customer account details"
            inputs:
                "email": string
            outputs:
                "accountInfo": object
        AnswerWithKnowledge:
            description: "Answers questions using knowledge base"
            inputs:
                "query": string
```

**Key improvements:**
- Fixed variable reference: `@variables.userName` → `{!@variables.userName}`
- Matched action use cases to instructions:
  - "looking up their account information" → `GetCustomerAccount` → added `{!@actions.GetAccount}`
  - "answering their questions" → `AnswerWithKnowledge` → added `{!@actions.AnswerQuestion}`
- Explicit action references improve the LLM's ability to select the correct action at runtime

## Interpolation Is Not Control Flow

```agentscript
# Still wrong when this must be an exact runtime branch
| If {!@variables.customer_tier} == "vip", use priority support.

# Runtime-owned exact fact
if @variables.customer_tier == "vip":
    | Offer the priority-support options available to this customer.

# Model-owned semantic judgment
| If the user is asking for a human rather than product guidance, use
  {!@actions.escalate_to_support}.
```

# Optimization Pattern 3: Fix Variable and Action Reference Syntax

## Detection Logic

Scan all `reasoning.instructions` blocks for two categories of issues:

### 1. Incorrect reference syntax

- Variables referenced directly as `@variables.X` instead of `{!@variables.X}` in natural language text
- Actions/tools mentioned by name without using `{!@actions.X}` syntax

### 2. Missing action references

- Scan all actions in `reasoning.actions` and their definitions in `actions:` section
- Identify what use case each action serves based on its name, description, inputs/outputs
- Check if `reasoning.instructions` mentions those use cases without explicit `{!@actions.X}` references
- Match phrases like "retrieve details", "get contact", "update status", "look up", "search for" to action names

## How to Fix

1. Change `@variables.X` to `{!@variables.X}` in natural language instruction text
2. Add `{!@actions.X}` syntax when referencing actions by their use case in instructions

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

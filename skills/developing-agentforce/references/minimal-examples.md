# Minimal Working Examples

Complete, deployable agent examples with single subagents, actions, and conditional logic.

---

## Hello-World Agent Script

A complete, deployable agent with one subagent, one action, and conditional logic:

```agentscript
system:
    messages:
        welcome: "Hello! How can I help you today?"
        error: "Sorry, something went wrong."
    instructions: "You are a helpful customer service agent."

config:
    developer_name: "simple_agent"
    description: "A minimal working agent example"
    agent_type: "AgentforceServiceAgent"
    default_agent_user: "agent_user@yourorg.com"

variables:
    customer_verified: mutable boolean = False

start_agent entry:
    description: "Entry point for all conversations"
    reasoning:
        instructions: |
            Greet the customer and route to the main subagent.
        actions:
            go_main: @utils.transition to @subagent.main
                description: "Navigate to main conversation"

subagent main:
    description: "Main conversation handler"
    reasoning:
        instructions: ->
            if @variables.customer_verified == True:
                | You are speaking with a verified customer.
                | Help them with their request.
            else:
                | Please verify the customer's identity first.
        actions:
            verify: @actions.verify_customer
                description: "Verify customer identity"
                set @variables.customer_verified = @outputs.verified
    actions:
        verify_customer: apex://VerifyCustomerAction
            description: "Verify customer identity"
            inputs:
                customer_id: string
                    label: "Customer ID"
            outputs:
                verified: boolean
                    label: "Verified"
```

### Key Points

- **`config` block**: `developer_name` must match the folder name (case-sensitive)
- **`default_agent_user`**: Must be a valid Einstein Agent User in the target org — query with `sf data query`
- **`instructions: ->`**: Procedural mode enables `if`/`else` and `run` directives
- **`instructions: |`**: Literal mode for static text passed to the LLM
- **`set @variables.X = @outputs.Y`**: Captures action output into mutable state
- **`@utils.transition`**: Permanent handoff (does not return to calling subagent)

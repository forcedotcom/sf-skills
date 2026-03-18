# Actions Reference

Complete guide to Agent Actions in Agentforce: Flow, Apex, API actions, and escalation routing.

---

## Action Properties Reference

All actions in Agent Script support these properties:

### Action Definition Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `target` | String | Yes | Executable target (see Action Target Types below) |
| `description` | String | Yes | Explains behavior for LLM decision-making |
| `label` | String | No | Display name in UI; auto-generated from action name if omitted |
| `inputs` | Object | No | Input parameters and requirements |
| `outputs` | Object | No | Return parameters |
| `available_when` | Expression | No | Conditional availability for the LLM |
| `require_user_confirmation` | Boolean | No | Ask user to confirm before execution; defaults to `False` |
| `include_in_progress_indicator` | Boolean | No | Show progress indicator during execution; defaults to `False` |
| `progress_indicator_message` | String | No | Custom message shown during execution (e.g., "Processing your request...") |

> **Note**: `label`, `require_user_confirmation`, `include_in_progress_indicator`, and `progress_indicator_message` are valid on action definitions with `target:` but NOT on `@utils.transition` utility actions.

### Input Properties

| Property | Type | Description |
|----------|------|-------------|
| `description` | String | Explains the input parameter to LLM; auto-generated from field name if omitted |
| `label` | String | Display name in UI; auto-generated from field name if omitted |
| `is_required` | Boolean | Marks input as mandatory for the LLM; defaults to `False` |
| `is_user_input` | Boolean | LLM extracts value from conversation context; defaults to `False` |
| `complex_data_type_name` | String | Lightning data type mapping (required for complex types) |

### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `description` | String | Explains the output parameter to LLM; auto-generated from field name if omitted |
| `label` | String | Display name in UI; auto-generated from field name if omitted |
| `filter_from_agent` | Boolean | `True` = exclude output from agent context; defaults to `False` |
| `is_used_by_planner` | Boolean | `True` = LLM can reason about this value for routing decisions; defaults to `False` |
| `complex_data_type_name` | String | Lightning data type mapping (required for complex types) |

### Example with All Properties

```agentscript
actions:
   process_payment:
      description: "Processes payment for the order"
      require_user_confirmation: True    # Ask user before executing
      include_in_progress_indicator: True
      inputs:
         amount: number
            description: "Payment amount"
         card_token: string
            description: "Tokenized card number"
      outputs:
         transaction_id: string
            description: "Transaction reference"
         card_last_four: string
            description: "Last 4 digits of card"
            filter_from_agent: True     # Hide from LLM context
      target: "flow://Process_Payment"
      available_when: @variables.cart_total > 0
```

---

## Action Target Types (Complete Reference)

AgentScript supports the following action types. Use the correct protocol for your integration.

| Short Name | Long Name | Description | Use Case |
|------------|-----------|-------------|----------|
| `apex` | `apex` | Apex Class | Custom business logic; requires `@InvocableMethod` |
| `prompt` | `generatePromptResponse` | Prompt Template | AI-generated responses |
| `flow` | `flow` | Salesforce Flow | Custom business logic; Must be Autolaunched |
| `standardInvocableAction` | `standardInvocableAction` | Built-in Salesforce actions | Send email, create task, etc. |
| `externalService` | `externalService` | External API via OpenAPI schema | External system calls |
| `quickAction` | `quickAction` | Object-specific quick actions | Log call, create related record |
| `api` | `api` | REST API calls | Direct API invocation |
| `apexRest` | `apexRest` | Custom REST endpoints | Custom @RestResource classes |
| `serviceCatalog` | `createCatalogItemRequest` | Service Catalog | Service catalog requests |
| `integrationProcedureAction` | `executeIntegrationProcedure` | OmniStudio Integration | Industry Cloud procedures |
| `expressionSet` | `runExpressionSet` | Expression calculations | Decision matrix, calculations |
| `cdpMlPrediction` | `cdpMlPrediction` | CDP ML predictions | Data Cloud predictions |
| `externalConnector` | `externalConnector` | External system connector | Pre-built connectors |
| `slack` | `slack` | Slack integration | Slack messaging |
| `namedQuery` | `namedQuery` | Predefined queries | Saved SOQL queries |
| `auraEnabled` | `auraEnabled` | Lightning component methods | @AuraEnabled Apex methods |
| `mcpTool` | `mcpTool` | Model Context Protocol | MCP tool integrations |
| `retriever` | `retriever` | Knowledge retrieval | RAG/knowledge base queries |

**Target Format**: `<type>://<DeveloperName>` (e.g., `apex://GetAccountInfo`, `prompt://Send_Email`)

**Common Examples:**
```agentscript
# Apex action
target: "apex://CustomerServiceController"

# Flow action
target: "flow://Get_Customer_Orders"

# Prompt template
target: "generatePromptResponse://Email_Draft_Template"

# Standard invocable action (built-in Salesforce)
target: "standardInvocableAction://sendEmail"

# External service (API call)
target: "externalService://Stripe_Payment_API"
```

---

## Action Invocation Methods

Agent Script provides two ways to invoke actions:

- **Actions Block** (`actions:` in `reasoning:`) — LLM chooses which to execute
- **Deterministic** (`run @actions.name`) — always executes when code path is reached

### Invoking Actions with `actions` Blocks

The LLM automatically selects appropriate actions from those defined in the `reasoning.actions` block:

```agentscript
topic order_management:
   description: "Handles order inquiries"

   reasoning:
      instructions: ->
         | Help the customer with their order.
         | When they ask about an order, look it up.
      actions:
         # LLM automatically selects this when appropriate
         lookup: @actions.get_order
            with order_id=...
            set @variables.order_status = @outputs.status

   actions:
      get_order:
         description: "Retrieves order information"
         inputs:
            order_id: string
               description: "The order ID"
         outputs:
            status: string
               description: "Order status"
         target: "flow://Get_Order_Details"
```

You can also reference action definitions inside `instructions:` using `{!@actions.name}` interpolation. This gives the LLM richer context about available actions.

```agentscript
reasoning:
   instructions: ->
      | To look up an order, use {!@actions.get_order}.
      | To check shipping status, use {!@actions.track_shipment}.
```

> See [action-patterns.md](action-patterns.md#2-instruction-action-references) for detailed usage patterns and examples.

### Invoking Actions Deterministically with `run`

The `run` keyword is only supported in `reasoning.actions:` post-action blocks and `instructions: ->` blocks.

```agentscript
# ❌ DOES NOT WORK — run in before_reasoning (no LLM context)
before_reasoning:
   run @actions.log_turn    # May not execute as expected

# ✅ WORKS — run in reasoning.actions post-action block
create: @actions.create_order
   with customer_id = @variables.customer_id
   run @actions.send_confirmation
   set @variables.order_id = @outputs.id

# ✅ WORKS — run in instructions: -> block
reasoning:
   instructions: ->
      run @actions.load_customer
         with id = @variables.customer_id
         set @variables.name = @outputs.name
```

---

## Action Type 1: Flow Actions

### When to Use

- Standard Salesforce data operations (CRUD)
- Business logic that can be expressed in Flow
- Screen flows for guided user experiences
- Approval processes

### Implementation

```yaml
actions:
  create_case:
    description: "Creates a new support case for the customer"
    inputs:
      subject:
        type: string
        description: "Case subject line"
      description:
        type: string
        description: "Detailed case description"
      priority:
        type: string
        description: "Case priority (Low, Medium, High, Urgent)"
    outputs:
      caseNumber:
        type: string
        description: "Created case number"
      caseId:
        type: string
        description: "Case record ID"
    target: "flow://Create_Support_Case"
```

### Flow Requirements

For an action to work with agents, the Flow must:

1. **Be Autolaunched** — `processType: AutoLaunchedFlow`
2. **Have Input Variables** — Marked as `isInput: true`
3. **Have Output Variables** — Marked as `isOutput: true`
4. **Be Active** — `status: Active`

**Flow Variable Example:**
```xml
<variables>
    <name>subject</name>
    <dataType>String</dataType>
    <isCollection>false</isCollection>
    <isInput>true</isInput>
    <isOutput>false</isOutput>
</variables>
```

### Best Practices

| Practice | Description |
|----------|-------------|
| Descriptive names | Use clear Flow API names that describe the action |
| Error handling | Include fault paths in your Flow |
| Bulkification | Design Flows to handle multiple records |
| Governor limits | Avoid SOQL/DML in loops |

---

## Action Type 2: Apex Actions

### When to Use

- Complex calculations or algorithms
- Custom integrations requiring Apex
- Operations not possible in Flow
- Bulk data processing
- When you need full control over execution

#### Step 1: Create Apex Class with @InvocableMethod

> ⚠️ **An Apex class can only have ONE `@InvocableMethod`.** If you need multiple actions, create separate classes — one per action.

```apex
public with sharing class CalculateDiscountAction {

    // ─── REQUEST WRAPPER ──────────────────────────────────────────
    // Each @InvocableVariable field name becomes an action input
    // name in the .agent file. Must match character-for-character.

    public class DiscountRequest {
        @InvocableVariable(
            label='Order Amount'
            description='Total order amount before discount'
            required=true
        )
        public Decimal orderAmount;

        @InvocableVariable(
            label='Customer Tier'
            description='Customer membership tier (Bronze, Silver, Gold, Platinum)'
            required=true
        )
        public String customerTier;
    }

    // ─── RESULT WRAPPER ───────────────────────────────────────────
    // Each @InvocableVariable field name becomes an action output
    // name in the .agent file. Must match character-for-character.

    public class DiscountResult {
        @InvocableVariable(
            label='Discount Percentage'
            description='Applied discount percentage'
        )
        public Decimal discountPercentage;

        @InvocableVariable(
            label='Final Amount'
            description='Final order amount after discount'
        )
        public Decimal finalAmount;
    }

    @InvocableMethod(
        label='Calculate Discount'
        description='Calculates discount based on order amount and customer tier'
    )
    public static List<DiscountResult> calculateDiscount(List<DiscountRequest> requests) {
        List<DiscountResult> results = new List<DiscountResult>();
        for (DiscountRequest req : requests) {
            DiscountResult result = new DiscountResult();
            result.discountPercentage = getTierDiscount(req.customerTier);
            result.finalAmount = req.orderAmount * (1 - result.discountPercentage / 100);
            results.add(result);
        }
        return results;
    }

    private static Decimal getTierDiscount(String tier) {
        Map<String, Decimal> tierDiscounts = new Map<String, Decimal>{
            'Bronze' => 5, 'Silver' => 10, 'Gold' => 15, 'Platinum' => 20
        };
        return tierDiscounts.containsKey(tier) ? tierDiscounts.get(tier) : 0;
    }
}
```

#### Step 2: Reference DIRECTLY in Agent Script via `apex://`

```yaml
topic discount_calculator:
   description: "Calculates discount for customer order"

   # Level 1: Action DEFINITION with target
   actions:
      calculate_discount:
         description: "Calculates discount based on order amount and customer tier"
         inputs:
            orderAmount: number
               description: "The total order amount before discount"
            customerTier: string
               description: "Customer membership tier"
         outputs:
            discountPercentage: number
               description: "Applied discount percentage"
            finalAmount: number
               description: "Final order amount after discount"
         target: "apex://CalculateDiscountAction"

   reasoning:
      instructions: |
         Help the customer calculate their discount.
      # Level 2: Action INVOCATION referencing the Level 1 definition
      actions:
         calc: @actions.calculate_discount
            with orderAmount=...
            with customerTier=@variables.tier
            set @variables.final_amount = @outputs.finalAmount
```

#### I/O Name Matching Rules

Action `inputs:` and `outputs:` names in Agent Script must **exactly match** the `@InvocableVariable` field names in the Apex class:

```agentscript
# Given this Apex field:
#   @InvocableVariable
#   public Decimal orderAmount;

# ❌ WRONG — snake_case doesn't match camelCase field name
inputs:
   order_amount: number

# ❌ WRONG — different name entirely
inputs:
   amount: number

# ✅ CORRECT — exact match to Apex field name
inputs:
   orderAmount: number
```

> **Partial Output Pattern**: You can declare a **subset** of the target's outputs in your action definition — you don't need to map every output parameter. This is useful when you only need one field from a multi-output action.

#### Bare @InvocableMethod Pattern (NOT Compatible)

Apex classes using bare `List<String>` parameters without `@InvocableVariable` wrapper classes are **incompatible** with Agent Script. The framework cannot discover bindable parameter names without `@InvocableVariable` annotations.

```apex
// ❌ WRONG — bare parameters, no wrappers (Agent Script cannot bind inputs/outputs)
public class BareAction {
    @InvocableMethod(label='Bare Action')
    public static List<String> execute(List<String> inputs) {
        return inputs;
    }
}

// ✅ CORRECT — wrapper classes with @InvocableVariable
public class WrappedAction {
    public class Request {
        @InvocableVariable(
            label='Input Text'
            description='Text to process'
            required=true
        )
        public String inputText;
    }
    public class Response {
        @InvocableVariable(
            label='Output Text'
            description='Processed result'
        )
        public String outputText;
    }
    @InvocableMethod(label='Wrapped Action')
    public static List<Response> execute(List<Request> requests) { ... }
}
```

> ⚠️ **Namespace Warning (Unresolved)**: In namespaced packages, `apex://ClassName` may fail at publish time with "invocable action does not exist," even when the Apex class is confirmed deployed via SOQL. It is unclear whether namespace prefix syntax is required (e.g., `apex://ns__ClassName`). If you encounter this in a namespaced org, try: (1) `apex://ns__ClassName` format, (2) wrapping the Apex in a Flow and using `flow://` instead. See [known-issues.md](known-issues.md#issue-2-sf-agent-publish-fails-with-namespace-prefix-on-apex-targets) for tracking.

---

## Action Type 3: API Actions (External System Integration)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  API ACTION ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│  Agent Script                                               │
│       │                                                     │
│       ▼                                                     │
│  flow://HTTP_Callout_Flow                                   │
│       │                                                     │
│       ▼                                                     │
│  HTTP Callout Action (in Flow)                              │
│       │                                                     │
│       ▼                                                     │
│  Named Credential (Authentication)                          │
│       │                                                     │
│       ▼                                                     │
│  External API                                               │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Steps

1. **Create Named Credential** (via sf-integration skill)
2. **Create HTTP Callout Flow** wrapping the external call
3. **Reference Flow in Agent Script** with `flow://` target

### Security Considerations

| Consideration | Implementation |
|---------------|----------------|
| Authentication | Always use Named Credentials (never hardcode secrets) |
| Permissions | Use Permission Sets to grant Named Principal access |
| Error handling | Implement fault paths in Flow |
| Logging | Log callout details for debugging |
| Timeouts | Set appropriate timeout values |

---

## Connection Block (Escalation Routing)

The `connection` block enables escalation to human agents via Omni-Channel. Always use `connection messaging:` (singular).

### Basic Syntax

```agentscript
# ❌ WRONG — plural wrapper block (invalid syntax)
connections:
   messaging:
      escalation_message: "Transferring you to a human agent..."
      outbound_route_type: "OmniChannelFlow"
      outbound_route_name: "flow://Support_Queue_Flow"

# ✅ CORRECT — singular with channel type
connection messaging:
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "flow://Support_Queue_Flow"
   escalation_message: "Transferring you to a human agent..."
   adaptive_response_allowed: True
```

### Multiple Channels

Each channel gets its own top-level `connection <channel>:` block:

```agentscript
connection messaging:
   escalation_message: "Transferring to messaging agent..."
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "flow://Agent_Support_Flow"
   adaptive_response_allowed: True
```

### Connection Block Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `outbound_route_type` | String | Yes | `"OmniChannelFlow"` is the only validated value. |
| `outbound_route_name` | String | Yes | API name of Omni-Channel Flow (must exist in org) |
| `escalation_message` | String | Yes | Message shown to user during transfer |
| `adaptive_response_allowed` | Boolean | No | Allow agent to adapt responses during escalation (default: False) |

### Supported Channels

| Channel | Description | Use Case |
|---------|-------------|----------|
| `messaging` | Chat/messaging channels | Enhanced Chat, Web Chat, In-App |
| `telephony` | Voice/phone channels | Service Cloud Voice, phone support |

**CRITICAL**: Values like `"queue"`, `"skill"`, `"agent"` for `outbound_route_type` cause validation errors!

### Escalation Action

```agentscript
actions:
   transfer_to_human: @utils.escalate
      description: "Transfer to human agent"
```

### Prerequisites for Escalation

1. Omni-Channel configured in Salesforce
2. Omni-Channel Flow created and deployed
3. Connection block in agent script
4. Messaging channel active (Enhanced Chat, etc.)

---

## Cross-Skill Integration

### Orchestration Order for API Actions

When building agents with external API integrations, follow this order:

```
┌──────────────────────────────────────────────────────────────┐
│  INTEGRATION + AGENTFORCE ORCHESTRATION ORDER                │
├──────────────────────────────────────────────────────────────┤
│  1. sf-connected-apps  → Connected App (if OAuth needed)     │
│  2. sf-integration     → Named Credential + External Service │
│  3. sf-apex            → @InvocableMethod (if custom logic)  │
│  4. sf-flow            → Flow wrapper (HTTP Callout / Apex)  │
│  5. sf-deploy          → Deploy all metadata to org          │
│  6. sf-ai-agentscript  → Agent with flow:// target           │
│  7. sf-deploy          → Publish (sf agent publish           │
│                           authoring-bundle)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `Tool target 'X' is not an action definition` | Action not defined in topic `actions:` block, or target doesn't exist in org | Define action with `target:` in topic-level `actions:` block; ensure Apex class/Flow is deployed |
| `invalid input 'X'` or `invalid output 'X'` | I/O name doesn't match `@InvocableVariable` field name in Apex | Use exact field names from the Apex wrapper class (case-sensitive) |
| `Internal Error` with inputs-only action | Action has `inputs:` but no `outputs:` block | Add `outputs:` block — the server-side compiler requires it (see known-issues.md Issue 15) |
| `Internal Error` with bare @InvocableMethod | Apex uses `List<String>` without `@InvocableVariable` wrappers | Refactor Apex to use wrapper classes with `@InvocableVariable` annotations |
| `apex://` target not found | Apex class not deployed or missing `@InvocableMethod` | Deploy class first, ensure it has `@InvocableMethod` annotation |
| Flow action fails | Flow not active or not Autolaunched | Activate the Flow; ensure it's Autolaunched (not Screen) |
| API action timeout | External system slow | Increase timeout, add retry logic |
| Permission denied | Missing Named Principal access | Grant Permission Set |

### Debugging Tips

1. **Check deployment status:** `sf project deploy report`
2. **Test Flow independently:** Use Flow debugger in Setup with sample inputs
3. **Check agent logs:** Agent Builder → Logs

---

## Related Documentation

- [action-patterns.md](action-patterns.md) — Context-aware descriptions, instruction references, binding strategies
- [action-prompt-templates.md](action-prompt-templates.md) — Prompt template invocation (`generatePromptResponse://`)
- [fsm-architecture.md](fsm-architecture.md) — FSM design and node patterns

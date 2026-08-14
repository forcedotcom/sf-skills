# Architecture Patterns

> Architecture mechanics reference. Start with `references/patterns-by-requirement.md`
> to choose patterns by scenario, then use this file for implementation details.

> All architecture patterns below work for both `AgentforceServiceAgent` and `AgentforceEmployeeAgent`. The only difference is that employee agents cannot use `@utils.escalate` or `connection messaging:` — replace escalation with a `@utils.transition` to a help subagent or an action that creates a case/ticket.

## When to Use Each Pattern

These are composable mechanics, not stages or a hierarchy. Start with the
smallest architecture that satisfies the requirements, then add each
independently required gate or post-action behavior.

| Pattern | Use When |
|---------|----------|
| Single Scope | Default. One domain `start_agent` block, zero `subagent` blocks, and one compatible set of instructions, actions, authority, and escalation behavior |
| Router-First Architecture | Multiple genuine domains require different objectives, instructions, actions, authority, or escalation behavior; use HyperClassifier when the router is transition-only and routing latency matters |
| Verification Gate | Sensitive data, payments, or PII require identity verification first |
| Post-Action Re-resolution | Trusted action output must drive a named follow-up instruction, gate, or action input |

## Smallest Architecture First

Default to one domain `start_agent` block and zero `subagent` blocks. Do not
create an `agent_router` that only transitions to that one domain. Add a
subagent only when the boundary changes at least one of:

```text
objective | instructions | available actions | authority | escalation behavior
```

Use `start_agent agent_router` only when multiple genuine domains require
current-intent classification. Verification gates and post-action
re-resolution are independent mechanics that can be combined with either a
single-subagent or router-first design. Linear sequencing is workflow-local
external ordering, not a default conversation architecture.

## Router-First Architecture Mechanics

A central `agent_router` routes to specialized subagents. Transition paths should be use-case-driven: subagent -> subagent when workflow continues naturally, and subagent -> router when the conversation needs reclassification.

```agentscript
start_agent agent_router:
    description: "Route user requests to the appropriate subagent"

    model_config:
        model: "model://sfdc_ai__DefaultEinsteinHyperClassifier"

    reasoning:
        actions:
            to_orders: @utils.transition to @subagent.order_support
                description: "Order questions"
            to_returns: @utils.transition to @subagent.return_support
                description: "Return or refund requests"
            to_general: @utils.transition to @subagent.general_support
                description: "General questions"

subagent order_support:
    description: "Handle order inquiries"
    reasoning:
        instructions: ->
            | Help the customer with their order.
        actions:
            lookup: @actions.get_order
                description: "Look up order"
            to_returns: @utils.transition to @subagent.return_support
                description: "Continue to return workflow when needed"
```

> **Routing lives in `start_agent`** -- put classification transitions in `start_agent agent_router:`. Do NOT create a separate routing-only subagent (e.g. `main_menu`, `central_hub`) -- that duplicates the router, adds an extra LLM hop (~3-5s latency), and confuses the platform. A transition back to router is optional and should only be added when the use case requires reclassification.

### Fast routing with Einstein HyperClassifier

Use HyperClassifier when the node has one job: select one transition from the
current request and conversation context. Adding this model configuration makes
the block a restricted router node rather than a general reasoning node:

```agentscript
model_config:
    model: "model://sfdc_ai__DefaultEinsteinHyperClassifier"
```

It is a good fit when multiple genuine domains already justify a router and
classification latency matters. The router selects a destination; the target
subagent handles the request and produces the user-facing response.

The restrictions are part of the design:

- reasoning actions must be `@utils.transition`;
- `before_reasoning` and `after_reasoning` are not supported;
- it cannot classify from images;
- it cannot fill action inputs, run domain actions, set variables, escalate, or
  delegate to a connected agent;
- it cannot ask a clarifying question directly. When ambiguity needs a
  conversation, transition to a clarification or fallback subagent.

Use `available when` to remove routes based on trusted runtime state before
classification. Give every route a distinct description that states its
positive scope and important exclusions. Treat those descriptions as the
primary classification contract. Keep `reasoning.instructions` concise: state
the shared routing duty, such as selecting exactly one route without answering,
and put route-specific boundaries in the action descriptions. Add a fallback
route only when the agent has an intended fallback behavior.

An instruction-free router is structurally valid. It can preserve an optimized
one-step routing path in runtimes where router instructions compile into a
lifecycle hook, but use that form only when the action descriptions fully carry
the routing contract and preview traces confirm the intended optimization.
Instructions are not prohibited by HyperClassifier; this is a measured latency
tradeoff, not a language requirement.

When adding HyperClassifier to an existing compatible router, preserve its
instruction block unless changing that contract is separately required. An
`instructions: ->` block containing only `|` prompt text is valid; do not
normalize it to `instructions: |` as part of the model-config repair merely
because it has no runtime statements.

Keep an ordinary reasoning model when the entry node must answer, clarify,
collect information, manipulate state, invoke non-transition actions, inspect
images, or use lifecycle hooks. HyperClassifier is an optimization for a
compatible router, not a reason to create more subagents.

Validate structure, then validate routing behavior:

```bash
sf agent validate authoring-bundle --json --api-name <BundleName> -o <OrgAlias>
sf agent preview start --json --use-live-actions --authoring-bundle <BundleName> -o <OrgAlias>
```

Preview positive and negative examples for every route, ambiguous boundary
utterances, follow-up turns, unavailable-route states, and the intended
fallback. Inspect the selected transition in the trace; response text alone
does not prove routing.

Without HyperClassifier, transition actions on an ordinary reasoning node
remain model-selected and the node can respond instead. That flexibility is
useful when conversation at the entry node is intentional.

## Verification Gate

Users must pass through identity verification before accessing protected subagents. Use when handling sensitive data, payments, or PII. Uses deterministic routing (`instructions: ->`) so the gate cannot be bypassed by LLM conversational drift.

```agentscript
variables:
    is_verified: mutable boolean = False

start_agent agent_router:
    description: "Route through identity verification"
    reasoning:
        instructions: ->
            if @variables.is_verified == False:
                transition to @subagent.identity_verification

            | Select the best tool to call based on conversation history and the user's current intent.
        actions:
            to_account: @utils.transition to @subagent.account_mgmt
                description: "Account management"
                available when @variables.is_verified == True
            to_refund: @utils.transition to @subagent.refund_processor
                description: "Process a refund"
                available when @variables.is_verified == True

subagent identity_verification:
    description: "Verify customer identity"
    reasoning:
        instructions: ->
            if @variables.is_verified == True:
                | Identity verified. Ask which protected task to continue.
            else:
                | Ask for the minimum information needed to verify identity.
        actions:
            verify_email: @actions.verify_identity
                description: "Verify customer email"
                set @variables.is_verified = @outputs.verified

            to_account: @utils.transition to @subagent.account_mgmt
                description: "Account management"
                available when @variables.is_verified == True

            escalate_now: @utils.escalate
                description: "Transfer to human"
```

`is_verified` has one trusted writer (`verify_identity`) and named consumers
(the authorization transitions). Define its expiry, reset, correction, and
cancellation behavior. No mutable variable is needed for the user's ordinary
follow-up context.

## Post-Action Re-resolution

The subagent can re-resolve after an action completes. Persist action output
only when a named later runtime consumer needs the exact value. Make
post-action and first-entry duties mutually exclusive; placing the post-action
check first can make that ownership easier to review, but position alone does
not exclude another fragment:

```agentscript
variables:
    risk_score: mutable number = -1

subagent retention_review:
    description: "Use a returned risk score to select retention guidance"
    reasoning:
        instructions: ->
            # POST-ACTION CHECK (first for readability, exclusive by predicate)
            if @variables.risk_score >= 80:
                | Use the returned risk score {!@variables.risk_score}. Offer
                  the approved high-risk retention options.
            else if @variables.risk_score >= 0:
                | Use the returned risk score {!@variables.risk_score}. Follow
                  the standard retention policy.
            else:
                | Explain that a risk assessment is needed before making an offer.
        actions:
            assess_risk: @actions.load_risk_score
                with customer_id = ...
                available when @variables.risk_score < 0
                set @variables.risk_score = @outputs.score
```

Here `risk_score` is trusted action output consumed by prompt branches and the
repeat-prevention gate. Define when a new request resets or refreshes it.

## Migrating to Multi-Domain Router-First Architecture

Refactor a flat agent only after identifying multiple genuine domains whose
boundaries change objective, instructions, actions, authority, or escalation
behavior:

1. **Prove the boundaries** — group related intents unless behavior changes
2. **Move instructions and actions** from the monolithic subagent into specialized subagents. Each subagent needs BOTH its Level 1 action definitions (under `subagent > actions`) AND Level 2 action invocations (under `subagent > reasoning > actions`).
3. **Create `start_agent agent_router:`** with transition actions pointing to each specialized subagent
4. **Add transitions based on workflow needs** — subagent -> subagent for continuous workflows, or subagent -> router for reclassification turns
5. **Re-preview immediately** — verify subagent routing works before making further changes

**Common migration mistakes:**
- Creating a separate `main_menu` subagent instead of using `start_agent agent_router:` as the hub — adds an unnecessary LLM hop
- Leaving action definitions in `start_agent` instead of moving them to specialized subagents — all actions visible in all subagents, confusing the planner
- Routing everything back to router by default, even when a direct subagent-to-subagent transition better matches the workflow
- If trace shows `topic: "DefaultTopic"`, check that subagent descriptions contain keywords matching test utterances

## Multi-Intent Handling

When a user sends requests for multiple domains in one message, route one
domain and preserve the remaining request in conversation history:

```agentscript
start_agent agent_router:
    description: "Route one domain request at a time"
    reasoning:
        instructions: |
            You are a router only. Do NOT answer questions directly.
            If the user asks about multiple domains in one message, route to
            the first domain. After that task is complete, remind the user
            about the other request from conversation history.
```

No queue variable is needed while the original turn survives in conversation
history. Persist a queue only if exact external ordering must outlive the
configured history window, and then define its writer, consumer, reset, expiry,
correction, and cancellation behavior.

## Handling Incomplete Action Inputs

- Use `with param = ...` (slot-fill) for inputs the LLM should extract from conversation
- Add instructions that tell the LLM to invoke the action with whatever data is available
- Anti-pattern: Making the LLM ask for ALL inputs before invoking

## Controlling Opportunistic Action Chains

In long action chains (A->B->C->D), the LLM may invoke downstream actions as soon as prerequisites are met. To control this:

- Add explicit gating in instructions: "Only invoke generate_resolution if the user explicitly asks"
- Use `available when` guards when successful external output, authorization,
  confirmation, or required ordering supplies a machine-checkable precondition
- Distinguish between "analyze only" and "full resolution" workflows in instructions

Anti-pattern: Leaving action chains ungated so the LLM runs the entire pipeline for every query.

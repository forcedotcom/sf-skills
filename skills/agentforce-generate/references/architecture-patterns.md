# Architecture Patterns

> Extracted from SKILL.md Section 8. This file is loaded on demand when architecture pattern guidance is needed.

> All architecture patterns below work for both `AgentforceServiceAgent` and `AgentforceEmployeeAgent`. The only difference is that employee agents cannot use `@utils.escalate` or `connection messaging:` — replace escalation with a `@utils.transition` to a help subagent or an action that creates a case/ticket.

## When to Use Each Pattern

| Pattern | Use When |
|---------|----------|
| Hub-and-Spoke | Agent has 2+ distinct subagents with different intents (most common) |
| Verification Gate | Sensitive data, payments, or PII require identity verification first |
| Post-Action Loop | Actions produce state that drives follow-up logic (e.g., risk scoring) |
| Single Subagent | Agent serves one focused purpose with no routing needed |

## Hub-and-Spoke (Most Common)

A central `agent_router` routes to specialized spoke subagents. Each spoke has a "back to hub" transition. Use when users may have multiple distinct intents.

```
start_agent agent_router:
	description: "Route user requests to the appropriate subagent"
	reasoning:
		instructions: |
			You are a router only. Do NOT answer questions directly.
			Always use a transition action to route immediately.
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
			back: @utils.transition to @subagent.agent_router
				description: "Route to a different subagent"
```

> **Routing lives in `start_agent`** -- put all transition actions directly in `start_agent agent_router:`. Do NOT create a separate routing-only subagent (e.g. `main_menu`, `central_hub`) -- that duplicates the router, adds an extra LLM hop (~3-5s latency), and confuses the platform. Subagents that need "go back" should transition to `@subagent.agent_router`.

## Verification Gate

Users must pass through identity verification before accessing protected subagents. Use when handling sensitive data, payments, or PII.

```
start_agent agent_router:
	description: "Route through identity verification"
	reasoning:
		instructions: |
			You are a router only. Do NOT answer questions directly.
			Route all users to identity verification first.
		actions:
			verify: @utils.transition to @subagent.identity_verification
				description: "Begin verification"

subagent identity_verification:
	description: "Verify customer identity"
	reasoning:
		instructions: ->
			if @variables.failed_attempts >= 3:
				| Too many failed attempts. Transferring to human agent.
				transition to @subagent.escalation

			if @variables.is_verified == True:
				| Identity verified! How can I help?

			if @variables.is_verified == False:
				| Please verify your identity.

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

## Post-Action Loop

The subagent re-resolves after an action completes. Place post-action checks at the TOP of `instructions: ->` so they trigger on the loop:

```
reasoning:
	instructions: ->
		# POST-ACTION CHECK (at TOP - triggers on re-resolution)
		if @variables.refund_status == "Approved":
			run @actions.create_crm_case
				with customer_id = @variables.customer_id
			transition to @subagent.confirmation

		# PRE-LLM: Load data
		run @actions.load_risk_score
			with customer_id = @variables.customer_id
			set @variables.risk_score = @outputs.score

		# DYNAMIC INSTRUCTIONS
		| Risk score: {!@variables.risk_score}
		if @variables.risk_score >= 80:
			| HIGH RISK - Offer retention package.
		else:
			| STANDARD - Follow normal process.
```

## Migrating to Hub-and-Spoke

When refactoring a flat agent (all logic in one subagent) into hub-and-spoke:

1. **Identify distinct intents** — each becomes a spoke subagent
2. **Move instructions and actions** from the monolithic subagent into spoke subagents. Each spoke needs BOTH its Level 1 action definitions (under `subagent > actions`) AND Level 2 action invocations (under `subagent > reasoning > actions`).
3. **Create `start_agent agent_router:`** with transition actions pointing to each spoke
4. **Add "back to hub" transitions** in each spoke: `@utils.transition to @subagent.agent_router`
5. **Re-preview immediately** — verify subagent routing works before making further changes

**Common migration mistakes:**
- Creating a separate `main_menu` subagent instead of using `start_agent agent_router:` as the hub — adds an unnecessary LLM hop
- Leaving action definitions in `start_agent` instead of moving them to spoke subagents — all actions visible in all subagents, confusing the planner
- Forgetting to add "back to hub" transitions — users get stuck in a spoke subagent
- If trace shows `topic: "DefaultTopic"`, check that subagent descriptions contain keywords matching test utterances

## Multi-Intent Handling

When a user sends multiple intents in one message, the start_agent router should handle the first intent and queue the second:

```
instructions: |
	You are a router only. Do NOT answer questions directly.
	If the user asks about multiple subagents in one message, route to the first
	subagent. After that task is complete, remind the user about the other request.
```

## Handling Incomplete Action Inputs

- Use `with param = ...` (slot-fill) for inputs the LLM should extract from conversation
- Add instructions that tell the LLM to invoke the action with whatever data is available
- Anti-pattern: Making the LLM ask for ALL inputs before invoking

## Controlling Opportunistic Action Chains

In long action chains (A->B->C->D), the LLM may invoke downstream actions as soon as prerequisites are met. To control this:

- Add explicit gating in instructions: "Only invoke generate_resolution if the user explicitly asks"
- Use `available when` guards on downstream actions
- Distinguish between "analyze only" and "full resolution" workflows in instructions

Anti-pattern: Leaving action chains ungated so the LLM runs the entire pipeline for every query.

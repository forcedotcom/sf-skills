# Optimization Pattern 4: Repair Promised Human Handoff

## Detection Logic

Apply this pattern only when requirements or existing instructions specify
human help, live transfer, or escalation. If no such requirement or promise
exists, skip it. Do not add escalation as default boilerplate.

When it does apply, inspect both the instructions and channel capabilities:

1. Use a live handoff when the agent type, channel, and configuration support
   `@utils.escalate`.
2. Give the real support path when live handoff is unavailable.
3. Never claim that a transfer occurred when no supported handoff exists.

## How to Fix

1. If instructions promise a live handoff, verify that a reachable
   `@utils.escalate` action exists.
2. Put the action in the current execution block by default. Add an escalation
   subagent only when it needs separate instructions, actions, or authority.
3. If live handoff is unsupported, remove the promise and state the real
   support path.
4. Do not escalate merely because a request is difficult unless that trigger is
   an explicit business requirement.

## Example

**Before:**
```agentscript
start_agent customer_support:
    description: "Handles customer support requests"
    reasoning:
        instructions: ->
            | Help customers with supported questions.
              Transfer users to a person when they ask.
        actions:
            answer_question: @actions.AnswerQuestionWithKnowledge
                with query = ...
```

**After:**
```agentscript
start_agent customer_support:
    description: "Handles customer support requests"
    reasoning:
        instructions: ->
            | Help customers with supported questions.
              If the user explicitly asks for a person, use
              {!@actions.human_handoff} without also answering the request.
        actions:
            answer_question: @actions.AnswerQuestionWithKnowledge
                with query = ...
            human_handoff: @utils.escalate
                description: "Transfer the user to a human agent."
```

This example assumes a service-agent channel with live handoff configured. For
an employee agent or unsupported channel, omit `human_handoff` and replace the
instruction with a verified support URL, queue, phone number, or case-creation
action.

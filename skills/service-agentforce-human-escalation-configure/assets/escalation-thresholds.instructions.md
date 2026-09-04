<!--
Agent Script failure-threshold directive snippet (NGA / Agent Script authoring model).

This is a TEMPLATE of directive text, NOT an enforced runtime counter. It is injected
into the agent's topic/system instructions so the planner escalates consistently.
Salesforce Agentforce does not expose a metadata field that counts failed turns; the
threshold is expressed as instruction text and verified by an ADK eval rubric plus a
documented manual conversation test — never by a deterministic metadata read.

Substitute the tokens below when authoring:
  __DEFAULT_FAILURES__   default consecutive-failure threshold (recommended: 2)
  __OVERRIDE_TOPIC_LABEL__ label of a topic that needs a tighter threshold (e.g. "Password Reset")
  __ESCALATION_MESSAGE__ customer-facing handoff line
-->

# Escalation policy (agent directives)

Add the following to the agent's global/system instructions:

- When you cannot resolve the user's request after __DEFAULT_FAILURES__ consecutive
  failed attempts on the same request, escalate to a human agent instead of continuing
  to retry.
- Treat "failed attempt" as: you asked a clarifying question and still could not act, a
  tool/action returned an error, or the user states your answer did not resolve the
  issue.
- On escalation, tell the user: "__ESCALATION_MESSAGE__" and then invoke the human
  handoff (the escalation topic is enabled to transfer to the human queue).
- Do not disclose internal error details, stack traces, or system identifiers when
  escalating.

# Per-topic override

Add the following to the __OVERRIDE_TOPIC_LABEL__ topic instructions (tighter threshold):

- For __OVERRIDE_TOPIC_LABEL__ requests, escalate to a human after a SINGLE failed attempt.
  Time-sensitive requests (for example password/credential problems) should not be
  retried repeatedly.

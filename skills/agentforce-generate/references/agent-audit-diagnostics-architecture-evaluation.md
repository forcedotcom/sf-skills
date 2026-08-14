# AgentScript Architecture and Evaluation Diagnostics

Use these categories to evaluate architectural pressure, evidence quality, and
cases that should remain non-findings.

## Architecture and prompt density

Check:

- subagents exist without an objective, instruction, action, authority, or
  escalation boundary;
- routers duplicate behavior better handled in one execution block;
- state and transitions compensate for unclear instructions rather than real
  runtime needs;
- huge product lists, phrase lists, and repeated rules obscure higher-priority
  behavior;
- one reasoning iteration must reconcile too many classifications, precedence
  rules, exact sequences, or mutually dependent decisions for the deployed
  model;
- one subagent owns unrelated objectives or incompatible authority.

Fix:

- Start from the smallest architecture satisfying the use cases.
- Split when a boundary materially changes objective, instructions, actions,
  authority, or escalation and that separation is worth the routing and
  lifecycle cost.
- Remove duplicated prose before adding state.
- Match the reasoning burden to the actual target model and configuration. If
  the target model is unknown, report capability fit as unassessed.
- Do not use a stronger model as a substitute for resolving contradictions,
  impossible sequences, or missing runtime data.

Evaluate with the deployed target model, representative routes, and prompt
inspection. Vary phrasing at semantic boundaries. Do not treat reduced line
count as a behavior result.

## Evaluation integrity

Check:

- candidate-only tests;
- changed expected behavior after seeing a failure;
- aggregate score hiding a critical regression;
- simulated actions presented as live proof;
- parent and candidate labels that do not identify concrete revisions;
- tests encoding generic preferences absent from the Agent Spec or baseline.

Fix:

- Freeze the matrix and evaluator before editing.
- Record immutable baseline and candidate identifiers.
- Separate structural, simulated, and live evidence.
- Report individual critical cases as well as aggregate score.

## Non-findings

Do not automatically report:

- a large file;
- one execution block rather than several subagents;
- absence of persistent state;
- absence of generic ambiguity, off-topic, or human-help branches;
- lack of a router in a focused workflow;
- model judgment over unstructured user intent;
- wording or formatting preferences without a reachable consequence.

These become findings only when the use cases and evidence establish harm.

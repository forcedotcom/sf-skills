# AgentScript Audit Scope and Path Review

Follow this first half of the audit workflow before selecting or applying a
repair level.

## Contents

- [Establish Scope and Evidence](#1-establish-scope-and-evidence)
- [Reconstruct the Use Cases](#2-reconstruct-the-use-cases)
- [Audit Every Reachable Path](#3-audit-every-reachable-path)

## Workflow

### 1. Establish Scope and Evidence

- Locate the complete `.agent` bundle, its metadata, action implementations,
  Agent Spec, test specifications, and relevant repository instructions.
- Determine whether the input is a complete agent, one extracted subagent, or
  a pasted fragment. Do not report missing bundle scaffolding as a defect in an
  intentionally extracted fragment.
- Inspect the worktree before editing. Preserve unrelated user changes.
- Identify available validation surfaces: Salesforce CLI and target org,
  project commands, preview, test suites, and session traces.
- Read the full agent and every directly referenced action contract needed to
  understand its behavior. Do not infer action outputs from names alone.
- Create the audit ledger or report shell now. Record artifact scope, baseline
  identity, evidence limits, initial use cases, and the highest-priority
  supported observations. Keep incomplete entries explicitly marked instead of
  withholding the artifact until the audit is complete.
- Run the strongest available read-only project check. If an authenticated
  target org and complete bundle are available, run:

  ```bash
  sf agent validate authoring-bundle --json --api-name <BundleName>
  ```

  Preserve the baseline diagnostics.

If only a fragment is available, perform a bounded semantic review and state
which structural, reachability, and runtime claims cannot be verified.

#### Scale the audit before reading a large agent

As a workflow heuristic, use the indexed audit below when a file is large
enough that a single-pass review would lose cross-node context. Rough defaults
are more than 2,000 lines or 10 execution nodes; adjust them to the density and
complexity of the artifact. They are not AgentScript runtime limits.

1. Build a deterministic index first: block boundaries, variables, actions,
   action outputs, transitions, lifecycle hooks, and available diagnostics.
   Follow [AgentScript Compiler Setup](agentscript-toolchain.md) to load an
   ambient SDK, install the public npm package, or build the public source
   fallback, then run
   `node <skill-directory>/scripts/index-agent.mjs <path-to-agent-file>` and
   retain its JSON outside the bundle. This helper uses the real
   parser/compiler rather than regex and reports its exact provider. If both
   installation paths fail, record **compiler not used** and continue with
   target-org validation or a bounded static review; do not stall the audit.
2. Seed one audit ledger keyed by execution node and use-case ID immediately
   after indexing. Do not rely on a single giant narrative summary.
3. Screen each node for user-visible harm and confidence. Add supported
   Critical and High findings to the ranked ledger as soon as they are found;
   do not wait for every node to be deeply traced.
4. Deep-trace the highest-ranked affected paths first. Open another reference
   or source file only after naming the decision its evidence could change.
   Stop a line of inquiry when two consecutive reads or queries add no material
   evidence to that decision.
5. Checkpoint the ledger after each reviewed node or coherent cause group. Mark
   remaining nodes as pending so an interrupted audit still leaves a useful,
   honest deliverable.
6. After the node screening pass, run one cross-node pass for shared variables,
   instruction overrides, transition arrivals, action ownership, and reset
   behavior, then revise the rankings.
7. Repair one coherent cause group per batch. Keep a coupled group small enough
   to attribute any regression, then run validation, affected regression cases,
   and representative unaffected canaries before the next batch.
8. Report deferred accepted findings after every batch. Do not hold the first
   useful result until the whole file has been rewritten.

Large size is not itself a defect. Do not split an agent merely to make the
analysis easier.

### 2. Reconstruct the Use Cases

Build a use-case matrix before fixing anything. Prefer, in order:

1. user-supplied behavior and acceptance criteria;
2. an approved Agent Spec;
3. existing tests and evaluation definitions;
4. reachable behavior inferred from the agent and action contracts.

Label inferred use cases. Do not quietly turn them into new requirements.

For each user-facing objective, record:

- initial utterance and required follow-up turns;
- expected response, question, action, transition, refusal, or escalation;
- actions that must be available and actions that must be unavailable;
- trusted prerequisites and expected state changes;
- external side effect, if any, and which mechanism owns it.

Include only the boundaries material to the artifact or user intent:

- positive path;
- missing or invalid input;
- failure and retry;
- cancellation or topic switch when supported;
- repeated request or repeated action;
- multi-turn continuation;
- transition arrival with the current customer message;
- explicit negative action-availability cases.

### 3. Audit Every Reachable Path

Trace each use case through:

```text
effective instructions
-> available actions
-> selected action or response
-> returned output
-> stored state
-> next reasoning iteration or transition
-> externally observable result
```

Apply every relevant category in the Diagnostic Catalog. Pay special attention
to:

- structural indentation versus indentation inside `|` text;
- repeated adjacent `|` markers that fragment one contiguous prompt block;
- runtime values named in `|` text without `{!@variables.X}` interpolation;
- exact machine-known comparisons whose consequences must be stable but are
  written as model prose instead of runtime predicates;
- subagent system instructions replacing global instructions;
- independent conditions that overlap or leave gaps;
- invalid `elif`, unsupported nested conditionals, or independent branches that
  should be one first-match `else if` chain;
- HyperClassifier used for a node that must do more than transition, or omitted
  from a compatible pure router despite an established routing-latency need;
- action availability broader than the prompt branch mentioning it;
- `|` prompt text treated as though it pauses deterministic `run`, `set`, or
  `if` resolution;
- a requested model action treated as executed merely because the model was
  told to call it;
- raw or stale outputs controlling consequential decisions;
- completion flags set before every derived field is usable;
- redundant state that encodes one phase several ways, duplicates conversation
  history, or lacks reset semantics;
- reasoning burden that exceeds the target model's demonstrated capability;
- lifecycle hooks that overwrite legitimate later state;
- unsupported syntax or lifecycle constructs;
- two mechanisms claiming the same side effect;
- tests that encode a new preference instead of existing intent.
- categorical or causal findings whose evidence supports only a recommendation,
  possibility, or version-specific observation.

Rank findings by observable harm, not visual ugliness:

- **Critical:** unsafe or unauthorized effect, data exposure, or systemic
  inability to perform the primary objective.
- **High:** wrong routing, wrong action, duplicate effect, dead primary path,
  or trusted decision based on untrusted data.
- **Medium:** reachable failure, retry, continuation, or maintenance defect
  with bounded impact.
- **Low:** concrete clarity or resilience defect with a plausible failure mode.

No location, consequence, use case, and verification plan means no finding.
A missing entry in an abbreviated reference list is not evidence of a defect.
Likewise, a style preference with no diagnostic, supported-use-case
consequence, or user-approved cleanup scope is not a Surface repair. Preserve
valid optional metadata and semantically equivalent control-flow shapes.
Do not add a supposedly required field to an existing bundle without a
diagnostic from the selected compiler or target validator and evidence for its
correct value. Never guess deployment semantics merely to complete a schema.

Keep the ranked ledger current while tracing. Finish the Critical and High
paths before spending time on Medium or Low hypotheses. A lower-priority issue
may be recorded as pending when further research would delay a supported,
higher-impact finding or repair.

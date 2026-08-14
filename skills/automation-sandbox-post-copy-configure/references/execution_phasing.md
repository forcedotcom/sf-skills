# Execution Phasing

The `ExecutionOrder` field in each config entry is a **phase number**,
not a per-row counter. This file explains the model; the deterministic
enumeration is owned by `scripts/plan-phases.mjs` (authoring standard
A9). Invoke that script and consume its `phases[]` output directly —
do not re-implement the grouping rule in prose.

## Grouping rules (implemented in `scripts/plan-phases.mjs`)

1. Read every entry from the config JSON.
2. Bucket entries by their `ExecutionOrder` integer value.
3. Sort buckets ascending — the phase with the smallest
   `ExecutionOrder` runs first.
4. Assign each bucket an `ordinal` = 1-indexed position in the sorted
   list. Sparse values (`1, 2, 5`) collapse to (`1, 2, 3`) — no empty
   phases for the gaps.

Example — a config with these values:

```text
Entry A: ExecutionOrder = 1
Entry B: ExecutionOrder = 1
Entry C: ExecutionOrder = 2
Entry D: ExecutionOrder = 1
Entry E: ExecutionOrder = 5
```

...produces three phases:

```text
Phase 1 (ExecutionOrder = 1): [A, B, D]  ← parallel-eligible
Phase 2 (ExecutionOrder = 2): [C]        ← runs after Phase 1 completes
Phase 3 (ExecutionOrder = 5): [E]        ← runs after Phase 2 completes
```

The absolute value of `ExecutionOrder` is not meaningful — a jump from
2 to 5 does not imply three empty phases. Only the ordering matters.

## Intra-phase concurrency

Entries within a single phase are eligible to run in parallel. The
concurrency cap is **5 by default** to avoid tripping Salesforce API
rate limits (`REQUEST_LIMIT_EXCEEDED`, HTTP 429).

- If the phase has ≤5 entries: run them all concurrently.
- If the phase has >5 entries: run them in batches of 5, waiting for
  each batch to complete before starting the next.

On any HTTP 429 within a phase, reduce the concurrency for the
remainder of the run (5 → 2) and continue. Do not abort — the cap can
recover on the next phase.

## Phase boundaries — strict serialization

Never overlap phases. Every entry in Phase N must have a terminal
outcome (SUCCESS, FAILED, NOT_FOUND, SKIPPED, DRY_RUN,
DELETE_NOT_SUPPORTED, UNSUPPORTED_CONFIGURATION_NAME) before any entry
in Phase N+1 starts.

Rationale (from the design doc v264 execution model):

> "Since we might not be able to copy or perform tasks in any order as
> there might be tasks which will be dependent on others… Stage 2:
> tasks in parallel, each waits for ALL of Stage 1."

A later phase may depend on the effect of an earlier phase — e.g.,
Remote Site Settings must be updated before the Outbound Messages that
target hosts covered by those Remote Sites are re-activated. Skipping
the barrier means the later phase sees stale state.

## Handling failures across phases

- **Default (`continue-on-error = true`)**: A phase completes even if
  some entries fail. The next phase still starts. All failures are
  captured in the summary.
- **Strict (`continue-on-error = false`)**: The first failure inside
  a phase aborts the current phase mid-flight (the remaining
  parallel-eligible entries in that phase are cancelled) and blocks
  every subsequent phase. Emit `NOT_ATTEMPTED` outcomes for the
  cancelled and blocked entries.
- **`NOT_FOUND` is treated as a failure** for the purposes of the
  continue-on-error flag — the customer typically wants to know
  their config referenced a record that does not exist on the target
  org.

## Empty phases and duplicate ExecutionOrder

- **All entries share the same `ExecutionOrder`**: one phase, all
  parallel-eligible. This is the common case for small configs and is
  perfectly valid.
- **`ExecutionOrder` is missing or non-integer on any entry**: treat
  the config as malformed and abort before Step 2 of the workflow.

# Test Drive Instrumentation Harness (`--instrument` mode)

Framework-owned, **optional** instrumentation that wraps *any* test drive to measure developer-experience
friction and surface automation gaps. It is generalized from the Service Cloud team's original
"system prompt" harness so every product team's drive gets the same DX telemetry for free — without
each team baking measurement into their own prompt.

**Default is clean.** When the engine runs a drive without `--instrument`, none of this applies — no
logs, no counters, no meta commentary. Only activate everything below when the user passed
`--instrument` (or when running the feasibility spike, which is exactly this harness pointed at a
throwaway org).

This same harness is the **feasibility-spike instrument**: run a drive with it against a scratch/dev
org to produce the manual-step map, API-gap map, and error catalog that then inform the catalog
manifest and the prompt's narrated checkpoints.

---

## What to maintain during an instrumented run

### 1. Session log file

Create `session-log-<YYYYMMDD-HHMM>.md` at the start of the run and append to it as you go. In a normal
`--instrument` run, write it to the current working directory; during the feasibility spike, write it
under `.context/test-drive-spike/logs/`. Record the drive `id`, the connected org alias/edition, and
the start time in a header.

### 2. Five counters

Keep a running tally, updated as each event happens, and reproduce it in the final summary:

| Counter | Increment when… |
|---|---|
| `sf` CLI calls | you invoke the Salesforce CLI |
| `curl` calls | you fall back to a raw REST/Tooling API call via curl |
| `python3` calls | you fall back to a python3 script/one-liner |
| setup pauses | you pause for a **configuration** question that shapes the build (positive — this is the demo) |
| permission pauses | you pause to ask "should I proceed?" (friction — a rough edge to design away) |

`curl` and `python3` counts are automation-gap signals: every one means no first-class `sf` subcommand
covered the need.

### 3. Checkpoint entries

For each meaningful build phase, log a checkpoint: phase name, start time, end time, **active** time,
**wait** time (time blocked on a pause), and the outcome (success / partial / failed).

### 4. API Gap Log

One entry per `curl` or `python3` call:
- **Phase** it occurred in
- **Why no `sf` subcommand** fit (what was missing)
- The **exact command** run (redact secrets/tokens)
- **Outcome / error**
- The **underlying CLI/API gap** it represents (so it can become a product ask)

### 5. Error Log

One entry per error hit (`INVALID_TYPE`, `INVALID_FIELD`, `NOT_FOUND`, deploy failures, etc.):
- The **verbatim** error message
- The **workaround** applied
- A **"graceful handling" note** — how a future run should anticipate and handle this smoothly

### 6. Pause Log

One entry per pause, classified:
- **setup pause** — a wizard/config question that shapes the build. Positive; keep these in the live demo.
- **permission pause** — a "should I proceed?" prompt. Friction; a candidate to pre-answer via
  `presetInputs` or to remove.

### 7. Prompt log

Record the **verbatim** prompt that was injected (the drive's `promptPath` contents plus any applied
`presetInputs`), so the run is reproducible.

---

## Final summary table

Close the session log with a summary: the five counters, total active vs. wait time, checkpoint
pass/fail counts, the count of API-gap and error entries, and a short "top frictions" list ranked by
impact. This summary is the artifact that graduates from a spike — it drives what the catalog manifest
should pre-answer and what belongs in a product ask.

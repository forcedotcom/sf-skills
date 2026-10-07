# tableau-next-asset-create

A skill for building **Tableau Next semantic models that actually return data**
via a `tableau-next-*` MCP server, then enriching, querying, and visualizing
them.

## What it does

Routes an agent through the full authoring workflow: ingest CSVs to DLO/DMO,
discover and row-gate sources, join the semantic data model (SDM), add
calculated fields and metrics, run semantic queries, and build visualizations
and dashboards. It encodes the failure modes that produce **empty or
confidently-wrong dashboards** in Tableau Next — building on zero-row source
objects, leaving objects unjoined, inventing field apiNames instead of reading
them back, and shipping a populated-but-wrong model (an ID summed as a measure,
a snapshot inflated by its date count).

Trigger it for "analyze this CSV", "analyze account engagement", "build a
dashboard from these extracts" — whenever the user wants insight from data that
**isn't modeled yet** — and also for unnamed counts/totals ("how many orders…
from existing Tableau Next data") and for designing the dashboard
narrative/layout *before* charting. Plain counts, totals, and scalars against
existing Tableau Next data go to `run_semantic_query` (the model need not be
named). Interpreted breakdowns, rankings, trends, and comparisons go to
`analyze_data`. Not for debugging a broken MCP server, writing application
code, or reviewing someone else's existing dashboard without changing it.

## Structure

```text
SKILL.md                     # thin router: G1 precondition + intent→guide table + no-dispatch rule
references/
  shared-gates.md            # single source of truth for the overlapping guardrails (G1–G8)
  tasks/                     # thin task guides — one per capability; each opens with its gate header
    build-end-to-end.md      # greenfield: build model + dashboard from scratch (Step 0→11)
    ingest-flat-file.md      # ingest CSV → DLO → DMO
    profile-dataset.md       # read-only: profile / discover / verify / triage empty
    edit-sdm.md              # add a RAW object / dimension / measure / join / logical view
    enrich-model.md          # add a CALCULATED dimension / measure / metric
    ai-readiness-audit.md    # backfill readiness metadata / validate a model
    query-model.md           # run_semantic_query for figures (model need not be named)
    analyze-data.md          # interpreted breakdown / ranking / trend / comparison
    create-viz.md            # create a single visualization
    edit-viz.md              # edit an EXISTING visualization / persist via update_visualization
    build-dashboard.md       # design / create / update a dashboard, add widgets/filters
  # deep references (verified payloads + tool shapes) — cited BY the task guides:
  build-workflow.md          # full numbered-step procedural spine with verified payloads
  large-flat-file-handling.md
  data-understanding.md
  sdm-tool-reference.md
  empty-source-handling.md
  semantic-query-and-enrichment.md
  ingest-and-metric-gotchas.md
  viz-authoring.md
  edit-visualization.md
  dashboard-authoring.md
  dashboard-design-principles.md
  ai-readiness.md
```

The router asserts **G1** (a Tableau Next MCP server must be connected) once,
then dispatches an intent to a task guide. Each guide's header names the gates
it must assert (from `shared-gates.md`) before any tool call, then points *down*
to a deep reference for the verified payload. The overlapping guardrails live
in exactly one place (`shared-gates.md`).

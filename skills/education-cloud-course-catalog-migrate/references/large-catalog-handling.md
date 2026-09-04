# Large Catalog Handling

Applies whenever the parsed course count exceeds **200 courses** (8+ batches at the standard batch size of 25) OR the primary source document exceeds **20 pages**. Below these thresholds, follow the standard Workflow in `SKILL.md` as written — nothing here overrides it.

## 1. Large source documents (PDF/website)

- The `Read` tool caps large PDFs at **~20 pages per call** and requires an explicit page range above 10 pages. Never attempt a single `Read` on a 100+ page catalog PDF.
- Read in sequential page-range chunks (e.g. `pages: "1-20"`, `"21-40"`, ...). Merge parsed course rows across chunks before running the completeness check (step 3) — do not validate completeness per-chunk, a course description that spans a page boundary will false-positive as missing.
- For a paginated website catalog, the existing "fetch all pages before parsing" rule (`references/gotchas.md`) already covers this — no change, just note it applies here too.
- State the total page/chunk count to the user before starting the read pass: `"Source document is 640 pages — I'll read it in 32 chunks of 20 pages."` Silent chunking with no upfront count leaves the user unable to judge how long ingestion will take.

## 2. Modality / delivery-method duplicates

Real catalogs sometimes list the same course twice under different delivery modalities (e.g. Online vs. On-Campus), each with its own `Duration`/`DurationUnit`. This is a **source-data shape issue**, detected during Phase 2 parsing — distinct from the step 8 org-conflict check, which only looks at records *already in the org*.

- After parsing, run `scripts/detect_modality_variants.py` on the parsed rows (JSON array with `CourseCode`, `Duration`, `DurationUnit`, `Description` per row). It groups by `CourseCode` and flags any group whose rows differ in those fields. Use its flagged output for the representation decision below — never silently dedupe (drop one) or silently merge (average/pick one) a flagged group.
- Before assuming there's no dedicated field for the distinction, run `GET /services/data/vXX.X/sobjects/Learning/describe` and check for a delivery-method/modality field. Education Cloud orgs vary — do not assume absence without checking.
- If no such field exists on the describe result, pause and ask the user how to distinguish the variants once (not per-course): typically either (a) separate `Learning` records with the modality appended to `Name` (e.g. `"BIO-201 (Online)"`), or (b) a single record if the org treats modality as an offering-level (not course-level) attribute. Apply the chosen pattern to every flagged variant in this run, and state the pattern in the Phase 5 summary.

## 3. Batch-count disclosure and checkpointing

- Before Phase 3 begins, tell the user the total course count and batch count: `"1,438 courses parsed. This will run as 58 batches of 25 (116 Composite API calls). I'll report progress after every batch."`
- Print the existing `Batch N complete — X Learning + X LearningCourse records created` line (step 9) after **every** batch, not just at the end — this is the checkpoint. The step 8 existing-course check is what makes a checkpoint useful: if this run is interrupted and re-invoked, step 8 will find the already-created courses and skip them, so print it as an explicit resume contract to the user rather than only as a conflict check: `"Resuming — found 425 of 1,438 courses already created from a prior run, continuing from course 426."`
- Do not build a separate progress-manifest file. The org itself (queryable via step 8) is the source of truth for what's done — a local manifest can drift from it after an interruption and is one more thing to keep in sync.

## 4. Parallel batch fan-out (optional acceleration)

Only attempt this when the current surface exposes a capability to run independent units of work concurrently (e.g. Claude Code's `Agent`/Task tool). **Never assume this capability exists** — Agentforce, plain MCP surfaces, and the ADK eval harness's `vibes-cli` runtime do not expose it. If no such capability is available, run batches sequentially per the standard Workflow — this is the default, not a degraded fallback.

When available, follow these rules exactly:

1. **Fan-out unit is one whole batch**, never a half-batch. A batch's Learning-create-then-LearningCourse-create sequence (step 9) is strictly ordered — the child create needs the parent's returned Id. Splitting a batch's two steps across workers is not allowed.
2. **Partition before fan-out, by index, not content.** Divide the full course list into disjoint batches up front (course 1-25 → batch 1, 26-50 → batch 2, ...). Two workers must never receive overlapping course records.
3. **Run step 8 (existing-course check) once, globally, before fan-out** — never per-worker. A per-worker check races: two workers can both see "no conflict" for the same course code in the same instant and both create it.
4. **Cap concurrency at 4 workers.** Do not fan out all batches at once — Salesforce enforces per-org concurrent long-running-request limits; unbounded fan-out risks `REQUEST_LIMIT_EXCEEDED` that a sequential run would never hit. Launch the next batch only when a worker slot frees up.
5. **Each worker's prompt must be fully self-contained.** A freshly spawned worker does not see this conversation. Include in its prompt: the exact course-record slice (not a range to look up), the resolved API version, the `ProviderId`, the field-placement rule that `ProviderId`/`Duration`/`DurationUnit` go on `Learning` only, never on `LearningCourse` (and that `CipCode` is opt-in — leave unset unless the source supplies a real CIP code), and that the existing-course conflict check keys on `LearningCourse.SubjectAbbreviation`+`CourseNumber`, never `Learning.CipCode` — restating the gotcha per-worker is cheaper than a worker rediscovering it via a failed create.
6. **Aggregate before Phase 4/5 — this is a hard barrier.** Collect every worker's created-Ids-and-errors list before running the Phase 4 data quality scan or the Phase 5 summary. Do not run quality validation on a partial result set.
7. **Isolate failures per batch.** A failed worker must not abort sibling workers. Track outcome per batch (`succeeded` / `failed` / `partial`) and report each in the Phase 5 summary — do not collapse to a single aggregate count when any batch failed or partially failed.

### Verification status

This fan-out path is **not covered by the current ADK eval harness** — the eval runtime (`vibes-cli` surface) has no subagent/parallel-task tool, the same class of gap as headless-360's absence there. Verification for this path is manual, against real large catalogs (e.g. a 1,438-course, two-modality catalog), not automated eval — until that manual pass is done and recorded, treat this as unverified best-effort, and say so plainly if asked whether it's covered by CI.

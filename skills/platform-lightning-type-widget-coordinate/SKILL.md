---
name: platform-lightning-type-widget-coordinate
description: "Orchestrate Apex-backed Lightning Type + HXL widget generation. TRIGGER only when the prompt EXPLICITLY invokes Lightning Types: user says 'Lightning Type', 'CLT', 'Custom Lightning Type', 'Apex-backed type', references '@apexClassType/...', asks to build a widget or card for a named Lightning Type, asks to create a new Lightning Type and widget together, or grounds a widget in a specific Apex class as its schema. DO NOT TRIGGER when the prompt names only a subject, domain, feature, or entity noun. Also DO NOT TRIGGER when: authoring only a Custom Lightning Type (use platform-custom-lightning-type-generate), only an Apex class (use platform-apex-generate), editing an existing widget without any Lightning Type change, or grounding a widget on an object/JSON-based Lightning Type (lightning__objectType with primitives)."
metadata:
  version: "1.3"
  minApiVersion: "68.0"
  relatedSkills:
    - "platform-apex-generate"
    - "platform-custom-lightning-type-generate"
    - "platform-widget-generate"
  cliTools:
    - tool: ["git"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Building a Lightning Type With a Widget

Coordinate Lightning Type, Apex class, and HXL widget generation across the two paths below. This skill never authors content directly — it loads and invokes leaf skills in dependency order, gates progress on user approval, and runs validation gates before reporting completion.

## Scope

Apex-backed Lightning Types only — root `lightning:type` of the form `@apexClassType/<namespace>__<ClassName>` (outer class). The class itself carries the `@AuraEnabled` fields that define the payload shape; nested list-element types live as inner classes referenced by `List<Inner>` fields on the outer class. Object/JSON-based Lightning Types (root `lightning__objectType` with primitive `properties`) are out of scope; route those to `platform-custom-lightning-type-generate` and `platform-widget-generate` separately.

---

## Phase Graph

| Phase | Purpose | Runs in | Output |
|---|---|---|---|
| 1 — Path selection | Pick the path (`existing-lightning-type-with-widget` · `new-lightning-type-with-widget`) from the user prompt. | All paths | `path` |
| 2 — Lightning Type discovery | Local project first; then `sf project retrieve --metadata LightningTypeBundle:<name>`; ambiguity resolution; in-scope verification. | **`existing-lightning-type-with-widget` only** | `lightningTypeSchema` (path + SHA-256 + Apex class FQN) |
| 3 — Build plan | Print the plan in full; proceed unless the next reply explicitly pushes back. | All paths | printed plan |
| 4 — Generation | Load and invoke leaf skills per path. | All paths | files written |
| 5 — Validation | Run hard gates (block) and warn gates (advisory). | All paths | gate report |
| 6 — Summary | Files, validations, preview readiness, next steps. | All paths | summary |

**Per-phase pattern:**

| Step | What to do |
|---|---|
| 1. Load skill | Invoke the named skill. Even if you remember its content, skills evolve — always load fresh. |
| 2. Execute | Follow the loaded skill's workflow. |
| 3. Verify | Confirm outputs exist and match the spec. |
| 4. Checkpoint | Confirm phase completion before moving on. |

---

## Phase 1 — Path selection

Determine the path from the user prompt and pick the corresponding leaf-skill load order:

| Path | Trigger | Phase 4 sub-skill load order |
|---|---|---|
| `existing-lightning-type-with-widget` | Prompt names a Lightning Type and treats it as existing (no *create*, *generate*, or *new* qualifier on the type). Phase 2 confirms it exists and is in scope. | `platform-widget-generate` (renderer wiring is authored inline per the Phase 4 "Renderer.json wiring step" — no separate skill load) |
| `new-lightning-type-with-widget` | Prompt asks for a new Lightning Type (verbs: *create*, *generate*, *build*, *make a new*) **or** Phase 2 finds nothing in the local project or in the org. | `platform-apex-generate` → `platform-custom-lightning-type-generate` (schema authoring) → `platform-widget-generate` (renderer wiring authored inline afterwards per the Phase 4 "Renderer.json wiring step") |

If the prompt names no Lightning Type at all (just a widget against prompt-provided fields or sample data), this orchestrator should not have been triggered — route the user to `platform-widget-generate` directly.

If the prompt is ambiguous between the two paths, ask **one** clarifying question max and pick. The `new-lightning-type-with-widget` path's `platform-apex-generate` step is engaged automatically — do not prompt the user to confirm Apex.

---

## Phase 2 — Lightning Type discovery (`existing-lightning-type-with-widget` only)

Skipped for `new-lightning-type-with-widget` (the Lightning Type does not yet exist).

**For `existing-lightning-type-with-widget`, FIRST Read `references/lightning-type-discovery.md` (REQUIRED — do NOT skip; do not run Phase 2 from this summary alone), then execute its find → verify → ensure-class procedure step by step.** The bullets below are a reminder, not a substitute for the reference:

- Local project first: search `force-app/**/lightningTypes/<TypeName>/schema.json`.
- If not found, run `sf project retrieve --metadata LightningTypeBundle:<TypeName>` against the connected org.
- If multiple candidates surface, list them with FQNs and paths. Ask the user to pick.
- After locating the schema, verify it is in scope (root `lightning:type` starts with `@apexClassType/`). If the type is object/JSON-based, surface that and stop.
- **Ensure the backing Apex class is in the local project.** Parse `<ClassName>` from the `@apexClassType/<ns>__<ClassName>` root. If `<pkgDir>/classes/<ClassName>.cls` is absent, run `sf project retrieve --metadata ApexClass:<ClassName>`. This runs whether the Lightning Type was found locally or retrieved from the org — a locally-present Lightning Type can still reference an absent class. If the class exists nowhere, surface it and stop (the type is unrenderable). See the reference for the full procedure.
- If retrieval fails, surface the CLI error and offer: (a) ask the user to run retrieve manually and re-run, or (b) downgrade to `new-lightning-type-with-widget` if appropriate. Never silently downgrade.
- If retrieval finds nothing, prompt the user to confirm flipping to `new-lightning-type-with-widget` before continuing.

Capture the Lightning Type `schema.json` SHA-256 and the Apex class FQN (parsed from `@apexClassType/...`) at the end of this phase. The Phase 5 `lightning-type-unchanged` gate compares the SHA against the on-disk SHA at end of Phase 4 to enforce no silent schema edits.

> Staleness: do NOT maintain a cross-session cache. Always read the local project fresh and always re-retrieve from the org per session.

---

## Phase 3 — Build plan + approval gate

Print a build plan using the template in `references/build-plan-format.md`. The plan must list:

- A one-line developer-facing summary of what will be built (the `PLAN:` line in the template).
- Lightning Type name and source (existing in local project · retrieved from org · newly created), plus the Apex class FQN it references.
- Files about to be created or modified, with absolute paths.
- Sub-skills that will run after approval.
- Validations that will run after generation.

The plan is read by the developer. Keep it concrete: name the artifacts, files, sub-skills, and validations.

**Print the plan in full, then proceed unless the user's next reply explicitly pushes back.** Explicit pushback = `no`, `stop`, `wait`, `change X`, `use Y instead`, or an equivalent rejection / revision request. Explicit approval (`yes`, `approve`, `go`, `looks good`, `ok`) is welcome but NOT required — silence, an unrelated follow-up, or the natural continuation of a single-turn eval all count as implicit approval. The plan being visible in the transcript is the invariant; blocking on interactive approval is not. If pushback arrives, revise the plan and re-print before moving on.

---

## Phase 4 — Generation

Execute the sub-skill load order from the chosen path's row in the Phase 1 table. For each sub-skill:

1. Load the skill.
2. Execute the leaf skill's authoring workflow against the spec from Phase 3. The leaf skill is authoritative for its own deliverables.
3. Verify the outputs match what the build plan promised.
4. Checkpoint before invoking the next sub-skill.

**`new-lightning-type-with-widget` handoff contract:**

- Apex authors a class whose `@AuraEnabled` fields define the desired Lightning Type shape. Inner classes are used only for nested list-element types. Capture the **outer class FQN** (`<namespace>__<ClassName>`).
- The Custom Lightning Type references the outer class via `lightning:type: "@apexClassType/<namespace>__<ClassName>"`.
- Widget grounds on the outer class's `@AuraEnabled` fields and binds attributes via `{!$attrs.X}`.
- After the widget bundle is written, author the Lightning Type's renderer wiring per the **renderer.json wiring step** below.

**`existing-lightning-type-with-widget` handoff contract:**

- Hand the widget skill the Lightning Type `schema.json` path and the Apex class FQN captured in Phase 2. The widget skill derives its own `schema.json` from the Apex class's `@AuraEnabled` fields (see `platform-widget-generate/references/schema-from-lightning-type.md`).
- After the widget bundle is written, author the Lightning Type's renderer wiring per the **renderer.json wiring step** below. The Lightning Type `schema.json` is NOT modified (`lightning-type-unchanged` enforces this) — only `renderer.json` is written.

**Renderer.json wiring step (BOTH flows — never optional):**

**First, Read `platform-custom-lightning-type-generate/references/widget-rendition.md` (REQUIRED — do NOT skip; do not author `renderer.json` from memory or by copying an existing project sample, which may use a deprecated shape).**

After the widget bundle exists, author `<pkgDir>/lightningTypes/<TypeName>/renderer.json` using the **widget-rendition pattern** documented in `platform-custom-lightning-type-generate/references/widget-rendition.md`. The renderer file is a thin wrapper — its first child references the widget via `"definition": "@widget/c/<widgetName>"` and maps **every widget schema property** to the Lightning Type instance's matching attribute via `{!$attrs.<schemaPropertyName>}`. Do **NOT** duplicate the widget body inside `renderer.json`; the widget bundle is the single source of truth for the rendering tree.

Existing-renderer handling (`existing-lightning-type-with-widget` only): if `renderer.json` already exists at the target path, read it first.

- If it already references the same widget (same `@widget/c/<widgetName>`) with the same attribute mapping, leave it alone.
- If it references a **different** widget OR uses a custom-LWC root override (`c/<componentName>`), STOP and surface the conflict to the user before overwriting. Do not silently replace the user's existing rendition.
- If the file exists but is not a widget-rendition (e.g. property-level overrides only), surface that and ask whether to merge or replace.

Without this wiring the widget is unreachable from the Lightning Type — the widget bundle ships dead. `renderer-wires-widget` enforces existence and binding correctness.

---

## Phase 5 — Validation gates

Read `references/validation-gates.md` and **run every gate**. The orchestrator runs cross-skill gates only — widget-bundle-internal checks (schema parse, root keys, leaf `lightning:type`, `{!$attrs.X}` resolution, `.uiwidget-meta.xml` well-formedness, `<UiWidgetBundle>` root, `<masterLabel>`, `<description>`, and `<widgetType>JSON</widgetType>`) are owned by `platform-widget-generate` and run as part of its own self-validation step.

**Hard — block on failure:**

1. `lightning-type-unchanged` — **`existing-lightning-type-with-widget` only.** Recompute SHA-256 of the on-disk Lightning Type `schema.json` and compare against the SHA captured in Phase 2. Mismatch = orchestrator silently edited the type.
2. `renderer-wires-widget` — **both paths.** Confirm `<pkgDir>/lightningTypes/<TypeName>/renderer.json` exists, parses as JSON, wires this widget via `componentOverrides["$"].definition === "@widget/c/<widgetName>"`, and `componentOverrides["$"].attributes` binds every widget schema property as `{!$attrs.<schemaPropertyName>}`. See "renderer.json wiring step" in Phase 4 and `validation-gates.md` for the required shape.

**Warn — advisory:**

1. `field-trace` — **both paths.** RUN the trace procedure in `references/validation-gates.md` (grep `@AuraEnabled` from the outer .cls, `jq` widget schema property keys, print both lists, classify INVENTED vs OMITTED). PRINT both lists in the gate report — asserting `pass` without printing the lists is a hard violation. Silent omissions (Apex field absent from widget AND absent from the Phase 3 `Properties omitted:` plan) warn.
2. `deploy-check` — **`new-lightning-type-with-widget` only.** RUN `sf project deploy --check-only --source-dir <pkgDir>/classes/<ClassName>.cls,<pkgDir>/lightningTypes/<TypeName>` and report the result. Reporting `pass` without running this command is a hard violation. See `validation-gates.md` for the "not yet deployed is not a valid skip reason" rule.

Report each gate result by name in Phase 6 (`pass`, `fail (<reason>)`, `warn (<reason>)`, `not run`). Do **not** summarize as "all passed" — list each gate explicitly.

---

## Phase 6 — Summary

Report. The summary is read by the developer — list only the files actually written; group by bundle so the developer can locate them quickly.

```text
Lightning Type + Widget Build Complete: <widgetName>

FILES GENERATED:
  Widget bundle:
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.json
    <pkgDir>/uiWidgets/<widgetName>/schema.json
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.uiwidget-meta.xml

  Lightning Type bundle:
    <pkgDir>/lightningTypes/<TypeName>/schema.json                # only when newly created
    <pkgDir>/lightningTypes/<TypeName>/renderer.json              # always — wires the Lightning Type to the widget

  Apex (only when newly created):
    <pkgDir>/classes/<ClassName>.cls
    <pkgDir>/classes/<ClassName>.cls-meta.xml

VALIDATIONS:
  widget self-validation (platform-widget-generate gates): <pass | fail — see sub-skill report>
  Lightning Type schema unchanged from before this run: <pass | fail | n/a (newly created)>
  Lightning Type renderer wires this widget: <pass | fail (<reason>)>
  widget↔apex field trace (INVENTED + OMITTED lists printed): <pass | warn (<reason>) | fail (invented: <list>)>
  sf project deploy --check-only: <pass | warn | n/a (no new Apex or Lightning Type to deploy)>

NEXT STEPS:
  - Deploy: sf project deploy start --source-dir <pkgDir>
  - Preview: <preview-surface guidance>
```

---

## Hard Rules (always apply)

1. **Plan-first, then proceed.** Print the full Phase 3 build plan before writing any file. If the next turn contains explicit rejection or a change request, stop and revise; otherwise continue to Phase 4. The invariant is the plan being visible in the transcript — not an interactive human approval — so this rule holds in manual chat, in agent-to-agent flows, and in single-turn eval runs where no follow-up user message arrives.
2. **No silent schema edits** to existing Lightning Types. Phase 5 `lightning-type-unchanged` enforces this for `existing-lightning-type-with-widget`.
3. **No silent Apex changes** to existing Apex. If Phase 4 needs to modify a pre-existing class, surface it in Phase 3. **A leaf skill that hits a shape gap mid-Phase-4 MUST stop and surface to the orchestrator instead of editing `.cls` directly** — Phase 3 covers gaps the orchestrator already knew about; this clause covers gaps discovered later by a leaf skill.
4. **No invented fields, no silent omissions.** Every `{!$attrs.X}` must trace to the widget `schema.json`, and the widget `schema.json` must be a subset of the Apex class's `@AuraEnabled` fields. Default disposition for every Apex field is **include**; omission requires the field to appear in the Phase 3 build plan's `Properties omitted:` section with a rationale the user has approved. `field-trace` prints both APEX_FIELDS and WIDGET_PROPS lists and warns on silent omissions. `List<InnerClass>` fields are NEVER candidates for silent omission.
5. **One clarification at most** when Lightning Type lookup is ambiguous.
6. **Always load the leaf skill** before generation. Do not author from memory.
7. **Out-of-scope types stop the orchestrator.** If Phase 2 discovers an object/JSON-based Lightning Type, route the user to `platform-custom-lightning-type-generate` and `platform-widget-generate` separately.
8. **Run gates, do not describe them.** Phase 5 gates are concrete checks/commands. Reporting `pass` without executing the gate is a hard violation; report `not run` instead.
9. **Lightning Type rendition is mandatory, never optional.** Both paths end with `<pkgDir>/lightningTypes/<TypeName>/renderer.json` wiring the Lightning Type to the widget via `@widget/c/<widgetName>` with attribute mapping per the widget-rendition pattern. Without this, the widget bundle ships dead. `renderer-wires-widget` enforces existence and binding.
10. **No shell metacharacters that trigger the Vibes safe-shell filter.** In every `Bash` tool call emitted by this orchestrator and by any leaf skill it invokes, do NOT use command substitution (`$(…)` or backticks), process substitution (`<(…)`, `>(…)`), brace expansion (`{a,b,c}` or `{1..N}`), or `eval` / `exec`. These patterns force manual approval even under Bypass mode and stall the eval. Instead: run separate commands (`mkdir -p a && mkdir -p b`, not `mkdir -p {a,b}`); print each intermediate value with its own command and reason about the result rather than capturing it (`jq … file` on its own, not `X=$(jq … file)`); use plain shell variables (`X=literal`) or here-strings when a value must be reused across commands.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/lightning-type-discovery.md` | Phase 2 — local-project scan, org retrieve, ambiguity handling, in-scope verification, and ensuring the backing Apex class is in the local project. |
| `references/build-plan-format.md` | Phase 3 — plan template the model fills before STOP. |
| `references/validation-gates.md` | Phase 5 — full hard / warn gate table with error→fix mapping. |
| `examples/existing-lightning-type-with-widget-prompt.md` | Phase 3 — before drafting the build plan, read this for a complete `existing-lightning-type-with-widget` walkthrough. |
| `examples/new-lightning-type-with-widget-prompt.md` | Phase 3 — before drafting the build plan, read this for a complete `new-lightning-type-with-widget` walkthrough. |

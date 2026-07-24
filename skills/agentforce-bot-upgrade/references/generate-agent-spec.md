# Generate Agent Spec

## What This Skill Is For

This skill implements **only Phase 1 of migration**:

- **In scope**: Einstein Bot -> normalized migration model -> Agent Spec handoff package
- **Out of scope**: `.agent` generation, validation, publish, activate, or deployment

The generated handoff is explicitly designed so `/agentforce-generate` can consume it as the starting spec input for Agent Script authoring.

## How to Use This Skill

Treat this file as the execution router. Always read the referenced files before executing each step.

Follow this fixed sequence:

1. Intake and normalize source bot artifacts
2. Build migration mapping model (dialogs/intents/entities/actions/transitions)
3. Generate Agent Spec handoff artifacts for `/agentforce-generate`
4. Resolve open questions with the user one-by-one (or auto-apply recommended defaults when `--interactive=false`) and persist decisions
5. Generate handoff invocation prompt for `/agentforce-generate` when ambiguity is cleared

## Rules That Always Apply

1. **Do not generate `.agent` in this skill.** Stop at Agent Spec + handoff artifacts.
2. **No implementation invention.** If action target details are unknown, use `NEEDS_STUB`.
3. **Preserve behavioral intent, not XML shape.** Convert deterministic bot flow into subagent-oriented behavioral design.
4. **Track uncertainty explicitly.** Every ambiguous mapping must be captured in `open_questions`.
5. **Mandatory resolution loop.** After artifact generation, process open questions and persist every resolved decision. In interactive mode, resolve them one-by-one with the user; when `--interactive=false`, auto-apply the recommended default for each open question without prompting and record the decision.
6. **Prompt handoff after clarity.** Once all open questions are resolved without ambiguity, generate a complete invocation prompt package for `/agentforce-generate` (do not invoke the skill from this skill).
7. **Use deterministic guardrails for risky flows.** Identity checks, escalation, sensitive operations, and regulated advice must be explicit in the spec.
8. **Input gate is a hard block.** Do not read any workspace files, bot metadata, Apex classes, SFDX project contents, or existing spec files until input mode is explicitly selected and all required inputs for that mode are confirmed. Speculative reading of artifacts found in the workspace is prohibited.

## Task Domains

### Build Agent Spec from Einstein Bot

Use this when user provides Einstein Bot artifacts and asks to migrate/upgrade into Agentforce.

#### Required Steps

0. **Collect mode and required inputs (HARD GATE)** — Parse inputs using this contract:
   - `--mode <online|offline>` (optional; default to `online` when omitted)
   - If `mode=online`, required inputs:
     - `--org-alias <org-alias>`
     - `--bot <bot-name>`
     - `--bot-version <bot-version>`
   - If `mode=offline`, required input:
     - `--offline-dir <offline-dir>` (directory containing/associated with bot metadata inputs)
   - `--interactive <true|false>` (optional; default `true`). When `false`, run autonomously: do not prompt at any decision point, apply the recommended default for every open question/ambiguity, and record each auto-applied decision.
   If required mode-specific inputs are missing, stop and ask in interactive mode; in non-interactive mode halt with an explicit error (do not prompt). Do not read files/metadata/workspace contents until mode and required inputs are confirmed.  
   Note: if `--mode` is omitted, treat mode as `online` immediately (do not ask user to choose mode in that case).

1. **Ingest source artifacts** — Read [Input Contract](input-contract.md) and normalize user-provided bot inputs into one canonical migration model.
   - For `mode=online`, run required SF CLI bot/version/dependency retrieval using [SF CLI Bot Reference](sf-cli-bot-reference.md). Use ONLY the query patterns documented there — do NOT invent or modify field names.
   - For `mode=offline`, skip org retrieval and process **all relevant local metadata** from `--offline-dir`:
     - bot and botVersion XML metadata (required)
     - Flow metadata under `flows/` (when present)
     - Apex classes under `classes/` (when present)
     - any other local files referenced by bot artifacts that are needed for extraction/mapping fidelity
   - In offline mode, do not limit ingestion to only two XML files if additional referenced artifacts are available locally.
2. **Extract migration structure** — Read [Extraction Blueprint](extraction-blueprint.md) and derive:
   - bot capabilities
   - dialog graph
   - intent map
   - variable/entity usage
   - invocation/action inventory
   - fallback/escalation behavior
3. **Map Einstein Bot -> Agent Spec components** — Read [Mapping Rules](mapping-rules.md) and produce topic/subagent, action, routing, and state mappings.
4. **Generate handoff artifacts** — Read [Handoff Output Format](handoff-output-format.md) and write:
   - `<run_project_dir>/<AgentName>-AgentSpec.md`
   - `<run_project_dir>/<AgentName>-einstein-bot-handoff.json`
   - `<run_project_dir>/<AgentName>-open-questions.md`
   Use the same run-specific SFDX project directory created in the SF CLI setup step; do not write handoff artifacts to repository root.
   The Agent Spec markdown MUST use the same section names/order as
   `skills/agentforce-generate/assets/agent-spec-template.md`, then append the
   `## Migration Notes (Einstein Bot -> Agentforce)` appendix defined in [Handoff Output Format](handoff-output-format.md).
5. **Validate handoff quality** — Read [Quality Checklist](quality-checklist.md) and verify all required sections and mapping completeness before presenting output.
6. **Resolve open questions loop (required)** — After generating artifacts, resolve all entries in `<run_project_dir>/<AgentName>-open-questions.md`. In interactive mode, guide the user through them one-by-one; when `--interactive=false`, auto-apply the recommended default for each entry without prompting. For each resolved item, immediately update:
   - `<run_project_dir>/<AgentName>-AgentSpec.md`
   - `<run_project_dir>/extraction-summary.json`
   and remove/mark-resolved the corresponding open question.
7. **Generate `/agentforce-generate` invocation package (no direct invoke here)** — When all open questions are resolved without ambiguity, generate and persist:
   - `<run_project_dir>/agentforce-generate-invocation-prompt.md` (the exact prompt to pass to `/agentforce-generate`)
   - `<run_project_dir>/agentforce-generate-output-contract.md` (expected outputs that orchestrator must capture)
   The prompt must include:
   - `current_working_directory` (run folder path) for all reads/writes
   - `<run_project_dir>/<AgentName>-AgentSpec.md` as source-of-truth spec
   - `<run_project_dir>/extraction-summary.json` as supporting context
   - `<run_project_dir>/<AgentName>-einstein-bot-handoff.json` and `<run_project_dir>/<AgentName>-open-questions.md`
   - `input_mode` (`online` or `offline`) explicit context
   For `input_mode=offline`, include these strict instructions in the prompt:
   - syntax/structural validation is still mandatory
   - skip only org-dependent CLI operations
   - use local artifacts only
   - keep unresolved implementations as structurally complete `NEEDS_STUB` action definitions
   - do not deploy/publish/activate
   Do not invoke `/agentforce-generate` from this skill.

#### Reference Files

1. [Input Contract](input-contract.md) — accepted source types and normalization schema
2. [Extraction Blueprint](extraction-blueprint.md) — what to extract from Einstein Bot metadata and why
3. [Mapping Rules](mapping-rules.md) — canonical mapping from bot constructs to Agent Spec constructs
4. [Handoff Output Format](handoff-output-format.md) — required output files and exact structure
5. [Quality Checklist](quality-checklist.md) — validation criteria before handoff to `/agentforce-generate`
6. [SF CLI Bot Reference](sf-cli-bot-reference.md) — required `sf` command sequence to validate bot/version and retrieve dependencies

## Deliverables

At completion, always return:

1. Agent Spec handoff file path
2. Handoff JSON path
3. Open questions path
4. `/agentforce-generate` invocation package status:
   - `generated` with prompt/output-contract paths when all open questions are resolved
   - `blocked` when unresolved ambiguity remains (include unresolved question IDs)
5. Generated `/agentforce-generate` invocation prompt path (when status is `generated`)
6. Generated `/agentforce-generate` output contract path (when status is `generated`)
7. Short migration-risk summary (top unresolved items)

## Important Constraints

- Do not invoke deployment/publish/activate flows in this skill.
- Do not claim parity with Einstein Bot unless all dialogs/intents/actions are mapped or explicitly deferred.
- Do not collapse critical decision branches into vague LLM-only behavior; represent gates and transitions explicitly in the Agent Spec.

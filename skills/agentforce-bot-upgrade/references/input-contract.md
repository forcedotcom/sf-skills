# Input Contract

## Mode Selection

Input mode is selected from `--mode <online|offline>`:

1. **Online (Mode A: org-backed retrieval)** — Use org alias + bot identity, then fetch metadata/dependencies via SF CLI.
2. **Offline (Mode B: local metadata input)** — Use provided local metadata/artifacts directly without org fetch.

If `--mode` is omitted, default to **online**.
Only ask the user to clarify mode when provided inputs are insufficient or contradictory for the inferred/default mode. When `--interactive=false`, do not ask — proceed with the inferred/default mode and record the assumption; halt only if the inputs cannot support any mode.

## Supported Input Modes

### Mode A: Org-backed retrieval

Required inputs:

1. `--org-alias <org-alias>` — Salesforce org alias used as source context (for discovery, validation, and traceability).
2. `--bot <bot-name>` — Einstein Bot developer name/identifier to migrate.
3. `--bot-version <bot-version>` — specific version to migrate (for example: `v3`).

### Mode B: Offline metadata input (new)

Required inputs:

1. `--offline-dir <offline-dir>` — directory containing/associated with local bot metadata inputs.

Within `--offline-dir`, `.bot-meta.xml` and `.botVersion-meta.xml` inputs are treated as authoritative bot metadata sources for extraction/mapping.

## Offline Directory Processing Scope (Required)

When `--mode offline` is selected, process **all relevant local artifacts** in `--offline-dir` (recursively), not just bot XML:

1. Bot metadata:
   - `*.bot-meta.xml`
   - `*.botVersion-meta.xml`
2. Flow artifacts:
   - files under `flows/` (for example `*.flow-meta.xml`)
3. Apex artifacts:
   - files under `classes/` (for example `*.cls`, `*.cls-meta.xml`)
4. Misc referenced artifacts:
   - any other files referenced by bot/flow/action mappings that improve extraction/mapping fidelity

Processing rules:

1. If `flows/` exists, parse flow signatures and mappings to improve action inventory contracts.
2. If `classes/` exists, parse invocable Apex signatures (`@InvocableMethod`, `@InvocableVariable`) to improve action I/O contracts.
3. If both bot mapping and local implementation artifacts exist, prefer concrete local implementation signatures over inferred placeholders.
4. If referenced artifacts are missing locally, continue with inferred signatures and mark unresolved details in `open_questions`.
5. Never require org retrieval in offline mode.

If required inputs for the selected mode are missing, stop and ask for them before processing artifacts.

## Identity Resolution Rules

- For Mode A, use `org-alias + bot + bot-version` as the run identity key.
- For Mode B, use `bot + bot-version` derived from provided XML metadata (or confirmed from user when not derivable).
- Do not merge artifacts from different versions in the same run.
- If source files contain a mismatched bot identity, pause and ask the user which identity is authoritative. When `--interactive=false`, do not pause — treat the identity declared in the authoritative bot metadata as the recommended default and record the assumption in `open_questions`.

## Missing/Partial Input Handling

- If action signatures are missing: keep action in inventory with `target: NEEDS_STUB`.
- If intent training data is missing: infer intent purpose from dialog labels/descriptions and mark confidence.
- If transitions are unclear: preserve as unresolved branch in `open_questions`.

## Post-Input Finalization Workflow (Required)

### Mode A: Org-backed retrieval

After `--org-alias + --bot + --bot-version` are finalized, execute the SF CLI sequence in:

- [SF CLI Bot Reference](sf-cli-bot-reference.md)

This is the canonical command list for:

1. Enforcing SF CLI and org access prerequisites
2. Validating bot and bot version
3. Retrieving bot metadata
4. Retrieving required Apex/Flow/ML domain dependencies

Any unresolved dependency must be recorded in `open_questions` and mapped as `NEEDS_STUB` where applicable.

### Mode B: Offline metadata input

When both XML files are provided (`.bot-meta.xml` + `.botVersion-meta.xml`):

1. Create a run folder in repo root named `<bot-name>-<bot-version>-agent`.
2. Copy the provided bot metadata files into that run folder:
   - `<BotName>.bot-meta.xml`
   - `<version>.botVersion-meta.xml`
3. Use that run folder as the working directory for this offline run.
4. Skip all SF CLI org validation/retrieval commands.
5. Do not fetch bot/dependency metadata from org.
6. Continue directly with extraction and mapping using all available local artifacts in `--offline-dir` as source inputs.
7. If `flows/` and/or `classes/` are present, include them in extraction before finalizing action contracts.
8. If referenced dependencies (Apex/Flow/MLDomain/etc.) are not available locally, record them as unresolved in `open_questions` and map as `NEEDS_STUB` where applicable.
9. If action signatures (Apex/Flow/etc.) cannot be fully resolved in offline mode, continue execution with best-effort signature expansion and mark unresolved fields.

All generated outputs for that run (for example `extraction-summary.json`, Agent Spec handoff, and open questions) must be written inside the same run-specific SFDX project directory for the selected mode.

# Planner Workflow Reference

Use this reference during orchestrator Step 3 when processing multiple bots in a single invocation.

## When To Apply

- Apply only when there are more than 1 ready-for-authoring Agent Specs.
- If there is 1 or fewer specs, skip planner workflow and keep specs unchanged.

## Inputs

Required inputs to this workflow:

1. `spec_paths`: all ready-for-authoring Agent Spec paths
2. `working_dir`: orchestrator working directory where planner output must be written
3. associated artifacts for each spec when present:
   - handoff JSON
   - open questions

## Required Workflow

1. Read all specs and associated artifacts.
2. Build a final candidate set of specs that will each map to one actual downstream agent.
3. Identify existing subagent grouping/context in each spec.
4. Attempt regrouping based on:
   - intent
   - underlying object/entity
   - broad category
5. Allowed structural operations across specs:
   - merge
   - split
   - move
   - delete
6. Apply operations only when they improve:
   - modularity
   - context-awareness
   - interactive user experience
7. Never perform changes for superficial consistency only.
8. Preserve full functional coverage:
   - no input functionality may be lost
   - if any functionality loss risk is detected, abandon changes and mark unchanged

## Required Output File

Write:
- `<working_dir>/bot-upgrade-planner-output.json`

Schema:

```json
{
  "specs_changed": true,
  "updated_specs": [
    {
      "original_spec_path": "/path/original/spec-a.md",
      "updated_spec_path": "/path/updated/spec-a.md",
      "run_project_dir": "/path/updated/run-project-dir",
      "handoff_json_path": "/path/updated/spec-a-einstein-bot-handoff.json",
      "open_questions_path": "/path/updated/spec-a-open-questions.md"
    }
  ]
}
```

Rules:

1. `specs_changed` is boolean.
2. If `specs_changed=false`, then `updated_specs=[]`.
3. If `specs_changed=true`, `updated_specs` must include entries for all changed specs.
4. Every changed entry must include:
   - `original_spec_path`
   - `updated_spec_path`
   - `run_project_dir`
   - `handoff_json_path`
   - `open_questions_path`
5. If any functionality-loss risk exists, force:
   - `specs_changed=false`
   - `updated_specs=[]`

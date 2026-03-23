# Rule: Salesforce Metadata Generation

## Objective
Enforce: **skill load -> API context -> file generation** for all Salesforce metadata.

## Constraints

1. **Never write** without a loaded metadata type skill for that type.
2. **One type at a time** - complete the full cycle for the current type before moving to the next type.
3. **Always attempt `salesforce-api-context` MCP** for each type before writing; if it is unavailable after a real attempt, proceed with the loaded skill only.
4. **Child types need their own API context response** - if adding child metadata inside a parent metadata file, load the child metadata skill and use `salesforce-api-context` MCP for each child type separately; do not rely on the parent's schema or API context response for child metadata creation. The same fallback in constraint 3 applies.
5. **Max one clarifying question** before starting.
6. **Do not call `execute_metadata_action` unless a skill instructs you to do so.**

## Skill Selection

- Search available skills and load the best-matching app-level skill first when the request asks for a Lightning app, end-to-end solution, or a business app spanning multiple metadata types.
- Search available skills and load the best-matching per-type metadata skill first when the request targets individual metadata components.

## Initial Gate

Never create files or generate metadata before completing skill selection.

1. Determine whether the request is app-level or metadata-type-level.
2. Search available skills for the request and identify the best-matching candidate skill.
3. If the request is app-level, load the best-matching app-level skill by reading its contents and use it to identify metadata types and dependency order.
4. If the request is metadata-type-level, identify the target metadata type and the best-matching per-type metadata skill for that type. Do not treat skill selection as the per-type skill-load step.
5. Confirm skill selection with:
   `intent=<app|type> selected_skill=<exact-skill-name|none> skill_selection=complete|pending`
6. Set `skill_selection=complete` only after the exact selected skill name has been identified and recorded.
7. Print this exact skill-selection status line in the chat before proceeding.

Do not continue until `skill_selection=complete` and `selected_skill=<exact-skill-name|none>` are recorded.

## Per-Type Loop (a-e)

For each metadata type in scope, whether identified by an app-level skill or requested directly, execute steps a through e below one metadata type at a time. Do not create or modify files for the current metadata type, and do not move to the next metadata type, until steps a through e are complete.

**a. Load Skill**
- Search available skills for the best-matching skill for the current metadata type and load it by reading its SKILL.md.
- Record `selected_skill=<exact-skill-name|none>` for the current metadata type before proceeding.
- Load once per type, not per record.
- If no skill exists after a real search, stop and ask for guidance instead of writing without a skill.

**b. Use `salesforce-api-context` MCP**
- Use one or more of these tools as required:
  - `get_metadata_type_sections`
  - `get_metadata_type_context`
  - `get_metadata_type_fields`
  - `get_metadata_type_fields_properties`
  - `search_metadata_types`
- Attempt API context for every type before writing.
- Record which tools were called for the current metadata type before proceeding.
- If API context is unavailable after a real attempt, record that state and continue with the loaded skill only.
- Treat templates, generators, pipelines, and CLI bootstraps as implementation aids, not as replacements for this gate.

**c. Pre-Write Gate**
- Before EVERY write: confirm `selected_skill=<exact-skill-name>` is recorded and that skill is loaded for this type.
- Before EVERY write: confirm `mcp_tools=<tool-list>` is recorded for this type, or confirm `mcp=unavailable` after a real attempt.
- If `selected_skill=none` or the skill is missing -> stop.
- If `mcp_tools=none` and `mcp` is not `unavailable` -> stop and call MCP now.

**d. Generate Files**
- Use skill constraints + API context when available.
- Use skill constraints only when API context was unavailable after a real attempt.
- Generate all records for this type now.

**e. Checkpoint**
- Record:
  `type=<metadata-type> selected_skill=<exact-skill-name|none> skill=complete|pending mcp=complete|pending|unavailable mcp_tools=<tool-list|none>`
- Skill loaded? API context called or unavailable after a real attempt? All files written?
- Only proceed to the next type when all are true.

## Anti-Patterns

| Don't | Why | Do |
|-------|-----|-----|
| Never write without loading the metadata skill | Missing platform constraints | Search for and load the skill before any write |
| Never mark `skill_selection=complete` without `selected_skill=<exact-skill-name|none>` | Fake gate completion | Record the exact selected skill before continuing |
| Never treat skill selection as skill loading | Fake gate completion | Perform the actual per-type skill load in step a |
| Never skip the Initial Gate | Sequence breach | Complete skill selection before any generation |
| Never reload a skill per record | Wastes tokens | Load once per type |
| Never skip the API context attempt for any type | No schema for those types | Attempt API context for EVERY type |
| Never write using API context alone without a loaded skill | Missing platform constraints | Stop and ask for guidance when no skill exists |
| Never write without recorded `mcp_tools` or `mcp=unavailable` | No evidence of MCP gate completion | Record MCP tool usage before any write |
| Never ask more than 1 clarifying question | Token waste | Max 1 question |
| Never skip any gate in the loop (skill load, API context, pre-write, checkpoint) | Wrong artifacts | Follow all mandatory gates in the loop (a-e) |
| Never write with a missing checkpoint | Aware violation | Stop and complete missing step |

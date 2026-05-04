# Progressive Disclosure — What Goes Where

SKILL.md is the workflow controller. It tells the agent what to do and when to read other files.
It does **not** contain the detailed content itself.

## Hard Rules

These are not guidelines. Always follow them.

| Content type | Goes in | Example filename |
|-------------|---------|-----------------|
| Code templates | `assets/` | `service.cls`, `batch.cls`, `rest_resource.cls` |
| XML schemas / metadata templates | `assets/` | `meta_template.xml`, `object_schema.xml` |
| Config samples, manifests | `assets/` | `sfdx-project.json`, `package.xml` |
| API reference docs | `references/` | `api_patterns.md`, `rest_endpoints.md` |
| Detailed decision tables (> 20 rows) | `references/` | `error_codes.md`, `field_mappings.md` |
| Step-by-step sub-procedures | `references/` | `deployment_steps.md`, `migration_guide.md` |
| Edge case handling guides | `references/` | `edge_cases.md`, `null_handling.md` |
| Full input/output examples | `examples/` | `basic_usage.md`, `AccountService.cls` |
| Sample generated files | `examples/` | `example_output.xml`, `sample_trigger.trigger` |

## What Stays in SKILL.md

Only these belong in the main file:

- **Frontmatter** (name, description, metadata)
- **Overview** (1-3 sentences)
- **Scope** (in/out boundary)
- **Required Inputs** (bullet list of what to gather)
- **Workflow** (numbered steps with read instructions to subdirectory files)
- **Rules/Constraints** (short table — max 15 rows)
- **Gotchas** (short table — max 10 rows)
- **Output Expectations** (file list only, not content)
- **Cross-Skill Integration** (delegation table)
- **Reference File Index** (maps every subdirectory file to its trigger)

Target: **< 300 lines** for SKILL.md body.

## How to Reference from SKILL.md

Every file in a subdirectory needs a specific load instruction in the workflow section.

**Good — embedded in a workflow step:**

```markdown
1. **Read the service template** — load `assets/service.cls` before generating.
2. **Check error handling patterns** — if the class needs custom exceptions, read `references/error_handling.md`.
3. **Compare against example** — verify output matches `examples/AccountService.cls`.
```

**Good — in the Reference File Index:**

```markdown
| File | When to read |
|------|-------------|
| `assets/service.cls` | Before generating any service class |
| `references/error_handling.md` | When implementing custom exception handling |
| `examples/AccountService.cls` | To verify generated output matches expected format |
```

**Bad — vague references the agent will ignore:**

```markdown
See the `references/` directory for more details.
Check `assets/` for templates.
```

## Common Mistakes

| Mistake | Why it's wrong | Fix |
|---------|---------------|-----|
| Inlining a 50-line code template in SKILL.md | Bloats the file, wastes tokens on every invocation | Put in `assets/`, add a read instruction |
| Pasting an API spec into the workflow | Spec content is static reference, not workflow | Put in `references/`, read only when needed |
| Adding example output inline | Examples are for validation, not every-run context | Put in `examples/`, reference from output section |
| Creating subdirectory but not referencing it | Agent never reads unreferenced files | Add entry to Reference File Index |
| Using "see references/" without naming a file | Agent doesn't know which file to read | Always name the specific file |

## Token Budget

| Component | Target | Maximum |
|-----------|--------|---------|
| SKILL.md body | < 300 lines | 500 lines |
| Single reference file | < 200 lines | 300 lines |
| Single asset file | No line limit | Keep focused on one template |
| Single example file | < 100 lines | 200 lines |

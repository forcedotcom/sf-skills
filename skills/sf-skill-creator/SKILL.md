---
name: sf-skill-creator
description: "AI-assisted skill authoring pipeline for the afv-library. Use when the user wants to create a new skill, update an existing skill, generate a skill spec, scaffold skill files, or add a new capability to the skill catalog. TRIGGER when: user says create skill, new skill, skill creator, author skill, scaffold skill, generate skill, update skill, add a skill, skill pipeline. DO NOT TRIGGER when: user is directly editing an existing SKILL.md without asking for guided authoring.Invoke this skill whenever someone needs to add a new capability to the afv-library skill catalog, or wants to update/improve an existing skill. This includes creating skills for Apex, metadata, LWC, Flow, Agentforce, or any Salesforce domain."
license: LICENSE.txt has complete terms
metadata:
  version: "1.0"
  stage: Pilot
---

# Instructions

You are a contributor onboarding tool for the [afv-library](https://github.com/forcedotcom/afv-library).
Your job is to take minimal input and generate a complete, validated skill as fast as possible.
Ask **one thing at a time**. Generate first, refine after. Do not explain the pipeline.

The full contribution lifecycle has 5 phases:

| Phase | What | Status |
|-------|------|--------|
| 1 | Gather authoritative input | **This skill handles** |
| 2 | Generate v1 Draft | **This skill handles** |
| 3 | Generate test stubs | **This skill handles** |
| 4 | Run eval, move to Under Review | Next step for contributor |
| 5 | Push PR to afv-library, CI publishes | Final step for contributor |

---

## On Start

If the user passed `$ARGUMENTS` (a skill name), check if `skills/$0/SKILL.md` already exists.
If yes, use `AskUserQuestion`: options `Update existing skill` | `Create new skill with different name`.

Otherwise proceed to Step 1.

---

## Step 1 — Infer or confirm skill type

**Try to infer the skill type from the user's message before asking.**

| If the user mentions… | Infer type |
|----------------------|------------|
| metadata, object, field, validation rule, permission set, flow, layout, component, prompt template | Metadata generation |
| Apex class, trigger, batch, LWC, JavaScript, test class | Code generation |
| deploy, debug, setup, migrate, process, pipeline | Workflow / process |

- If confident: state the inferred type inline. Suggest 2-3 gerund skill names, **pick one as your recommendation, and briefly explain why** (e.g. most specific, matches naming convention, clearest intent). Move to Step 2.
- If genuinely uncertain: use `AskUserQuestion`:

```
question: "What kind of skill do you want to create?"
header: "Skill type"
options:
  - label: "Metadata generation"
    description: "Creates Salesforce metadata — custom objects, fields, validation rules, etc."
  - label: "Code generation"
    description: "Generates Apex classes, triggers, LWC components, or other code artifacts."
  - label: "Workflow / process"
    description: "Guides the user through a multi-step process — deployments, debugging, org setup, etc."
  - label: "Other"
    description: "Something else — I'll describe it."
```

After confirming type, **suggest 2-3 skill names inline** using the gerund naming convention
(e.g., `generating-validation-rule`, `building-data-cloud-connector`). Present as text, not a question.

---

## Step 2 — Describe the skill + gather reference material

**Do not expose step numbers to the user.** Never say "Step 2" or label sections in user-facing messages.

Use `AskUserQuestion` to understand the use case:

```
header: "Use case"
question: "What's the use case for this skill? Tell me what problem it solves, who would use it, and what it should produce.

If you have any examples, schemas, or docs handy, feel free to share them too — a file path, URL, or paste works."
options:
  - label: "I'll describe it here"
    description: "Type your use case and I'll generate from that."
  - label: "I have reference material"
    description: "I'll share a schema, example file, or doc."
```

Read every resource the user provides. Then summarize what you extracted — keep it tight, 2-3 bullets max:

> **Extracted context:**
> • …
> • …

**Now generate the description** using both the user's description and the extracted context.
Expand it to include trigger phrases, `TRIGGER when` / `DO NOT TRIGGER when` clauses, and the word "use".

**Print the description as plain text in your response message first**, then call `AskUserQuestion`. The user cannot see the description inside the tool's question or option fields — it must appear in the message body before the tool call.

Example message format:
```
Here's the skill description I've drafted:

> **Skill name:** `generating-<name>`
>
> **Description:** <full description text here>

Does this capture it?
```

Then use `AskUserQuestion`:

```
question: "Does this description capture what you want the skill to do?"
header: "Description"
options:
  - label: "Looks good (Recommended)"
    description: "Use this and proceed to generation."
  - label: "I want to edit it"
    description: "Tell me what to change."
```

If they edit, incorporate and re-confirm.

**Silent background work before generating:**
- Scan `skills/` for existing skills with overlapping scope (duplicate check).
- Identify dependency candidates from existing skill names.
- Infer gotchas from domain knowledge and the provided reference material.

---

## Step 3 — Generate

Tell the user: **"Generating Skill..."**

Then do the work. Do not ask any more questions.

1. Read `./references/progressive_disclosure.md` — use it to decide what
   goes in SKILL.md vs `assets/` vs `references/` vs `examples/`.
2. Read `./templates/skill_template.md`.
3. Read `./templates/frontmatter_reference.yaml`.
4. Read `./references/best_practices.md`.
5. Generate all files following the rules below.

### What goes WHERE — hard rules

SKILL.md is **only** for the workflow, rules, and gotchas. Everything else goes into subdirectories.

| Content type | Where it goes |
|-------------|---------------|
| Code templates (`.cls`, `.xml`, `.js`, `.html`) | `assets/` |
| Code examples / sample output | `examples/` |
| API specs, schemas, XML definitions | `references/` or `assets/` |
| Detailed reference tables (> 20 rows) | `references/` |
| Step-by-step guides for sub-procedures | `references/` |
| Input/output example pairs | `examples/` |
| Configuration files, manifests | `assets/` |

**What stays in SKILL.md**: frontmatter, overview (1-3 sentences), scope, required inputs,
workflow steps, constraint table, gotchas table (short), output expectations (file list only),
cross-skill integration table, and Reference File Index.

### How to reference files from SKILL.md

Every file in `assets/`, `references/`, or `examples/` **must** have a specific load instruction
in SKILL.md. Use this pattern:

```markdown
1. **Read the service template** — load `assets/service.cls` before generating.
2. **For REST endpoints**, read `references/rest_api_patterns.md` for status codes.
3. **See example output** in `examples/basic_service.cls` for the expected structure.
```

Never write "see references/ for details." Always name the specific file and scenario.

### Directory structure to create

```
skills/<skill-name>/
├── SKILL.md                  # Workflow + rules + gotchas ONLY (target < 300 lines)
├── assets/                   # Code templates, XML schemas, config files
├── references/               # Prose docs, detailed tables, sub-guides
├── examples/                 # Input/output pairs, sample generated files
└── tests/
    └── evals/
        ├── <skill-name>-<scenario-1>/
        │   ├── prompt.md     # Exact trigger prompt (no heading — just the prompt text)
        │   └── gold/         # Expected output artifact
        ├── <skill-name>-<scenario-2>/
        │   ├── prompt.md
        │   └── gold/
        └── <skill-name>-<scenario-3>/
            ├── prompt.md
            └── gold/
```

Read `./templates/tests_structure.md` before scaffolding `tests/`.

Create `assets/`, `references/`, and `examples/` only if there is content to put in them.
Do NOT create `tests/unit/` — only create `tests/evals/` with 2-3 datasets.

### Generating SKILL.md content

**Frontmatter — always set `stage: Draft`:**

```yaml
---
name: <skill-name>
description: "<from Step 2>"
license: LICENSE.txt has complete terms
metadata:
  version: "1.0"
  stage: Draft
---
```

**Body rules:**
- Add what the agent lacks, omit what it knows.
- Task-oriented: every section = an instruction, not a description.
- Target < 300 lines for SKILL.md body.

**Required sections:**

| Section | What to write |
|---------|---------------|
| Title + overview | 1-3 sentences — what and why |
| Scope | In-scope / out-of-scope boundary |
| Required Inputs | What context to gather before acting |
| Workflow | Numbered steps with `read` instructions |
| Rules | Hard constraints table |
| Gotchas | Short table of pitfalls — max 10 rows |
| Output Expectations | List of files produced (not their content) |
| Cross-Skill Integration | When to delegate (if applicable) |
| Reference File Index | Maps every subdirectory file to when it's read |

### Write all files

1. Write `skills/<skill-name>/SKILL.md`.
2. Write each `assets/` file — code templates, schemas.
3. Write each `references/` file — detailed guides, tables.
4. Write each `examples/` file — sample inputs/outputs.
5. Write `tests/evals/` datasets — see Step 4 below for eval content rules.

### Validate

Run the validator:

```bash
npx tsx scripts/validate-skills.ts 2>&1
```

For the full list of rules, see `./references/validation_rules.md`.

**If validation fails**: fix the issues and re-run. Only surface to the user if you cannot
resolve an issue yourself.

---

## Step 4 — Review

Tell the user:

> **"Your skill is generated and in draft state — please review and let me know if you'd like any changes."**

Then print the file tree and key decisions:

```
skills/<name>/
├── SKILL.md
├── assets/<files>
├── references/<files>
├── examples/<files>
└── tests/
    └── evals/<dataset-1>/, <dataset-2>/, <dataset-3>/

Key decisions:
• <e.g. "Formula reference table moved to references/ — 25 rows, too large for SKILL.md">
• <e.g. "assets/template.xml built from the schema provided in context">
• <e.g. "5 gotchas inferred from domain knowledge">
```

Use `AskUserQuestion`:

```
question: "Would you like to make any changes?"
header: "Review"
options:
  - label: "Looks good"
    description: "Proceed to generating eval datasets."
  - label: "I want changes"
    description: "Tell me what to modify and I'll update the skill."
```

If changes requested: collect feedback, edit files, re-validate, re-print, return here.

---

## Step 5 — Generate eval datasets

Read `./templates/tests_structure.md` before writing eval files.

For each of 2-3 positive trigger scenarios (derived from the skill description):

**`tests/evals/<skill-name>-<scenario>/prompt.md`** — write the exact prompt a user would type.
No heading, no title, no markdown framing — just the raw prompt text:

```
<The exact user message that should trigger this skill>
```

**`tests/evals/<skill-name>-<scenario>/gold/<artifact>`** — expected output file with the
correct extension for the artifact type (e.g. `ContactEmail.validationRule-meta.xml`, `AccountService.cls`).
Infer extension from skill type. Mark with a stub comment at the top:

```
# STUB — review and update expected output before running eval
```

Do **not** create `seed-data/` folders — those are filled in by the contributor during eval.

Use `AskUserQuestion`:

```
question: "Eval stubs generated. How do they look?"
header: "Evals"
options:
  - label: "Looks good"
    description: "Proceed to next steps."
  - label: "Add or change some"
    description: "Tell me what to adjust."
```

---

## Step 6 — Done

Print the final summary:

```
Skill: <name>
Location: skills/<name>/
Stage: Draft

What this skill does:
• <1-line summary of primary capability>
• <key scope boundary or constraint>
• <notable pattern, delegation, or integration>

Next steps:
1. Run the eval prompts in tests/evals/ and review the outputs against gold/.
   When the outputs look right, update the frontmatter: stage: Under Review
2. Once you're happy with the skill, open a PR to forcedotcom/afv-library.
   CI will validate the skill and publish it to the catalog.
```

---

## Gotchas (for you, the agent)

| Issue | What to do |
|-------|------------|
| Description missing "use" | Validator requires it. Always include "Use when..." in generated descriptions. |
| YAML parse error | Descriptions contain `: ` — always wrap in double quotes. |
| Gerund naming | First word must end in `-ing`. Suggest names that follow this. |
| Body over 500 lines | Split into `references/`. See `./references/progressive_disclosure.md`. |
| User gives vague input | Don't ask repeatedly — make your best guess, generate, and confirm. |
| Validation fails | Fix it yourself. Only ask the user if you genuinely can't resolve it. |
| No reference material provided | Generate representative stubs; mark everything `# STUB`. |
| Skill type is clear from user message | Do not ask — infer it, state it, move on. |

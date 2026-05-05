# Skill Authoring Best Practices

Principles for writing high-quality skills. Based on patterns observed across 30+
production skills in the afv-library and the Agent Skills best practices guide.

## Core Principles

### 1. The Extraction Method

The best way to build a skill is to **complete the real task hands-on with an agent in
chat first**. Pay attention to the corrections you make and the context you have to
provide, then extract that exact sequence into your SKILL.md.

1. Perform the task yourself (or watch someone do it) in an agent conversation.
2. Note every decision point, correction, tool invocation, and gotcha encountered.
3. Write the skill as the instructions you wish you had before starting.
4. Feed real execution traces back into the skill.

The first draft usually needs refinement. Run the skill against 3-5 real prompts, read the
full execution trace (not just the final output), and identify false positives, false
negatives, wasted tokens, and vague instructions.

### 2. Explain the Why, Not Just the What

If you find yourself writing ALWAYS or NEVER in all caps, that is a yellow flag. Reframe
and explain the reasoning so the model understands **why** the constraint matters. A model
that understands intent handles edge cases better than one following rigid rules.

**Bad**: "NEVER include `<required>` on MasterDetail."

**Good**: "Omit `<required>` on MasterDetail fields because the platform implicitly
enforces requirement and adding it causes the error: 'Master-Detail Relationship Fields
Cannot be Optional or Required.'"

Favor procedures over declarations. Instead of listing rules, describe the reasoning
process an expert would follow.

### 3. Add What the Agent Lacks, Omit What It Knows

The most common mistake is including general knowledge the LLM already has.
Focus exclusively on:

- **Project-specific conventions** — naming patterns, directory structure, coding standards
  unique to this project.
- **Domain-specific procedures** — workflows, API quirks, deployment steps that are
  not publicly documented or are team-specific.
- **Non-obvious edge cases** — failure modes, known bugs that the agent would not anticipate.

**Omit**: general programming concepts, language syntax, well-known design patterns.
Use this as a filter for what belongs in each tier of the specification.

### 4. Cross-Model Testing

Test your skill against the different models your team uses. A skill that works on one
model may fail on another due to different instruction-following behavior, context window
handling, or default assumptions. Cross-model testing catches brittle instructions that
rely on model-specific quirks rather than clear communication.

### 5. Task-Oriented, Not Concept-Oriented

Structure skills around what the agent should **do**, not what **exists**.

**Bad**: "Apex supports various class types including Service, Selector, Domain..."

**Good**: "1. Identify the class type needed. 2. Read the matching template from assets/.
3. Generate the class following the template pattern."

### 6. Concise Over Comprehensive

Every token in a SKILL.md costs compute and risks confusing the agent with
irrelevant instructions. Cut ruthlessly:

- Remove sections the agent never follows.
- Remove examples that duplicate other examples.
- Remove caveats about edge cases that never happen.

SKILL.md must be under 500 lines. If your skill needs more detail, move content to
`references/` files and link from SKILL.md. Reference files load on demand and are a
good way to avoid diluting critical skill instructions.

## Description Writing

The description is the most important field — it is the **sole mechanism** by which agents
decide whether to activate your skill.

### Requirements

- **100-300 words** — use the full budget.
- Start with what the skill does in imperative form.
- Include the metadata type name and Salesforce terminology.
- List 5+ specific trigger phrases users would say.
- List relevant file extensions (e.g., `.field-meta.xml`).
- Include negative triggers ("Do NOT trigger when...").

### Do

- Front-load the primary use case.
- Include specific keywords users say: "Apex", ".cls", "trigger", "batch job".
- Add `TRIGGER when:` and `DO NOT TRIGGER when:` clauses.
- **Be pushy about triggers**: list implicit triggers where the user may not use the
  domain term directly.
- Keep it factual and specific.

### Don't

- Use vague language: "helps with Salesforce development".
- Include implementation details: "uses the AccountService pattern".
- Make it too narrow: only one exact phrase triggers it.
- Make it too broad: triggers on everything.

### Be Pushy About Triggers

Err on the side of listing more implicit triggers, not fewer. A skill that never fires is
useless; a skill that fires on a near-miss is recoverable. Explicitly call out contexts
where the skill applies **even if the user doesn't name the domain directly**:

> "TRIGGER when: user asks to add a rule, restrict a field, or enforce a policy — even if
> they don't explicitly say 'validation rule' or 'Apex'."

This is especially important for domain keywords the user may not know (e.g., they say
"make this field required" not "add a required validation rule").

### Template

```
<Primary purpose statement>. ALWAYS ACTIVATE when <high-confidence triggers>.
Use this skill for <broader use cases>. TRIGGER when: <specific list — include implicit
contexts where the user may not use the exact domain term>.
DO NOT TRIGGER when: <exclusions with delegation targets>.
```

## Workflow Structure

### Phase-Based

For multi-step skills, use numbered phases:

```markdown
### Phase 1 — Discover
1. **Read project conventions** — check for existing patterns.
2. **Identify inputs** — what context is needed.

### Phase 2 — Generate
3. **Read template** — load the matching template.
4. **Author code** — generate following the template.

### Phase 3 — Validate
5. **Run checks** — execute validation tools.
6. **Report** — present results.
```

### Decision Matrices

For complex decisions, use tables instead of nested conditionals:

```markdown
| Scenario | Pattern | Template |
|----------|---------|----------|
| Standard async work | Queueable | assets/queueable.cls |
| Large datasets | Batch Apex | assets/batch.cls |
| Recurring schedule | Schedulable | assets/schedulable.cls |
```

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Wall of text with no structure | Agent can't find relevant instructions | Use headers, tables, numbered steps |
| Generic advice | Wastes tokens on things the agent knows | Add only project-specific knowledge |
| Deeply nested conditionals | Agent loses track of which branch it's in | Flatten into decision tables |
| Too many optional steps | Agent follows all of them, wasting time | Make steps required or remove them |
| Missing gotchas section | Agent hits known pitfalls | Add gotchas from real execution failures |
| Referencing files that don't exist | Agent hallucinates content | Verify all referenced paths exist |
| Duplicating content from other skills | Wastes tokens and risks staleness | Reference the other skill instead |

## Cross-Skill Integration Patterns

When your skill needs another skill's capability:

1. **Delegate explicitly**: "For Apex tests, delegate to `generating-apex-test` skill."
2. **Define boundaries clearly**: "This skill handles X. For Y, use Z skill."
3. **Don't duplicate**: If another skill covers a topic, reference it, don't copy.

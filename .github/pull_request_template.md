**References:** [Contributing guide](../CONTRIBUTING.md) · [Skill authoring guide](../README.md) · [Agent Skills spec](https://agentskills.io/specification)

## What changed

<!-- Briefly describe what skill(s) were added, updated, or removed. -->

## Why

<!-- What gap does this fill, or what problem does it solve? -->

## Notes

<!-- Anything reviewers should know — testing approach, follow-ups, open questions. -->

---

## Skills

### Manual checklist

**Description quality**
- [ ] Describes what the skill does and the expected output
- [ ] Includes relevant Salesforce domain keywords (Apex, LWC, SOQL, metadata types, etc.)
- [ ] Trigger phrases are specific enough for Vibes to select this skill reliably

**Instructions**
- [ ] Clear goal statement
- [ ] Step-by-step workflow
- [ ] Validation rules for generated output
- [ ] Defined output / artifact

**Context efficiency**
- [ ] Core instructions are concise — supporting material lives in `templates/`, `examples/`, or `docs/` subdirectories
- [ ] No unnecessary background explanation in the body

### Automated checks

Enforced by CI ([`npm run validate:skills`](../scripts/validate-skills.ts)) per the [Agent Skills spec](https://agentskills.io/specification):

- Directory is one level deep, named in kebab-case (max 64 chars), contains `SKILL.md`
- Frontmatter `name` matches directory name; `description` is present, ≥ 20 words, ≤ 1024 characters, and includes trigger language
- Body is non-empty and under 500 lines
- Name uses gerund form ⚠ (warning — does not block merge)

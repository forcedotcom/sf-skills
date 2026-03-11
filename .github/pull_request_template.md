## What changed

<!-- Briefly describe what skill(s) were added, updated, or removed. -->

## Why

<!-- What gap does this fill, or what problem does it solve? -->

## Notes

<!-- Anything reviewers should know — testing approach, follow-ups, open questions. -->

---

# Skills

## Checklist

**Naming**
- [ ] Name uses gerund form — first word ends in `-ing` (e.g. `generating-apex-tests`)

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

---

**Automated checks** — enforced by CI (`npm run validate:skills`):

- Directory is one level deep, named in kebab-case, contains `SKILL.md`
- Frontmatter `name` matches directory name; `description` is present, ≥ 20 words, and includes trigger language
- Body is non-empty and under 500 lines

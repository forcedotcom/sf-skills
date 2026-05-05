# PR Quality Checklist

Use this checklist when reviewing a pull request that adds or modifies a skill in the
afv-library. Every item should pass before the PR is approved.

---

## Frontmatter

- [ ] `name` is kebab-case and matches the directory name exactly
- [ ] `description` is 100-300 words with 5+ trigger phrases
- [ ] `description` includes file extensions and Salesforce terminology
- [ ] `description` includes negative triggers (DO NOT use when / SKIP when)
- [ ] `description` uses the TRIGGER / SKIP pattern
- [ ] `metadata.version` is present (use "1.0" for new skills)
- [ ] `metadata.related-skills` lists actual afv-library skill names (if applicable)
- [ ] `compatibility` declares required tools/environment (if applicable)
- [ ] `allowed-tools` declares which tools the skill can access (if applicable)
- [ ] `license` is a top-level field, not nested under metadata

---

## Structure

- [ ] SKILL.md is under 500 lines
- [ ] Specification section with tiered constraints (Tier 1-4)
- [ ] Verification Checklist with checkboxes is present
- [ ] Every file in `assets/`, `references/`, or `examples/` has a specific load
      instruction in SKILL.md (no orphaned files)
- [ ] Reference File Index maps every subdirectory file to its trigger
- [ ] Directory name follows gerund naming convention (`generating-`, `building-`, etc.)

---

## Content Quality

- [ ] Every constraint has a rationale (not just "best practice")
- [ ] Incorrect/correct example pairs for every critical (Tier 3) constraint
- [ ] Incorrect examples include exact Salesforce error messages
- [ ] Decision logic uses IF/THEN/DEFAULT format
- [ ] All enumerated values are complete (no "etc." or "and more")
- [ ] No vague instructions ("optionally", "you can also", "consider")
- [ ] No placeholders or TODOs remaining in the skill
- [ ] Constraints explain **why**, not just **what** (per the explain-the-why principle)
- [ ] Clarifying questions only ask about things that cause deployment failure or
      significant rework if assumed wrong

---

## Cross-Skill

- [ ] Related skills referenced by correct name
- [ ] No circular dependencies between skills
- [ ] Scope does not overlap with existing skills in the catalog
- [ ] SKIP/DO NOT TRIGGER clauses delegate to correct skill names

---

## Testing

- [ ] At least 2-3 eval datasets in `tests/evals/`
- [ ] Each eval has a `prompt.md` with a realistic user prompt
- [ ] Each eval has a `gold/` directory with expected output artifacts
- [ ] Gold files use correct file extensions for the artifact type
- [ ] Eval scenarios cover distinct use cases (different objects, types, or complexity)

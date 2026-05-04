# Validation Rules Reference

Complete reference for all validation checks enforced by `scripts/validate-skills.ts`.
The validator runs structure checks first (before reading SKILL.md), then content checks.

## Structure Checks

These run on every entry in `skills/` before SKILL.md is read.
A fatal error aborts all content checks for that entry.

### 1. Entry Must Be a Directory

- **Severity**: Error (fatal)
- **Rule**: No loose files in `skills/` — only directories.
- **Fix**: Move the file into a skill directory or remove it.

### 2. Must Contain SKILL.md

- **Severity**: Error (fatal)
- **Rule**: Every skill directory must have a `SKILL.md` file.
- **Fix**: Create `SKILL.md` with proper frontmatter and body.

### 3. Name Must Be Kebab-Case

- **Severity**: Error
- **Pattern**: `^[a-z0-9]+(-[a-z0-9]+)*$`
- **Allowed**: lowercase letters, digits, hyphens
- **Not allowed**: uppercase, underscores, dots, spaces
- **Examples**:
  - `generating-apex` (valid)
  - `Generating-Apex` (invalid — uppercase)
  - `generating_apex` (invalid — underscore)

### 4. Name <= 64 Characters

- **Severity**: Error
- **Rule**: Directory name must not exceed 64 characters.

### 5. Gerund First Word

- **Severity**: Warning (not blocking)
- **Rule**: First word of the skill name should end in `-ing`.
- **Rationale**: Convention for consistency (e.g., `generating-`, `building-`, `deploying-`).
- **Examples**:
  - `generating-apex` (pass)
  - `agentforce-development` (warning — "agentforce" doesn't end in -ing)

### 6. No Nested Skills

- **Severity**: Error
- **Rule**: No subdirectory of a skill may contain its own `SKILL.md`.
- **Fix**: Flatten nested skills to be siblings under `skills/`.

## Content Checks

These run after SKILL.md is read successfully.

### 7. Valid YAML Frontmatter Block

- **Severity**: Error (fatal)
- **Rule**: SKILL.md must start with `---\n...\n---` YAML frontmatter.
- **Fix**: Add frontmatter between `---` delimiters at the top of the file.

### 8. JSON-Compatible YAML

- **Severity**: Error
- **Rule**: Frontmatter must parse with `js-yaml` JSON_SCHEMA.
- **Common cause**: Unquoted values containing `: ` (colon + space).
- **Fix**: Wrap values in single or double quotes.
  ```yaml
  # BAD
  description: Primary skill: generates Apex classes
  
  # GOOD
  description: "Primary skill: generates Apex classes"
  ```

### 9. `name` Matches Directory

- **Severity**: Error
- **Rule**: The `name` field in frontmatter must exactly match the directory name.
- **Fix**: Ensure `name: generating-apex` if the directory is `skills/generating-apex/`.

### 10. `description` Present and Non-Empty

- **Severity**: Error
- **Rule**: Frontmatter must include a `description` field with content.

### 11. Body Non-Empty

- **Severity**: Error
- **Rule**: There must be content after the frontmatter block.

### 12. Description >= 20 Words

- **Severity**: Error
- **Rule**: Description must contain at least 20 words.
- **Rationale**: Short descriptions don't provide enough trigger context.

### 13. Description <= 1024 Characters

- **Severity**: Error
- **Rule**: Description must not exceed 1024 characters.

### 14. Description Contains "use"

- **Severity**: Error
- **Rule**: Description must include the word "use" (case-insensitive).
- **Rationale**: Enforces trigger/activation language.
- **Fix**: Include phrases like "Use when...", "Use this skill for...", "Used to...".

### 15. Body <= 500 Lines

- **Severity**: Warning (not blocking)
- **Rule**: Skill body should be under 500 lines for context efficiency.
- **Fix**: Extract detailed content into `references/` with conditional load instructions.

## Running Validation

```bash
# Validate all skills
npm run validate:skills

# Validate only changed skills (CI mode)
npm run validate:skills -- --changed --base=origin/main

# Validate a specific skill (filter output)
npx tsx scripts/validate-skills.ts 2>&1 | grep -A5 "<skill-name>"
```

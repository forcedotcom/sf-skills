# Section-by-Section Guide

Detailed quality guidance for every section of a metadata generation SKILL.md.
Use this reference when authoring or reviewing individual sections to ensure each
meets the standards proven across 30+ production skills.

---

## A. Frontmatter Standards (Mandatory)

The YAML frontmatter is the skill's identity and activation mechanism.

```yaml
---
name: {action}ing-{metadata-type}
description: "{PRIMARY_PURPOSE}. Trigger when users mention {METADATA_NAMES},
  {FILE_EXTENSIONS}, or ask to {ACTION_VERBS}. Also use when users say things like
  {TRIGGER_PHRASES}. Always use this skill for any {DOMAIN} metadata work."
metadata:
  version: "1.0"
  related-skills: "{skill1}, {skill2}"
  author: "{team-name}"
  last_updated: "{YYYY-MM-DD}"
  compatibility: "Requires Salesforce CLI, Python 3.9+"
license: Apache-2.0
allowed-tools: Bash Read Write
---
```

### The TRIGGER / SKIP Description Pattern

The description is the sole mechanism by which agents decide whether to activate your
skill. Use the TRIGGER / SKIP pattern (from Anthropic's skill design) to make activation
explicit:

**Good description:**

```
description: "Generate and validate Salesforce Custom Field metadata.
  TRIGGER when: user mentions custom fields, field types, Roll-up Summary,
  Master-Detail, Lookup, formula fields, picklists, .field-meta.xml files,
  or field deployment errors.
  SKIP when: user needs the object itself (use generating-custom-object),
  needs a validation rule (use generating-validation-rule), or needs a
  page layout (use generating-flexipage)."
```

**Bad descriptions** are too vague, contain no trigger keywords, no file types, no
exclusions. The description must be 100-300 words with 5+ specific trigger phrases.

### allowed-tools Field

Declares which tools the skill can access. This scopes the agent's tool use during
skill execution:

```yaml
allowed-tools: Bash Read Write
```

Include only the tools the skill actually needs. Common values: `Bash`, `Read`, `Write`,
`Edit`. If the skill only reads files and generates output, `Read Write` may suffice.

### license Field

Top-level frontmatter field (not nested under metadata):

```yaml
license: Apache-2.0
```

### related-skills

Cross-skill referencing lists actual afv-library skill names. Skills are self-contained;
orchestration between skills happens outside the skill via the agent's routing. List
related skills so the agent knows where to delegate:

```yaml
metadata:
  related-skills: "generating-custom-object, generating-validation-rule"
```

### Key Rule: name Must Match Directory

The `name` field in SKILL.md frontmatter must match the directory name exactly.
`generating-custom-field/SKILL.md` must have `name: generating-custom-field`.

---

## B. Overview / Purpose (Optional)

1-2 paragraphs explaining:
- What this metadata type is.
- What problem the skill solves.
- Which areas have the highest failure rate.

Keep it brief. The overview orients the agent but does not contain actionable instructions.

---

## C. Clarifying Questions (Optional)

Before generating metadata, the agent often needs information the user has not provided.
Rather than guessing (which causes deployment failures), define explicit questions the
agent should ask.

```markdown
## Clarifying Questions

Before generating metadata, ask the user if not already clear:

- What object is this for? (standard object name or custom object API name)
- What field type do you need? (Text, Number, Lookup, Master-Detail, etc.)
- Is this field required? (Note: cannot be set on Master-Detail fields)
- For relationship fields: what is the related object?
- For picklist fields: what are the values?
- Should this be an external ID or unique field?
```

**Guidelines:**
- Only include questions where the wrong assumption leads to deployment failure or
  significant rework.
- Do not ask about things the agent can safely default.
- Order questions from most critical to least critical.
- Include parenthetical notes about constraints that affect the answer (e.g., "cannot be
  set on Master-Detail fields").

---

## D. Specification / Tiered Constraints (Mandatory)

Organize constraints by severity so the agent prioritizes correctly. This four-tier
structure has proven most effective across all metadata generation skills.

### Tier 1 — Syntactic Essentials

Elements that MUST be present for deployment to succeed. Present as a table.

```markdown
## Syntactic Essentials

| Element | Requirement | Notes |
|---------|-------------|-------|
| `<fullName>` | Required | Must end in `__c` for custom |
| `<label>` | Required | Title Case, user-visible |
| `<type>` | Required | Must be a valid Metadata API type value |
```

Every required element gets a row. Keep notes column brief — link to Tier 3 if the
element has complex constraints.

### Tier 2 — Smart Defaults and Decision Logic

Choices the skill makes when the user does not specify. Present as decision trees
using IF/THEN/DEFAULT format.

```markdown
## Smart Defaults

### Sharing Model

| Condition | Value | Rationale |
|-----------|-------|-----------|
| IF object has Master-Detail field | `ControlledByParent` | Required by platform |
| IF object is confidential (HR, finance) | `Private` | Security best practice |
| DEFAULT | `ReadWrite` | Most common for business objects |
```

Every decision point gets its own subsection with a table. Always include a DEFAULT
row. The Rationale column must explain **why**, not just restate the condition.

### Tier 3 — Critical Constraints

Rules that cause the highest deployment failure rate. This is the most important tier.

**Requirements for every Tier 3 constraint:**

1. **Every constraint must have a pair** — both an incorrect and correct example.
2. **Use exact error messages** — do not paraphrase. Paste the real error string so
   agents recognize the error when users report it.
3. **Annotate the incorrect example** — use inline XML comments (`<!-- WRONG -->`)
   pointing to the specific problem.
4. **Keep examples minimal** — show only the elements relevant to the constraint.
   Do not pad with unrelated attributes.
5. **Mark highest-failure-rate constraints with CRITICAL.**

**Example — Custom Field Skill:**

```markdown
### Master-Detail Forbidden Attributes   CRITICAL

Omit `<required>` and `<deleteConstraint>` on MasterDetail fields because the
platform implicitly enforces these and adding them causes deployment errors.

INCORRECT — Master-Detail with forbidden attributes:

  <CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <type>MasterDetail</type>
    <referenceTo>Account</referenceTo>
    <relationshipOrder>0</relationshipOrder>
    <required>true</required>              <!-- WRONG -->
    <deleteConstraint>Cascade</deleteConstraint>  <!-- WRONG -->
  </CustomField>

Errors:
- Master-Detail Relationship Fields Cannot be Optional or Required
- Can not specify 'deleteConstraint' for a CustomField of type MasterDetail

CORRECT:

  <CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <type>MasterDetail</type>
    <referenceTo>Account</referenceTo>
    <relationshipOrder>0</relationshipOrder>
    <reparentableMasterDetail>false</reparentableMasterDetail>
    <!-- NO required, deleteConstraint, or lookupFilter -->
  </CustomField>
```

### Tier 4 — Common Deployment Errors

Error-message-to-fix table. This is a quick-reference troubleshooting section.

```markdown
## Common Deployment Errors

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `DUPLICATE_DEVELOPER_NAME` | API name already exists | Use a unique name |
| `MAX_RELATIONSHIPS_EXCEEDED` | >2 Master-Detail fields | Use Lookup instead |
```

Include the exact error string in backticks. The Cause column should be one phrase.
The Fix column should be an actionable instruction.

---

## E. Type-Specific Rules (Optional)

If the metadata type has subtypes (field types, flow types, page types), document each
with its required attributes in a table.

```markdown
## Field Data Types

| Type | `<type>` Value | Required Attributes |
|------|----------------|---------------------|
| Auto Number | `AutoNumber` | `displayFormat` (must include `{0}`), `startingNumber` |
| Checkbox | `Checkbox` | Default `defaultValue` to `false` |
| Date | `Date` | No precision/length required |
| Lookup | `Lookup` | `referenceTo`, `relationshipName`, `deleteConstraint` |
| Master-Detail | `MasterDetail` | `referenceTo`, `relationshipName`, `relationshipOrder` |
```

**Guidelines:**
- One row per subtype.
- Required Attributes column lists only the attributes unique to that subtype.
- Add notes about constraints that differ from the base type.
- If a subtype has complex rules, reference a Tier 3 constraint rather than repeating it.

---

## F. Verification Checklist (Mandatory)

A checkbox list that must be verified BEFORE presenting output. Every critical constraint
from the specification must have a corresponding checkbox. Organize by concern:

```markdown
## Verification Checklist

### Universal Checks
- [ ] Does `<fullName>` use valid format and end in `__c`?
- [ ] Are `<description>` and `<inlineHelpText>` both populated?

### Master-Detail Field Checks   CRITICAL
- [ ] Is `<required>` attribute ABSENT?
- [ ] Is `<deleteConstraint>` attribute ABSENT?

### Roll-Up Summary Field Checks   CRITICAL
- [ ] Is `<summaryForeignKey>` in format `ChildObject__c.MasterDetailField__c`?

### Naming Checks
- [ ] Is the API name free of reserved words?
- [ ] Does the file name match the API name pattern?

### Architectural Checks
- [ ] Does the sharing model align with relationship fields?
- [ ] Are cross-object references valid?
```

**Guidelines:**
- Every Tier 3 (Critical Constraint) must have at least one corresponding checkbox.
- Group checkboxes by concern (universal, type-specific, naming, architectural).
- Mark groups that correspond to CRITICAL constraints.
- Use question format ("Does X...?", "Is Y...?") for clarity.
- The checklist is the agent's final gate before presenting output to the user.

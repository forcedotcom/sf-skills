# Tests Directory Structure

Every skill in afv-library must include a `tests/` directory. This is the canonical layout.

## Full Structure

```
skills/<skill-name>/
└── tests/
    └── evals/
        ├── <skill-name>-<scenario-1>/
        │   ├── prompt.md            # Exact trigger prompt for this scenario
        │   ├── gold/                # Expected output artifact(s)
        │   └── seed-data/           # Input dependencies
        ├── <skill-name>-<scenario-2>/
        │   ├── prompt.md
        │   ├── gold/
        │   └── seed-data/
        └── <skill-name>-<scenario-3>/
            ├── prompt.md
            ├── gold/
            └── seed-data/
```

---

## evals/

### Dataset naming

`<skill-name>-<short-scenario>` — kebab-case, descriptive, specific to the test case.

Examples:
- `generating-validation-rule-required-field`
- `generating-apex-service-class`
- `deploying-permission-set-with-field-access`

Generate **2-3 datasets** covering the main positive trigger scenarios. Scenarios should be
distinct — different objects, different rule types, or different complexity levels.

### prompt.md

The exact prompt a user would type to trigger the skill for this scenario. No heading, no title,
no markdown framing — just the raw prompt text.

**Format:**
```
<The exact user message that should trigger this skill>
```

**Example:**
```
Create a validation rule that requires the Email field on the Contact object.
```

### gold/

Expected output artifact(s) the skill should produce. Use the correct file extension for the
artifact type — do not use `expected.md`.

| Skill type | Extension examples |
|------------|-------------------|
| Validation rule | `ContactEmailRequired.validationRule-meta.xml` |
| Apex class | `AccountService.cls` |
| LWC component | `myComponent.html`, `myComponent.js` |
| Custom object | `My_Object__c.object-meta.xml` |
| Permission set | `My_Permission_Set.permissionset-meta.xml` |

Mark the top of every gold file as a stub:
```
<!-- STUB — review and update expected output before running eval -->
```
or for non-XML:
```
# STUB — review and update expected output before running eval
```

### seed-data/

Input dependencies the eval needs to run. This is the context the skill would normally gather
from the org or the user:
- Object field lists (JSON)
- Existing metadata samples (XML)
- Schema fragments
- Any other input fixture

Derive from reference material provided during authoring. If none was provided, generate
representative seed data and mark it as a stub.

---

## Lifecycle

| Stage | Who | Action |
|-------|-----|--------|
| Draft | Agent (this skill) | Scaffold all stubs, mark everything `# STUB` |
| Under Review | Contributor | Fill in gold files, validate fixtures, run evals manually |
| Published | CI | Evals run automatically on PRs |

# Rule: Salesforce Metadata Generation

## Objective
Enforce: **skill load → API context → file generation** for all Salesforce metadata.

## Constraints

1. **Never write** without both: metadata type skill loaded AND `Salesforce API Context` MCP Server called for that type
2. **One type at a time** - complete full cycle before next type
3. **Child types need own context** - if adding any child metadata inside a parent metadata's file, load skill and call `Salesforce API Context` for each child type (e.g. CustomField inside CustomObject) separately; don't rely on the parent's schema for creating child metadata
4. **Max one clarifying question** before starting
5. **Don't call `execute_metadata_action` unless a skill instructs to do so**

## Workflow

### 1. Detect Intent
- **App skill** (end-to-end capability like lex/react App) → App Path
- **Direct metadata** (specific fields/objects/pages) → Direct Path

### 2. App Path
1. Load App related skill, extract metadata type sequence
2. For each type, execute loop (a-e below)
3. Proceed to Step 3

### 2. Direct Path
1. Identify all needed types
2. For each type in dependency order, execute loop (a-e below)
3. Proceed to Step 3

### Loop (a-e) - Execute for Each Type

**a. Load Skill**
- Load metadata type skill once (not per record)
- If no skill exists, continue with API context only

**b. Call API Context**
- Use `Salesforce API Context` and make use of these tools as per requirement:
- `get_metadata_type_sections`
- `get_metadata_type_context`
- `get_metadata_type_fields`
- `get_metadata_type_fields_properties`
- `search_metadata_types`

**c. Pre-Write Gate**
- Before EVERY write: confirm API context called for this type
- If no → stop and call now

**d. Generate Files**
- Use skill constraints + API context
- Generate all records for this type now

**e. Checkpoint**
- Skill loaded? API context called? All files written?
- Only proceed to next type when all true

### 3. Deploy Verification
```bash
sf project deploy start --dry-run -d "force-app/main/default" --target-org <alias> --test-level NoTestRun --wait 10 --json
```
On failure: attempt to fix the errors and re-run, retrying up to a maximum of 3 times until it succeeds.

## Anti-Patterns

| Don't | Why | Do |
|-------|-----|-----|
| Write without API context | Missing schema validation | Call API context before first write |
| Reload skill per record | Wastes tokens | Load once per type |
| Skip API context for later types | No schema for those types | Call for EVERY type |
| Skip metadata skills | Missing platform constraints | Load skill for every type |
| Ask 3+ questions | Token waste | Max 1 question |
| Skip App skill gates | Wrong artifacts | Follow all mandatory gates |
| Write despite missing checkpoint | Aware violation | Stop and complete missing step |
| Batch types in API call | Violates constraint #3 | One type per call |
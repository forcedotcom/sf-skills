# Rule: Salesforce Metadata Generation

## Constraints

1. **Never write** without both: metadata type skill loaded AND context tools from `salesforce-api-context` MCP server called for that type.
2. **One type at a time** - finish one type before starting the next
3. **One type per API call** - do not batch types when calling MCP tools
4. **Child types need their own context** - if adding any child metadata inside a parent metadata's file, treat the child metadata seperately; don't rely on the parent's schema for creating child metadata
5. **Max one clarifying question** before starting

## Workflow

### Step 1: Metadata Loop - Execute for Each Type
For each type, execute loop below

**a. Load Skill**
- Load the metadata type skill once (not per record)

**b. Get entity context**
- Use these tools from `salesforce-api-context` MCP server for entity context. 
    - `get_metadata_type_sections`
    - `get_metadata_type_context`
    - `get_metadata_type_fields`
    - `get_metadata_type_fields_properties`
    - `search_metadata_types`


### Step 2. Verify deployment
```bash
sf project deploy start --dry-run -d "force-app/main/default" --target-org <alias> --test-level NoTestRun --wait 10 --json
```
On failure: attempt to fix the errors and re-run, retrying up to a maximum of 3 times until it succeeds.


## Anti-Patterns

| Don't | Why | Do |
|-------|-----|-----|
| Reload skill per record | Wastes tokens | Load once per type |
| Skip metadata skills | Missing platform constraints | Load skill for every type |
| Ask 3+ questions | Token waste | Max 1 question |
| Batch types in calls to MCP tools | Violates constraint | One type per call |
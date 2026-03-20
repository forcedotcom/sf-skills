# Rule: Salesforce Metadata Generation

**Description:** Generate deployment-ready Salesforce metadata by leveraging metadata skills and API context tools.

**⚠ Critical:** This workflow is MANDATORY even when the task seems simple. Do NOT rely on your own knowledge of Salesforce metadata XML — always load the skill and fetch context first.

## Step 1: Metadata Generation Loop

Process each metadata type **one at a time, in order**. Complete the full loop (a → b → c) for one type before starting the next — do not mix types.

**a. Load Skill** — Load the metadata type's skill once (not per metadata file).

**b. Get Entity Context** — Use these tools to fetch entity context for the metadata type:
- `get_metadata_type_sections`
- `get_metadata_type_context`
- `get_metadata_type_fields`
- `get_metadata_type_fields_properties`
- `search_metadata_types`

**c. Generate Files** — Generate all files for that type using the skill + context output. If multiple metadata files are needed (e.g., several Custom Fields), generate them all now — do not re-call tools per metadata file.

**Child metadata:** If a parent file contains child metadata (e.g., fields inside an object), treat the child type separately — load its own skill and call its own context tools.

Do NOT run deployment commands during Step 1.

## Step 2: Deployment Verification

After ALL types are generated, run a dry-run deployment of all metadata together (max 3 retries):

```bash
sf project deploy start --dry-run -d "force-app/main/default" --target-org <alias> --test-level NoTestRun --wait 10 --json
```

On failure: fix the errors and re-run. The task is NOT complete until this command succeeds or all 3 retries are exhausted.

## Guardrails

| Rule | Common Violation |
|------|------------------|
| ALWAYS load skill + call context tools before writing any file — even for "simple" types| Skipping tools because the task "seems easy", then generating incorrect XML |
| Complete the full loop (skill → context → generate) for one type before starting the next | Mixing types — e.g., loading skills for two types before generating either |
| One skill load and one tool-call set per type, not per metadata file | Reloading the skill for each Custom Field |
| Child types need their own skill + context | Using CustomObject context to generate CustomField metadata |
| Deploy all metadata together after generation is complete | Running `sf project deploy` after each type |
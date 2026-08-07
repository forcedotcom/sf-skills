---
name: platform-agentsetup-categories-fetch
description: "Fetch agentic setup prompt categories from a connected Salesforce org using the Connect API. Use this skill to call GET /agenticsetup/categories and return the list of prompt categories, optionally with their nested prompts. TRIGGER when: user asks to get, fetch, list, or show agentic setup categories, prompt categories, setup copilot categories, prompt library categories, available setup prompts, Agentforce prompt library, or copilot prompts. DO NOT TRIGGER when: user wants to create new categories, work with non-categories endpoints, or generate OpenAPI specs."
allowed-tools: Bash Read
metadata:
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  version: "1.0"
  minApiVersion: "67.0"
---

# platform-agentsetup-categories-fetch

Fetch prompt categories from the Agentic Setup Categories Connect API on a connected Salesforce org.

## Scope

**In scope:**
- Calling `GET /services/data/{apiVersion}/agenticsetup/categories` via SF CLI
- Passing the `fetchPrompts` query parameter to include nested prompts
- Parsing and presenting the JSON response (categories, labels, prompts)
- Handling errors (403 when feature is disabled, auth failures)

**Out of scope — delegate elsewhere:**
- Creating or modifying prompt categories → not supported via this API (read-only)
- Org authentication setup → use `sf org login` separately
- Permission set assignment → assigning-permission-set

---

## Required Inputs

The agent needs:
- A connected org (already authenticated via `sf org login`)
- Optionally: whether to include nested prompts (`fetchPrompts=true`)
- Optionally: target API version (default: v67.0). Replace `v67.0` in the URL with the user-specified version if provided.

---

## Workflow

### 1. Verify org connectivity

```bash
sf org display --json
```

Confirm the org is authenticated and extract the instance URL. If no default org is set, ask the user which org to target with `--target-org`.

### 2. Call the Categories API

**Basic call (categories only):**
```bash
sf api request rest /services/data/v67.0/agenticsetup/categories --method GET
```

**With nested prompts:**
```bash
sf api request rest "/services/data/v67.0/agenticsetup/categories?fetchPrompts=true" --method GET
```

### 3. Parse and present the response

The API returns a JSON object with a `categories` array. Each category has `name`, `label`, and `prompts` fields. See `references/api-response-schema.md` for the full response structure and examples for both `fetchPrompts=true` and `fetchPrompts=false`.

Present the results clearly:
- List categories with their name and label
- If `fetchPrompts=true` was used, show nested prompts under each category
- Note any categories with empty `prompts` arrays (means no prompts exist for that category)

### 4. Handle errors

| Error | Meaning | Action |
|-------|---------|--------|
| Success (exit 0) | 200 OK | Parse and display results |
| `FUNCTIONALITY_NOT_ENABLED` | Feature not enabled for this org/user | Tell user the Agentic Setup Categories feature needs to be enabled — check Setup > Einstein/Agentforce |
| `INVALID_SESSION_ID` | Session expired | Re-authenticate with `sf org login` |
| `NOT_FOUND` | Endpoint not found | API version too old or feature not deployed to this org |

---

## Rules / Constraints

| Rule | Rationale |
|------|-----------|
| Always use `sf api request rest` — never curl or raw HTTP | curl bypasses `~/.sfdx` session tokens and requires manual Authorization headers, making it brittle |
| NEVER use SOQL queries | Categories are NOT in standard objects — only available via this Connect REST API |
| NEVER generate files (LWC, Apex, XML) | This is a data-fetching task, not a code generation task |
| Default to v67.0 unless user specifies | This is the min-version where the endpoint was introduced |
| Don't pass fetchPrompts unless asked | Reduces payload size; prompts can be large |
| Categories are sorted by label | The API returns them alphabetically — don't re-sort |
| Prompts are sorted by text | Within each category, prompts come alphabetically |

---

## Output Expectations

When finishing, present:

1. **Number of categories** returned
2. **Category list** — name and label for each
3. **Prompts** (if requested) — nested under their category
4. **Any errors** encountered with suggested fixes

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/api-response-schema.md` | When you need to understand the full response structure and field descriptions |

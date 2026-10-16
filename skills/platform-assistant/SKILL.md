---
name: platform-assistant
description: |
  Discover and navigate the Anypoint Platform API developer portal to find APIs,
  agent skills, and schemas. Use when bootstrapping knowledge of the Anypoint
  Platform, onboarding to the API ecosystem, finding available APIs, understanding
  the portal structure, resolving URNs, looking up JTBD skills, understanding
  x-origin dynamic parameters, or planning multi-API workflows.
---

# Anypoint Platform Operations

## Overview

Navigate the Anypoint Platform developer portal to discover available APIs, agent skills, and extension schemas. The portal is the single source of truth for all public Anypoint Platform API specifications and agent-executable workflows. The portal URL is provided in the agent context preamble injected at the top of this file.

The portal exposes three machine-readable discovery files designed for AI agent consumption. Start with `llms.txt` for a quick inventory, read `AGENTS.md` for the full operating manual, and query `registry.json` for programmatic access to every document.

**Important:** All portal files are plain-text source documents (YAML, JSON, Markdown). Always retrieve them with raw HTTP tools (curl, direct GET requests) — never pass portal URLs through summarizer or browser-rendering tools, which will truncate structured content.

### llms.txt -- Quick Inventory

Fetch `{portal-url}/llms.txt` for a lightweight, one-page summary following the [llmstxt.org](https://llmstxt.org) convention. It lists:

- A link to `AGENTS.md` (the full agent entry point)
- A link to `registry.json` (the machine-readable catalog)
- Schema references for `x-origin` and JTBD extensions
- Every public API with a one-line description
- Every agent skill with a one-line description

Use `llms.txt` when you need a quick overview of what the portal offers before diving deeper.

### AGENTS.md -- The Agent Operating Manual

Fetch `{portal-url}/AGENTS.md` for the complete reference designed specifically for AI agents. This is the most important file to read thoroughly. It covers:

- **Site structure** -- where every file type lives (specs, skills, schemas)
- **Registry format** -- field definitions for `registry.json` entries
- **URN scheme and resolution** -- how to convert identifiers to fetchable URLs:
  - `urn:api:{slug}` resolves to `{portal-url}/apis/{slug}/api.yaml`
  - `urn:skill:{slug}` resolves to `{portal-url}/skills/{slug}/SKILL.md`
  - `urn:schema:x-origin` resolves to `{portal-url}/schemas/x-origin.schema.json`
- **API spec conventions** -- `operationId` format, authentication, server variables
- **x-origin extension** -- how dynamic parameters reference other APIs
- **Skill format (JTBD)** -- step structure, input types, output chaining
- **Common agent workflows** -- step-by-step patterns for discovery, execution, and resolution

### registry.json -- Programmatic Catalog

Fetch `{portal-url}/registry.json` for the complete document index as a flat JSON array. Each entry contains:

- `$id` -- URN identifier (e.g., `urn:api:api-manager`)
- `kind` -- document type: `oas` (API spec), `agent-skill`, `json-schema`, or `schema-doc`
- `slug` -- URL-safe short name
- `name` and `description` -- human-readable metadata
- `href` -- relative path to the raw source file
- `docs` -- relative path to the rendered HTML page
- `apis` -- (skills only) array of API slugs this skill references

Filter by `kind` to segment the catalog:

- Find all APIs: `kind == "oas"`
- Find all skills: `kind == "agent-skill"`
- Find skills for a specific API: `kind == "agent-skill"` AND `apis` contains the target slug
- Find extension schemas: `kind == "json-schema"` or `kind == "schema-doc"`

### Understanding x-origin (Dynamic Parameters)

Many API parameters have valid values that come from another API's response. These parameters carry an `x-origin` annotation in the OpenAPI spec:

```yaml
parameters:
  - name: environmentId
    in: path
    schema:
      type: string
    x-origin:
      - api: urn:api:access-management
        operation: listEnvironments
        values: "$.data[*].id"
        labels: "$.data[*].name"
```

To resolve an `x-origin` parameter:

1. Read the `x-origin` array on the parameter
2. For each source, resolve the API URN to fetch the referenced spec
3. Find and call the referenced `operation` (by `operationId`)
4. Apply the `values` JSONPath expression to extract valid identifiers
5. Optionally apply the `labels` JSONPath to get human-readable display names

The `values` field is always required. The `labels` field is optional -- when absent, display the value directly. Both can be single JSONPath strings or arrays of paths.

Full schema: `{portal-url}/schemas/x-origin.schema.json`
Documentation: `{portal-url}/schemas/x-origin-schema.md`

### Understanding JTBD Skills

Skills are multi-step API workflows written in markdown. Each skill's `SKILL.md` contains:

1. **YAML frontmatter** with `name` (kebab-case) and `description` (includes trigger terms for agent matching)
2. **Numbered steps** (`## Step N: Title`) each containing a YAML code block with:
   - `api` -- URN of the target API (e.g., `urn:api:api-manager`)
   - `operationId` -- the operation to call
   - `inputs` -- parameter mappings with four possible types
   - `outputs` -- values to capture for subsequent steps

The four input types are:

| Type | Syntax | Use when |
|---|---|---|
| From another API | `from.api` + `from.operation` + `from.field` | Value must be fetched from an API call |
| From previous step | `from.variable` | Using an output captured earlier in the workflow |
| Literal | `value: "..."` | Static constant known in advance |
| User-provided | `userProvided: true` | Agent must prompt the user or use context |

Outputs chain between steps -- a value captured as `name: environmentApiId` in Step 1 can be referenced as `from.variable: environmentApiId` in Step 2.

Some skills define **Execution Paths** -- alternative routes through the steps depending on what the agent already has (e.g., skip authentication if already logged in).

Full schema: `{portal-url}/schemas/jtbd-schema.md`
Template: `{portal-url}/schemas/jtbd-template.md`

## Fetching Strategy

Portal files (`*.md`, `*.yaml`, `*.json`) are plain-text source documents, NOT rendered web pages. When retrieving them:

1. **Use raw HTTP tools** (curl, direct GET, file-read tools) — NOT browser-rendering or summarizer tools (e.g., WebFetch). Summarizers truncate structured content like JSON arrays, YAML code blocks, and tables.
2. **Parse responses verbatim** — `registry.json` must be parsed as JSON, API specs as YAML, and skills as Markdown. Do not summarize or abbreviate.
3. **Fetch files individually** when you need their content:
   - Registry: `GET {portal-url}/registry.json`
   - API spec: `GET {portal-url}/apis/{slug}/api.yaml`
   - Skill definition: `GET {portal-url}/skills/{slug}/SKILL.md`
   - Agent guide: `GET {portal-url}/AGENTS.md`

## Prerequisites

1. **Network access** -- ability to make HTTP requests to the portal URL (see agent context preamble for the base URL)
2. **Anypoint Platform credentials** (for executing skills) -- Bearer token or OAuth2 client credentials for API calls
3. **HTTP fetch capability** -- ability to fetch and parse YAML, JSON, and Markdown responses directly (raw HTTP, not via summarizer)

## Tips and Best Practices

### Discovery Strategy

- **Start with `registry.json`** for programmatic discovery -- it is structured, filterable, and machine-parseable
- **Read `AGENTS.md`** when you need to understand conventions, resolve ambiguity, or learn how the portal works
- **Use `llms.txt`** for a quick, lightweight overview before committing to a deeper exploration
- **Always use raw HTTP tools** (curl, direct GET) for portal files -- never use summarizer tools that pass content through an intermediate model

### Working with x-origin

- **Always check x-origin** on parameters before hardcoding values -- dynamic enums change per organization and environment
- **Chain x-origin calls**: one API's x-origin often references Access Management, which itself provides foundational IDs for other APIs
- **Cache `organizationId` and `environmentId`** -- they are reused across nearly every API call and rarely change within a session
- **Read the full x-origin array** -- some parameters offer multiple sources (e.g., different API endpoints for different contexts)

### Skill Execution

- **Read the full skill before starting** -- execution paths may let you skip steps if prerequisites are already met
- **Chain variables between steps** -- outputs from one step become inputs to the next via `from.variable`
- **Check the troubleshooting section** of each skill when errors occur -- skills document known failure modes and solutions
- **Resolve user-provided inputs early** -- gather all `userProvided: true` inputs before starting execution to avoid mid-workflow interruptions

### Portal Navigation

- **Raw files via `href`** -- use this for machine consumption (OpenAPI YAML, SKILL.md, JSON Schema)
- **Rendered pages via `docs`** -- use this when you need HTML documentation (useful for extracting formatted content)
- **URN resolution** -- always resolve URNs through the portal URL, never hardcode file paths

## Troubleshooting

### Portal Files Not Accessible

**Symptoms:** HTTP errors when fetching llms.txt, AGENTS.md, or registry.json

**Possible causes:**
- Incorrect portal URL
- Network connectivity issues
- Portal is being redeployed

**Solutions:**
- Verify the base URL matches the one in the agent context preamble at the top of this file
- Check that the full URL path is correct (no trailing slash issues)
- Retry after a brief wait if the portal is temporarily unavailable

### Registry Returns Empty or Unexpected Results

**Symptoms:** registry.json parses but filtering returns no results

**Possible causes:**
- Using wrong `kind` value for filtering
- API slug does not match any entry

**Solutions:**
- Valid kind values are exactly: `oas`, `agent-skill`, `json-schema`, `schema-doc`
- List all slugs first to find exact matches (slugs are kebab-case, e.g., `api-manager` not `API Manager`)
- Skills have an `apis` array field -- APIs do not have a `skills` field

### URN Resolution Fails

**Symptoms:** Fetching a URL constructed from a URN returns 404

**Possible causes:**
- Incorrect URN-to-URL mapping
- API or skill has been renamed or removed

**Solutions:**
- Follow the exact resolution rules: `urn:api:{slug}` maps to `/apis/{slug}/api.yaml`, not `/apis/{slug}.yaml`
- Check `registry.json` for the `href` field which gives the canonical relative path
- For schemas, resolution is not slug-based: `urn:schema:x-origin` maps to `/schemas/x-origin.schema.json`

### x-origin Operation Not Found

**Symptoms:** The operationId referenced in x-origin does not exist in the target API spec

**Possible causes:**
- API spec version has changed
- Incorrect operationId spelling (operationIds are camelCase)

**Solutions:**
- Fetch the latest API spec via its URN and search for the operationId
- Check the API spec's `paths` for all available operations

## Related Jobs

- **secure-api**: Apply security and traffic management policies to an API instance
- **apply-policy-to-api-instance**: Apply a specific policy to an existing API instance
- **setup-service-scanner**: Configure scanners to discover services from cloud platforms
- **run-service-scan-and-view-results**: Execute a scanner and view discovered services

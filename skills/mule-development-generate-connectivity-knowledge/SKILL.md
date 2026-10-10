---
name: generate-connectivity-knowledge
description: >
  Generate connectivity knowledge for a SaaS API when no dedicated Mule
  connector exists. Researches the API from user-defined use cases and
  documentation, produces an OpenAPI 3.0 specification, asks the user for
  credentials, validates every operation against the live API with auto-fix,
  and writes connectivity-schema/<apiName>/ (api-reference.md +
  <apiName>.yaml + config.properties). The resulting folder feeds downstream
  HTTP-Connector flow generation in build-mule-integration so an HTTP
  fallback path inherits the same auth, pagination, and entity awareness a
  dedicated connector would carry. Use when the user's prompt names a SaaS
  for which no Exchange connector was found, or asks to "generate api
  knowledge", "research a SaaS API", "build connectivity schema", "validate
  spec against live API", or similar phrasings.
license: Apache-2.0
compatibility:
  required_tools:
    - WebSearch
    - WebFetch
    - Read
    - Write
    - Edit
    - Bash
metadata:
  author: ms-interpreted-connectivity-tooling
  version: "1.0.0"
---

# Generate Connectivity Knowledge

This skill produces the connectivity knowledge a Mule HTTP-Connector flow needs in order to integrate with a SaaS that has no dedicated Mule connector in Exchange. It walks three stages — **research the API**, **generate an OpenAPI 3.0 spec**, **validate every operation against the live service** — and writes a self-contained folder at `connectivity-schema/<apiName>/` containing `api-reference.md`, `<apiName>.yaml`, and a placeholder `config.properties`.

`build-mule-integration` invokes this skill from its Step 3a (HTTP-fallback branch) when `get_latest_connector.sh` finds no plausible connector for a system. The flow generator then reads the produced knowledge to wire the HTTP Request operations with correct auth, pagination, and entity shapes.

## Who consumes the output

- **`build-mule-integration` Phase 2** — uses `api-reference.md`'s Authentication, Rate Limits, Use Cases, and Entity Reference sections to generate HTTP Request configs and DataWeave transforms.
- **The user, post-merge** — `<apiName>.yaml` is a real OpenAPI 3.0 spec they can publish to Exchange or feed into other tooling.

Every artifact this skill produces should serve at least one of those consumers. If a piece of information helps neither construct a request, validate a response, wire a dependency, nor collect credentials, it does not belong here.

## Autonomy principle

The research and spec-generation stages run autonomously — no user prompts. The live-validation stage runs autonomously **except** for four mandatory pause points:

1. **Credential collection** — when `config.properties` does not exist or lacks required keys, the skill creates it with placeholders, asks the user to fill it in, and waits. **Mandatory** — do NOT skip validation, write a placeholder report, or proceed without credentials.
2. **Entity IDs** — when an operation requires references to existing entities, the skill asks the user to provide them.
3. **Destructive operation confirmation** — before executing DELETE or destructive PUT, the skill warns the user about consequences and asks for confirmation.
4. **Unresolvable failures** — after the validation loop completes, if any operations failed, the skill asks the user how to proceed (retry / keep / remove / cancel).

Auth failures (401/403) halt the loop immediately and present a halt report; that is not an interactive pause, the loop simply stops.

Everything else — operation selection, request construction, execution, schema comparison, error handling, retries — happens silently. The user sees a compact progress line and the final result.

## Credential Security — MANDATORY

These rules apply throughout the entire workflow. Violating them is a critical failure.

1. **NEVER** read, display, echo, log, or reason about credential values from `config.properties`.
2. To verify a credential key exists, use `grep -c '^KEY_NAME=' config.properties` — this returns a count (0 or 1), not the value.
3. To inject credentials into `curl` commands, use inline shell substitution: `$(grep '^KEY_NAME=' config.properties | cut -d'=' -f2-)`. The value flows through the shell but never enters conversation context.
4. If a curl command's output accidentally contains credentials (e.g., in error messages), do NOT repeat that output. Summarize the result without the sensitive content.

## Workflow

```
INPUTS → DOC_DISCOVERY → PRIMARY_ENDPOINTS → PRIMARY_ENTITIES → CRUD_COMPLETION
       → DEPENDENCY_ANALYSIS → SECONDARY_CRUD → ACTION_PLAN → DEEP_RESEARCH
       → API_REFERENCE_CONSOLIDATION → OPENAPI_SPEC_GENERATION
       → VALIDATION_PREREQUISITES → VALIDATION_LOOP → FINAL_REPORT
```

Execute the steps below in order. Do not skip ahead — every step depends on the output of the previous one.

---

## Step 1: Inputs

Parse the following from `$ARGUMENTS` or ask the user if missing:

1. **`apiName`** — the SaaS platform / API name in kebab-case (e.g., `canva-lms`, `jira`, `coda`). This becomes the subfolder under `connectivity-schema/` and the OpenAPI filename.
2. **`useCases`** — one or more concrete operations the integration needs. Examples:
   - "Get the newest courses and notify on new ones"
   - "Retrieve a Jira ticket and update its status"
3. **`Project Folder`** *(optional)* — directory where output files are written. Defaults to `<workspaceRoot>/connectivity-schema/<apiName>/`. Resolve `<workspaceRoot>` to the active VS Code workspace, or to the current working directory if no workspace is open.
4. **`documentation`** *(optional)* — one or more URLs pointing to the API documentation. When provided (e.g., from a calling skill), these are used directly in Step 2 instead of searching.

Verify items 1–2 are present. If either is missing, ask the user. Do not proceed without them.

Throughout the rest of this skill, `{PROJECT_FOLDER}` refers to the resolved Project Folder. Create it if it does not yet exist.

---

## Step 2: Documentation Discovery

Find the API documentation the agent will read during research.

**If documentation URLs were provided in Step 1:** WebFetch each URL to confirm it is accessible and contains endpoint documentation. If all provided URLs are valid, use them as your documentation sources and skip to the selection step (4 below). Only fall through to WebSearch if the provided URLs are inaccessible or lack endpoint documentation.

1. **WebSearch** for the API's official documentation. Search for:
   - Official REST API reference (e.g., `"{apiName} REST API reference"`)
   - OpenAPI / Swagger specification (e.g., `"{apiName} OpenAPI spec"`)
   - Developer portal or API explorer
2. **Prioritize machine-readable sources** — OpenAPI specs and structured REST references are more useful than blog posts or tutorials because they contain exact field types, required/optional markers, and schema definitions that downstream agents need.
3. **Select the most authoritative sources** and document your selections with reasoning. Typically you need two sources: the human-readable API reference (for context and examples) and a machine-readable spec (for exact schemas).
4. **WebFetch** the selected documentation pages to confirm they are accessible and contain endpoint documentation. If a source is broken or unhelpful, find an alternative.

**Do not proceed until you have at least one confirmed, accessible documentation source.**

Read `references/examples.md` → "Step 2: Documentation Discovery" for a worked example.

---

## Step 3: Primary Endpoint Identification

Map each use case to specific API endpoints. These are the endpoints the user explicitly asked for.

**CRITICAL — Use-Case Filtering.** This skill produces a MINIMAL spec that covers the user's use cases plus ONE connectivity-test endpoint (added in Step 11). Do NOT include every endpoint the API offers. The goal is the smallest faithful spec, not a comprehensive catalog.

For each use case, read the confirmed API documentation and identify:

| Column | What to capture | Why (downstream consumer) |
|---|---|---|
| Use Case Action | What the endpoint does | Context for spec generation |
| Method | HTTP method (GET, POST, PUT, DELETE) | Spec generation builds OpenAPI operations |
| Path | Exact path with parameter placeholders | Spec generation + validation construct URLs |
| Path Parameters | Parameter names and types | Spec generation needs types for OpenAPI path items |
| Has Body | Whether the endpoint accepts a request body | Validation needs to know if it should send a body |
| Content Type | Usually `application/json` | Spec generation populates content type |

Build a mapping table with exactly these columns:

```
| Use Case Action | Method | Path | Path Parameters | Has Body | Content Type |
|---|---|---|---|---|---|
| ... | GET | /resource/{id} | id (string) | No | application/json |
```

If a use case maps to multiple endpoints (e.g., updating a Jira ticket status requires the Transitions API, not a simple PUT), include all of them and note the deviation.

If a use case cannot be mapped to an endpoint, flag it and explain why.

**Do not proceed until every use case is mapped to at least one endpoint.**

Read `references/examples.md` → "Step 3: Primary Endpoint Identification" for a worked example.

---

## Step 4: Primary Entity Extraction

Identify the entities that primary endpoints operate on and note their identifiers.

The identifier field is critical for the validation loop in Step 13. When it creates a test entity, it needs to know which field in the response contains the ID to use in subsequent requests. Get this right.

Build a table with exactly these columns:

```
| Entity | Identifier Field | Alt Identifier | Role |
|---|---|---|---|
| Issue | id (string) | key (string, PROJ-123) | Primary |
| Project | id (string) | key (string, PROJ) | Secondary (dependency) |
```

CRUD coverage gaps don't need a separate table — Step 5's CRUD catalog tracks which operations came from the use case vs. CRUD completion via the `Source` column.

**Do not proceed until all primary entities are identified with their identifier fields.**

---

## Step 5: CRUD Completion

For each primary entity, find endpoints for the missing CRUD operations. The validation loop needs these to manage test data:

- **Create** → `test-setup` — create test entities before running the use case
- **List/Search** → `test-validation` — verify operations worked
- **Delete** → `test-cleanup` — clean up after tests
- **Read/Update** → fill out the CRUD surface if endpoints exist

Build a table with these columns:

| Column | What to capture |
|---|---|
| Operation | Create, Read, Update, Delete, List |
| Method | HTTP method |
| Path | Exact path with parameter placeholders |
| Path Parameters | Parameter names and types |
| Has Body | Boolean |
| Lifecycle Purpose | `test-setup`, `test-validation`, `test-cleanup`, or `—` |

If a CRUD operation does not exist in the API (e.g., no Delete endpoint), document it explicitly — the validation loop needs to know this affects cleanup strategy.

**Do not proceed until CRUD gaps are filled for every primary entity.**

---

## Step 6: Dependency Analysis

Identify entities that primary entities **require** to exist. This is the most important phase for the validation loop — it determines operation ordering, test-data creation chains, and which entities must be set up before testing can begin.

### The Mandatory Dependency Test

For each entity referenced by a primary entity, apply this test:

> **"Will the API return an error if I create the primary entity WITHOUT providing a reference to this entity?"**
> - **YES** → **Secondary entity** — include it. The validation loop must create this before creating the primary entity.
> - **NO** → **Excluded** — optional relationship, skip it.

### Capture reference field detail

For each mandatory dependency, record:

| Column | What to capture | Why |
|---|---|---|
| Referenced entity | The dependency entity name | Validation needs to know what to create |
| Required field | The exact JSON field path (e.g., `fields.project.id`) | Validation needs to populate this field in create requests |
| Reference format | Whether it uses ID or key | Validation needs to know which identifier to extract from the dependency's create response |
| Decision | SECONDARY ENTITY / PRE-EXISTING / EXCLUDED | Determines next steps |

### Pre-existing dependencies

Some mandatory fields reference **system-managed entities** that cannot be created or deleted via the API (e.g., issue types, priorities, statuses in Jira). These are not secondary entities — tests discover valid values instead of creating them. For each pre-existing dependency, record the **List/Get endpoint** that returns valid values.

### Walk the tree recursively

Secondary entities may themselves have mandatory dependencies. Apply the same test recursively until you reach entities that can be created standalone (no mandatory dependencies).

### Build the dependency diagram

Create a Mermaid diagram showing the dependency tree. Use solid arrows for mandatory dependencies and dashed arrows for pre-existing dependencies. Include the field reference on each arrow.

### Document all decisions

Log every inclusion, exclusion, and pre-existing classification with reasoning. The workflow is fully autonomous — these decisions need to be reviewable after completion.

**Do not proceed until the full dependency tree is mapped and all decisions are documented.**

---

## Step 7: Secondary Entity CRUD

For each secondary entity identified in Step 6, discover full CRUD endpoints. The validation loop needs these to:

- **Create** the dependency chain bottom-up (e.g., create Project before Issue)
- **Delete** the dependency chain top-down (e.g., delete Issue before Project)

Use the same table format as Step 5 (CRUD Completion), including lifecycle purpose labels and identifier fields for each secondary entity.

**Do not proceed until all secondary entities have full CRUD endpoint catalogs.**

---

## Step 8: Action Plan

Consolidate all findings into a structured action plan organized by downstream consumer. This is the final output of the discovery and planning phases.

### Structure the action plan with these sections

**1. For Spec Generation** (Step 11)
- Primary endpoint catalog — these become OpenAPI operations. Use this table format:

```
| Use Case Action | Method | Path | Path Parameters | Has Body | Content Type |
|---|---|---|---|---|---|
| {action} | {method} | {path} | {params or —} | {Yes/No} | {content type} |
```

- Entity list with identifier fields — these become schema definitions

**2. For Live Validation** (Steps 12–13)
- Full CRUD endpoint catalog (primary + secondary) with lifecycle purpose labels — the validation loop uses `test-setup` endpoints to create test data, `test-cleanup` to delete it
- Dependency graph with field references (Mermaid diagram) — determines operation ordering
- Creation order (bottom-up) and deletion order (top-down) — use inline arrow notation (`→`) on a single line per order (e.g., `Create A → Create B → Create C`), not numbered lists
- Pre-existing dependencies with discovery endpoints — the validation loop calls these to get valid values instead of trying to create
- Decision log — consolidate ALL dependency decisions (included as secondary, pre-existing, excluded) with reasoning into a single table so the validation loop can review why each entity was or was not included

**3. For Credential Collection** (Step 12)
- Auth scheme identified from documentation (if discoverable at this stage): type (Bearer, API Key, Basic, OAuth), required credential keys, header format
- If auth details are not yet clear, note this as a gap for deep research in Step 9

**4. Research Plan**
- Research order: secondary entities first (bottom of dependency tree), then primary. This way, when documenting a primary entity, its dependency details are already known.
- Scope: total entities to research, total endpoints discovered
- Excluded entities with reasoning

### Write the action plan

Save the action plan to `{PROJECT_FOLDER}/action-plan.md` using the Write tool. This file persists the discovery work for the deep research phase (Step 9).

Read `references/examples.md` → "Step 8: Action Plan" for a complete worked example.

---

## Step 9: Deep Research

For each entity in the research plan, read the API documentation and document detailed schemas, fields, and behaviors that downstream consumers need to construct requests, validate responses, wire dependencies, and collect credentials.

**Input:** The action plan from Step 8 (`{PROJECT_FOLDER}/action-plan.md`) provides the research order, endpoint catalog, dependency graph, and documentation sources confirmed in Step 2.

**Documentation source priority:** Use the OpenAPI spec (if available from Step 2) as the primary source for request/response schemas and field details — it has exact types, required/optional markers, and schema definitions. Use the human-readable API reference as a supplement for pagination patterns, rate-limit behavior, side effects, and behavioral details not captured in the spec. If no OpenAPI spec is available, use human-readable docs for everything.

**Critical:** Copy field names, types, and constraints exactly from the documentation. Do not infer or guess field details.

### Processing Order

Follow the Research Plan section from the action plan:

1. Research **API-level notes** first (auth scheme and rate limits — these apply globally)
2. Document **pre-existing entities** next (lightweight treatment — discovery schema only)
3. Research **secondary entities** in bottom-up order (bottom of dependency tree first)
4. Research **primary entities** last

Write each entity's research to the output file immediately after completing it. Do not accumulate all research in conversation before writing.

### API-Level Notes

Before researching individual entities, document two API-level categories. WebFetch the API's authentication and rate-limiting documentation pages.

| Item | What to capture | Why (downstream consumer) |
|---|---|---|
| Auth type | Bearer, Basic, API Key, OAuth | Credential collection needs the injection pattern |
| Header format | Exact header name and value pattern | Validation constructs request headers |
| Required credentials | Credential key names | Credential collection prompts the user |
| Base URL | URL pattern (with variable parts noted) | Validation constructs request URLs |
| Global rate limits | Requests per second/minute | Validation paces requests |
| 429 behavior | Retry-After header? Body format? | Validation implements backoff |
| Retry strategy | Recommended approach | Validation retries failed requests |

### Pre-Existing Entity Treatment

**Pre-existing entities** (identified as PRE-EXISTING in the dependency analysis) are system-managed and cannot be created or deleted via the API. Tests discover valid values instead of creating them.

For each pre-existing entity, document **only**:
1. The discovery endpoint's response schema — what fields come back from the List/Get endpoint
2. The field to extract — which field the downstream consumer needs (e.g., `id`, `name`) and its type

**Skip** request schemas (no Create/Update), field catalog, entity references, pagination, and side effects for pre-existing entities.

### Per-Entity Deep Research

For each secondary and primary entity, research and document the following 6 categories. Auth scheme and rate limits are API-level — do not repeat them per entity.

#### Category 1: Request Schemas

For each operation that accepts a request body (typically Create and Update), document the exact request structure.

| Item | What to capture |
|---|---|
| Operation | Create, Update, or other body-accepting operation |
| Content-Type | `application/json`, `application/x-www-form-urlencoded`, etc. |
| Minimal request body | Smallest valid request (required fields only) |
| Full request body | All fields including optional |

Format each operation as:

```
**Create — POST `/path`**
Content-Type: application/json

Minimal request body (required fields only):
{json}

Full request body (all fields):
{json}
```

If an operation does not accept a body (e.g., DELETE), skip it in this section.

#### Category 2: Response Schemas

For each operation, document the response structure including status code.

| Item | What to capture |
|---|---|
| Operation | Create, Read, List, Delete, etc. |
| Success status code | 200, 201, 204, etc. |
| Response body | Exact JSON structure (or "No response body" for 204) |
| Identifier location | Where the entity ID appears in the response |

Format each operation as:

```
**Read — GET `/path/{id}` → 200**
{json}

**Create — POST `/path` → 201**
{json}

**Delete — DELETE `/path/{id}` → 204**
No response body.
```

For List operations, show the response envelope (wrapper structure with pagination fields) and one item in the collection.

#### Category 3: Field Catalog

A consolidated table of all fields across all operations. This is the single source of truth for field details.

| Column | What to capture |
|---|---|
| Field | JSON path (e.g., `fields.project.id`) |
| Type | string, number, boolean, array, object, or enum |
| Required for | Which operations require this field (Create, Update, both, or —) |
| Constraints | Max length, format pattern, allowed enum values |
| Default | Default value if field is omitted, or — |

Build the table:

```
| Field | Type | Required for | Constraints | Default |
|---|---|---|---|---|
| `name` | string | Create | max 255 chars | — |
| `status` | enum | — | `active`, `inactive` | `active` |
```

For enum fields, list all valid values. If the enum has more than 10 values, list representative values and note "see API docs for full list."

#### Category 4: Entity References

Document how this entity references other entities. This enriches the dependency analysis from Step 6 with field-level detail that the validation loop needs to wire dependencies.

| Column | What to capture |
|---|---|
| Field | The field path that holds the reference (e.g., `fields.project.id`) |
| Referenced Entity | The entity being referenced |
| Reference Format | ID, key, name, or compound |
| Mandatory | Yes / No / Pre-existing |

Build the table:

```
| Field | Referenced Entity | Reference Format | Mandatory |
|---|---|---|---|
| `fields.project.id` | Project | ID (string) | Yes |
| `fields.assignee.accountId` | User | Account ID (string) | No |
```

#### Category 5: Pagination

Document how List/Search endpoints handle pagination. If the entity has no List endpoint, write "No list endpoint — pagination not applicable."

**CRITICAL PAGINATION DETECTION ORDER:**

1. **ALWAYS check for cursor-based pagination FIRST** — look for: `continuation`, `continuation_token`, `next_cursor`, `cursor`, `after`, `before`, `next_page_token`, `offset` (when it's a token/string, not numeric).
2. **Distinguish offset vs cursor**: Offset uses NUMERIC values (0, 10, 20...). If a parameter named `offset` contains TOKEN/STRING values like `"eyJ0eXAi..."`, it's cursor-based, NOT offset.
3. Some APIs include both cursor tokens AND page metadata (page_count, page_number) in responses — the actual pagination mechanism is cursor-based. Always use cursor-based when a continuation/cursor token exists.
4. Only use page-based pagination if documentation explicitly shows "page" parameters AND no cursor indicators exist.
5. Each endpoint has EXACTLY ONE pagination type. NEVER mix types.
6. Search documentation for `"{apiName} pagination"` to find official patterns.

For each List endpoint, document using this **exact structured format**:

```
**List — GET `/path`**
- **Pagination type:** offset | cursor | page | timestamp | none
- **Items field:** {dot-notation path to items array, e.g., "data", "results", "values"}
```

Then include ONLY the fields for the applicable type:

**For cursor:**

```
- **Cursor param:** {query parameter name, e.g., "cursor", "after", "nextToken"}
- **Reference type:** marker | uri
- **Reference expression:** {dot-notation path to next cursor value, e.g., "pagination.nextCursor"}
```

- Use `marker` when the response contains a cursor VALUE (token/string).
- Use `uri` when the response contains a complete URL for the next page.
- NEVER use any other value for reference type — only `marker` or `uri`.

**For offset:**

```
- **Offset param:** {query parameter name, e.g., "startAt", "offset"} — must be NUMERIC
- **Initial offset value:** {number, typically 0}
```

**For page:**

```
- **Page number param:** {query parameter name, e.g., "page", "pageNumber"}
- **Initial page number:** {number, typically 0 or 1}
```

**For timestamp:**

```
- **Timestamp param:** {query parameter name, e.g., "since", "after"}
```

#### Category 6: Side Effects & Behaviors

Document behaviors that affect how downstream agents construct, execute, or validate operations. For each item, write the behavior or "none" if not applicable.

```
- **Delete behavior:** hard delete / soft delete / archive / deactivate / no delete endpoint
- **Cascade on delete:** deleting this entity also deletes {children} / no cascade
- **Immutable fields:** {field list} cannot be changed after creation / none
- **Async operations:** {operation} returns 202, poll {url} for completion / none
- **Conditional requirements:** {field} required only when {condition} / none
- **Non-standard patterns:** {any API-specific quirks, e.g., status changes via transitions}
```

### Write the deep research

Save the deep research to `{PROJECT_FOLDER}/api-reference.md` using the Write tool. Write each entity's section immediately after researching it — do not accumulate all research before writing.

Structure the file as:

```markdown
# {Service} API Reference — Deep Research

## API-Level Notes
{auth scheme + rate limits}

## Pre-Existing Entities
### {Entity} [PRE-EXISTING]
{discovery schema only}

## Secondary Entities
### {Entity} [SECONDARY]
{6 categories}

## Primary Entities
### {Entity} [PRIMARY]
{6 categories}
```

**Do not proceed until every entity in the research plan has been documented with all applicable categories.**

---

## Step 10: api-reference.md Consolidation

Consolidate the action plan (Step 8) and deep research (Step 9) into a single, self-contained `api-reference.md`. After this step, downstream consumers (the OpenAPI generator in Step 11, the validation loop in Steps 12–13, the calling `build-mule-integration` skill) need only this one file — they should never need to read `action-plan.md`.

### Inputs

- `{PROJECT_FOLDER}/action-plan.md` from Step 8
- `{PROJECT_FOLDER}/api-reference.md` from Step 9 (the deep research file)

### Steps

1. **Read** `action-plan.md` and extract:
   - Use case endpoint table (from §1 For Spec Generation)
   - Full CRUD endpoint catalog (from §2 For Live Validation)
   - Mermaid dependency graph (from §2)
   - Creation order and deletion order (from §2)
   - Pre-existing dependencies table (from §2)
   - Decision log table (from §2)
   - Auth scheme details (from §3 For Credential Collection)
   - Documentation source URL (from the header)

2. **Read** `api-reference.md` (Step 9 deep research) and note:
   - API-Level Notes content (Auth Scheme + Rate Limits) — this will become the top-level Authentication and Rate Limits sections
   - All entity sections (Pre-Existing, Secondary, Primary) with their full category detail

3. **Write** the final `api-reference.md` following the exact template below. Use the Write tool to overwrite the Step 9 file with the consolidated output.

### Output template

Write the final `api-reference.md` with exactly this structure:

```markdown
# {Service} API Reference

## Overview
- **Service:** {apiName}
- **API Version:** {version from documentation, e.g., "v3", "v1", "2023-08-01"}
- **Base URL:** {base URL from API-Level Notes}
- **Documentation:** {primary documentation URL from action plan header}

## Authentication
- **Type:** {Bearer / Basic / API Key / OAuth}
- **Header format:** {exact header pattern, e.g., `Authorization: Basic base64({email}:{api_token})`}
- **Required credentials:** {credential key names, e.g., `BASIC_USERNAME`, `BASIC_PASSWORD`}
{include any additional auth details from the deep research — alternative auth methods, transport requirements, test mode info}

## Rate Limits & Constraints
{Rate Limits content from Step 9 API-Level Notes — copy the full detail including global limits, burst limits, 429 behavior, retry strategy, endpoint-specific limits}

## Use Cases

{endpoint table from action plan §1, copied exactly:}

| Use Case Action | Method | Path | Path Parameters | Has Body | Content Type |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

{include any deviation notes from the action plan}

## Entity Dependency Graph

{Mermaid diagram from action plan §2, copied exactly}

- **Creation order:** {bottom-up arrow notation from action plan}
- **Deletion order:** {top-down arrow notation from action plan}

**Pre-existing dependencies (discover, don't create):**

{pre-existing dependencies table from action plan §2, or "None — all mandatory dependencies can be created and deleted via the API." if no pre-existing deps}

**Decision log:**

{decision log table from action plan §2, copied exactly}

## Full CRUD Endpoint Catalog

{CRUD catalog table from action plan §2, copied exactly:}

| Entity | Operation | Method | Path | Lifecycle Purpose | Source |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

## Entity Reference

### Pre-Existing Entities
#### {Entity} [PRE-EXISTING]
{discovery schema only — copied from Step 9}

### Secondary Entities
#### {Entity} [SECONDARY]
{all 6 categories — copied from Step 9}

### Primary Entities
#### {Entity} [PRIMARY]
{all 6 categories — copied from Step 9}
```

### Heading level adjustment

Step 9 writes entity sections with these heading levels:
- `## Pre-Existing Entities`, `## Secondary Entities`, `## Primary Entities`
- `### {Entity} [TYPE]`
- `#### Category N: {name}`

In the final output, these live under the `## Entity Reference` parent, so demote each by one level:
- `### Pre-Existing Entities`, `### Secondary Entities`, `### Primary Entities`
- `#### {Entity} [TYPE]`
- `##### Category N: {name}`

### What NOT to include in Entity Reference

Do not include `## API-Level Notes` (Auth Scheme + Rate Limits) in the Entity Reference section — that content has been extracted into the top-level Authentication and Rate Limits sections. The Entity Reference section starts directly with `### Pre-Existing Entities` (or `### Secondary Entities` if there are no pre-existing entities).

### Verification checklist

Before completing this step, verify the final `api-reference.md` contains:

- [ ] Title is `# {Service} API Reference` (no "Deep Research" suffix)
- [ ] Overview section with base URL
- [ ] Authentication section with type, header format, required credentials
- [ ] Rate Limits & Constraints section
- [ ] Use Cases table with all use cases from input
- [ ] Entity Dependency Graph with Mermaid diagram
- [ ] Creation order and deletion order (inline arrow notation)
- [ ] Pre-existing dependencies table (or "None" statement)
- [ ] Decision log table
- [ ] Full CRUD Endpoint Catalog with lifecycle labels
- [ ] Entity Reference section contains every entity from Step 9
- [ ] All 6 per-entity categories preserved for each secondary and primary entity
- [ ] Pre-existing entities have discovery-only treatment (no request schemas, field catalogs)
- [ ] No duplicated API-Level Notes in Entity Reference

**Do not proceed until all checklist items pass.**

---

## Step 11: OpenAPI 3.0 Spec Generation

Read the consolidated `api-reference.md` from Step 10 and produce a complete OpenAPI 3.0 specification at `{PROJECT_FOLDER}/<apiName>.yaml`. The spec must accurately reflect every operation, schema, parameter, and authentication requirement documented in the api-reference, and nothing more.

### Requirements

- OpenAPI version 3.0.x.
- Complete `info` section: `title` ending with "API", semver `version` (e.g., `1.0.0`), and a one-sentence imperative `description`.
- `servers` section with the base URL (including the API version prefix if the API uses one).
- `paths` section with ONLY the endpoints documented in `api-reference.md`'s Use Cases table — do NOT add endpoints beyond what the research discovered.
- `components` section with: authentication schemes from §Authentication, reusable schemas for request/response bodies, common parameters, error responses.
- For each endpoint: complete parameter definitions (path, query, header, body), full response schemas with data types, error responses (4xx, 5xx), authentication requirements.
- Add ONE connectivity-test endpoint if the API has an obvious lightweight "ping" endpoint (e.g., `GET /me`, `GET /health`). This single extra operation gives Step 12's prerequisites a way to verify credentials before the full loop runs. If the API has no such endpoint, do not invent one — Step 12 will use the first GET in `paths` instead.

### CRITICAL Path and Versioning Rules

- API version (e.g., `/v3`) MUST be in `servers[].url`, NOT in endpoint paths.
- Remove ALL API version prefixes from endpoint paths.
- Endpoint paths MUST NOT end with a trailing slash.

**Correct:**

```yaml
servers:
  - url: https://api.example.com/v3
paths:
  /users:
    get: ...
  /users/{id}:
    get: ...
```

**Incorrect:**

```yaml
servers:
  - url: https://api.example.com
paths:
  /v3/users:
    get: ...
  /users/{id}/:
    get: ...
```

### Other rules

- Every operation has a unique `operationId` in camelCase (e.g., `listCourses`, `getCourseById`).
- Every operation has a `description` (imperative voice, one sentence).
- Every operation has at least one request example and at least one response example.
- Every property in every schema has a `description`.
- Strings with constrained values use `enum` (no naked strings).
- `required` fields are explicit on every object schema where applicable.
- Path and query parameters have descriptions and types.

Write the file with the Write tool. Do NOT show the spec to the user — proceed to Step 12 immediately.

---

## Step 12: Live Validation — Prerequisites

Before entering the per-operation validation loop, verify four prerequisites in order. If any fails, report the specific problem and stop. Do not narrate each check unless it fails.

### 1. OpenAPI Spec File

- Read `{PROJECT_FOLDER}/<apiName>.yaml`.
- Verify it is valid YAML.
- Verify it contains an `openapi` key with a value starting with `3.` (OpenAPI 3.x).
- Verify `paths` contains at least one operation.
- Count the total number of operations — this is **M**, the denominator in the progress line (`N/M`).

### 2. `api-reference.md`

- Read `{PROJECT_FOLDER}/api-reference.md`.
- Verify it contains these sections: **Authentication**, **Entity Dependency Graph**, **Full CRUD Endpoint Catalog**, **Entity Reference**.
- Read the **Authentication** section and extract:
  - Auth type (e.g., Bearer token, Basic, API Key)
  - Header format (e.g., `Authorization: Bearer <TOKEN>`)
  - Required credential key name(s) (e.g., `CODA_API_TOKEN`)
  - For API Key auth: injection location — header name (e.g., `X-API-Key`) or query parameter name(s) (e.g., `key`, `token`)

### 3. `config.properties`

Check whether `{PROJECT_FOLDER}/config.properties` exists.

**If the file does NOT exist — create it:**

1. Take the credential key name(s) extracted in step 2 (e.g., `CODA_API_TOKEN`, or `TRELLO_API_KEY` and `TRELLO_API_TOKEN`).
2. Generate a placeholder value for each key by lower-casing the key name, replacing underscores with hyphens, and wrapping with `your-` and `-here` (e.g., `CODA_API_TOKEN` → `your-coda-api-token-here`).
3. Create `{PROJECT_FOLDER}/config.properties` with one `KEY=placeholder` line per credential:

   ```bash
   printf '%s\n' 'CODA_API_TOKEN=your-coda-api-token-here' > {PROJECT_FOLDER}/config.properties
   ```

   For multiple keys, write all lines in one command:

   ```bash
   printf '%s\n' 'TRELLO_API_KEY=your-trello-api-key-here' 'TRELLO_API_TOKEN=your-trello-api-token-here' > {PROJECT_FOLDER}/config.properties
   ```

4. Report to the user and wait:

   ```
   Created config.properties with placeholder credentials:

     CODA_API_TOKEN=your-coda-api-token-here

   Please replace the placeholder value(s) with real credentials and let me know when ready.
   ```

   **▸ WAIT — Do not proceed until the user confirms the credentials are in place.**

5. Once the user confirms, proceed to **verify keys** below.

**Verify keys** (runs after file creation + user confirmation, or immediately if the file already existed):

- For each credential key identified in step 2, verify the key exists:

  ```bash
  grep -c '^CREDENTIAL_KEY=' {PROJECT_FOLDER}/config.properties
  ```

  The result must be `1`. Do **NOT** read or display the value.

### 4. Base URL

- Read the **Overview** section of `api-reference.md` and extract the `Base URL` value (e.g., `https://coda.io/apis/v1`).
- Verify it starts with `https://` or `http://`.

### Prerequisites check

Verify all four silently. If all pass, proceed to Step 13 without narrating each check. If any fails, report the specific problem to the user and stop.

**▸ STOP — Do not proceed to Step 13 until ALL four prerequisites pass.**

---

## Step 13: Live Validation — Loop

After prerequisites pass, set up the iteration loop before processing individual operations.

### Enumerate operations

Walk the `paths` object in the OpenAPI spec in document order. For each path, for each HTTP method defined on that path (GET, POST, PUT, PATCH, DELETE), record `(method, path)` as one operation. Build an ordered list of all operations. Total count = **M**.

### Collect entity IDs upfront

Before entering the loop, scan **all** operations in the enumerated list for path parameters. For each unique path parameter name:

1. Cross-reference with the **Entity Reference** section of `api-reference.md` to determine which entity the parameter refers to.
2. Build a deduplicated set of `(parameter_name, entity_type, description)`.

If the set is non-empty, prompt the user **once** for all values:

```
The operations in this spec require the following entity IDs:

- `docId` (string) — references a Doc entity. Used by 8 operations. Please provide an existing Doc ID.
- `pageIdOrName` (string) — references a Page entity. Used by 4 operations. Please provide an existing Page ID or name.
```

Store the provided values for reuse during the loop. If no operations have path parameters, skip this step.

### Loop counters

Initialize: `completed = 0`, `passed = 0`, `fixed = 0`, `failed = 0`, `skipped = 0`, `auth_halted = false`, `any_2xx_seen = false`.

For each operation in the enumerated list, in order, reset the per-operation retry state:
- `attempt_count = 0` — incremented every time a curl request is executed for this operation.
- `retry_history = []` — after each attempt, append: `{ attempt_number, status_code, error_summary, fix_applied_if_any }`.
- `last_failure_signature = null` — the `(status_code, error_message_key)` pair from the most recent failed attempt.

Then execute, per operation:

1. Set the current operation to `(method, path)`.
2. **Operation Analysis** — Step 13.1.
3. **Request Execution and Response Validation** — Step 13.2.
4. If `auth_halted` is true, exit the loop immediately — do NOT proceed to steps 5–9. Jump to Step 14.
5. Increment `completed`.
6. Classify the result (`passed`, `fixed`, `failed`, or `skipped`) and update the corresponding counter.
7. Emit the progress line: `Validation: {completed}/{M} | passed {X} | fixed {Y} | failed {Z}` — append `| skipped {S}` only when `skipped > 0`.
8. If the operation failed, emit a detail line: `  ✗ {METHOD} {path}  {status_code} — {reason}`.
9. Proceed to the next operation.

After all operations are processed (or the loop is halted by an auth failure), proceed to **Step 14** (Final Report).

**▸ STOP — Do not enter the loop until all entity IDs are collected (if any were needed).**

### Step 13.1 — Operation Analysis

Read the current operation from the loop and extract everything needed to construct an HTTP request.

**13.1.1 — Identify the current operation.** The operation's `(method, path)` is already determined by the enumeration.

**13.1.2 — Extract the operation definition.** From the spec:

- **HTTP method** (GET, POST, PUT, DELETE, PATCH).
- **Path template** (e.g., `/docs/{docId}/pages/{pageIdOrName}`).
- **Path parameters** — for each: name, type, required (yes/no).
- **Query parameters** — for each: name, type, required, default value.
- **Request body schema** — if the method has a `requestBody` definition (typically POST, PUT, PATCH). Extract required fields and their types.
- **Expected success response** — the 2XX status code declared in the spec's `responses` section (e.g., `200`, `201`, `202`). If multiple 2XX codes exist, note all of them.
- **Response body schema** — the schema under `responses.{status}.content.application/json.schema`. If the schema uses `$ref`, resolve the reference by looking up `components/schemas/{name}` in the spec. If no response body is defined (e.g., 204), note "no body."
- **Security requirements** — which security scheme the operation uses (from the operation-level or spec-level `security` field).

**13.1.3 — Substitute entity IDs.** For each path parameter in the current operation, substitute the stored value into the path template. If a path parameter was not collected during enumeration (an unexpected parameter), ask the user for it now. If the operation has no path parameters, skip this sub-step.

**13.1.4 — Verify readiness.** Before proceeding, verify internally that the operation definition is fully extracted and all required entity IDs have been provided.

### Step 13.2 — Request Execution and Response Validation

Construct the HTTP request, execute it against the live SaaS, and validate the response.

#### 13.2.1 — Construct the curl command

Build the curl command from the operation definition.

**URL.** Combine the base URL with the path template, substituting path parameters with user-provided values.
Example: `https://coda.io/apis/v1/docs/AbCDeFGH/pages/canvas-abc123`.

**Method.** Use the `-X` flag (e.g., `-X GET`, `-X POST`).

**Authentication header.** Construct based on the auth type from `api-reference.md`. Use shell substitution to inject the credential from `config.properties`:

- **Bearer token:**

  ```bash
  -H "Authorization: Bearer $(grep '^CODA_API_TOKEN=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-)"
  ```

- **Basic auth:**

  ```bash
  -H "Authorization: Basic $(echo -n "$(grep '^API_USER=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-):$(grep '^API_PASS=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-)" | base64)"
  ```

- **API Key (header):**

  ```bash
  -H "{header_name}: $(grep '^API_KEY=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-)"
  ```

- **API Key (query parameter):** Append the credential as a URL query parameter. Use `?` for the first parameter, `&` for subsequent ones:

  ```bash
  "https://api.example.com/endpoint?{param_name}=$(grep '^API_KEY=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-)"
  ```

  For APIs requiring multiple query-parameter credentials (e.g., separate `key` and `token` params):

  ```bash
  "https://api.example.com/endpoint?key=$(grep '^TRELLO_API_KEY=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-)&token=$(grep '^TRELLO_API_TOKEN=' {PROJECT_FOLDER}/config.properties | cut -d'=' -f2-)"
  ```

  If the URL already has query parameters (from 13.1.2 required query params), append with `&`.

**Content-Type header.** `-H "Content-Type: application/json"` (include for all requests).

**Request body.** If the operation requires a body (POST, PUT, PATCH), construct a minimal JSON payload using only the required fields from the spec's request body schema. Use realistic placeholder values matching the field types and constraints. Pass via `-d '{...}'`.

**Response capture.** Add `-s -w "\n%{http_code}" -D /tmp/validation_headers.txt` to suppress progress output, append the HTTP status code on the last line, and dump response headers to a temporary file for inspection when needed (e.g., `Retry-After` on 429 responses).

#### 13.2.2 — Destructive operation confirmation

Before executing the curl command, check whether the current operation is **destructive**:

- **DELETE** (any entity) — always destructive.
- **PUT** that replaces an entire entity — destructive (overwrites existing state).

**PATCH** operations are NOT considered destructive — they apply partial updates and are generally safe. **POST** (create) operations are NOT destructive — they create new entities, not modify existing ones.

If the operation IS destructive:

1. **Warn the user** before executing:

   ```
   ⚠️  Destructive operation: {METHOD} {path}
   This will {consequence} the {entity_type} with ID `{entity_id}`.
   This action may not be reversible.

   Proceed? (yes / skip)
   ```

   Where `{consequence}` is:
   - DELETE → "permanently delete"
   - PUT → "overwrite all fields of"

2. **If the user says "yes"** (or equivalent affirmative) → proceed to 13.2.3 and execute the request.
3. **If the user says "skip"** (or equivalent negative) → do NOT execute the request. Classify the operation as **skipped**. Increment the `skipped` counter. Emit a progress line with a skip detail:

   ```
     ⏭ {METHOD} {path}  skipped — user declined destructive operation
   ```

   Proceed directly to 13.2.7. Do not count this as a failure.

If the operation is NOT destructive, proceed to 13.2.3 without any prompt.

#### 13.2.3 — Execute the request

Run the curl command via the Bash tool. The shell substitution resolves the credential inline — the actual value never appears in conversation context.

Increment `attempt_count` for the current operation. After parsing the response (13.2.4), if non-2XX: append an entry to `retry_history` (attempt_number, status_code, error_summary, fix_applied_if_any) and update `last_failure_signature` with `(status_code, key error details from response body)`.

#### 13.2.4 — Parse the response

From the curl output:
- **Status code:** the last line of output (from `-w "\n%{http_code}"`).
- **Response body:** all lines except the last. If empty, the response has no body.
- **Response headers:** available in `/tmp/validation_headers.txt` if needed by error handlers (e.g., `Retry-After` for 429 responses).

Verify the status code is in the 2XX range (200–299). If the status code IS 2XX, set `any_2xx_seen = true` — this tracks that the credentials worked at least once during this session. If the status code is NOT 2XX, proceed to **13.2.5** (error response schema check) before recording the result.

#### 13.2.5 — Error response schema check (non-2XX only)

Before classifying the error, check whether the error response body matches the error schema defined in the spec:

1. Look up the error response schema in the spec for the actual status code: `responses.{status_code}.content.application/json.schema`. If no schema is defined for this specific status code, also check for a `default` response schema.
2. If no error schema exists in the spec → skip schema checking.
3. If an error schema exists and the response has a body → compare the error body against the schema using the same comparison logic from 13.2.7 Branch A (steps 1–6).
4. If mismatches are found → apply the same auto-fix strategies from 13.2.7 to correct the error schema in the spec. Write the updated spec to disk and log the fixes.
5. No re-validation is needed for error schemas — the error itself still stands. The agent is only correcting the spec's description of the error response format.

After error schema checking, proceed to **13.2.6** to classify and handle the error.

#### 13.2.6 — Error cause handling (non-2XX only)

Determine the appropriate action based on the status code.

**401/403 — Authorization/Permission Error.** The credentials are invalid, expired, or lack permissions. The agent cannot fix credentials autonomously — this is a **blocking exception** that halts the entire validation loop.

1. **Classify the failure context:**
   - If `any_2xx_seen == false` → **permanent auth failure** (wrong credentials or insufficient permissions).
   - If `any_2xx_seen == true` → **mid-session token expiration** (credentials worked before but have now expired).
2. **Record the auth failure:**
   - Set `auth_halted = true`.
   - Note the current operation `(method, path)` and the status code (401 or 403).
   - Note the failure context (permanent or mid-session).
3. **Emit a halted progress line:**

   ```
   Validation: {completed}/{M} | passed {X} | fixed {Y} | failed {Z} | AUTH HALTED
     ⛔ {METHOD} {path}  {status_code} — {reason from response body}
   ```

   Use `⛔` (not `✗`) to visually distinguish auth halts from normal failures.
4. Do **NOT** increment `completed` or `failed` — the operation was not fully processed.
5. Do **NOT** proceed to 13.2.7 or 13.2.8.
6. Return to the validation loop, which checks `auth_halted` and exits to Step 14.

**5XX (500–599) — Server Error.** The SaaS service is unavailable or experiencing server-side issues. This is not a problem with the spec or the request — the agent cannot fix it.
- Classify as **failed** with reason "server error ({status_code})" (e.g., "server error (503)").
- Do **NOT** retry the operation.
- Skip 13.2.7 and proceed directly to 13.2.8 to record the result.

**404 — Not Found (entity ID remediation).** The endpoint requires a reference to an existing entity, but the entity was not found. This typically means the entity ID provided during upfront collection is wrong, stale, or refers to a deleted entity.

1. **Identify the suspect path parameter(s):**
   - Extract all path parameters from the current operation's path template.
   - For each path parameter, note the value currently substituted (from the stored entity ID map).
   - If the path has multiple parameters, use the response body to infer which entity was not found. If the response body does not indicate which parameter is wrong, suspect the **most specific** (deepest-nested) parameter first.
2. **Ask the user for a corrected entity ID:**

   If one parameter is clearly suspect:

   ```
   404 Not Found — {METHOD} {path}

   The API returned 404, which means the entity referenced by `{suspect_param}`
   (current value: `{current_value}`) was not found.

   Please provide a valid {entity_type} ID for `{suspect_param}`:
   ```

   If multiple path parameters might be wrong:

   ```
   404 Not Found — {METHOD} {path}

   The API returned 404. The following entity IDs may be incorrect:
   - `{param1}` (current value: `{value1}`) — {entity_type_1}
   - `{param2}` (current value: `{value2}`) — {entity_type_2}

   Please provide corrected values (or confirm if a value is correct):
   ```

3. **Update stored entity IDs:** after the user provides corrected value(s), update the stored entity ID map so that **all subsequent operations** using the same parameter name(s) will use the corrected value(s).
4. **Reconstruct and retry:**
   - Rebuild the curl command from 13.2.1 using the corrected entity ID(s).
   - If the operation is destructive (DELETE or PUT), re-trigger the **13.2.2** destructive operation confirmation before executing.
   - Execute the rebuilt curl command (13.2.3) and parse the response (13.2.4).
5. **Evaluate the retry result:**
   - **2XX response** → the corrected ID worked. Proceed to 13.2.7 for schema validation as normal.
   - **404 again (same error)** → classify as **failed** with reason "404 — entity not found (user-provided ID also not found)". Do NOT ask the user again. Proceed to 13.2.8.
   - **Different non-2XX error** → pass the new error through **13.2.5** and **13.2.6** as if it were the initial response.
6. **Retry limit:** one user-interactive retry per 404. If the retry itself returns 404, fail immediately.

**400 — Bad Request (three-tier remediation).** The request was rejected by the API due to malformed syntax, missing fields, or invalid values. The agent attempts autonomous remediation through three escalating tiers. No user interaction — this is fully autonomous. All retries within this handler are subject to the retry strategy below. Before each re-execution of 13.2.3, verify `attempt_count < 10` and run the progress gate.

1. **Tier 1 — Error message diagnosis:**
   - Parse the error response body for actionable details (e.g., "field X is required", "invalid value for parameter Y", "unknown field Z").
   - If the message identifies a specific field, constraint, or format issue:
     - Fix the request accordingly (add missing field, correct a value, remove an invalid field).
     - Re-execute the curl command (13.2.3) and parse the response (13.2.4).
     - **2XX** → proceed to 13.2.7 (schema validation).
     - **Still 400** → check progress gate. If no progress, classify as **failed** and proceed to 13.2.8. If progress, escalate to Tier 2.
     - **Different non-2XX** → pass through 13.2.5 and 13.2.6 for the new error code. The 400 tier sequence does NOT continue.
   - If the message is NOT actionable → skip directly to Tier 2 without retrying.
2. **Tier 2 — `api-reference.md` consultation:**
   - Read the relevant sections of `api-reference.md`:
     - **Entity Reference** for the entity being operated on — required fields, field types, enum values, constraints.
     - **CRUD Endpoint Catalog** for the current endpoint — request body format, required parameters.
   - Compare the current request against the documented requirements.
   - Identify discrepancies and reconstruct the request to match the documented format.
   - Re-execute the curl command (13.2.3) and parse the response (13.2.4).
   - **2XX** → proceed to 13.2.7.
   - **Still 400** → check progress gate. If no progress, classify as **failed** and proceed to 13.2.8. If progress, escalate to Tier 3.
   - **Different non-2XX** → pass through 13.2.5 and 13.2.6 for the new error code.
3. **Tier 3 — Official API documentation research:**
   - Use WebSearch and/or WebFetch to find the official SaaS API documentation for this endpoint.
   - Look for: required fields, field format/constraints, valid values, API-specific validation rules not captured in `api-reference.md`.
   - Apply any discovered fixes to the request.
   - Re-execute the curl command (13.2.3) and parse the response (13.2.4).
   - **2XX** → proceed to 13.2.7.
   - **Still 400** → classify as **failed** with reason "400 — {error message} (all remediation tiers exhausted)". Proceed to 13.2.8.
   - **Different non-2XX** → pass through 13.2.5 and 13.2.6 for the new error code.

**429 — Too Many Requests (Rate Limit).** The API is rate-limiting requests. The agent waits and retries autonomously — no user interaction.

1. **Check for `Retry-After` header:**
   - Read `/tmp/validation_headers.txt` and look for a `Retry-After` header (case-insensitive).
   - If present as an integer (e.g., `Retry-After: 5`) → wait duration is that many seconds.
   - If present as an HTTP date → compute seconds until that time. If the date is in the past, treat as 0.
   - **Cap:** if the computed wait exceeds 120 seconds, cap at 120 seconds.
   - If no `Retry-After` header is present → use exponential backoff (step 2).
2. **Exponential backoff (when no `Retry-After` header):**
   - First 429: wait 2 seconds.
   - Second consecutive 429: wait 4 seconds.
   - Third consecutive 429: wait 8 seconds.
   - Continue doubling, capped at 120 seconds per wait.
3. **Wait and retry:**
   - Execute `sleep {seconds}` via Bash to wait the computed duration.
   - Re-execute the same curl command (13.2.3) and parse the response (13.2.4).
4. **Evaluate the retry result:**
   - **2XX** → rate limit cleared. Proceed to 13.2.7 for schema validation.
   - **429 again** → still rate-limited. Repeat from step 1.
   - **Different non-2XX** → pass through 13.2.5 and 13.2.6 for the new status code. The 429 retry sequence does NOT continue.
5. **Progress gate exception:** repeated 429s bypass the progress gate. Before each retry, verify `attempt_count < 10`.
6. **Exhaustion:** if the absolute ceiling (10 attempts) is reached and the response is still 429, classify as **failed** with reason "429 — rate-limited (retry limit reached after {N} attempts)". Proceed to 13.2.8.
7. **Silent operation:** do NOT emit progress lines during 429 waits. Only emit the final result when the operation completes.

**All other non-2XX status codes (e.g., 409 Conflict, 422 Unprocessable Entity, 405 Method Not Allowed).** Same three-tier remediation as 400. Tier 1 examines error-code-specific guidance:

- **409 Conflict:** look for resource name/ID conflicts — change the conflicting value.
- **422 Unprocessable Entity:** look for field-level validation failures — correct the field.
- **405 Method Not Allowed:** check for an `Allow` response header listing valid methods — correct the HTTP method.

Tiers 2 and 3 are identical to 400.

#### Retry strategy

This unified framework governs all retry scenarios in 13.2. Individual error handlers (400, 429, others) and schema auto-fix (13.2.7) reference it for retry decisions.

**Failure signature.** A pair of `(HTTP status code, key error details)`. Key error details = the primary error message or error code from the response body, ignoring dynamic content like timestamps, request IDs, or trace IDs. Two failures are "the same" when both status code AND key error details match; "different" when either differs.

**Progress gate.** Before any handler re-executes 13.2.3, compare the current failure signature to `last_failure_signature`:
- **Different** = forward progress. Allow retry (subject to ceiling).
- **Same** = no progress. Stop retrying immediately — classify as **failed** (unresolvable) and proceed to 13.2.8.

**429 exception.** Repeated 429 responses bypass the progress gate. A 429 is a transient condition (the rate limit is active), not a persistent failure.

**Absolute ceiling.** Maximum **10 total attempts** per operation (1 initial + up to 9 retries). The `attempt_count` is shared across ALL handlers for the same operation. Before any re-execution of 13.2.3, check `attempt_count < 10`. If the ceiling is reached, stop immediately regardless of progress.

**Exhaustion behavior.** When retries stop — whether by progress gate (same failure) or by absolute ceiling — mark the operation as **failed** (unresolvable) and include:
- Total `attempt_count`.
- Whether stopped by "no progress" (progress gate) or "retry limit reached" (ceiling).
- The full `retry_history`.

Proceed to 13.2.8 with the failure classification.

#### 13.2.7 — Validate the response

Branch based on whether the response has a body.

**Branch A: 2XX response WITH body.** Compare the actual response JSON against the spec's response schema:

1. **Parse** the response body as JSON. If parsing fails, report "Response is not valid JSON" and stop.
2. **Resolve the spec schema.** Read the response schema for the matched status code from the spec. If it uses `$ref`, follow the reference to `components/schemas/{name}` and expand it. Continue resolving any nested `$ref` references.
3. **Compare fields.** For each field in the response:
   - Check if the field is defined in the spec schema's `properties`.
   - If defined, check that the JSON type matches the schema type:
     - `string` ↔ string
     - `integer` or `number` ↔ number
     - `boolean` ↔ boolean
     - `array` ↔ array
     - `object` ↔ object
   - If the field is NOT in the schema, note it as an **extra field**.
4. **Check required fields.** For each field in the schema's `required` array, verify the field exists in the response. If missing, note it as a **missing required field**.
5. **Check nested objects (one level).** For fields of type `object` that have a `properties` definition in the schema, repeat steps 3–4 on the nested object.
6. **Check arrays.** For fields of type `array`, verify the response value is an array. If the schema defines `items`, compare the first array element against the `items` schema (if the array is non-empty).
7. **Determine result:**
   - If NO mismatches found → classify as **passed**. Proceed to 13.2.8.
   - If mismatches found → apply the auto-fix strategies below, then re-validate.

**Auto-fix strategies (Branch A only):**

| Mismatch Type | Fix Strategy |
|---|---|
| **Type mismatch** — spec declares a different type than the response returns | Update the property's `type` in the spec schema to match the actual type from the response. |
| **Extra field** — field present in the response but not in the spec schema | Add the field to the schema's `properties` as an optional property (do NOT add to `required`). Infer the type from the response value. |
| **Missing required field** — spec lists a field in `required` but the response omits it | Remove the field from the schema's `required` array. Keep the field in `properties`. |
| **Structural mismatch** — nested object/array shape differs from spec | Update the spec schema to match the actual structure. |

Apply ALL fixes for the current set of mismatches in one pass. Modify `components/schemas/{name}` definitions (not inline response schemas) so fixes propagate to all operations that reference the same schema via `$ref`. Write the updated spec to disk using the Edit tool. Log each fix applied: `{schema_name}.{field_path}: {mismatch_type} — {description of change}`.

**Re-validate after auto-fix:**

1. Re-execute the same curl command from 13.2.3 (always use a fresh response).
2. Parse the response using 13.2.4 logic.
3. If the response is still 2XX, repeat the schema comparison (Branch A steps 1–6) using the **updated** spec schema.
4. Evaluate:
   - **No mismatches** → classify as **fixed**. Proceed to 13.2.8.
   - **Mismatches remain but are different from the previous attempt** → forward progress. Apply additional fixes and re-validate.
   - **Mismatches remain and are identical** → no progress. Classify as **failed** with reason "schema mismatch (auto-fix unsuccessful)". Proceed to 13.2.8.
   - **Non-2XX response on re-validation** → classify as **failed** with the error status code and reason. Proceed to 13.2.8.
5. Schema auto-fix retries share `attempt_count` with the error handlers — do not exceed 10 total attempts.

**Branch B: 2XX response with NO body.**

- Validate that the actual HTTP status code matches the expected status code from the spec.
- If it matches → classify as **passed**.
- If it does not match → classify as **failed** with reason "status code mismatch" (report actual vs. expected).

#### 13.2.8 — Record the result and emit progress

Classify the outcome:

- **passed** — 2XX response, schema matched (or no body, status matched). Includes operations that succeeded after 404 entity ID correction.
- **fixed** — 2XX response, schema did not match initially, but the agent auto-fixed the spec and re-validation succeeded.
- **failed** — non-2XX response after all remediation, OR 2XX response where schema auto-fix could not resolve all mismatches after retries.
- **skipped** — user declined to execute a destructive operation after the 13.2.2 confirmation prompt.

Auth failures (401/403) do not reach this step — they halt the loop from 13.2.6 and are reported in Step 14.

Emit a **progress line** to the user:

```
Validation: 1/5 | passed 1 | fixed 0 | failed 0
Validation: 2/5 | passed 1 | fixed 0 | failed 1
  ✗ POST /docs/{docId}/pages  400 — missing required field: name (3 attempts)
Validation: 3/5 | passed 2 | fixed 0 | failed 1
```

Rules:
- One progress line per completed operation.
- Detail line ONLY for **failed** operations (during the loop). When `attempt_count > 1`, append `({attempt_count} attempts)`.
- Record the `retry_history` for failed ops and the fix summary for **fixed** ops — Step 14 may emit them in the final report.
- **Fixed** operations count as successes in the progress — no detail line in the loop.
- Do NOT print detail lines while the agent is still attempting remediation.

After recording the result, return to the loop to process the next operation. If this was the last operation, proceed to **Step 14**.

---

## Step 14: Final Report and Knowledge Ready

This step executes after all operations in the validation loop have been processed, or after an auth failure halts the loop early.

### Auth failure — loop halted early

If `auth_halted` is true, present the auth failure report instead of the normal summary.

**Permanent auth failure** (`any_2xx_seen == false`):

```
Auth failure — validation halted.

  ⛔ {METHOD} {path}  {status_code} — {reason}

The API returned {status_code} on the first operation attempted. The credentials in
config.properties may be invalid or lack permissions for this API.

Please verify the credentials and re-run validation.
```

**Mid-session token expiration** (`any_2xx_seen == true`):

```
Auth failure — validation halted after {completed}/{M} operations.

  ⛔ {METHOD} {path}  {status_code} — {reason}

  Completed before failure: passed {X}, fixed {Y}, failed {Z}

The first {completed} operations were processed, but operation {completed+1} returned {status_code}.
This likely indicates the API token has expired mid-session.

Please refresh the token in config.properties and re-run validation.
The agent will re-validate all operations from the beginning.
```

After the auth failure report, **stop**. Do not present the normal summary or ask "Would you like to retry?"

### Normal completion

Present a summary line followed by detail lines for fixed, failed, and skipped operations. Passed operations get no detail line. Append `| skipped {S}` only when `skipped > 0`.

Detail line ordering: fixed operations first (✔), then failed (✗), then skipped (⏭).

```
Validation complete: 5/5 | passed 2 | fixed 1 | failed 1 | skipped 1

  ✔ GET /docs/{docId}  fixed — Doc.owner: type mismatch (object → string), Doc.sourceDoc: structural mismatch (string → object)
  ✗ POST /docs/{docId}/pages  400 — missing required field: name (3 attempts)
  ⏭ DELETE /docs/{docId}  skipped — user declined destructive operation
```

Detail line rules:
- **Fixed (✔):** `  ✔ {METHOD} {path}  fixed — {fix_summary}`. When `attempt_count > 1`, append `({attempt_count} attempts)`.
- **Failed (✗):** `  ✗ {METHOD} {path}  {status_code} — {reason}`. When `attempt_count > 1`, append `({attempt_count} attempts)`.
- **Skipped (⏭):** `  ⏭ {METHOD} {path}  skipped — user declined destructive operation`.

**If there are failed operations** (not counting skipped), present the summary and ask the user how to proceed:

```
{N} operation(s) could not be validated. How would you like to proceed?

1. Provide additional information so I can retry the failed operations
2. Keep the failed operations in the spec as-is (no changes to their definitions)
3. Remove the failed operations from the spec and proceed with the corrected spec
4. Cancel — stop the validation process
```

When the user selects an option:

- **Option 1:** Present the `retry_history` for each failed operation so the user understands what was already tried. Accept the user's additional information, then re-run validation for just the failed operations. After re-validation, present an updated summary and repeat the decision flow if failures remain.
- **Option 2:** Pass the spec forward as-is. Auto-fixes applied during validation are already written to disk.
- **Option 3:** Remove the failed operations from the spec's `paths` object using the Edit tool. Write the updated spec to disk.
- **Option 4:** Stop. Do not pass the spec forward.

For options 1–3, after the spec is finalized, confirm the output:

```
Knowledge ready: {PROJECT_FOLDER}
  - api-reference.md
  - {apiName}.yaml
  - config.properties
```

**If all operations passed, were fixed, or were skipped** (i.e., `failed == 0`), report the summary and confirm the output without further user interaction:

```
Knowledge ready: {PROJECT_FOLDER}
  - api-reference.md
  - {apiName}.yaml
  - config.properties
```

The caller (typically `build-mule-integration` Step 3a) reads `api-reference.md` to inform HTTP-Connector configuration and DataWeave transforms; `<apiName>.yaml` is the corrected, validation-tested OpenAPI spec.

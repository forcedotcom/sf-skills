---
name: education-cloud-multi-campus-configure
description: "Use this skill when a Salesforce Administrator needs to create OR maintain an institutional hierarchy for Education Cloud by parsing organizational structure from a PDF, URL, text, or CSV. On a first run it creates System, Campus, College, and Department Account records linked via ParentId plus 1:1 Business Profile records. On later runs it reconciles the org's existing hierarchy against the desired structure and applies only the delta — adding new units, renaming, or moving a node under a different parent — never recreating what exists. TRIGGER when the user wants to set up, configure, build, update, restructure, or reorganize a multi-campus structure, institutional hierarchy, or account hierarchy with business profiles; or add, rename, or move a campus, college, or department. DO NOT TRIGGER for single-campus flat setups without hierarchy levels, one-off manual account creation, or non-Education-Cloud account management."
metadata:
  version: "1.0"
  minApiVersion: "65.0"
  domains:
    - "Education"
  relatedSkills:
    - "education-cloud-domain-configure"
  accessCheck:
    - type: "license"
      value: "Education Cloud"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
allowed-tools: |
  Read AskUserQuestion Bash
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
  distribution:
    sf-skills:
      visibility: "public"
    headless360Mcp:
      visibility: "public"
---

# Education Cloud Multi-Campus Institutional Hierarchy Configuration

Guides Salesforce Administrators through the full lifecycle of an institutional hierarchy: initial creation AND ongoing maintenance. Parses organizational structure from documents, URLs, CSV, or text, then either builds the hierarchy from scratch or reconciles it against what already exists in the org — creating only the delta. Supports any number of hierarchy levels (e.g., System → Campus → College → Department, or System → Region → Campus → Division → Department) based on the input. Creates/updates Account records with parent-child relationships and Business Profiles for each level, derives materialized paths on the fly for semantic navigation, and validates the result.

## Mechanism

Try **`headless-360`** first for every Account/BusinessProfile read or write — reads via `dispatch_readonly`, writes via `dispatch` (see `references/mcp-invocation.md` for call shape, response envelope, and per-step invocations). Probe with `GET /services/data/vXX.0/limits` before the first call: 2xx → route everything through it. Absent/4xx/5xx → probe other available transports (another Salesforce MCP server, or authenticated `sf` CLI) with the same read, use the first healthy one, and tell the user which transport is in use. None healthy → stop, ask the user to connect one; never fabricate a result.

## Scope

- **In scope**: Parsing institutional structure from PDF/URL/text/CSV with any number of hierarchy levels (2+); **new setup** (create full hierarchy); **update/reconcile** (compare desired structure to the org's current hierarchy and apply only the delta — add new nodes, rename a node, move a node under a different parent); creating Account hierarchy with parent-child relationships via ParentId; generating Business Profiles for all levels; deriving materialized paths on demand from the parent chain; validating parent-child relationships; handling API errors during bulk create/update
- **Out of scope**: Deleting Account or Business Profile records (destructive — report extras, do not delete unless the user explicitly confirms per Step 7); single-level flat structures (no parent-child relationships); non-Education-Cloud account management; migrating field data between hierarchy nodes

---

## Required Inputs

Gather or infer before proceeding:

- **Organizational structure source** (the *desired* structure): PDF document path, website URL, CSV, or plain text description
- **System name**: Top-level institutional system name (e.g., "Riverside Community College System")
- **Hierarchy levels**: All organizational levels present (Campus, College, Department, Division, Region, etc.) — infer from parsing, do not assume a fixed 4-level structure
- **Mode hint** (optional): Whether this is a first-time build or an update to an existing hierarchy. If not stated, detect in Step 4.
- **Existing root** (update mode only): The System (root) Account Id, so the current hierarchy can be traversed. A prior run of this skill prints this Id in its summary (Step 10).

Defaults unless specified:
- Record type for all accounts: resolve from org (do not hardcode) — see Step 3.5
- Business Profile creation: Enabled for every hierarchy level that lacks one
- Materialized path: Not a stored field — derived on the fly by walking the Account's ParentId chain to the System root when displaying a path
- Naming convention: Title Case with spaces preserved
- Deletion: Never automatic — extra nodes in the org are reported, not removed

If the user provides a complete hierarchy description or document, parse and confirm the structure before creating or changing records.

---

## Workflow

All steps are sequential. Do not skip or reorder. If blocked, stop and ask for missing context.

0. **Verify foundation prerequisites** — Follow `references/foundation_prerequisites.md`: org edition, Lightning Experience, Education Cloud license, running user's Full Access assignment, Education Cloud Foundation enabled (self-heal via confirm-then-enable if off). Do not proceed to Step 1 until all checks pass.

1. **Understand input format**
   - Ask user for organizational structure source: PDF path, URL, CSV, or text description
   - If PDF: use Read tool to extract text content
   - If CSV: read columns `Name,LevelType,Level,ParentName` (see `examples/sample_hierarchy_input.csv` for the expected shape; `examples/sample_hierarchy_input_edgecases.csv` shows duplicate names, abbreviations, and an orphaned parent reference)
   - If URL: recommend to user that a trusted structured dataset (JSON/CSV) is the preferred input — web crawl results can be incomplete, inaccurate, or out of date, and some institutional sites block crawling. If the URL is not blocked it will still work. Then fetch and parse HTML to extract hierarchy information
   - **If the URL fetch is blocked or fails**: do NOT silently substitute a different source (e.g. a search/research agent pulling from Wikipedia or another third-party site). Stop and ask the user for an alternative — a PDF, CSV, or pasted text from the institution's own site. The customer must never be left unaware of what their hierarchy was actually built from
   - If text: parse directly from user's message

2. **Parse desired hierarchy structure**
   - Extract System name (top level)
   - Identify all hierarchy levels present (e.g., Campus, College, Department, Division, Region, etc.)
   - Build parent-child relationships for each node based on nesting/indentation in source
   - Store the *desired* structure as a tree: each node has Name, Level, and ParentNode reference
   - For ambiguous structures, read `references/hierarchy_parsing_rules.md` for decision logic
   - **Do not assume fixed level names** — use whatever level names appear in the source (Campus/Location/Site are equivalent, College/School/Faculty are equivalent, Department/Division/Program are equivalent)

3. **Confirm desired structure with user**
   - Display extracted hierarchy in nested bullet format — see `examples/hierarchy_visualization.md` for the box-drawing template and formatting rules.
   - Ask: "Is this structure correct?" (Yes/Make changes/No)
   - If "Make changes": gather corrections and re-display
   - If "No": stop workflow

3.5. **Resolve Account RecordType from org**
   - Do NOT hardcode a RecordType Id or DeveloperName. Resolve the org's actual Account RecordType at runtime via describe (RecordType metadata like `developerName`/`available` isn't exposed through a plain Account SOQL query — describe is the correct source):
     - `GET /services/data/v68.0/sobjects/Account/describe` via `dispatch_readonly` (see `references/mcp-invocation.md`)
     - Read the `recordTypeInfos` array from `body`. Each entry has `developerName`, `name`, `recordTypeId`, `available`, `defaultRecordTypeMapping`.
   - Select the institutional/business RecordType by `developerName` (varies by org, e.g. `Business`, `Business_Accounts`). Ignore the `Master` entry (`developerName = "Master"`) — not selectable for records.
   - Selection logic:
     - If exactly one non-Master `available:true` RecordType → use it.
     - If multiple candidates → ask user which `developerName` to use.
     - If NO non-Master RecordType exists → missing prerequisite, not a dead end (common when this skill runs standalone, without a prior EDU setup skill). Follow `references/account_recordtype_prerequisite.md`: ask for/confirm a Label, confirm before creating, create via Tooling API, cold-verify `available:true`.
   - Capture that entry's `recordTypeId` into a runtime variable `recordTypeId` (a resolved value from THIS org's describe response — never a literal copied into the skill). Use `recordTypeId` for every Account create in Step 6.

4. **Determine mode: new setup vs. update**
   - Decide whether the org already has this hierarchy:
     - If the user states it is a first-time build, or no System (root) Account exists → **Case 1 (New setup)**.
     - If the user states it is an update/reorg, or supplies an existing System (root) Account Id → **Case 2 (Update/reconcile)**.
     - If unclear, ask: "Is this a brand-new hierarchy, or an update to one already in the org? If it exists, give me the System (root) Account Id (printed by the previous run's summary)."
   - **Case 1** → skip to Step 6 with an empty `existingTree` (every desired node is new).
   - **Case 2** → proceed to Step 5.

5. **(Update mode) Load current hierarchy and compute the delta**
   - Traverse the current tree from the System Account Id (children level-by-level via `ChildAccounts`, SOQL fallback), match desired vs. current by Name within sibling group, and classify each node as reuse / **CREATE** / **EXTRA** / **RENAME** / **MOVE** — full matching and cycle-rejection algorithm in `references/delta_computation.md`.
   - Result: a delta list of CREATE / RENAME / MOVE actions plus an EXTRA report (extras are reported, never deleted). If the delta is empty and no renames/moves were requested, tell the user the org already matches the desired structure and skip to Step 9 (verify).

6. **Preview before any write**
   - Show a summary BEFORE writing any records — new setup shows counts per level + RecordType; update/reconcile shows the delta explicitly (create/rename/move/unchanged/extra). See `examples/output_examples.md` for both templates.
   - If any EXTRA nodes exist and the user wants them removed, that deletion is destructive — confirm each explicitly in Step 7; default is to leave them.
   - Ask: "Proceed with these changes?" (Yes/No). If "No": stop workflow.

7. **Apply changes (create / rename / move)**
   - Once the user confirmed in Step 6, apply the delta via the transport resolved in Mechanism — call shapes for create/rename/move/delete are in `references/mcp-invocation.md` (Step 7). Capture each created Account's returned Id. Do not stop at a "pending"/"intended delta" plan — the confirmation is the go-ahead.
   - **Order matters**: process CREATE actions in depth-first order (create parent before children); apply MOVE and RENAME after creates so parent Ids resolve.
   - **Create**: body uses `RecordTypeId` (the field the Data API sObject POST accepts) — NOT a nested `RecordType`/`DeveloperName` object, which the sObject create endpoint rejects. Value is the `recordTypeId` variable resolved from describe in Step 3.5 — never a hardcoded 18-char Id. For the System (top level, new setup only), OMIT `ParentId` entirely (do not send `null`). Store returned Account ID: `accountMap[NodeId] = response.body.id`
   - **Rename**: patch `Name` only. **Move**: patch `ParentId` only (cycle already rejected in Step 5).
   - **Deletion** (only if the user explicitly confirmed an EXTRA node for removal in Step 6): confirm the specific node once more, then delete. Skip by default.
   - Print progress after each level/action: `[action] applied: [count] Accounts ([level name])`
   - Handle API errors per `references/error_handling.md`
   - **Repeat for all levels** — do not hardcode level count or names

8. **Create Business Profiles (new/changed Accounts only)**
   - For each Account **created** in Step 7 that does not already have a Business Profile:
     - `POST /services/data/v68.0/sobjects/BusinessProfile` with body `{AccountId}` (see `references/mcp-invocation.md`)
     - (Name field auto-populated from Account — do not set)
   - Do NOT create duplicate Business Profiles for Accounts that already had one (reused nodes in update mode) — BusinessProfile is 1:1 with Account.
   - **`InstitutionType` warning**: if the user asks to populate `InstitutionType` on a Business Profile, note that it is a **managed, restricted picklist** (typically `Public` / `Private` / `Charter` only — cannot be extended). For institutions outside that K-12/higher-ed taxonomy (e.g. vocational/trade, allied health, satellite/extension campuses), there is no valid value that fits. Tell the user this upfront rather than guessing or silently picking the closest match, and offer `Description` as the only available workaround field for that nuance — it is not a substitute for a real categorization field.
   - Print: `[Total N] Business Profiles created and linked`
   - Handle API rate limits per `references/error_handling.md` (retry with exponential backoff)

9. **Verify hierarchy (cold verification)**
   - `success:true` on a write is not proof. Cold `GET /services/data/v68.0/sobjects/Account/[Account Id]` (via `dispatch_readonly`) on each affected Account (created, renamed, moved, and their parents); read `Name`, `ParentId`, `RecordTypeId`. Confirm: `ParentId` resolves the expected parent (System has `ParentId: null`, no orphans); `RecordTypeId` matches Step 3.5's resolved value; RENAME/MOVE persisted correctly.
   - Spot-check at minimum: the deepest leaf (full chain to System) + one node per top-level branch + every renamed/moved node.
   - Print: `Hierarchy verification complete — [N] Accounts, parent chains valid, 0 orphans`

10. **Return structure summary (completion report)**
    - This report describes what was **actually created/changed** (past tense), not a plan. Lead with a success headline — e.g. `# Institutional Hierarchy Expanded Successfully` for an update run, `# Institutional Hierarchy Created Successfully` for new setup. If an output location was provided, you MUST actually write the report there as `report.md` by invoking the file-write tool — do not merely print the report body in chat and claim it was saved; a described-but-unwritten file does not exist. Otherwise display it.
    - Display hierarchy visualization (nested bullet format from Step 3, see `examples/hierarchy_visualization.md`)
    - Show total counts per level: System (1), Level 1 name (N), Level 2 name (N), etc.
    - For update mode, break down what changed: created, renamed, moved, unchanged, and any untouched extras.
    - **Print the System (root) Account Id** so a future update run can reference it.
    - Offer spot-check: "Would you like me to show the complete path for a specific node or verify any account?"
    - If user requests spot-check, GET the specific Account, then GET each ancestor up the ParentId chain to the System root and join their Names with ` / ` to display the materialized path (derived on the fly — no stored path field)

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Update mode changes only the delta — reuse existing Accounts, never recreate | Recreating produces duplicates and orphaned Business Profiles; reconcile is the correct maintenance model |
| Deletion is never automatic — report extras, delete only on explicit per-node user confirmation | Removing an Account cascades to its Business Profile and children; destructive and irreversible |
| System Account has no ParentId | Top-level account cannot reference a parent |
| Child ParentId must reference its immediate parent Account | Maintains tree structure integrity — children link to direct parent, not ancestors |
| Process CREATE in depth-first order; apply MOVE/RENAME after creates | ParentId references fail if parent doesn't exist yet |
| Reject a MOVE that places a node under its own descendant | Cycle would corrupt the tree; Salesforce also throws CIRCULAR_DEPENDENCY |
| BusinessProfile must link to exactly one Account via AccountId (1:1) | Required by Education Cloud; never create a second profile for an existing Account |
| All Account names must be unique within their sibling group | Delta matching keys on name-within-parent; duplicates make reconcile ambiguous |
| Account RecordType resolved at runtime from Account describe, never hardcoded — capture `recordTypeId` from `recordTypeInfos`; POST uses `RecordTypeId` (not nested `RecordType`/`DeveloperName`) | Hardcoded Id/DeveloperName silently mismatches other orgs; describe is the source of truth for RecordType metadata |
| Retry Business Profile creation on API rate limit | Bulk creation commonly hits rate limits; retry succeeds |
| Materialized path is derived on the fly (walk ParentId chain to root), not read from a stored field | No path column exists on Account; compute it by joining ancestor Names with ` / ` when a path is requested |
| Support any number of levels (2+) | Do not hardcode level count — parse whatever structure appears in source |
| `headless-360` is the default transport for every Account/BusinessProfile read/write; fall back to another available MCP or authenticated `sf` CLI only when it isn't set up, and announce the transport in use | Keeps org auth on the session's bound OAuth JWT when available; falling back silently would hide which credential/transport actually made the change |
| Never silently substitute a different data source when the requested URL is blocked | Customer must know what their hierarchy was actually built from — ask for a PDF/CSV/pasted alternative instead |
| `InstitutionType` on BusinessProfile is a managed restricted picklist — flag it, don't guess a value for institutions outside its taxonomy | Guessing a value (or forcing the closest fit) misrepresents the institution's real category |

---

## Gotchas

See `references/gotchas.md` for known failure modes and their resolutions (rename/delete ambiguity, duplicate update runs, paging, rate limits, ambiguous parsing, missing Education Cloud provisioning, and more).

---

## Output Expectations

Deliverables (new setup):
- **Account records**: 1 System + N Campuses + N Colleges + N Departments (all with the org's resolved Account RecordType)
- **BusinessProfile records**: 1 per Account, linked via `AccountId` field
- **Hierarchy visualization**: Nested bullet format showing complete structure
- **Verification summary**: Confirmation that all parent-child relationships are valid (materialized paths are derived on demand from the ParentId chain, not persisted)
- **System (root) Account Id**: Printed for reuse in future update runs

Deliverables (update/reconcile): the delta only — counts of created / renamed / moved / unchanged Accounts, any untouched extras, Business Profiles added for new Accounts, and the same verification summary.

See `examples/output_examples.md` for sample output structures (new setup and update/reconcile).

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/foundation_prerequisites.md` | Step 0 — org edition, Lightning Experience, EDU license, permission set assignment, Education Cloud Foundation enablement; run before Step 1 on every standalone invocation |
| `references/mcp-invocation.md` | Steps 3.5, 5, 7-9 — exact `dispatch`/`dispatch_readonly` call shape and response envelope for every Account/BusinessProfile read/write |
| `references/account_recordtype_prerequisite.md` | Step 3.5 — no non-Master Account RecordType exists in org; ask/confirm/create it as a self-resolving prerequisite |
| `references/hierarchy_parsing_rules.md` | Step 2 — when parsed structure is ambiguous (e.g., college names appear without explicit campus parent) |
| `references/delta_computation.md` | Step 5 — exact matching algorithm for reconciling desired vs. current hierarchy (reuse/CREATE/EXTRA/RENAME/MOVE), including cycle rejection |
| `references/error_handling.md` | Steps 7-8 — when API errors occur during Account create/patch or Business Profile creation |
| `references/gotchas.md` | Any step — known failure modes and their resolutions |
| `examples/hierarchy_visualization.md` | Steps 3 & 10 — to format the hierarchy structure summary for the user |
| `examples/output_examples.md` | Steps 6 & 10 — pre-write preview templates, and sample completion-report output for new setup and update/reconcile |
| `examples/sample_hierarchy_input.csv` | Step 1 — reference shape for CSV input (`Name,LevelType,Level,ParentName`) |
| `examples/sample_hierarchy_input_edgecases.csv` | Step 1 — CSV edge cases: duplicate sibling names, abbreviations, orphaned parent reference |

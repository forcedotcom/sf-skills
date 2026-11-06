# Tool and Prompt Discovery and Binding

Read this before Phase 4 discovery and binding. Use `<skill-dir>` and `<default-package>` as defined in [SKILL.md](../SKILL.md). On resume, read the sections needed to verify incomplete or changed state.

## Discovery (4a–4d)

Before binding assets, read the supported backings and availability patterns in [mcp-objects.md](mcp-objects.md). For a new setup or requested extension, complete and track the four discovery passes below separately and in order: site UI, local Apex/Flow, org Apex/Flow, and Prompt Builder. Record a short result and its supporting evidence for each pass before binding. When resuming, repeat only the passes needed to verify incomplete or changed state; reuse prior results only when they are still valid and intended bindings are confirmed. Org discovery is read-only and does not retrieve metadata into the project.

This skill discovers and builds tools backed by global Apex `@InvocableMethod` actions, eligible autolaunched Flows, and available Prompt Builder templates. It also binds active, published Flex templates as MCP prompts. Compose `aa:`, `fa:`, and `pr:` identifiers only after confirming availability.

### 4a. Front-end review

Run this pass first, before any Apex/Flow scan or org listing. Read [ui-frameworks.md](ui-frameworks.md) for ExperienceBundle and component scanning. Use the selected Phase 1 entry's `uiRoots`; rerun `list_sites.mjs` if source changed. If UI paths or referenced custom components are missing, follow Phase 1's stop-and-ask rule; do not skip UI review.

Read every site view/route and every referenced custom component, and trace each server call. Build an exhaustive **UI operation inventory**: one row per distinct CRUD operation the UI performs or exposes, including simple lists, searches, detail queries, and writes. For each row, record the view and component, observed server call, inputs, outputs, filters, and read/write behavior. Include every operation whether or not a backing action exists; do not judge coverage, look for backings, or drop rows in this pass. Exclude only navigation and presentation-only flows. Flag unresolved CRUD behavior rather than inventing it. If no operations are found, identify the inspected source supporting that conclusion.

### 4b. Local project scan
```bash
node "<skill-dir>/scripts/scan_tool_candidates.mjs"
```
Reports Apex `@InvocableMethod` actions whose containing class and method are `global`. Supported primitive `List` element types are eligible directly; custom request or result types and every exposed `@InvocableVariable` field must also be `global`. It also reports autolaunched Flows that have at least one input variable and at least one output variable. Those can be different `<variables>`. Eligible sources get a composable `apiIdentifier` (`aa:apex-<Class>`, `fa:flow-<Flow>`).

### 4c. Org action discovery

Run the read-only candidate listing:
```bash
node "<skill-dir>/scripts/retrieve_existing_tools.mjs" <target-org-alias>
```
The helper makes one REST list call for Apex actions and one for Flow actions, validates both response envelopes, and prints their runtime candidate records without writing files. The runtime catalog can include namespaced actions from installed packages; do not discard them solely because their source isn't locally retrievable.

Compare the candidate names with 4b and the server's existing `<tools>`. From the site purpose, the 4a inventory, and candidate labels and names, select a small set that plausibly helps this site's users. Do not describe every org action. For each plausible candidate, use its returned `url` for a read-only describe call:
```bash
sf api request rest "<candidate-url>" --target-org <target-org-alias> --method GET
```
Use the description plus input and output schemas to decide whether the action represents a coherent MCP tool and to propose an accurate title and description. For Flows, require an autolaunched action with both input and output parameters. For Apex found in local source, retain 4b's `global @InvocableMethod` check. For an org-only Apex action, report that the runtime catalog and describe response establish action availability but don't expose its source-level visibility; deployment remains the platform validation. If behavior annotations can't be determined from the descriptor, local implementation, or site behavior, ask the user rather than inventing them.

A non-zero exit means listing or response validation failed, not that the org has no candidates. Stop Phase 4, report the failure, and do not use partial output to conclude that a tool is absent. For an authentication failure, ask the user to reauthenticate the target org with `sf`, then rerun only after the failure is resolved.

**Reconcile and deduplicate.** Map every row of the 4a inventory to a backing, in this order: an existing server binding, a 4b local action, or a 4c org action. Merge rows that share one operation, and merge 4b/4c candidates that are the same action. IMPORTANT: Proactively suggest a tool for every inventory row, including simple lists, searches, detail queries, and writes; for each row with no matching backing, propose a new eligible backing action (Apex or Flow) using the row's observed inputs, outputs, filters, and behavior. Do not limit UI-derived suggestions to the strongest candidates, and do not drop a row because other tools already exist. Then add the strongest relevant unbound 4b/4c candidates that serve no inventory row, and explain why each fits.

Present the reconciled list once, showing each tool's source row or candidate and its backing (existing, local, org, or new), and ask add-or-skip for each unbound tool. Implement each approved tool with its real input, output, and behavior. Do not generate placeholder Apex classes.

Example: when the UI lists service requests, loads request details, and submits a new request, offer all three tools, reusing a matching action where one exists and proposing a new action for each one that doesn't.

### 4d. Prompt Builder discovery

Run the read-only listing:
```bash
node "<skill-dir>/scripts/retrieve_existing_prompts.mjs" <target-org-alias>
```
Compare candidate API names with existing `<prompts>` and `pr:` `<tools>` bindings. Inspect plausible template metadata and GET the returned action `url` when present to review its description and inputs. Offer confirmed active, published Flex templates as MCP prompts, runtime-available `pr:<template API name>` actions as tools, or both. Publication or runtime availability alone doesn't establish prompt eligibility. For inactive or unverified candidates, read [Prompt Builder eligibility](mcp-objects.md#prompt-builder-eligibility) before proposing a prompt binding. A non-zero exit means incomplete discovery, not absence; report it and continue the independent Apex/Flow and UI passes. Read [discovery troubleshooting](troubleshooting.md#tool-discovery-and-binding) before retrying.

## Author and bind (4e)

**Authoring new tools — invocable first.** Use global Apex `@InvocableMethod` for new custom logic, or an **autolaunched Flow** for declarative or admin-owned logic. Apply [Phase 4b's global visibility requirements](#4b-local-project-scan) to the Apex class, method, custom request/result types, and exposed fields.

**Custom Apex actions — validate inputs and enforce user access.** Load `platform-apex-generate` before authoring. Apply these requirements to each new action, each existing method newly exposed (including in-place edits; keep its signature and existing callers working), and any data-access helpers they call:

- Validate the request list and every request at runtime before queries, searches, DML, or other side effects. Reject null/empty lists, null items, missing required values, invalid IDs or IDs for the wrong sObject type, unsupported values, and values outside the operation's allowed lengths or ranges. Derive constraints from the actual operation and target schema; `@InvocableVariable(required=true)` and UI validation do not replace runtime checks. Validate all requests before starting a batch write.
- Use `global with sharing` for the entry class. Explicitly enforce user mode for every database operation: `WITH USER_MODE` for static SOQL/SOSL, `AccessLevel.USER_MODE` for dynamic query/search and `Database` DML methods, or `as user` for DML statements. Bind input values and allowlist dynamic object, field, and operator names. `with sharing` alone does not enforce CRUD/FLS; do not rely on API-version defaults.
- Return sanitized validation and access errors using the action's result contract, or a safe fault for an unrecoverable failure. Do not expose internal exception details or retry denied operations in system mode. Only use elevated access for an explicitly approved, justified requirement; isolate it in a narrowly scoped helper with an authorization check.
- Verify valid inputs, null/empty lists and items, invalid values and IDs, and denied record/object/field access. Check that invalid or unauthorized requests produce safe errors and no unauthorized writes.

For confirmed tools, write `apiIdentifier`, `toolTitle`, `descriptionOverride`, and all five behavior booleans (`destructive`, `idempotent`, `openWorld`, `readOnly`, `returnDirect`). Classify actual side effects from the implementation, authoritative descriptor, or confirmed behavior; never use names alone. Ask when behavior is unknown. `destructive` means any write, including indirect writes, not just deletion:

| Behavior | `readOnly` | `destructive` |
|---|---|---|
| Create, update, upsert, delete (for example insert a Case or change its status) | false | true |
| Read-only queries or text generation without side effects | true | false |

Creating a new record on every call is also `idempotent: false`. Determine prompt-backed annotations from the template and called actions; do not assume prompts are read-only. Leave `openWorld` and `returnDirect` false unless the backing calls outside the org or its result should return directly to the user. Prefer backing labels and descriptions, or write concise, accurate ones. `apiSource` defaults to `API_CATALOG`. For `aa:apex-`, `fa:flow-`, and `pr:` specs, the helper derives `operation` and `toolName`; set `toolName` if the exposed name should differ.

For confirmed MCP prompts, provide `promptName` (exposed name), `promptTemplateName` (exact template API name), `promptTitle`, and `descriptionOverride`. Group tools and prompts in a temporary JSON file:
```json
{
  "prompts": [{"promptName": "revenue_cloud__updateQuoteLineItems", "promptTemplateName": "revenue_cloud__updateQuoteLineItems", "promptTitle": "Update Quote Line Items", "descriptionOverride": "Updates line items on an existing quote."}],
  "tools": [{"apiIdentifier": "pr:revenue_cloud__activateOrderWorkflow", "toolName": "revenue_cloud_activateOrderWorkflow", "toolTitle": "Activate Order Workflow", "descriptionOverride": "Activates a Revenue Cloud order.", "destructive": true, "idempotent": false, "openWorld": false, "readOnly": false, "returnDirect": false}]
}
```

**Always use `merge_tools.mjs`; never edit `<tools>` or `<prompts>` XML directly for Phase 4 binding.** The Phase 6 widget linkage exception allows only adding or reconciling top-level `<resources>` and a selected tool's `<uiResource>` after authoritative retrieval, as specified in [widget-resources.md](widget-resources.md). It does not permit editing API bindings, behavior annotations, prompts, or other tool fields by hand. Merge the specs into the rendered or retrieved component:
```bash
node "<skill-dir>/scripts/merge_tools.mjs" <default-package>/main/default/mcpServerDefinitions/<name>.mcpServerDefinition-meta.xml <tools.json>
```
`merge_tools.mjs` validates tool and prompt specs and rejects a tool missing any behavior boolean or containing an inconsistent `readOnly`/`destructive` pair. It de-duplicates tools by `apiIdentifier` and prompts by `promptName`, preserves an existing `uiResource` node when rebuilding an updated tool, preserves other server content, and writes canonical element order. Widget linkage keys are not accepted in the JSON spec; Phase 6 owns attachment. `--dry-run` prints without writing; `--skip-existing` preserves already-bound entries. Before changing an existing binding, show the diff, explain that active clients may be affected, and confirm the change. Review the JSON summary and resulting metadata, then remove the temporary JSON file.

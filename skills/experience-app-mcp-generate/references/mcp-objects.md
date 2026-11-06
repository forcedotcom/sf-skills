# Custom Hosted MCP Object and Binding Reference

Read this reference during Phase 3 when reconciling a server and during Phase 4 before binding tools. The scripts and assets remain authoritative for rendering, API requests, activation, and verification.

## Object model

The server, tools, and prompts deploy as one Metadata API component with nested `<tools>` and `<prompts>` blocks. Activation is a separate Tooling API record.

| Concept | Runtime/Tooling object | Metadata representation |
|---|---|---|
| Server | `McpServerDefinition` | Root `<McpServerDefinition>`; file name is the DeveloperName |
| Tool | `McpServerToolDefinition` | One `<tools>` block |
| Tool backing | `McpServerToolApiDefinition` | `<apiDefinition>` inside `<tools>` |
| Prompt | — | One `<prompts>` block with `promptTemplateName` |
| Activation | `McpServerAccess` | No metadata type; separate Tooling write |

Deploy the Salesforce-hosted component at `<default-package>/main/default/mcpServerDefinitions/<DeveloperName>.mcpServerDefinition-meta.xml`.

## Metadata invariants

- Use the bundled server asset and `merge_tools.mjs`; do not hand-build or directly edit `<tools>` or `<prompts>` XML.
- Omit `Language`; it isn't a `McpServerDefinition` metadata field.
- Preserve root content such as prompts and resources when adding tools.
- Canonical tool element order is `apiDefinition`, `descriptionOverride`, `destructive`, `idempotent`, `openWorld`, `readOnly`, `returnDirect`, `toolName`, `toolTitle`.
- Canonical `<apiDefinition>` order is `apiIdentifier`, `apiSource`, `operation`.
- Set the five behavior booleans from the action's real behavior; do not blindly default them.
- Every newly authored tool must have a meaningful `descriptionOverride` and `toolTitle`; every prompt needs `descriptionOverride` and `promptTitle`.
- The emitted tool XML must contain `operation` and `toolName`. For `aa:apex-`, `fa:flow-`, and `pr:` JSON specs, `merge_tools.mjs` derives both from `apiIdentifier` when omitted.
- Canonical prompt element order is `descriptionOverride`, `promptName`, `promptTemplateName`, `promptTitle`.

## Existing-stack review

Run preflight and recover the confirmed site, server, ECA/client callbacks, intended bindings/widgets, and prior approvals. Ask only for missing or ambiguous choices. Use `check_setup_progress.mjs` for observations, not proof of setup completion. Read-only review stops with findings and unresolved checks; creation, retrieval, repairs, deployment, activation, and permission audits are outside that path.

- Compare local ECA files with `render_eca.mjs --check` using confirmed inputs and policy choice; read `eca-fields.md` for scopes, callbacks, policies, and cross-component ownership. Verify deployed settings separately through read-only org queries where available; inaccessible settings remain unknown.
- Inspect the actual local server XML against the bundled asset and confirmed intent, preserving intentional overrides. Compare with deployed state through read-only queries where available. Local files and activation alone do not establish deployed configuration or client readiness.
- Compare every intended tool/prompt with the authoritative available metadata and action/template contracts. Read `tool-bindings.md` to review existing behavior flags as well as new ones. Follow `widget-resources.md` for applicable dependencies/links. Report missing, contradictory, stale, or unverifiable settings; permission setup remains an admin reminder.
- For deployment requests, show the exact stack files and unresolved dependencies before Phase 5. Reuse prior approvals only for the same target, files, and actions. Keep client testing pending until verified.

## Supported tool backings

The supported tool bindings serialize with `apiSource=API_CATALOG`.

| Backing implementation | `apiIdentifier` | Availability pattern | Appropriate use |
|---|---|---|---|
| Global Apex `@InvocableMethod` | `aa:apex-<ClassName>` | Live/virtual | New custom logic; primary path |
| Autolaunched Flow with input and output variables | `fa:flow-<FlowName>` | Live/virtual | Declarative or admin-owned logic |
| Available Prompt Builder template action | `pr:<TemplateApiName>` | Runtime prompt-template action | Agent-invoked server-side generation |

Preserve every existing binding during reconciliation. Add new bindings from the supported implementations in this table.

Active, published Flex Prompt Builder templates can be MCP prompts under `<prompts>`. An available prompt-template action can also be a `pr:` MCP tool under `<tools>`; the same template may appear in both forms. MCP prompts are selected by people in compatible clients, while prompt-backed tools execute server-side when called by an agent.

## Availability patterns

Invocable Apex and autolaunched Flows are live sources. Confirm that the action exists in the org's runtime invocable-action catalog, then compose its `aa:` or `fa:` identifier.

`retrieve_existing_tools.mjs` reads `/actions/custom/apex` and `/actions/custom/flow` and doesn't write to the SFDX project. `retrieve_existing_prompts.mjs` pages through active templates at `/einstein/prompt-templates`, lists custom `GenAiPromptTemplate` metadata, reads custom template versions by API name, and lists or describes `/actions/custom/generatePromptResponse` actions. It reports active published custom Flex templates as MCP prompt candidates, inactive published custom Flex templates separately, active standard Flex templates with unverified MCP prompt eligibility, and actions backed by published custom or active standard Flex or Global templates as MCP tool candidates; `inventoryCounts` retains the broader API totals. The list responses provide candidate names and describe URLs. Describe only candidates relevant to the site's purpose; the candidate-specific response supplies the description and parameter schemas needed for review. Runtime discovery can include namespaced installed-package actions whose source isn't locally retrievable. An unavailable endpoint is not evidence that a template does not exist.

## Prompt Builder eligibility

A custom template can have a published version while `IsActive` is false; do not infer MCP prompt eligibility from publication, type, or a runtime action alone. For inactive or unverified Flex candidates, confirm they appear in Setup's Add Prompts picker or verify both active and published status before proposing a prompt binding.

Compare candidate API names with existing `<prompts>` and `pr:` `<tools>` bindings. Inspect plausible template metadata and GET the returned action `url` when present to review its description and inputs. Offer an eligible Flex template as an MCP prompt for client selection, a runtime-available `pr:<template API name>` action as an agent-invoked tool, or both when justified.

A non-zero exit means incomplete discovery, not absence; report it and continue the independent Apex/Flow and UI passes. Read [discovery troubleshooting](troubleshooting.md#tool-discovery-and-binding) before retrying.

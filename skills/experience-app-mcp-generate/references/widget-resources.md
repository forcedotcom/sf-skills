# MCP Tool Widget Resources

Read this only for Phase 6, after the MCP stack and its backing actions have deployed successfully. Use `<skill-dir>` and `<default-package>` from `../SKILL.md`. Do not run it for an explicit preview/activate-only request on an existing named server; that bypass leaves metadata unchanged.

## 1. Eligible deployed tools

Build the eligible list from the final deployed `<tools>` bindings. Include only an `apiIdentifier` starting with `aa:apex-`. Report `fa:flow-` and `pr:` tools as skipped; `<prompts>` bindings are unaffected. Never route these through the agent-action coordinator.

Use the selected tool's real `apiDefinition` / `operation` as the invocable action API name, including its namespace. Do not substitute `toolName`, a label, a folder name, or an action guessed from the identifier. Confirm this deployed action is available through a read-only Actions REST describe; never execute the MCP tool or backing action to discover its shape. If a deployed operation cannot be resolved, stop rather than falling back to stale local source. If no tools are eligible, report that explicitly and proceed to Phase 7 without changing resources.

## 2. Generate artifacts and check the response bundle

For each eligible tool, load and invoke `platform-mcp-tool-widget-coordinate` with the target org alias, server DeveloperName, actual deployed action API name (`operation`), current SFDX project, and default package metadata directory. The coordinator owns payload discovery, exactly two object-based CLTs, leaf-skill generation of the response CLT, envelope CLT and HXL widget, the envelope's default renderer, and validation. Do not duplicate its leaf generation or author those artifacts from memory.

Capture all generated filenames and named gate results. Resolve the response CLT, envelope CLT, and widget names from their actual bundle directories, and verify the reported files exist in the current project's default package. Require widget self-validation and every coordinator hard gate to pass; invented-field failures also block. Record advisory omissions. Missing or ambiguous artifacts, a failed gate, or not-run validation blocks deployment; report partial files and stop. Existing renderer conflicts must be read and resolved with the user's consent before replacement, never overwritten automatically.

The coordinator generates artifacts and reports its existing validation results; this caller owns the additional response-bundle check and deployment checklist below. Do not require the coordinator to emit a `DEPLOYMENT HANDOFF` or run the caller's extra check. Generation order is not deployment order.

**Caller-owned check: `response-bundle-schema-only`.** Run this after the coordinator's gates pass and before any artifact deployment:

1. Resolve `<default-package>/main/default/lightningTypes/<RESPONSE_CLT_NAME>/` from the verified response artifact. Inspect the entire directory recursively, including pre-existing files, hidden entries, and surface subdirectories; print its relative file inventory. Do not limit the inspection to the coordinator's generated-file list.
2. Require the bundle's only file to be its valid `schema.json`, matching the response CLT that passed the coordinator's gates. Any renderer, editor, surface-specific configuration, or other custom artifact makes it unsuitable for this response-first deployment plan. Report `response-bundle-schema-only: fail` with the conflicting paths and stop before deployment. Obtain approval for a new response name or reconciliation, then regenerate and rerun the affected gates and this check. Never delete unknown files to make the check pass.
3. Report `response-bundle-schema-only: pass` with the inspected bundle path and complete inventory only after executing the check. Missing source, an unreadable directory, an uninspected entry, or a not-run check blocks deployment. Reuse an existing response bundle only when it passes both this check and the coordinator's compatibility gates.

## 3. Prepare and execute the deployment checklist

After all generation gates and the caller's response-bundle check pass, prepare the checklist using the exact source metadata member names from the verified bundle directories. Keep these member names separate from runtime CLT FQNs, which are confirmed independently for resource attachment in step 5. Confirm that the deployed backing action from Phase 5 remains the action described for generation.

For each eligible tool, use this dependency order:

1. Deploy the schema-only response CLT. The envelope's `outputValues` references this type.
2. Deploy the widget bundle. The envelope's default renderer references this widget.
3. Deploy the envelope CLT, including its default renderer, after both dependencies are deployed.

Prepare the following narrow commands with the verified component names and confirmed target org alias, show the complete checklist, and ask for deployment confirmation:
```bash
sf project deploy start --metadata LightningTypeBundle:<RESPONSE_CLT_NAME> --target-org <target-org-alias>
sf project deploy start --metadata UiWidgetBundle:<WIDGET_NAME> --target-org <target-org-alias>
sf project deploy start --metadata LightningTypeBundle:<ENVELOPE_CLT_NAME> --target-org <target-org-alias>
```
The coordinator does not deploy; this caller executes the approved checklist. Never deploy a whole `lightningTypes/`, `uiWidgets/`, package, or metadata-type directory. Require `Succeeded` and read-only confirmation that the named component exists before advancing. Stop on the first failure; do not retrieve or modify the MCP server. For multiple tools, repeat this dependency order for each tool. An existing component can satisfy a step only after read-only verification that its deployed content matches the validated artifact; local presence alone is insufficient. Attach resources and deploy the named MCP server only after all artifact dependencies are ready, as specified in steps 4–6.

## 4. Retrieve authoritative server

After all generated artifact groups deploy successfully, retrieve the authoritative server before attaching anything. Inspect the destination file first. When local edits exist, show the diff and ask for overwrite consent **before retrieval**; without consent stop, preserving those edits. Never retrieve first and ask afterward. Preserve the approved binding snapshot for comparison; it is not a stale file to redeploy.

```bash
sf project retrieve start --metadata McpServerDefinition:<SERVER_DEV_NAME> --target-org <target-org-alias>
```

Confirm the destination is `<default-package>/main/default/mcpServerDefinitions/<SERVER_DEV_NAME>.mcpServerDefinition-meta.xml`. Verify every approved tool and prompt and their field values are intact. If a binding differs, stop and reconcile with the user; do not overwrite concurrent server changes using the old local copy.

## 5. Attach widget relationships

**Phase 6 widget linkage exception:** direct XML editing is permitted only for top-level `<resources>` and the selected existing tool's `<uiResource>` in this freshly retrieved component. Phase 4 API/tool/prompt bindings must still use `merge_tools.mjs`; its JSON keys do not accept widget links. Do not add a general XML parser or reconstruct the whole server.

1. Match the target tool using its existing `apiIdentifier`, `operation`, and `toolName`. If the match is ambiguous, ask before editing.
2. Use the generated envelope CLT FQN independently confirmed from project/package context and deployed metadata: `c__` for a local namespace-less bundle, or `<namespace>__` only when that generated bundle's runtime identity is confirmed. Never derive it from the action namespace or folder name. The generated local source references stay `c__` and `@widget/c/`, even in a namespace-bearing org; backing Apex references have their own namespace. An installed `pkg` action in a namespace-less project can use `@apexClassType/pkg__Outer$Inner` while the runtime resource URI remains `ui://widget/lightningType/c__Envelope`. Never point the resource at the response CLT.
3. Select a stable MCP-local resource name and human-readable title and description. Read existing resources and the tool's link first. Use idempotent reuse when the resource URI/title/description and selected tool link already match; leave them unchanged and do not duplicate them. If a name is taken by a different resource, the tool already links another resource, or existing metadata would need replacement, show the conflict and ask for explicit reuse, rename, or replacement approval. Do not delete a resource used by other tools or rename its consumers implicitly.
4. Add one top-level `<resources>` block, a sibling of `<tools>`, never nested in it. Its URI is precisely `ui://widget/lightningType/<EnvelopeCLT-FQN>`. Add exactly one `<uiResource>` in the selected tool whose value matches `resourceName` byte-for-byte, including case. XML-escape user-supplied values.
5. Preserve the root element, namespace, existing tools, prompts, resources, all field values, indentation, and surrounding field order. Only approved widget-linkage values may change; do not reorder or rebuild unrelated metadata.

PR-compatible structural example (preserve all existing tool fields):
```xml
<McpServerDefinition xmlns="http://soap.sforce.com/2006/04/metadata">
    <tools>
        <!-- Existing apiDefinition, behavior, name and title stay intact. -->
        <uiResource>hotelDetails</uiResource>
    </tools>
    <resources>
        <resourceName>hotelDetails</resourceName>
        <resourceUri>ui://widget/lightningType/c__hotelInfoResult</resourceUri>
        <resourceTitle>Hotel details</resourceTitle>
        <description>Displays the selected hotel's details.</description>
    </resources>
</McpServerDefinition>
```
This is a linkage fragment, not a replacement server or a complete tool spec. Use the independently confirmed deployed envelope FQN in the URI; do not infer it from a namespaced action or blanket-substitute that runtime prefix into generated local source references.

## 6. Validate and deploy the server

Validate before writing to the org:

- XML is well-formed; the root `McpServerDefinition` element and namespace are unchanged.
- Resources are top-level siblings of tools; `resourceName`, `resourceUri`, `resourceTitle`, and `description` are non-empty; resource names are unique.
- Each intended URI exactly equals `ui://widget/lightningType/<EnvelopeCLT-FQN>` and resolves to the successfully deployed envelope CLT with its renderer.
- Each selected tool has exactly one intended `<uiResource>` matching an existing `resourceName` including capitalization; no link is outside its selected tool.
- Every approved binding and all unrelated tools, prompts, resources, and field values remain intact. Review the diff against the freshly retrieved authoritative file.

Name mismatches, unresolved FQNs, missing `lightningType` URI segments, nested resources, misplaced or duplicate links, and unapproved changes are blocking. Report the tool, resource name, final URI, generated files/FQNs, and individual validation results. Ask for MCP deployment confirmation, then deploy only the named server:

```bash
sf project deploy start --metadata McpServerDefinition:<SERVER_DEV_NAME> --target-org <target-org-alias>
```

Stop on failure. Re-retrieve the same named component (apply the same prior overwrite-consent rule for any new local edits), and verify that every approved resource URI and tool relationship persisted and approved bindings remain intact **before activation**. A successful deploy alone is not relationship verification. For unchanged idempotent reuse, no redundant deploy is needed, but verify deployed relationships before Phase 7. Client-side widget rendering remains pending integration verification, not a claim this metadata read-back proves.

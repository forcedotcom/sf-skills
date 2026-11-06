# Troubleshooting — experience-app-mcp-generate

Read only the section relevant to the failed phase. Apply Phase 0's disclosure rules to preflight diagnostics.

## Preflight

**`decision: skip` or `disabled` (exit 0):** `isAppMcpEnabled: false` or invocable-action `INVALID_INPUT` means this skill must not be used. `--skill-named` selects silent `skip` or `disabled` with a user message. Follow Phase 0.

**`decision: needs_input` (exit 0):** Show the safe message and corrective action, ask for a valid authenticated alias or org-supported `sourceApiVersion` of at least `68.0`, then rerun preflight. Do not edit existing project configuration without approval. These input errors are actionable even before gate enablement is known.

**`decision: error` (nonzero):** Show the returned message and corrective action; resolve the failure and rerun preflight. After gate success, errors are visible even for unnamed requests. Before success, other inconclusive failures route to silent `skip` unless explicitly named. Missing metadata types do not establish entitlement.

## ECA and deployment

**OAuth returns `invalid_scope`:** Confirm that the deployed ECA OAuth settings include `MCP`. Review the rendered metadata and targeted deployment result before changing or redeploying anything.

**A metadata property is invalid for the API version:** Keep the project `sourceApiVersion`, target-org support, and rendered metadata aligned. Review and confirm any version change before editing `sfdx-project.json`.

## Tool discovery and binding

**A bound tool is missing from the client:** Confirm that the global invocable Apex action or eligible autolaunched Flow exists in the org, that its `aa:` or `fa:` identifier is correct, and that the org's invocable-action MCP gate is enabled.

**A discovery pass returns no candidates:** An empty local scan means the scanned source tree has no eligible metadata. Empty Apex and Flow action arrays mean the authenticated user has no runtime candidates exposed by those endpoints. A non-zero exit means the REST listing failed or returned an invalid envelope, so do not treat it as an empty result. If a specific describe call fails, omit that candidate and report why it couldn't be evaluated; don't infer that other candidates are unavailable.

**Prompt discovery fails or returns no candidates:** `retrieve_existing_prompts.mjs` reads active templates through Connect REST and available prompt-template actions through the Actions API. A non-zero exit is an incomplete read, not proof of absence; check Prompt Builder enablement, the authenticated user's access, and the reported endpoint before retrying. A successful empty list means no candidates were exposed to that user.

**A bound prompt is missing from the client:** Check that the template is published and Flex, that `promptTemplateName` matches its API name, and that the client supports MCP prompts. For a `pr:` tool, confirm its prompt-template action is runtime-available and its identifier matches the template API name.

**The UI scan reports an already implemented capability:** Reuse the existing action or Flow instead of generating another implementation.

## Activation and client discovery

**The protected-resource document lacks `mcp_api`:** Confirm that `McpServerAccess.Active` is `true`, the ECA includes the `MCP` scope, and the deployed server name matches the resource URL. If all three are correct, allow for propagation and recheck.

**Activation reports a duplicate access row:** A duplicate proves only that the row exists. Re-query it and report success only when `Active=true`.

## Recovery and secrets

**A run failed after creating or changing state:** Report the exact files and records affected. Deactivate the server first, confirm no client uses it, then delete or revert only components created or changed by this run. Never delete reused state.

**A consumer secret was printed or written:** Treat it as compromised and have the user rotate it in Setup. Deleting the visible copy isn't sufficient remediation.

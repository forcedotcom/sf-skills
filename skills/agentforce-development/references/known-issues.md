# Known Issues Tracker

Unresolved platform bugs, limitations, and edge cases that affect Agent Script development. Unlike the "Common Issues & Fixes" table in SKILL.md (which covers resolved troubleshooting), this file tracks **open platform issues** where the root cause is in Salesforce, not in user code.

---

## Issue Template

```markdown
## Issue N: [Title]
- **Status**: OPEN | RESOLVED | WORKAROUND
- **Date Discovered**: YYYY-MM-DD
- **Affects**: [Component/workflow affected]
- **Symptom**: What the user sees
- **Root Cause**: Why it happens (if known)
- **Workaround**: How to get around it
- **Open Questions**: What we still don't know
- **References**: Links to related docs, issues, or discussions
```

---

## Open Issues

### Issue 1: Agent test files block `force-app` deployment
- **Status**: WORKAROUND
- **Date Discovered**: 2026-01-20
- **Affects**: `sf project deploy start --source-dir force-app`
- **Symptom**: Deployment hangs for 2+ minutes or times out when `AiEvaluationDefinition` metadata files exist under `force-app/`. The deploy may eventually succeed but with excessive wait times.
- **Root Cause**: `AiEvaluationDefinition` metadata type triggers server-side processing that blocks the deployment pipeline. The metadata type is not well-suited for source-dir deploys.
- **Workaround**: Move test definitions to a separate directory outside the main deploy path, or use `--metadata` flag to deploy specific types instead of `--source-dir`.
  ```bash
  # Instead of:
  sf project deploy start --source-dir force-app -o TARGET_ORG

  # Use targeted deployment:
  sf project deploy start --metadata AiAuthoringBundle:MyAgent -o TARGET_ORG
  ```
- **Open Questions**: Will Salesforce optimize `AiEvaluationDefinition` deploy performance in a future release?

---

### Issue 2: `sf agent publish` fails with namespace prefix on `apex://` targets
- **Status**: OPEN
- **Date Discovered**: 2026-02-01
- **Affects**: Namespaced orgs using `apex://` action targets
- **Symptom**: `sf agent publish authoring-bundle` fails with "invocable action does not exist" error, despite the Apex class being deployed and confirmed via SOQL query.
- **Root Cause**: Unknown. Unclear whether `apex://ClassName` or `apex://ns__ClassName` is the correct format in namespaced orgs. The publish step may not resolve namespace prefixes the same way as standard metadata deployment.
- **Workaround**: None confirmed. Potential approaches to try:
  1. Use `apex://ns__ClassName` format
  2. Use unmanaged classes (no namespace)
  3. Wrap Apex in a Flow and use `flow://` target instead
- **Open Questions**:
  - Does `apex://ns__ClassName` work?
  - Is this a bug or by-design limitation?
  - Does the same issue affect `flow://` targets with namespaced Flows?

---

### Issue 3: Agent packaging workflow unclear
- **Status**: OPEN
- **Date Discovered**: 2026-02-05
- **Affects**: ISV partners, AppExchange distribution
- **Symptom**: No documented way to package Agent Script agents for distribution. The `AiAuthoringBundle` metadata type has no known packaging equivalent to `BotTemplate`.
- **Root Cause**: Agent Script is newer than the packaging system. Salesforce has not published ISV packaging guidance for `.agent` files.
- **Workaround**: None. Current options:
  1. Distribute as source code (customer deploys manually)
  2. Use unlocked packages (may include `.agent` files but subscriber customization is untested)
  3. Convert to Agent Builder UI (GenAiPlannerBundle) for packaging — loses Agent Script benefits
- **Open Questions**:
  - Will `AiAuthoringBundle` be supported in 2GP managed packages?
  - Can subscribers modify `.agent` files post-install?
  - Is there a roadmap item for Agent Script packaging?

---

### Issue 4: Legacy `sf bot` CLI commands incompatible with Agent Script
- **Status**: OPEN
- **Date Discovered**: 2026-01-25
- **Affects**: Users migrating from Einstein Bots to Agent Script
- **Symptom**: Old `sf bot` and `sf bot version` commands were removed in sf CLI v2 — these commands no longer exist, not just "don't recognize Agent Script". Running any `sf bot` command returns "Command not found".
- **Root Cause**: The `sf bot` command family was deprecated and removed in sf CLI v2. It targeted `BotDefinition`/`BotVersion` metadata types. Agent Script uses `AiAuthoringBundle`, a completely separate metadata structure.
- **Workaround**: Use `sf agent` commands exclusively for Agent Script:
  ```bash
  # ❌ Old commands (don't work with Agent Script):
  sf bot list
  sf bot version list

  # ✅ New commands (for Agent Script):
  sf project retrieve start --metadata Agent:MyAgent
  sf agent validate authoring-bundle --api-name MyAgent
  sf agent publish authoring-bundle --api-name MyAgent
  ```
- **Open Questions**: Will Salesforce unify the `sf bot` and `sf agent` command families?

---

### Issue 5: Agent tests cannot be deployed/retrieved for source control
- **Status**: OPEN
- **Date Discovered**: 2026-02-06
- **Affects**: CI/CD pipelines, test version control
- **Symptom**: Tests created in the Agent Testing Center UI cannot be retrieved via `sf project retrieve start`. Old test XML format references `bot`/`version` fields that don't exist in Agent Script. No metadata type or CLI command exists for new-style agent tests.
- **Root Cause**: The Agent Testing Center was originally built for Einstein Bots. The test metadata schema hasn't been updated for Agent Script's `AiAuthoringBundle` structure. The `AiEvaluationDefinition` type exists but doesn't correspond to the Testing Center's UI-created tests.
- **Workaround**:
  1. Use YAML test spec files managed in source control (see `/sf-ai-agentforce-testing` skill)
  2. Treat UI-created tests as ephemeral / org-specific
  3. Use the Connect API directly to run tests programmatically
- **Open Questions**:
  - Will a new metadata type be introduced for Agent Script tests?
  - Can `AiEvaluationDefinition` be used with Agent Script agents?
  - Is there a roadmap for test portability?
- **References**: See `references/custom-eval-investigation.md` in `sf-ai-agentforce-testing` for related findings on custom evaluation data structure issues.

---

### Issue 6: `require_user_confirmation` does not trigger confirmation dialog
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Date Updated**: 2026-02-17 (TDD v2.2.0 — confirmed compiles on target-backed actions)
- **Affects**: Actions with `require_user_confirmation: True`
- **Symptom**: Setting `require_user_confirmation: True` on an action definition does not produce a user-facing confirmation dialog before execution. The action executes immediately without user confirmation.
- **Root Cause**: The property is parsed and saved without error, but the runtime does not implement the confirmation UX for Agent Script actions. It may only work for GenAiPlannerBundle actions in the Agent Builder UI.
- **TDD Update (v2.2.0)**: Property compiles and publishes successfully on action definitions with `target:` (both `flow://` and `apex://`). Val_Action_Meta_Props confirms compilation. The issue is purely runtime — the confirmation dialog never appears. Property is NOT valid on `@utils.transition` actions (Val_Action_Properties, v1.3.0).
- **Workaround**: Implement confirmation logic manually using a two-step pattern: (1) LLM asks user to confirm, (2) action has `available when @variables.user_confirmed == True` guard.
- **Open Questions**: Will this be implemented for AiAuthoringBundle in a future release?

---

### Issue 7: OOTB Asset Library actions may ship without proper quote wrapping
- **Status**: WORKAROUND
- **Date Discovered**: 2026-02-14
- **Affects**: Out-of-the-box (OOTB) actions from the Agentforce Asset Library
- **Symptom**: Some pre-built actions from the Asset Library have input parameters that are not properly quote-wrapped, causing parse errors when referenced in Agent Script.
- **Root Cause**: Asset Library actions were designed for the Agent Builder UI path, which handles quoting differently than Agent Script's text-based syntax.
- **Workaround**: When importing Asset Library actions, manually verify all input parameter names in the action definition. If a parameter name contains special characters or colons (e.g., `Input:query`), wrap it in quotes: `with "Input:query" = ...`
- **Open Questions**: Will Salesforce update Asset Library actions for Agent Script compatibility?

---

### Issue 8: Lightning UI components do not render on new planner
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: Agents using Lightning Web Components for rich UI rendering
- **Symptom**: Custom Lightning UI components referenced in agent actions do not render in the chat interface when using the newer planner engine. Components that worked with the legacy planner appear as plain text or are silently dropped.
- **Root Cause**: The newer planner (Atlas/Daisy) does not support the same Lightning component rendering pipeline as the legacy Java planner.
- **Workaround**: None for rich UI. Fall back to text-based responses or use the legacy planner if Lightning component rendering is critical.
- **Open Questions**: Is Lightning UI rendering on the roadmap for the new planner?

---

### Issue 9: Large action responses cause data loss from state
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: Actions returning large payloads (>50KB response data)
- **Symptom**: When an action returns a large response payload, subsequent variable access may return null or incomplete data. State appears to lose previously stored values.
- **Root Cause**: Action output data accumulates in conversation context without compaction. Very large responses may push earlier state data beyond the context window boundary.
- **Workaround**: Design Flow/Apex actions to return minimal, summarized data. Use `filter_from_agent: True` on outputs the LLM doesn't need. Avoid `SELECT *` patterns in data retrieval.
- **Open Questions**: Will automatic context compaction be added for action outputs?

---

### Issue 10: Agent fails if user lacks permission for ANY action
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: Agents with actions targeting secured resources
- **Symptom**: If the running user (Einstein Agent User or session user) lacks permission to execute ANY action defined in the agent — even actions in other topics — the entire agent may fail with a permission error rather than gracefully skipping the unauthorized action.
- **Root Cause**: The planner appears to validate permissions for all registered actions at startup, not lazily per-topic.
- **Workaround**: For **Service Agents**: Ensure the Einstein Agent User has both the `AgentforceServiceAgentUser` system PS AND a custom `{AgentName}_Access` PS with `<classAccesses>` for ALL Apex classes across all topics. Do NOT rely on the auto-generated `NextGen_{AgentName}_Permissions` — it is often incomplete (ORM1 testing: 3/4 classes, missing `ShipmentTracker`). For **Employee Agents**: Ensure each employee user has the custom PS assigned. See [agent-user-setup.md](agent-user-setup.md) for the full provisioning workflow and permission set XML template. Alternatively, split agents by permission boundary.
- **Open Questions**: Will the planner support lazy permission checking in a future release?

---

### Issue 11: Dynamic welcome messages broken (`{!userName}` not resolved)
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: `system.messages.welcome` with variable interpolation
- **Symptom**: Variable references like `{!@variables.customer_name}` or `{!userName}` in the welcome message display as literal text instead of resolved values.
- **Root Cause**: Welcome messages are rendered before the agent runtime initializes variables. Mutable variables have not been set yet, and linked variables may not be resolved at welcome-message time.
- **Workaround**: Use static welcome messages. Personalize greetings in the first topic's instructions instead.
- **Open Questions**: Will welcome message variable resolution be supported in a future release?

---

### Issue 12: Welcome message line breaks stripped
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: `system.messages.welcome` with multi-line content
- **Symptom**: Line breaks (`\n`) in welcome messages are stripped, causing multi-line messages to render as a single line.
- **Root Cause**: The welcome message renderer does not preserve newline characters from the Agent Script source.
- **Workaround**: Keep welcome messages as a single line. Use the first topic's instructions with pipe syntax (`|`) for multi-line greetings.
- **Open Questions**: Is this by design or a bug?

---

### Issue 13: Related agent nodes fail in SOMA configuration
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: Multi-agent configurations using `related_agent` references
- **Symptom**: SOMA (Same Org Multi-Agent) configurations that reference related agents via node declarations fail with "Node does not have corresponding topic" error at runtime.
- **Root Cause**: The planner resolves agent references at compile time but may not correctly map cross-agent topic references when agents are deployed independently.
- **Workaround**: Use `@topic.X` delegation within the same agent instead of cross-agent references. For true multi-agent scenarios, use the `@utils.escalate` or connection-based handoff patterns.
- **Open Questions**: Will SOMA node resolution be fixed in a future planner update?

---

### Issue 14: Previously valid OpenAPI schemas now fail validation
- **Status**: OPEN
- **Date Discovered**: 2026-02-14
- **Affects**: External Service actions using OpenAPI 3.0 schemas
- **Symptom**: OpenAPI schemas that previously passed validation and worked with `externalService://` targets now fail with schema validation errors after org upgrades. No changes were made to the schema files.
- **Root Cause**: Salesforce tightened OpenAPI schema validation rules in recent releases. Schemas that were previously accepted with minor deviations (e.g., missing `info.version`, non-standard extensions) are now rejected.
- **Workaround**: Re-validate schemas against strict OpenAPI 3.0 spec. Common fixes: ensure `info.version` is present, remove non-standard `x-` extensions, verify all `$ref` paths resolve correctly.
- **Open Questions**: Will Salesforce publish the exact validation rules that changed?

---

### Issue 15: Action definitions without `outputs:` block cause "Internal Error" on publish
- **Status**: WORKAROUND
- **Date Discovered**: 2026-02-16
- **Date Updated**: 2026-02-17 (TDD v2.1.0 — clarified outputs specifically required)
- **Affects**: `sf agent publish authoring-bundle` with topic-level action definitions
- **Symptom**: `sf agent publish` returns "Internal Error, try again later" when topic-level action definitions have `target:` but no `outputs:` block. Also triggered when using `inputs:` without `outputs:`. LSP + CLI validation both PASS — error is server-side compilation only.
- **Root Cause**: The server-side compiler needs output type contracts to resolve `flow://` and `apex://` action targets. Without an `outputs:` block, the compiler cannot generate return bindings. The `inputs:` block alone is NOT sufficient — `outputs:` is specifically required.
- **Workaround**: Always include an `outputs:` block in action definitions. The `inputs:` block can be omitted if the target has no required inputs (the LLM will still slot-fill via `with param=...`), but `outputs:` must always be present.
- **TDD Validation**: `Val_No_Outputs` (v2.1.0) confirms inputs-only action definition → "Internal Error". `Val_Partial_Output` confirms declaring a subset of outputs IS valid. `Val_Apex_Bare_Output` confirms bare `@InvocableMethod` without wrapper classes also triggers this error.
- **Open Questions**: Will the compiler be updated to infer I/O schemas from the target's metadata?

---

### Issue 17: `EinsteinAgentApiChannel` surfaceType not available on all orgs
- **Status**: OPEN
- **Date Discovered**: 2026-02-16
- **Affects**: Agent Runtime API channel enablement via `plannerSurfaces` metadata
- **Symptom**: Adding `plannerSurfaces` with `surfaceType: EinsteinAgentApiChannel` causes deployment errors on some orgs. Valid surfaceType values on tested orgs: `Messaging`, `CustomerWebClient`, `Telephony`, `NextGenChat`.
- **Root Cause**: The `EinsteinAgentApiChannel` surfaceType may require specific org features or licenses that are not universally available.
- **Workaround**: Use `CustomerWebClient` for Agent Runtime API / CLI testing. This surfaceType is available on all tested orgs and enables API access.
- **Open Questions**: Is `EinsteinAgentApiChannel` limited to specific editions or feature flags?

---

### Issue 18: `connection messaging:` only generates `Messaging` plannerSurface — `CustomerWebClient` dropped on every publish
- **Status**: OPEN
- **Date Discovered**: 2026-02-17
- **Affects**: Agent Builder Preview, Agent Runtime API testing, CLI testing (`sf agent test`, `sf agent preview`)
- **Symptom**: After `sf agent publish authoring-bundle`, the compiled GenAiPlannerBundle only contains a `Messaging` plannerSurface. `CustomerWebClient` is never auto-generated. Agent Builder Preview shows "Something went wrong. Refresh and try again." because it requires `CustomerWebClient`.
- **Root Cause**: The `connection messaging:` DSL block only generates a `Messaging` plannerSurface during compilation. There is no `connection customerwebclient:` DSL syntax — attempting it causes `ERROR_HTTP_404` on publish. The compiler has no mechanism to auto-generate `CustomerWebClient`.
- **Impact**: Every publish overwrites the GenAiPlannerBundle, dropping any manually-added `CustomerWebClient` surface. This requires a post-publish patch after EVERY publish.
- **Workaround — 6-Step Post-Publish Patch Workflow:**
  1. `sf agent publish authoring-bundle --api-name AgentName -o TARGET_ORG --json` → creates new version (e.g., v22)
  2. `sf project retrieve start --metadata "GenAiPlannerBundle:AgentName_vNN" -o TARGET_ORG --json` → retrieve compiled bundle
  3. Manually add second `<plannerSurfaces>` block to the XML with `<surfaceType>CustomerWebClient</surfaceType>` (copy the existing `Messaging` block, change surfaceType and surface fields)
  4. `sf agent deactivate --api-name AgentName -o TARGET_ORG` → deactivate agent (deploy fails while active)
  5. `sf project deploy start --metadata "GenAiPlannerBundle:AgentName_vNN" -o TARGET_ORG --json` → deploy patched bundle
  6. `sf agent activate --api-name AgentName -o TARGET_ORG` → reactivate agent
- **Patch XML Example:**
  ```xml
  <!-- Add this AFTER the existing Messaging plannerSurfaces block -->
  <plannerSurfaces>
      <adaptiveResponseAllowed>false</adaptiveResponseAllowed>
      <callRecordingAllowed>false</callRecordingAllowed>
      <outboundRouteConfigs>
          <escalationMessage>One moment while I connect you with a support specialist.</escalationMessage>
          <outboundRouteName>Route_from_Your_Agent</outboundRouteName>
          <outboundRouteType>OmniChannelFlow</outboundRouteType>
      </outboundRouteConfigs>
      <surface>SurfaceAction__CustomerWebClient</surface>
      <surfaceType>CustomerWebClient</surfaceType>
  </plannerSurfaces>
  ```
- **Note**: The `outboundRouteConfigs` should mirror the Messaging surface config. If no routing is configured, omit `outboundRouteConfigs`.
- **Validated on**: YourOrg (Your_Agent_Name v22), 2026-02-17

---

### Issue 19: Comments inside `if` blocks treated as empty body
- **Status**: OPEN
- **Date Discovered**: 2026-03-04
- **Affects**: `if`/`else` blocks in `instructions: ->`
- **Symptom**: An `if` block containing only comments (e.g., `# TODO`) compiles but produces an empty body at runtime. The parser strips comments during tokenization, and the resulting `INDENT → DEDENT` with no executable statements creates a no-op branch that silently swallows the conditional path.
- **Root Cause**: Comments are not executable statements in Agent Script. The parser treats a comment-only block identically to an empty block.
- **Workaround**: Always include at least one executable statement (`| text`, `run`, `set`, or `transition`) in every `if`/`else` block. Never use comment-only blocks as placeholders.
  ```yaml
  # ❌ WRONG — empty body after comment stripping
  if @variables.premium == True:
    # TODO: add premium greeting

  # ✅ CORRECT — executable statement present
  if @variables.premium == True:
    | Welcome back, valued premium member!
  ```
- **Open Questions**: Will the compiler emit a warning for empty `if` bodies?

---

### Issue 20: GenAiPlannerBundle / AiAuthoringBundle / GenAiFunction NOT SOQL-queryable
- **Status**: WORKAROUND (by design — metadata types, not sObjects)
- **Date Discovered**: 2026-03-04
- **Affects**: Any workflow that attempts SOQL queries on agent metadata types
- **Symptom**: `SELECT ... FROM GenAiPlannerBundle` returns `INVALID_TYPE: GenAiPlannerBundle`. Same for `AiAuthoringBundle` and `GenAiFunction`. These types do not appear in `EntityDefinition` SOQL queries.
- **Root Cause**: These are **Metadata API types**, not sObjects. They exist in the metadata layer and are only accessible via `sf project retrieve start --metadata` or the Metadata API. This is by design, not a bug.
- **Workaround**: Use `sf project retrieve start --metadata "TypeName:ApiName"` instead of SOQL. For querying agent status/versions via SOQL, use `BotDefinition` and `BotVersion` sObjects.
  ```bash
  # ❌ WRONG — these are NOT sObjects
  sf data query --query "SELECT Id FROM GenAiPlannerBundle" -o ORG --json
  sf data query --query "SELECT Id FROM AiAuthoringBundle" -o ORG --json

  # ✅ CORRECT — use Metadata API
  sf project retrieve start --metadata "GenAiPlannerBundle:MyAgent_v1" -o ORG --json
  sf project retrieve start --metadata "AiAuthoringBundle:MyAgent" -o ORG --json

  # ✅ CORRECT — query sObjects for agent info
  sf data query --query "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'MyAgent'" -o ORG --json
  sf data query --query "SELECT Id, VersionNumber, Status FROM BotVersion WHERE BotDefinition.DeveloperName = 'MyAgent'" -o ORG --json
  ```
- **Open Questions**: None — this is by design.

---

## Resolved Issues

### Issue 16: `connections:` (plural) wrapper block not valid — use `connection messaging:` (singular)
- **Status**: RESOLVED
- **Date Discovered**: 2026-02-16
- **Date Resolved**: 2026-02-16
- **Affects**: Agent Script escalation routing configuration
- **Symptom**: CLI validation rejects `connections:` (plural wrapper) block with `SyntaxError: Invalid syntax after conditional statement`.
- **Root Cause**: The correct syntax is `connection messaging:` (singular, standalone top-level block) — NOT the `connections:` plural wrapper shown in some docs and `future_recipes/`. The `connection <channel>:` block is a Beta Feature available on production orgs.
- **Resolution**: Use `connection messaging:` as a standalone block (no wrapper). Both minimal form (`adaptive_response_allowed` only) and full form (with `outbound_route_type`, `outbound_route_name`, `escalation_message`) are validated.
- **CRITICAL**: `outbound_route_name` requires `flow://` prefix — bare API name causes `ERROR_HTTP_404` on publish. Correct format: `"flow://My_Flow_Name"`.
- **All-or-nothing rule**: When `outbound_route_type` is present, all three route properties are required.
- **Validated on**: YourOrg (Your_Agent_Name), 2026-02-16

---

## Contributing

When you discover a new platform issue during an Agent Script session:

1. Add it to the **Open Issues** section using the template above
2. Assign the next sequential issue number
3. Set status to `OPEN` or `WORKAROUND`
4. Include the date discovered
5. Be specific about the symptom and any error messages
6. Note what you've tried so far under "Workaround"

When an issue is resolved:
1. Update the status to `RESOLVED`
2. Add the resolution date and what fixed it (e.g., "Fixed in Spring '26 release")
3. Move the issue to the **Resolved Issues** section

---

*Last updated: 2026-03-04*

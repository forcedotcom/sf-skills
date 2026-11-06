---
name: experience-app-mcp-generate
description: "Create, extend, deploy, review readiness for, or activate an App MCP, a Salesforce custom hosted MCP server for an Aura Experience Site. Trigger when the user wants to expose an Experience UI or backend action to agents, create local ECA and server metadata, add eligible global invocable Apex or autolaunched Flow tools, add Prompt Builder templates as MCP prompts or tools, preview or perform server activation, deploy the existing MCP stack, or review its readiness. For server setup, offer optional HXL widgets for eligible Apex-backed tools through platform-mcp-tool-widget-coordinate. For a standalone request to generate Custom Lightning Types or widgets for an Apex-backed MCP tool, route directly to platform-mcp-tool-widget-coordinate; do not trigger this skill for HXL generation alone. Do not trigger for remote MCP registration or generic Apex and Flow work unrelated to Experience Site agent access."
metadata:
  relatedSkills:
  - experience-app-mcp-delivery-generate
  - platform-apex-generate
  - platform-mcp-tool-widget-coordinate
  version: "1.0"
  minApiVersion: "68.0"
  domains:
  - "Experience"
  cliTools:
  - tool:
    - "node"
    semver: ">=18.0.0"
  - tool:
    - "sf"
    semver: ">=2.0.0"
---

# Set Up Custom MCP for an Experience Site

End-to-end recipe: **ExternalClientApplication (ECA) → custom hosted MCP server → tools and prompts → deploy → optional HXL widgets + Custom Lightning Types + MCP widget resources → activate → verify → optional client delivery**. The Experience Site scopes naming and discovery; the MCP server is org-level.

Supports Aura Experience Sites with local ExperienceBundle source. The inventory checks the selected site's view components to determine source support.

## Shared rules

- `<skill-dir>` means the absolute directory containing this `SKILL.md`. Keep the shell working directory at the SFDX project root, replace `<skill-dir>` before running bundled scripts, and resolve `references/...` links relative to this `SKILL.md`.
- Run Phase 0 before every entry path, including repair, resume, and preview/activate-only requests. Proceed only on `decision: continue`.
- Reconcile with existing state before creating or changing anything. Reuse compatible ECAs, servers, and tool bindings by default. On interruption, use [the progress check](#check-progress--after-phase-2-or-on-resume).
- `McpServerDefinition` and related runtime records are Tooling API objects. Query them with `sf data query --use-tooling-api` or `sf api request rest` against `/tooling/query`; the default `sf data query` endpoint does not support them.
- For authoring, create a missing `sfdx-project.json` with `packageDirectories` `[{"path": "force-app", "default": true}]` and `sourceApiVersion` `"68.0"`. Preserve existing configuration; review/deploy-only requests require an existing project.
- `<default-package>` is the `path` of the `packageDirectories` entry with `"default": true`, or the first entry when none is marked. Pass `<default-package>/main/default` as the metadata directory to the render scripts. Phase 1 still inspects every package directory for the site.
- Track the exact metadata files created or changed during the run. Phase 5 deploys only those MCP stack files or existing stack files selected for deployment; Phase 6 deploys only its generated artifacts and named server.
- Handle preflight results as specified in Phase 0. For later failures, stop and report what changed. Read the relevant section of `references/troubleshooting.md` before proposing recovery.

## Review or deploy an existing stack

Run Phase 0, recover confirmed site/server/ECA identities, then use the progress check and [existing-stack review](references/mcp-objects.md#existing-stack-review). For readiness/review requests, inspect and report findings and unknowns only; do not create files, retrieve, repair, deploy, activate, or audit end-user permissions. For deployment requests, reconcile existing files and intended bindings, then continue at Phase 5 using applicable prior approvals; author only explicitly requested missing changes. Script success or file presence does not establish readiness.

## Repair existing ECA or MCP metadata

For ECA files, run the renderer in read-only comparison mode:
```bash
node "<skill-dir>/scripts/render_eca.mjs" <default-package>/main/default <ECA_DEV_NAME> --check
```
Follow the report's field findings, `expectedValues`, and `nextActions`. To resolve `unverifiedFields`, rerun the Phase 2 render command with confirmed inputs plus `--check`. Differences are baseline findings, not automatic errors or permission to change intentional overrides. For field ownership, read [references/eca-fields.md](references/eca-fields.md).

For MCP repairs, read `assets/__MCP_SERVER_NAME__.mcpServerDefinition-meta.xml` and [references/mcp-objects.md](references/mcp-objects.md). Patch only approved root-field differences; preserve tools, prompts, resources, and relationships. Use `merge_tools.mjs` for binding changes.

## Phase 0 — Preflight

IMPORTANT: Set `<skill-named>` to `true` only if the user's request explicitly names `experience-app-mcp-generate`; otherwise use `false`. Do not count the agent's own skill selection or messages.

```bash
node "<skill-dir>/scripts/preflight.mjs" <target-org-alias> --skill-named <skill-named>
```

Read the JSON `decision`:

- `continue`: follow the requested entry path; authoring starts at Phase 1. Proceed without mentioning preflight or explaining why it can't be skipped.
- `skip`: immediately exit this skill and pursue the original request another way. Say nothing about this skill, its check, or the result.
- `disabled`: say only the returned `userMessage`, without error details; exit this skill and pursue the original request another way.
- `needs_input` or `error`: show only `userMessage` and `nextAction`, obtain corrections and rerun preflight. Proceed only on `continue`; never infer entitlement from errors.

## Phase 1 — Experience Site + naming

1. **List local sites** from the SFDX project root:
   ```bash
   node "<skill-dir>/scripts/list_sites.mjs"
   ```
   Stop if the script fails. Report only each site's name and status, without framework, metadata/source-format labels, or extra discovery explanations. Match the user's site to an entry; if unclear, show the choices and ask the user to select one. The site scopes naming and UI review; the MCP server remains org-level.
2. **Check the selected entry's status before continuing.** For `ready`, report **Ready** and continue with its supported Aura ExperienceBundle views. For `unsupported`, stop with a short report only: the site name and **Unsupported**, one sentence that this skill supports only Aura Experience Sites with local ExperienceBundle source, and that no ECA, MCP server, or tool bindings were created. Omit script output, framework details, file-by-file lists, and next steps unless asked; if you created `sfdx-project.json` only to run the scripts, mention it in one clause. For `metadata-incomplete`, report its `reason` when present and resolve the selected site's source errors or Network-to-bundle association; obtain its ExperienceBundle or DigitalExperienceBundle and Network metadata as needed, then rerun the inventory. Inspect the entry's metadata evidence for its Network name and `<urlPathPrefix>`. For `ui-not-found`, or a requested site absent from the inventory, ask the user to confirm the site and provide its ExperienceBundle source location or authorize retrieval, then rerun the inventory. Continue with a `ready` entry and usable UI source. Problems with unselected sites do not block this workflow.
3. List deployed Experience Sites in the target org:
   ```sql
   SELECT Name, UrlPathPrefix FROM Network
   ```
   (via `sf data query` or Tooling REST.)
   Reconcile the local and org results:
   - If the site exists in both and the names and path prefixes agree, continue.
   - If it exists only locally, treat it as a valid planned site and continue the local MCP generation workflow. The MCP server is org-level, so an undeployed Network does not block local MCP authoring. Report that the site is not deployed; do not claim there is no site or that nothing can be bound. Before Phase 5 deployment or Phase 7 activation, confirm that the site has been deployed by its owning workflow. Do not add unchanged site metadata to this skill's targeted deployment.
   - If it exists only in the org, obtain its local site metadata as required by step 2 and rerun the inventory to determine source support before continuing.
   - If local and org definitions conflict, show the mismatch and ask which definition is authoritative before continuing.
   - Only report that the site must be created first when neither the local project nor the org contains it.
4. Derive a `McpServerDefinition.DeveloperName` from the site name and let the user know. The MCP server name must contain 2–60 alphanumeric characters; remove spaces, punctuation, and other symbols. Check for a collision by querying existing MCP servers using tooling API:
   ```bash
   sf data query --use-tooling-api --target-org <target-org-alias> --query "SELECT Id, DeveloperName FROM McpServerDefinition" --json
   ```
   If a matching MCP Server already exists, then check with the user if it can be reused.
5. Report to the user on whether we're creating a new MCP server with the derived name or if we're going to use an existing one.

## Phase 2 — ECA (reuse-or-create)

When reviewing rendered ECA metadata or changing its settings after rendering, read `references/eca-fields.md` to locate the owning metadata component and field. Treat callback URLs, OAuth scopes, permitted-user policy, and refresh-token policy as client-affecting settings: show the proposed diff and confirm before changing them. For a new ECA, read `references/eca-fields.md` to review permitted-user policy choices before rendering. Default to admin preauthorization; suggest self-authorization for all authenticated site users and apply it only if chosen.

1. Confirm the ECA DeveloperName, then check for an existing ECA matching it:
   ```sql
   SELECT Id, DeveloperName FROM ExternalClientApplication
   ```
   Confirm its OAuth scopes include `MCP` and `RefreshToken`, and that its callback URLs cover the confirmed MCP clients. If the clients or their callback URLs aren't known yet, ask before deciding that the ECA is compatible.
2. **If a compatible ECA is found: reuse it, read-only.** Report what it is and where it points. Do not touch it unless the user explicitly asks for a change — and even then, show the diff and warn about breaking live clients before writing.
3. **If absent:** If local ECA files exist, run the comparison above, reuse compatible files, and create only confirmed missing components from its named templates. Review differences before changing files; never delete files or bypass overwrite protection to rerender a partial set. If no local files exist, confirm the MCP clients and their exact OAuth redirect URIs, show the planned files, confirm the local write, then render:
   ```bash
   node "<skill-dir>/scripts/render_eca.mjs" <default-package>/main/default <ECA_DEV_NAME> <ECA_LABEL> <ECA_DESC> <CONTACT_EMAIL> "<callback-urls>"
   ```
   Run the ECA comparison above on rendered or reused local files and review its findings before proposing a diff. If the permitted-user and refresh-token policies were not already reviewed in the conversation, ask the user to review them because they control who may authorize and how long refresh tokens remain valid.

## Check progress — after Phase 2 or on resume

For new setups, run this after Phase 1 selects the site/server and Phase 2 confirms the ECA name. On resume, run Phase 0 first, recover those identifiers from the conversation or workspace, and ask only for missing or ambiguous choices. Include the optional confirmed site bundle for local readiness checks.

```bash
node "<skill-dir>/scripts/check_setup_progress.mjs" <target-org-alias> <SERVER_DEV_NAME> <ECA_DEV_NAME> [--site <SITE_BUNDLE>]
```

Present its `checks` and follow `nextAction`, `pendingVerification`, and `resumeRules`. Exit `0` means the audit ran, not setup completion; `auditStatus: partial` leaves affected reads unknown. Retain existing confirmation rules and resolve unknowns before dependent writes.

## Phase 3 — Custom MCP server (render inactive, via Metadata API)

1. Before reconciling existing state, read the object model and metadata invariants in `references/mcp-objects.md`. Query `McpServerDefinition` by the confirmed DeveloperName. If absent and a local server definition exists, inspect and reconcile it against the bundled template and confirmed inputs using [Repair existing ECA or MCP metadata](#repair-existing-eca-or-mcp-metadata); preserve its bindings, reuse the repaired component, and continue remaining binding review. Local metadata is not deployed state. Continue to step 2 only when the local component is missing. If the org component is partial, retrieve it and merge into it; re-rendering would drop tools, prompts, or resources that the scan did not reconstruct. Before retrieval, identify any destination file that already exists and confirm whether it may be overwritten, then retrieve the existing `McpServerDefinition:<name>` metadata so that a local `<default-package>/main/default/mcpServerDefinitions/<name>.mcpServerDefinition-meta.xml` file exists for Phase 4 to merge into. Phase 4 uses `merge_tools.mjs` to preserve existing bindings while adding approved tools and prompts. If the server is complete, reuse it and ask before changing its bindings. For a new setup or requested extension, do not skip Phase 4 merely because the server has bindings; during an interrupted setup, skip only when the intended bindings are confirmed from prior user decisions and verified complete locally and in the org.
2. When the local server component is missing, show the destination file and confirm the local write, then render the metadata component into the same SFDX project (no bindings yet). `<SERVER_LABEL>` must be human-readable (e.g. "Support Automation MCP") — never the bare DeveloperName repeated as the label:
   ```bash
   node "<skill-dir>/scripts/render_mcp_server.mjs" <default-package>/main/default <SERVER_DEV_NAME> <SERVER_LABEL> <SERVER_DESC>
   ```

## Phase 4 — Tools and prompts

Before discovery and binding, read [references/tool-bindings.md](references/tool-bindings.md). For new setups and requested extensions, complete all four passes in order: site UI, local Apex/Flow, org Apex/Flow, and Prompt Builder. Inventory every UI CRUD operation before scanning for backings, then suggest a tool for each one after deduplicating at the end of 4c. Record each pass's result and evidence separately before 4e. On resume, repeat only incomplete or changed passes and preserve confirmed choices. Then continue with Phase 4e below.

**4e. Author and bind approved tools and prompts — applies to candidates from 4a–4d.**

Ask add-or-skip per eligible candidate and whether a selected template should be a prompt, tool, or both. Before authoring or exposing custom Apex actions, load `platform-apex-generate` and apply the reference's runtime input-validation and explicit user-mode requirements. **Always use `merge_tools.mjs`; never edit `<tools>` or `<prompts>` XML directly for Phase 4 binding.** The Phase 6 widget linkage exception permits only the scoped resource relationships in [references/widget-resources.md](references/widget-resources.md), not tool or prompt authoring.

## Phase 5 — Deploy the MCP stack

Only after the ECA, server, backing actions/templates, and bindings are ready:

1. Show the exact metadata files changed during this workflow or selected from the existing stack for deployment. This normally includes the rendered ECA files, implemented Apex classes and their companion metadata or Flows, and the MCP server definition. **Ask the user to confirm deployment**, unless an applicable prior approval covers the same target, files, and actions, then deploy exactly those tracked metadata files using the two-wave ECA exception below. Keep the remaining stack deployment multi-file and atomic across metadata types. Do not deploy the package directory or a whole metadata-type directory.

   **ECA deploy order — two waves required.** If the tracked files include ECA metadata, deploy the `ExternalClientApplication` parent file alone in a first deploy, then deploy the other child types in a second deploy. Deploying all ECA files in one call fails silently or leaves children undeployed.

   When resuming after a verified parent deployment, reuse that wave. If successful deployment evidence for any child component is unavailable, report its deployed state as unknown and propose a narrow retry of the exact tracked child files under the applicable deployment approval. Exclude the verified parent and reused components outside this run's approved changes; keep child deployment incomplete until the retry succeeds.

   Stop if deployment fails. Do not activate a partially deployed server.
2. Confirm that the deployed `McpServerDefinition` contains every approved tool and prompt. Verify that the backing actions/templates deployed successfully; widget generation requires the real deployed Apex action contract, not stale local source.

## Phase 6 — Generate and attach MCP tool widgets

After Phase 5 succeeds and before loading `platform-mcp-tool-widget-coordinate`, establish whether the user wants HXL widgets for eligible Apex-backed tools. Reuse an explicit HXL request or prior approval; otherwise ask once whether to generate the widgets and prepare their local resource links. If the user declines, mark Phase 6 skipped and continue to Phase 7. If accepted, read [references/widget-resources.md](references/widget-resources.md) and execute its full procedure. It covers eligible `aa:apex-` tools only and delegates generation and its existing gates to `platform-mcp-tool-widget-coordinate`. This skill then checks the complete response bundle, prepares the narrow deployment checklist from the validated artifacts, retrieves the authoritative server with prior overwrite consent, and attaches and verifies widget resources. Flow-backed and prompt-backed tools and MCP prompts are skipped, not reinterpreted as Apex actions. Stop on any generation, gate, deployment, retrieval, or linkage failure; report partial files and do not activate.

## Phase 7 — Activate and verify

Continue after Phase 6 succeeds or is skipped. For an explicit preview/activate-only request for an already-deployed named server, start at step 1; skip earlier phases and preserve existing bindings and resources.

1. Activation uses Tooling writes because `McpServerAccess` has no metadata type. Preview first: without flags, `activate_server.mjs` queries the server and prints `plannedRequest` (method, URL and body) without writing. Show it and ask before using `--confirm`, which writes and re-queries the state. Use authenticated `sf` requests for activation and verification, never direct `curl`.
   ```bash
   node "<skill-dir>/scripts/activate_server.mjs" <target-org-alias> <SERVER_DEV_NAME>
   node "<skill-dir>/scripts/activate_server.mjs" <target-org-alias> <SERVER_DEV_NAME> --confirm
   ```
   An authentication failure means the target org must be reauthenticated before retrying; it does not mean Tooling activation is unavailable. Ask the user to use Setup only when the Tooling operation itself is unavailable.
2. Verify the definition, approved tools and prompts, Phase 6 widget-resource relationships when applicable, and active state. For tool-bearing servers, the read-only script reports `status: ready` only when the server is active and has at least one tool (otherwise `not_found`, `inactive` or `no_tools`, still exit 0); it does not verify widget relationships, which require Phase 6's metadata read-back:
   ```bash
   node "<skill-dir>/scripts/verify_server.mjs" <target-org-alias> <SERVER_DEV_NAME> [--json]
   ```
   For a prompt-only server, confirm active state with the activation script's read-only preview and inspect the deployed `McpServerDefinition` for the expected `<prompts>` entries; `verify_server.mjs` currently requires a tool and is not a prompt-only verifier. Test `prompts/list` in a compatible connected client when available.
   For client readiness, also fetch the OAuth protected-resource document associated with the final serving URL and confirm that `scopes_supported` includes `mcp_api`. This is an integration check outside `verify_server.mjs`; derive the document URL from authoritative routing information for the target environment rather than inventing a portal URL.
3. Report deployment/activation results, serving URL, bound tools/prompts, widget resources/URIs, HXL/Custom Lightning Type files/FQNs, and widget validation results. Keep preflight disclosure within Phase 0's rules. On a failed write, report existing records and offer reverse-order teardown; deactivate before deleting. Client connection is manual. Until the user confirms the deployed bindings and renditions in their client, mark connection, tool/prompt parity and widget rendering as pending integration verification.
4. Before client testing, remind the admin to verify end users' `API Enabled`, Apex Class Access, Flow access/`Run Flows`, required object CRUD, field permissions, record access/sharing, and tool-specific permissions. This skill does not audit, configure, or grant end-user permissions.

## Phase 8 — Deliver the MCP connection

After successful deployment, activation and verification, offer an MCP configuration or Claude plugin through **`experience-app-mcp-delivery-generate`**. Invoke it when the user requests delivery or accepts the offer; reuse an earlier request or acceptance. If the user declines, finish with the Phase 7 results. For a preview-only, activation-only or metadata-only request, finish at that request's boundary unless delivery was also requested.

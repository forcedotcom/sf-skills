---
name: service-digital-engagement-deployment-configure
description: "Configures Embedded Messaging Deployments for Messaging for In-App and Web (MIAW). Use when the user needs to create a new embedded messaging deployment from scratch using Connect API with defaults, or update an existing deployment's settings using Metadata API, including custom labels (widget text such as the Today divider, with translations). Produces Connect API request payloads for new deployments and EmbeddedServiceConfig metadata XML for updates. TRIGGER when the user mentions embedded messaging deployment, embedded service deployment, MIAW deployment, messaging widget setup, chat widget configuration, embedded chat deployment, changing or translating the text a messaging widget shows (custom labels), or references a .EmbeddedServiceConfig-meta.xml file. DO NOT TRIGGER when the user is creating a messaging channel (use service-digital-engagement-channel-configure), configuring legacy Live Agent embedded service, or generating the JavaScript code snippet for website embedding."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "automation-flow-generate"
    - "platform-permission-set-generate"
    - "service-digital-engagement-channel-configure"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.7.0"
---

# Configuring Embedded Messaging Deployment

Configures `EmbeddedServiceConfig` metadata for Salesforce Messaging for In-App and Web (MIAW). Supports two distinct workflows: creating new deployments via Connect API and updating existing deployments via Metadata API.

## How delegation is handled

### Service-Onboarding delegation

When `delegationFrom` is set to service-onboarding, fetch and follow
[the Service-Onboarding delegation guidelines](references/_vendored/service-onboarding-delegation-guidelines.md) before acting — it is the single
source of truth, identical across every service-onboarding delegate. When it is absent, ignore this
and run as a normal standalone conversation.

---

## Scope

- **In scope**: Creating new Embedded Service Deployments (API, Mobile, Web types) via Connect API; updating existing deployments with forms, branding, channel settings, and features via Metadata API; generating `EmbeddedServiceConfig` XML for updates
- **Out of scope**: Creating the messaging channel itself (use `service-digital-engagement-channel-configure`), generating the website code snippet (offered only as a next step, see `references/code_snippet.md`), creating Experience Sites (Connect API prerequisite for Web type)

---

## Entry points and transport

- **Delegated** (`delegationFrom` is set; alias `context.calledFrom == "service-onboarding"` until onboarding drops it): read the inputs from `intent` and ask only for what it leaves open (`deploymentName`, `deploymentType`, `channelName`). Never fabricate a value; invalid shell input or an unknown channel is `failed`. **Standalone** (no `delegationFrom`): run Clarifying Questions.
- **Shell safety**: before use in a command, the org alias must match `^[A-Za-z0-9][A-Za-z0-9_.@+-]*$`, the derived API name `^[a-zA-Z][a-zA-Z0-9_]*$`, a channel Id `^[A-Za-z0-9]{15,18}$`, and `hostDomain` `^[A-Za-z0-9.-]+(:[0-9]+)?$`; otherwise stop and ask (delegated: `failed`). Pass labels and other free text single-quoted, escaping any `'` as `'\''`, and build JSON bodies with `jq -n --arg` (see `references/connect_api_creation.md`), never by string splicing.
- **Transport A** (primary): headless-360 MCP `dispatch` / `dispatch_readonly` on `/services/data/vXX.0/headless/metadata`. **Transport B**: the `sf` commands below, only where a probe shows Transport A unavailable. **Decide the transport before the first org command and say it in one line** (`Transport: A, probe returned xmlRep` or `Transport: B, <signal>`); no org write without that line. For B, quote the failed tool load or the probe's error text: "dispatch isn't available" with no load attempt or probe result is not a reason. If `dispatch` / `dispatch_readonly` is not in your tool list, try to load it (e.g. ToolSearch) and probe before choosing B. If you have no tool-loading tool or the load fails, that is the signal: quote it, take B, and continue; never stop without writing. Use B only on one of these signals: `ROUTE_NOT_FOUND`, `UNSUPPORTED_OPERATION`, `METADATA_CRUD_ERROR`, or an auth/connection error. The choice resets at every step: an earlier `sf` step (e.g. the Web create) is never a reason to use `sf` for the next. The Web create also tries A first and falls back to B only on `INTERNAL_ERROR` from that call (step 17a).
- **Target org**: before the first write, confirm the target org and sandbox/production with the user (contract §2); a switch from Transport A to B is a new confirmation.

Details: `references/onboarding_contract.md` (§1 entry points, §2 transport, §3 pre-scan, §5 result).

---

## Clarifying Questions

Before generating, ask the user if not already clear (standalone only):

- **Create or update?** Are you creating a new deployment or updating an existing one?
- **Deployment type?** API (headless), Mobile (native apps), or Web (browser widget)?
- **Channel name?** What is the `channelPlatformKey` of the messaging channel to associate?
- For **create**: What should the deployment be named?
- For **update**: What features to configure? (pre-chat forms, custom labels, business hours, T&C, UI toggles)
- For **pre-chat** (if requested): the questions in `references/prechat_forms.md` §Inputs to Gather
- For **update (Web)**: What is the Experience Site name? Branding overrides needed?

---

## Required Inputs

Gather or infer before proceeding:

- **Operation**: `create` or `update`
- **Deployment type**: `API`, `Mobile`, or `Web`
- **Deployment name**: Used as `masterLabel`. Derive the API name (`fullName` / `DeveloperName`, Connect `name`) from it: replace each run of characters other than letters and digits with `_`, then trim leading/trailing `_` (`Acme Support Chat` → `Acme_Support_Chat`). The result must match `^[a-zA-Z][a-zA-Z0-9_]*$`. Use the API name for every lookup and write
- **Channel name**: The `channelPlatformKey` of the associated messaging channel

For **update** operations additionally:
- **Site name** (Web only): The Experience Site name (format `ESW_<name>_<timestamp>`)
- **Branding name** (optional): Reference to existing `BrandingSet`
- **Pre-chat form fields** (optional): see `references/prechat_forms.md` §Inputs to Gather
- **Business hours** (optional): Name of existing `BusinessHours` record

Defaults unless specified:
- `isEnabled`: `true`
- `deploymentFeature`: `EmbeddedMessaging`

---

## Workflow

All steps are sequential. Do not skip or reorder. Branch based on the operation type.

### Phase 1 — Gather Context

1. **Verify org API version** — run `scripts/check-api-version.sh 67.0 '<org-alias>'` and report any errors it returns. Exit 1 = org below 67.0: stop all org writes and relay the script's next step (delegated: `failed`); local template generation may continue. Exit 3 = invalid org alias: stop and ask for the alias (delegated: `failed`). Exit 2 = version could not be read: warn that it is unverified and continue; the deploy confirms it. Create `sfdx-project.json` in the metadata output folder only if none exists, with `sourceApiVersion` set to the script's `ORG_API_VERSION` (67.0 if exit 2).

2. **Determine operation** — standalone: ask whether the user wants to create a new deployment or update an existing one. Delegated: taken from `intent`, defaulting per contract §1, then confirmed by the pre-scan (step 4a).

3. **Collect inputs** — standalone: per Clarifying Questions. Delegated: from `intent` (`deploymentName`, `deploymentType`, `channelName` required; ask for any it omits).

3a. **Probe transport** — read-only `GET` of `EmbeddedServiceConfig` (contract §2).

4. **Read deployment settings reference** — load `references/deployment_settings.md` to understand all available configuration options.

4a. **Pre-scan** — look up the deployment by its derived API name (contract §3): none → `create` (Phase 2A); matches → no write, `already-configured`, skip to Phase 3; differs → `update` (Phase 2B), announce each change (standalone: ask first); linked to a different channel → standalone: ask before repointing, delegated: `failed`. Standalone, deployment exists: offer exactly three choices — no change / override / add to existing.

### Phase 2A — Create New Deployment

Use this path when the operation is `create`.

5. **Determine API method by type** — API/Mobile: Metadata API deploy. Web: Connect API (creates the Experience Site). All types need the channel to exist.

6. **For API/Mobile types** — read the template `assets/esd_api_mobile_template.xml` and generate the `EmbeddedServiceConfig` XML with:
   - `deploymentType` set to `API` or `Mobile`
   - `deploymentFeature` set to `EmbeddedMessaging`
   - All defaults applied

7. **For Web type** — inform the user that Web deployments require Connect API for initial creation because of a circular dependency between Network and CustomSite. Read `references/connect_api_creation.md` for the Connect API payload and instructions.

8. **Generate output** — produce the `.EmbeddedServiceConfig-meta.xml` file (for API/Mobile) or Connect API instructions (for Web).

9. **Present output and next steps** — as in step 17.

### Phase 2B — Update Existing Deployment (Metadata API)

Use this path when the operation is `update`.

10. **Retrieve the existing deployment** — take the current `EmbeddedServiceConfig` from the org before making changes. Transport A: the `xmlRep` from the step 3a/4a `GET`. Transport B:
    ```bash
    sf project retrieve start --metadata EmbeddedServiceConfig:<DEPLOYMENT_NAME> --target-org '<org-alias>'
    ```
    Use it as the starting structure — the update is always a **full document** (see Rules). If retrieval is not possible, load `assets/esd_web_update_template.xml` as a fallback reference.

11. **Apply messaging channel settings** — in `<embeddedServiceMessagingChannel>` set `messagingChannel` (the channel's `channelPlatformKey`) and the UI toggles (`shouldShow*`, `shouldStartNewLineOnEnter`, invitation flags). Include every boolean, even when `false`; full list in `references/deployment_settings.md`. Leave each `shouldShow*` / `shouldStartNewLineOnEnter` at its retrieved value (default `false` if nothing was retrieved); set one to `true` only when the user explicitly asks for that feature — never infer it from an example.

12. **Apply pre-chat forms** — pre-chat is OFF by default: omit `<embeddedServiceForms>` unless the user asks to collect data before the conversation. If they do, **read `references/prechat_forms.md` first** and follow it (field attributes, hidden fields, ChoiceList, `displayNameFormat`, deactivate vs. remove).
    - **Before generating**, run the checks in its §Validating and Remediating Prerequisites against the *retrieved* channel. Channel fixes go through `service-digital-engagement-channel-configure`; never hand-edit the channel here.
    - Delta to graft onto a base deployment: `examples/esd_web_prechat_fields.xml`.

12a. **Apply custom labels** (Web v1/v2 and Mobile, not API; only if asked) — read `references/custom_labels.md`. Labels are Tooling records, not `EmbeddedServiceConfig` XML: check the deployment type (Mobile: two keys only), Translation Workbench and language prerequisites first, warn that Web v1/v2 show different label sets, write them in Phase 2C, and they go live only on publish (17c). Reply to the user with the result, the Setup review link and one next question; leave out tool, recipe and endpoint names. Delegated: still end with the contract §5 result.

13. **Apply branding customization** (Web only) — a BrandingSet is automatically created with defaults when the deployment is created via Connect API. If the user wants to override specific branding properties (colors, fonts, dimensions), read `references/branding_and_tooling.md` for the Tooling API steps to update individual properties.

14. **Apply invitation** (Web only) — set `isInvitationEnabled` to `true`, add `<embdMsgChannelInvitationConditions>` (fields and operators in `references/deployment_settings.md`), and keep `formula` (e.g. `1 AND 2`) in sync with the condition `sequence` numbers whenever conditions change.

15. **Apply additional settings**:
    - `isTermsAndConditionsEnabled` / `isTermsAndConditionsRequired` — T&C in pre-chat
    - `site` — Web: the retrieved value, unchanged (see Rules); omit for API/Mobile

16. **Generate the file** — produce the `.EmbeddedServiceConfig-meta.xml` file at the path the user specifies, or default to `EmbeddedServiceConfig/` in the project's metadata source path.

17. **Present output and next steps** — show the generated file and summarize what was configured. Recommend as next steps:
    - **Publish** (Web) — only after the user approves, per step 17c
    - **Generate code snippet** for integration — see `references/code_snippet.md`

### Phase 2C — Apply to the org

Runs for both Phase 2A and 2B, except when the pre-scan returned `already-configured`. Standalone: confirm before writing. Delegated: the plan approval is the confirmation; still announce each write.

17a. **Write the deployment** —
    - Web create: Connect API (see `references/connect_api_creation.md`). Transport A first: `dispatch` `POST` on the fully-qualified path. If it returns `INTERNAL_ERROR` (MCP sessions can fail while the ESW site is built), quote the error, re-run the step 3 pre-scan, and continue on B with `sf api request rest` only if no partial `EmbeddedServiceConfig` for the name exists; if one does, stop and ask.
    - API/Mobile create: Transport A `POST` `EmbeddedServiceConfig` (body carries `type`, `fullName`, `xmlRep`); Transport B `sf project deploy start`.
    - Update: Transport A `PUT` of the **full** document; Transport B `sf project deploy start`.
    Check `results[].success`, not just HTTP status. On failure stop and report the step — no silent retry.

17b. **Re-read and diff** — `GET` the component again and confirm every intended field landed and no inline block (`embeddedServiceMessagingChannel`, forms) was dropped.

17c. **Publish (Web only) — never automatic.** Publishing makes the changes live to customers; the deploy only saves a draft. After 17b, stop: summarize what changed, give the plain Setup link `<instanceUrl>/lightning/setup/EmbeddedServiceDeployments/<EmbeddedServiceConfigId>/view` so the user can review the draft, and ask whether to publish now. Publish only on an explicit yes in that turn (a "publish" in the original request does not count). Then `dispatch` `POST` on the fully-qualified publish path; if it returns a path/route error, or on Transport B, run the `sf` publish command from `references/connect_api_creation.md`. Delegated: do not publish; return `published: true` only if a Web create auto-published (`isPublishSuccess: true`), else `false`. Note: a Web create via Connect API publishes by itself (`isPublishSuccess: true`); say so in the plan before creating.

### Phase 3 — Validate

18. **Verify against checklist** — confirm all items in the Verification Checklist below pass.

19. **Report** — delegated: return the contract §5 result. Standalone: the same outcome in plain language.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| `deploymentType` must be `API`, `Mobile`, or `Web` | Platform rejects other values |
| Web updates must include `site`, set to the retrieved value unchanged | Site (`ESW_<name>_<timestamp>`) is auto-generated at creation; the platform rejects a missing or changed value |
| `embeddedServiceMessagingChannelName` must reference an existing channel | Deployment fails if channel doesn't exist |
| File extension is `.EmbeddedServiceConfig-meta.xml` | Metadata API uses this specific extension |
| Do not hardcode file paths — respect `sfdx-project.json` package directories | Customer orgs customize source paths |
| Do not embed deploy/push commands inside generated files or artifacts | Artifacts stay portable; in-session writes happen in Phase 2C through the chosen transport |
| Update with the full retrieved document, never a minimal PUT | Omitted inline blocks can be silently cleared by the update |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Branding overrides not applied | Use Tooling API to update individual BrandingSet properties after the deployment is created |
| Pre-chat form, field, ChoiceList, or `displayNameFormat` issues | See the Gotchas table in `references/prechat_forms.md` |
| Changes not appearing in widget | The deploy is a draft until published (step 17c) |
| `sf api request rest` fails ("No 'mode' found", "Nonexistent flag: --url") | See `references/connect_api_creation.md` §Publishing After Updates |
| Deploy fails with "required field missing" or "upsert failed null" | All attributes are mandatory: boolean fields in `embeddedServiceMessagingChannel` (include all even with default `false`), and all pre-chat form field attributes |

---

## Verification Checklist

### Universal Checks
- [ ] Is `deploymentType` one of `API`, `Mobile`, or `Web`?
- [ ] Is `masterLabel` populated and unique?
- [ ] Does `messagingChannel` reference an existing channel?
- [ ] Is `deploymentFeature` set to `EmbeddedMessaging`?
- [ ] Is `isEnabled` set to `true`?

### Web Type Checks
- [ ] Is `site` populated with the Experience Site name?
- [ ] If branding is configured, does `embeddedServiceBrandingName` reference an existing BrandingSet?
- [ ] Pre-chat (if configured): does every item in the `references/prechat_forms.md` Verification Checklist pass?
- [ ] If `isInvitationEnabled` is `true`, is `formula` populated and consistent with all `sequence` numbers in `<embdMsgChannelInvitationConditions>`?

### API/Mobile Type Checks
- [ ] Is `siteUrl` empty (no site needed)?
- [ ] Is `deploymentType` correctly set to `API` or `Mobile`?

### Post-Deploy Checks
- [ ] Web: did you stop before publishing, give the review link, and publish only after the user's explicit yes? Is the user reminded to activate any deployed messaging components (Tooling API)?

---

## Output Expectations

Deliverables:
- **API/Mobile create, and any update**: `<source-path>/EmbeddedServiceConfig/<DeploymentName>.EmbeddedServiceConfig-meta.xml`
- **Web create**: Connect API payload and instructions (no XML file)

File structure follows the templates in `assets/`.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Creating the messaging channel | `service-digital-engagement-channel-configure` skill |
| Channel custom parameters, flow-variable mappings, or Queue → Omni-Flow routing | `service-digital-engagement-channel-configure` skill (pass the retrieved channel; see step 12) |
| Creating Omni-Channel routing flows | `automation-flow-generate` skill |
| Creating permission sets for agents | `platform-permission-set-generate` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/onboarding_contract.md` | Pre-scan (§3, both modes); delegated mode (`delegationFrom` set), org writes (transport), module registration |
| `assets/esd_api_mobile_template.xml`, `assets/esd_web_update_template.xml` | Before generating API/Mobile deployments and Web updates, respectively |
| `references/deployment_settings.md` | When configuring deployment options beyond defaults; less common gotchas (embedded flow, reCAPTCHA, business hours) |
| `references/custom_labels.md` | Whenever custom labels are requested — prerequisites, key validation, create/update/remove, transport |
| `references/prechat_forms.md` | Whenever pre-chat is requested — inputs, field rules, ChoiceList, `displayNameFormat`, deactivate vs. remove, pre-chat gotchas and checklist |
| `references/connect_api_creation.md` | When creating Web type deployments (Connect API required); publish command and ID query |
| `references/branding_and_tooling.md` | When user asks about branding configuration |
| `references/code_snippet.md` | When user wants the JavaScript embed code snippet for their website |
| `scripts/check-api-version.sh` | Phase 1 — verify org API version meets the passed minimum (67.0) |
| `examples/esd_api.xml`, `esd_mobile.xml`, `esd_web_full.xml`, `esd_web_prechat_fields.xml` | To verify output per type; the pre-chat file is a forms delta to graft onto `esd_web_full.xml` |

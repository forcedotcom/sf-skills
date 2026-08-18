---
name: service-digital-engagement-deployment-configure
description: "Configures Embedded Messaging Deployments for Messaging for In-App and Web (MIAW). Use when the user needs to create a new embedded messaging deployment from scratch using Connect API with defaults, or update an existing deployment's settings using Metadata API. Produces Connect API request payloads for new deployments and EmbeddedServiceConfig metadata XML for updates. TRIGGER when the user mentions embedded messaging deployment, embedded service deployment, MIAW deployment, messaging widget setup, chat widget configuration, embedded chat deployment, or references a .EmbeddedServiceConfig-meta.xml file. DO NOT TRIGGER when the user is creating a messaging channel (use service-digital-engagement-channel-configure), configuring legacy Live Agent embedded service, or generating the JavaScript code snippet for website embedding."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "automation-flow-generate"
    - "platform-permission-set-generate"
    - "service-digital-engagement-channel-configure"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Configuring Embedded Messaging Deployment

Configures `EmbeddedServiceConfig` metadata for Salesforce Messaging for In-App and Web (MIAW). Supports two distinct workflows: creating new deployments via Connect API and updating existing deployments via Metadata API.

## Scope

- **In scope**: Creating new Embedded Service Deployments (API, Mobile, Web types) via Connect API; updating existing deployments with forms, branding, channel settings, and features via Metadata API; generating `EmbeddedServiceConfig` XML for updates
- **Out of scope**: Creating the messaging channel itself (use `service-digital-engagement-channel-configure`), publishing deployments (Connect API post-step), creating Experience Sites (Connect API prerequisite for Web type)

---

## Clarifying Questions

Before generating, ask the user if not already clear:

- **Create or update?** Are you creating a new deployment or updating an existing one?
- **Deployment type?** API (headless), Mobile (native apps), or Web (browser widget)?
- **Channel name?** What is the `channelPlatformKey` of the messaging channel to associate?
- For **create**: What should the deployment be named?
- For **update**: What features to configure? (pre-chat forms, business hours, T&C, UI toggles)
- For **update (Web)**: What is the Experience Site name? Branding overrides needed?

---

## Required Inputs

Gather or infer before proceeding:

- **Operation**: `create` or `update`
- **Deployment type**: `API`, `Mobile`, or `Web`
- **Deployment name**: Used for `masterLabel` and the API name
- **Channel name**: The `channelPlatformKey` of the associated messaging channel

For **update** operations additionally:
- **Site name** (Web only): The Experience Site name (format `ESW_<name>_<timestamp>`)
- **Branding name** (optional): Reference to existing `BrandingSet`
- **Pre-chat form fields** (optional): Field names and required status
- **Business hours** (optional): Name of existing `BusinessHours` record

Defaults unless specified:
- `isEnabled`: `true`
- `deploymentFeature`: `EmbeddedMessaging`

---

## Workflow

All steps are sequential. Do not skip or reorder. Branch based on the operation type.

### Phase 1 — Gather Context

1. **Verify org API version** — run `scripts/check-api-version.sh 67.0 <org-alias>` and report any errors it returns. If the script fails, generate a `sfdx-project.json` in the metadata output folder with `"sourceApiVersion": "67.0"`.

2. **Determine operation** — ask whether the user wants to create a new deployment or update an existing one.

3. **Collect inputs** — gather deployment name, type, and channel name per Clarifying Questions above.

4. **Read deployment settings reference** — load `references/deployment_settings.md` to understand all available configuration options.

### Phase 2A — Create New Deployment

Use this path when the operation is `create`.

5. **Determine API method by type**:

   | Deployment Type | Creation Method | Prerequisites |
   |----------------|-----------------|---------------|
   | API | Metadata API deploy | Channel must exist |
   | Mobile | Metadata API deploy | Channel must exist |
   | Web | Connect API | Channel must exist + Experience Site required |

6. **For API/Mobile types** — read the template `assets/esd_api_mobile_template.xml` and generate the `EmbeddedServiceConfig` XML with:
   - `deploymentType` set to `API` or `Mobile`
   - `deploymentFeature` set to `EmbeddedMessaging`
   - All defaults applied

7. **For Web type** — inform the user that Web deployments require Connect API for initial creation because of a circular dependency between Network and CustomSite. Read `references/connect_api_creation.md` for the Connect API payload and instructions.

8. **Generate output** — produce the `.EmbeddedServiceConfig-meta.xml` file (for API/Mobile) or Connect API instructions (for Web).

9. **Present output and next steps** — show the generated file and summarize what was configured. Recommend as next steps:
   - **Publish** the deployment via Connect API to make it live:
     ```bash
     sf api request rest "/services/data/v67.0/connect/embeddedservice/embeddedserviceconfig/publish/<EMBEDDED_SERVICE_CONFIG_ID>" -X POST -o <org-alias>
     ```
     To obtain the `EMBEDDED_SERVICE_CONFIG_ID`:
     ```bash
     sf data query --query "SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName = '<DEPLOYMENT_NAME>'" --target-org <org-alias>
     ```
   - **Generate code snippet** for integration — see `references/code_snippet.md`

### Phase 2B — Update Existing Deployment (Metadata API)

Use this path when the operation is `update`.

10. **Retrieve the existing deployment** — retrieve the current `EmbeddedServiceConfig` metadata from the org before making changes:
    ```bash
    sf project retrieve start --metadata EmbeddedServiceConfig:<DEPLOYMENT_NAME> --target-org <org-alias>
    ```
    Use the retrieved file as the starting structure. If retrieval is not possible, load `assets/esd_web_update_template.xml` as a fallback reference.

11. **Apply messaging channel settings** — configure `<embeddedServiceMessagingChannel>` with:
    - `messagingChannel` — the channel's `channelPlatformKey`
    - `shouldShowAgentforceTagline` — Agentforce branding
    - `shouldShowDeliveryReceipts` — delivery receipts
    - `shouldShowEmojiSelection` — emoji picker
    - `shouldShowReadReceipts` — read receipts
    - `shouldShowTypingIndicators` — typing indicators
    - `shouldStartNewLineOnEnter` — Enter key behavior
    - `isChatInvitationCustomizable` / `isInvitationEnabled` — chat invitation settings

12. **Apply pre-chat forms** — if the user needs pre-chat data collection, generate `<embeddedServiceForms>` with `<embeddedServiceFormFields>` elements containing `embeddedServiceFormFieldName` and `isRequired`.

13. **Apply branding customization** (Web only) — a BrandingSet is automatically created with defaults when the deployment is created via Connect API. If the user wants to override specific branding properties (colors, fonts, dimensions), read `references/branding_and_tooling.md` for the Tooling API steps to update individual properties.

14. **Apply invitation** (Web only) — if the user wants the widget to proactively invite visitors based on conditions:
    - Set `isInvitationEnabled` to `true` in `<embeddedServiceMessagingChannel>`
    - Generate repeatable `<embdMsgChannelInvitationConditions>` elements with `sequence`, `conditionType`, `operand`, `value`, and optionally `customVariableName`
    - Update the `formula` field in `<embeddedServiceMessagingChannel>` to reference the condition sequences (e.g., `1 AND 2`, `1 OR 2`). The formula must be updated whenever conditions are added or removed to stay in sync with the `sequence` numbers
    - See `references/deployment_settings.md` for available condition types and operators

15. **Apply additional settings**:
    - `isTermsAndConditionsEnabled` / `isTermsAndConditionsRequired` — T&C in pre-chat
    - **Do NOT update `site`** — the site name is auto-generated during creation and must never be modified

16. **Generate the file** — produce the `.EmbeddedServiceConfig-meta.xml` file at the path the user specifies, or default to `EmbeddedServiceConfig/` in the project's metadata source path.

17. **Present output and next steps** — show the generated file and summarize what was configured. Recommend as next steps:
    - **Publish** the deployment via Connect API to make changes live:
      ```bash
      sf api request rest "/services/data/v67.0/connect/embeddedservice/embeddedserviceconfig/publish/<EMBEDDED_SERVICE_CONFIG_ID>" -X POST -o <org-alias>
      ```
      To obtain the `EMBEDDED_SERVICE_CONFIG_ID`:
      ```bash
      sf data query --query "SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName = '<DEPLOYMENT_NAME>'" --target-org <org-alias>
      ```
    - **Generate code snippet** for integration — see `references/code_snippet.md`

### Phase 3 — Validate

18. **Verify against checklist** — confirm all items in the Verification Checklist below pass.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always retrieve existing deployment before updating | Ensures current settings are preserved and only intended changes are applied |
| `deploymentType` must be `API`, `Mobile`, or `Web` | Platform rejects other values |
| Never update the `site` field on a Web deployment | Site name is auto-generated at creation and must not be changed |
| Web deployments cannot be created via Metadata API | Circular dependency between Network and CustomSite — use Connect API |
| `embeddedServiceMessagingChannelName` must reference an existing channel | Deployment fails if channel doesn't exist |
| `site` field required for Web type updates | Web widget must be associated with an Experience Site |
| BrandingSet is auto-created with defaults by Connect API | To override branding properties, use Tooling API — see `references/branding_and_tooling.md` |
| Pre-chat form fields must reference valid channel custom parameters | ChoiceList fields need the parameter deployed on the channel first |
| File extension is `.EmbeddedServiceConfig-meta.xml` | Metadata API uses this specific extension |
| Do not hardcode file paths — respect `sfdx-project.json` package directories | Customer orgs customize source paths |
| Never include deploy/push commands in generated output | This skill produces artifacts only |
| Publish step (Connect API) required after Web ESD updates | Changes are not live until published |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Web ESD creation fails via Metadata API | Web type requires Connect API for initial creation; use Metadata API only for updates |
| Site name not found | Site must exist before Web ESD update; format is `ESW_<name>_<timestamp>` |
| Branding overrides not applied | Use Tooling API to update individual BrandingSet properties after the deployment is created |
| Pre-chat ChoiceList not showing | ChoiceList requires two-step deploy: create ChoiceList first, then assign to form field |
| Changes not appearing in widget | Web ESDs must be published via Connect API after any update |
| `embeddedServiceFlowConfig.enabled` error | Set to `false` unless you specifically need embedded flows (not routing flows) |
| reCAPTCHA configuration rejected | reCAPTCHA is `@HideInWsdl` — must use Tooling API |
| Business hours not taking effect | Only updating existing business hours works; creation is managed separately |
| Deploy fails with "required field missing" or "upsert failed null" | All attributes are mandatory: boolean fields in `embeddedServiceMessagingChannel` (include all even with default `false`), and all form field attributes (`formField`, `formFieldType`, `isHidden`, `isRequired`, `displayOrder`, `messagingChannelParameterType`) |
| Standard pre-chat field not found | Use `_` prefix for standard fields in `formField`: `_FirstName`, `_LastName`, `_Email`, `_Subject` |

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
- [ ] Are pre-chat form field names valid (match channel custom parameters)?
- [ ] If `isInvitationEnabled` is `true`, is `formula` populated and consistent with all `sequence` numbers in `<embdMsgChannelInvitationConditions>`?

### API/Mobile Type Checks
- [ ] Is `siteUrl` empty (no site needed)?
- [ ] Is `deploymentType` correctly set to `API` or `Mobile`?

### Post-Deploy Checks
- [ ] Is user reminded to publish (Connect API) for Web deployments?
- [ ] Is user reminded to activate components (Tooling API) if messaging components were deployed?

---

## Output Expectations

Deliverables:
- **For API/Mobile create**: `<source-path>/EmbeddedServiceConfig/<DeploymentName>.EmbeddedServiceConfig-meta.xml`
- **For Web create**: Connect API payload and instructions (no XML file)
- **For update**: `<source-path>/EmbeddedServiceConfig/<DeploymentName>.EmbeddedServiceConfig-meta.xml`

File structure follows the templates in `assets/`.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Creating the messaging channel | `service-digital-engagement-channel-configure` skill |
| Creating Omni-Channel routing flows | `automation-flow-generate` skill |
| Creating permission sets for agents | `platform-permission-set-generate` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/esd_api_mobile_template.xml` | Before generating API or Mobile type deployments |
| `assets/esd_web_update_template.xml` | Before generating Web type updates |
| `references/deployment_settings.md` | When configuring deployment options beyond defaults |
| `references/connect_api_creation.md` | When creating Web type deployments (Connect API required) |
| `references/branding_and_tooling.md` | When user asks about branding configuration |
| `references/code_snippet.md` | When user wants the JavaScript embed code snippet for their website |
| `scripts/check-api-version.sh` | Phase 1 — verify org API version meets the passed minimum (67.0) |
| `examples/esd_api.xml` | To verify output for API type deployment |
| `examples/esd_mobile.xml` | To verify output for Mobile type deployment |
| `examples/esd_web_full.xml` | To verify output for fully configured Web deployment |

# BotEmailDefinition — field, validation, and deploy reference

`BotEmailDefinition` is the Metadata API type (available **API v68.0+**) that connects an Agentforce Service Agent to Service Email, so the agent can respond to Email-to-Case messages. It backs the "Agentforce for Service on Email" Setup feature (`/lightning/setup/AsaForEmail/home`). Branch C deploys it headlessly instead of asking the user to fill in that Setup form.

It is a top-level component (`keyPrefix 1NY`, `isTopLevel=true`), but it is **not registered in the Salesforce CLI's source-deploy-retrieve (SDR) registry** — a source deploy that names the type directly (`sf project deploy start --metadata BotEmailDefinition:<name>`) fails with `Missing metadata type definition in registry for id 'BotEmailDefinition'`. Deploy it in **metadata format** with `--metadata-dir` instead (see "Deploying" below). It is not the `CaseSettings` singleton, so it does not use the two-phase `updateMetadata` CRUD call.

## Fields (WSDL complexType, extends `Metadata`)

All six are **required on create** — the WSDL marks none of them `minOccurs="0"` — and none are platform-generated/read-only.

| Field | Type | Notes |
|-------|------|-------|
| `botDefinition` | string | **Required.** Developer/API name of the `AgentforceServiceAgent` (Bot) to link. Resolved to the Bot's ID at deploy. The agent must be **active**, of type `EinsteinServiceAgent`, have a bot user, and that bot user must hold `agentforceServiceAgentUser`. |
| `emailTemplate` | string | **Required.** Reference to the reply email template. **Must be folder-qualified** — e.g. `unfiled$public/AgentforceForServiceEmailTemplate`, not a bare `AgentforceForServiceEmailTemplate` (a bare name fails with `no EmailTemplate named X found`). Must satisfy the ASA rules below. |
| `label` | string | **Required.** Display label for the email definition. |
| `legalDisclaimer` | string | **Required.** Legal disclosure / footer text appended to replies. **Minimum 10 characters** (`MinLengthNotMet`). |
| `replyAll` | boolean | **Required.** `true` = reply-all; `false` = reply to sender only. |
| `signature` | string | **Required.** Email signature block. **Minimum 10 characters** (`MinLengthNotMet`). |

`fullName` is **not** a child element — for a top-level component it is the file name (`<DeveloperName>.botEmailDefinition-meta.xml`). The routing address references this `fullName`.

## Save-time validation order (verified against Core, release 266)

The org validates the fields in this exact order — note the surface/active-version check (step 5) fires **last**, after the two text-length checks and all the agent/template checks. Following the same order in preflight surfaces the most likely blocker first.

1. **`legalDisclaimer` length** — must be ≥10 chars, else `MinLengthNotMet`.
2. **`signature` length** — must be ≥10 chars, else `MinLengthNotMet`.
3. **`botDefinition`** — in order:
   - empty → `RequiredFieldMissing`;
   - not found → `BotDefinitionInvalid`;
   - agent type ≠ `EinsteinServiceAgent` → `BotDefinitionAgentTypeIncorrect`;
   - bot user null/invalid → `BotUserNull` / `BotUserInvalid`;
   - bot user missing the `agentforceServiceAgentUser` permission → `BotUserHasNoAgentforceServiceAgentUserPerm`.
4. **`emailTemplate`** — in order:
   - `uiType` ≠ SFX → `EmailTemplateUiTypeIncorrect`;
   - blank HTML body → `EmailTemplateDoesntContainHtmlValue`;
   - missing `[[[GENERATED_CONTENT]]]` → `EmailTemplateMissingGeneratedContent`;
   - missing `[[[LEGAL_DISCLOSURE]]]` → `EmailTemplateMissingLegalDisclosure`;
   - private/user folder (id prefix `005`, or folder `AccessType` ≠ `PUBLIC`) → `EmailTemplateIsPrivate`.
5. **Surface / active-version check** — fires **last**:
   - the agent has no **active version** → `AgentMustBeActive`;
   - the active version does not have the **`ServiceEmail` surface** enabled → `SurfaceMissingForSave` (label section `AsaForEmail`).
   The check uses the **active-version** id, not the bot id.

## Prerequisite: the `ServiceEmail` surface (`connection service_email:`)

The save checks that the agent's **active version** has the `ServiceEmail` surface enabled. That surface is enabled by a `connection service_email:` block in the agent's `.agent` (AiAuthoringBundle) file, which compiles to `<plannerSurfaces><surfaceType>ServiceEmail</surfaceType><surface>SurfaceAction__ServiceEmail</surface></plannerSurfaces>`. Branch C **Step 3** adds this block and republishes before the deploy, so the active version already carries the surface — enabling it after publish would require deactivate → deploy → reactivate.

Detect an existing surface on the published agent:
```bash
sf project retrieve start --metadata "AiAuthoringBundle:{AGENT_DEVELOPER_NAME}" --target-org $ORG
# then grep the retrieved .agent file for:  connection service_email:
```

## Case assignment — why the binding alone is not enough

The routing address's `botEmailDefinition` child only selects *which agent/template generates the reply*; it does **not** route the case to the agent. Branch C does that with one of two mechanisms (Step 2), written onto the routing address in Step 4d:

- **Direct case-owner assignment (default):** set `caseOwner` = the bot user's Username with `caseOwnerType: User`. The agent replies only when `Case.Owner` equals its bot user **at the moment the inbound email is processed**, and that owner must be assigned **synchronously during the case save** — a delayed/async assignment (e.g. a late-running assignment rule) prevents the reply until the customer emails again. Setting `caseOwner` satisfies this: it is copied onto every new case at save time, no extra infrastructure.
- **Omni-Channel flow (advanced):** set `routingFlow` (an inbound Copilot RoutingFlow) + `fallbackQueue`; the flow routes each case to the agent via Omni-Channel.

Set one path's fields, not both. An empty `caseOwner` with no `routingFlow` → the case falls to the org default owner and the agent stays silent.

## The email template (ASA-valid `EmailTemplate`)

A template is ASA-valid only if **all** of these hold (each maps to an error in step 4 above):

1. **`uiType = SFX`** — a Lightning email template; classic (`Aloha`) is rejected. `uiType` is **set-once** (create SFX; cannot flip later).
2. **HTML body present** — the `.email` body must be non-blank.
3. **Both literal ASA tokens** — the HTML body must contain, verbatim, `[[[GENERATED_CONTENT]]]` and `[[[LEGAL_DISCLOSURE]]]`. These are raw substrings, **not** `{!...}` merge fields.
4. **Public** — the org-wide public bucket (`unfiled$public`) or a folder whose `AccessType` is `Public`. A private/user folder is rejected.
5. **Exists** — the FK is `Restrict`, so the template must pre-exist the deploy.

Branch C validates the fallback template with `python3 scripts/validate-emailtemplate.py <path-to-.email-meta.xml>` before deploying. Deploying the fallback requires the deploying user to have Lightning (SFX) email-template permission, write access to public templates (`editPublicTemplates`), and org HTML email enabled.

## Deploying (metadata format)

Because `BotEmailDefinition` is not in the CLI's SDR registry, deploy it in **metadata format**. Build a metadata-format package directory from `assets/mdapi-package.xml` and the component file (renamed to drop `-meta.xml`):

```text
<mdapi-dir>/
├── package.xml                                       # from assets/mdapi-package.xml
└── botEmailDefinitions/
    └── <DeveloperName>.botEmailDefinition            # same XML as the source file, NO -meta.xml suffix
```

Set `package.xml` `<version>` to the org's resolved API version. Then:

```bash
sf project deploy start --metadata-dir <mdapi-dir> --target-org $ORG --json
```

Confirm `success: true` with the component listed. `BotEmailDefinition` is **not SOQL-queryable** and may not read/retrieve back cleanly, so treat a successful deploy result as authoritative — do not treat a failed read-back as a failed deploy.

## Org gate (composite)

Everything here is gated by a **composite** capability, not a single permission:

```text
orgHasAgentforceServiceAgentEmail =
      OrgPermissions.AgentforceServiceAgent
   && OrgPermissions.HasEmailToCase
   && (OrgPermissions.UniversalCreditMetering || OrgPermissions.ASAEmailEarlyAccess)
   && EinsteinBot.orgHasChatbotFoundationEnabled
```

Create/edit/delete of the component additionally requires `UserPermissions.CustomizeApplication`. If the composite gate is not satisfied, the type is unavailable and the deploy fails — stop and surface the error.

# Branch C — Email-to-Case inbound routing

Inbound routing gets each new case to the agent's bot user by one of two mechanisms (Step 2) — direct case-owner assignment (default) or an Omni-Channel flow. Also includes the mandatory `connection service_email:` surface block and a mandatory BotEmailDefinition step (Email Configuration).

## Precondition — org must be on API v68.0+

`BotEmailDefinition` (the Email Configuration that links the agent to Service Email — Step 4) is exposed to the Metadata API only at **API v68.0+**. Gate the entire branch on this **before configuring anything** — do not enable Email-to-Case, create routing addresses, deploy the inbound flow, or modify the agent on an org that can't complete the wiring.

Resolve the org's **true max** supported API version and stop if it is below 68.0. Query `/services/data` (the live version list) rather than `sf org display`'s `apiVersion` — that value is a cached `instanceApiVersion` that can lag the org's real max, so an upgraded-but-not-re-authed v68 org could wrongly fail this gate:

```bash
ORG_API_VERSION=$(sf api request rest --target-org "$ORG" "/services/data" \
  | python3 -c "import sys, json; print(max((v['version'] for v in json.load(sys.stdin)), key=float))")

python3 -c "import sys; sys.exit(0 if float('$ORG_API_VERSION') >= 68.0 else 1)" || {
  echo "Org API version $ORG_API_VERSION is below 68.0 — Agentforce Email-to-Case (BotEmailDefinition) is not available on this org. Stopping without making changes."
  exit 1
}
```

If the check fails, **stop and tell the user** their org's API version does not support Agentforce Email-to-Case, and configure nothing. **There is no manual Setup fallback for this branch** — if the org can't complete the wiring headlessly, stop. If it passes, carry `ORG_API_VERSION` forward for the Step 4 deploy manifest.

## Step 0 — Enable Email-to-Case

Ensure the two required CaseSettings flags are on. Read the current state:

```bash
sf api request rest -o "$ORG" --method GET \
  "/services/data/v67.0/tooling/query?q=SELECT+Metadata+FROM+CaseSettings+LIMIT+1"
```

Check `metadata.emailToCase.enableEmailToCase` and `metadata.emailToCase.enableOnDemandEmailToCase`. If either is `false`, deploy a settings file that sets both to `true` (use the same safe-fields-only Metadata API deploy pattern used when patching routing addresses — include only the `emailToCase` block with known-safe fields). Verify they are `true` before continuing.

---

## Step 1 — Existing routing address or new one?

Query existing Email-to-Case routing addresses on the org:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT Id, PersonalName, Address FROM EmailRoutingAddress ORDER BY PersonalName"
```

Ask the user via `AskUserQuestion`:
- **One or more found** → present each as `{PersonalName} <{Address}>`, plus *"Create a new email routing address"*
- **Zero found** → skip the question; proceed directly to create a new routing address

### If creating a new routing address

1. Ask for the support email address:

   > *"What email address should receive support emails? This is the address customers will email — e.g. `support@yourcompany.com`.*
   > *Note: Salesforce will send a verification email to this address. You must click the verification link before inbound emails will be processed."*

2. Create the `EmailRoutingAddress` record:
   ```bash
   sf data create record --target-org $ORG \
     --sobject EmailRoutingAddress \
     --values "PersonalName='{SUPPORT_EMAIL}' Address='{SUPPORT_EMAIL}'" \
     --json
   ```
   Capture the new record `Id` as `ROUTING_ADDRESS_ID`.

3. Set `CaseOrigin`, `SaveEmailHeaders`, and `AddressType` via CaseSettings read-modify-write:

   a. Read current CaseSettings from the Tooling API:
   ```bash
   sf api request rest -o "$ORG" --method GET \
     "/services/data/v{ORG_API_VERSION}/tooling/query?q=SELECT+Metadata+FROM+CaseSettings+LIMIT+1"
   ```

   b. In the returned `Metadata.emailToCase.routingAddresses` array (not a top-level `caseEmailRoutingAddresses`), find the entry whose `emailAddress` matches `{SUPPORT_EMAIL}`. Patch that entry:
   - `caseOrigin`: query `Case.Origin` picklist values and select `Email` if present, otherwise the closest match
   - `saveEmailHeaders`: `true`
   - `addressType`: `EmailToCase`

   c. Deploy the patched Metadata back:
   ```bash
   sf api request rest -o "$ORG" --method PATCH \
     "/services/data/v{ORG_API_VERSION}/tooling/sobjects/CaseSettings/{CASE_SETTINGS_ID}" \
     --body '{"Metadata": {<patched metadata object>}}'
   ```
   If the Tooling API PATCH fails, fall back to a **metadata-format** `Settings:Case` deploy — the same `--metadata-dir` pattern as Step 4d point 3 (assemble a package from `assets/settings-mdapi-package.xml` pinned to `ORG_API_VERSION`, drop the `Case.settings` file under `settings/`, and deploy with `sf project deploy start --metadata-dir`). Do **not** fall back to a source deploy (`sf project deploy start --metadata Settings:Case`): it reads `sourceApiVersion` from the project's `sfdx-project.json` (which the api-version flag does not override), so v68-only fields fail on a project pinned lower, and pinning it there mutates the user's project permanently. As in Step 4d, a settings deploy replaces the whole `routingAddresses` collection, so the deployed file must carry every existing address.

4. Inform the user about email verification — then continue without waiting:

   > *"A verification email has been sent to `{SUPPORT_EMAIL}`. Click the link in that email when you get it — inbound mail won't be processed until the address is verified, but you can complete the rest of the setup now.*
   >
   > *If you don't receive the verification email, your domain may have email verification policies that block it:*
   > *[Email Verification Requirements for Salesforce Orgs](https://help.salesforce.com/s/articleView?id=xcloud.security_email_verification_requirements.htm&type=5)*"*

   Continue to the next step immediately — do not wait for the user to confirm.

### If using an existing routing address

Set `ROUTING_ADDRESS_ID` to the selected record's `Id` and continue. No provisioning steps needed.

---

## Step 2 — Inbound routing to the agent

Each new case must reach the agent's bot user. There are two mechanisms — ask the user which to use (`AskUserQuestion`):

- **Direct case-owner assignment (default)** — set the agent's bot user as the routing address's `caseOwner`. It is copied straight onto every new case during save. No extra org configuration.
- **Omni-Channel flow (advanced)** — an inbound routing flow routes each case to the agent via Omni-Channel, with a fallback queue when the agent is unavailable.

Either way, resolve the agent's **bot user** first — the record Setup surfaces as the "Agent User" / context user (Agent Details tab), which also equals the `.agent` file's `default_agent_user`. It is `BotDefinition.BotUserId` resolved to its `Username`:
```bash
sf data query --target-org $ORG --json \
  --query "SELECT BotUserId FROM BotDefinition WHERE DeveloperName='{AGENT_DEVELOPER_NAME}'"
sf data query --target-org $ORG --json \
  --query "SELECT Username FROM User WHERE Id='{BOT_USER_ID}'"
```
Capture `BOT_USER_USERNAME`.

### Path A — Direct case-owner assignment (default)

The bot user must own the case **at the moment the inbound email is processed**, and the owner must be assigned **synchronously during the case save** — a delayed/async assignment (e.g. a late-running assignment rule) prevents the automated reply until the customer emails again. Setting `caseOwner` = `BOT_USER_USERNAME` (`caseOwnerType: User`) satisfies this. Write it in the Step 4d settings deploy — do not deploy twice.

### Path B — Omni-Channel flow (advanced)

1. Resolve the org's **Case-based `ServiceChannel`** (`RelatedEntity='Case'`); provision one if absent — see `references/channel-types.md`. Capture `SERVICE_CHANNEL_DEV_NAME` / `SERVICE_CHANNEL_LABEL`.
2. Create the inbound `Copilot` RoutingFlow that routes to the agent with the Phase 1 queue as fallback, using the template in `references/routing-flow.md` **Part 1**. Deploy and verify `ActiveVersionId` is non-null. Capture `INBOUND_FLOW_DEVELOPER_NAME`.
3. In the Step 4d settings deploy, set `routingFlow` = `INBOUND_FLOW_DEVELOPER_NAME` and `fallbackQueue` = `QUEUE_DEVELOPER_NAME` on the routing address — **instead of** `caseOwner` (set one path's fields, not both).

---

## Step 3 — Mandatory ServiceEmail surface: `connection service_email:`

Email-to-Case requires the agent to carry the **ServiceEmail surface** before the BotEmailDefinition (Step 4) can be created. The `connection service_email:` block is what enables that surface; its **presence** is what's mandatory (not any escalation wiring). Do not offer this as optional or skip it.

This is a surface-only add with no outbound flow, so it is self-contained here — it does **not** go through the escalation path in `agent-wiring.md`.

1. Retrieve the agent's authoring bundle:
   ```bash
   sf project retrieve start --metadata "AiAuthoringBundle:{AGENT_DEVELOPER_NAME}" --target-org $ORG
   ```

2. Add the block to the `.agent` YAML with a single `description` field (an empty block fails validation):
   ```yaml
   connection service_email:
       description: "Replies to inbound Email-to-Case messages."
   ```

3. Republish and activate. The agent is already active at this point (Phase 1), and **publishing a surface/connection change onto an active agent fails** with `We couldn't find the default agent user <username>` — the active version holds the agent user, so it must be released first. Deactivate → publish → activate:
   ```bash
   echo "Y" | sf agent deactivate     --api-name {AGENT_DEVELOPER_NAME} --json
   sf agent validate authoring-bundle --api-name {AGENT_DEVELOPER_NAME} --json
   sf agent publish  authoring-bundle --api-name {AGENT_DEVELOPER_NAME} --json
   echo "Y" | sf agent activate       --api-name {AGENT_DEVELOPER_NAME} --json
   ```

   **Batch escalation here to avoid a second publish cycle.** Each surface/connection change on an active agent costs a full deactivate → publish → activate. If the user will also want outbound escalation (Phase 3), wire it in *this* edit instead of republishing again later: resolve the escalation queue and create the outbound `QueueBased` RoutingFlow first (`references/queue-resolution.md`, `references/routing-flow.md`), then add the outbound-route fields to this same `connection service_email:` block (per `references/agent-wiring.md`) before the single publish/activate above — the surface `description` and the outbound route then go live together.

Verify the block is present in the deployed bundle before continuing. Escalation is separate from this surface step — if the user wants it, add it via Phase 3 (`agent-wiring.md`), exactly like the other channels. It is not required to save the BotEmailDefinition.

---

## Step 4 — BotEmailDefinition (Email Configuration)

The `BotEmailDefinition` component links the agent to Service Email (the "Agentforce for Service on Email" feature). Read `references/botemaildefinition.md` in full before this step. Run this only after Step 3 confirmed `connection service_email:` is deployed on the agent.

### Step 4a — Preflight the save-time gates (fail fast, in Core's order)

`BotEmailDefinition`'s save-time validation runs in a fixed order (see `references/botemaildefinition.md`). Check the agent-side gates now so a deploy failure isn't the first signal:

1. **Bot user + perm.** The agent must have a bot user that holds `agentforceServiceAgentUser`:
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT Id, BotUserId FROM BotDefinition WHERE DeveloperName='{AGENT_DEVELOPER_NAME}'"
   ```
   Confirm `BotUserId` is non-null. Then confirm the bot user has the perm:
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId='{BOT_USER_ID}' AND PermissionSet.PermissionsAgentforceServiceAgentUser = true LIMIT 1"
   ```
   Querying `PermissionSetAssignment` (not standalone `PermissionSet`) covers all three grant paths at once — the profile's own permission set, a directly assigned permission set, and a permission-set-group member. If it returns no row, stop with a clear message — the deploy would fail `BotUserHasNoAgentforceServiceAgentUserPerm`.

2. **Active version + ServiceEmail surface.** Phase 1 already confirmed an active version. Confirm the active version carries the surface (added in Step 3):
   ```bash
   sf project retrieve start --metadata "AiAuthoringBundle:{AGENT_DEVELOPER_NAME}" --target-org $ORG
   ```
   Grep the retrieved `.agent` file for `connection service_email:`. If absent, return to Step 3 — the deploy would fail `AsaForEmail/SurfaceMissingForSave`.

3. **No customer-verification topic (safety net).** In the same retrieved `.agent` file, check for a `ServiceCustomerVerification` subagent / topic (or a router branch gated on `isVerified`). If present, **stop and warn** — an email agent carrying customer verification dead-ends inbound email at the verification step (a fresh sender is never `isVerified`, and verification can't complete over async email). Do not auto-remove it here — this skill only wires an already-authored agent, and the topic may be legitimate for a multi-surface agent that also serves chat.

### Step 4b — Provide the reply email template

The agent needs an ASA-valid `EmailTemplate` (`uiType=SFX`, HTML, public, containing both `[[[GENERATED_CONTENT]]]` and `[[[LEGAL_DISCLOSURE]]]`). Ask the user whether they have one:

- **User names an existing template** → confirm it is SFX, HTML-bodied, in a public folder, and contains both tokens. Use its **folder-qualified** name (e.g. `unfiled$public/<Name>`) as `EMAIL_TEMPLATE`.
- **User has none** → deploy the fallback from `assets/email/unfiled$public/AgentforceForServiceEmailTemplate.email` + `.email-meta.xml`. Validate first, then deploy:
  ```bash
  python3 scripts/validate-emailtemplate.py "assets/email/unfiled\$public/AgentforceForServiceEmailTemplate.email-meta.xml"
  # The asset is already source-format (email/<folder>/<name>) — deploy it by path, not by --metadata
  # (a named-type deploy resolves only components in the project's package directories, not this skill's assets/).
  sf project deploy start --source-dir "assets/email" --target-org $ORG --json
  ```
  Use `unfiled$public/AgentforceForServiceEmailTemplate` as `EMAIL_TEMPLATE`.

### Step 4c — Build, validate, and deploy the BotEmailDefinition

Elicit `label`, `legalDisclaimer` (≥10 chars), `signature` (≥10 chars), and `replyAll` (reply-all vs reply-to-sender) from the user. Choose a `DeveloperName`, e.g. `{AgentDevName}_Email_Config`.

1. Copy `assets/BotEmailDefinition.botEmailDefinition-meta.xml` to `/tmp/sfskills/{DeveloperName}.botEmailDefinition-meta.xml` and substitute `{AGENT_DEVELOPER_NAME}`, `{EMAIL_TEMPLATE_FOLDER}/{EMAIL_TEMPLATE_DEVELOPER_NAME}` (= `EMAIL_TEMPLATE`), `{LABEL}`, `{LEGAL_DISCLAIMER_TEXT}`, `{SIGNATURE_TEXT}`, and `replyAll`.

2. Validate:
   ```bash
   python3 scripts/validate-botemaildefinition.py /tmp/sfskills/{DeveloperName}.botEmailDefinition-meta.xml
   ```
   Resolve any errors before deploying.

3. Assemble the metadata-format package and deploy (source deploy naming the type directly fails — it is absent from the SDR registry):
   ```bash
   MDDIR=/tmp/sfskills/botemaildef-mdapi
   mkdir -p "$MDDIR/botEmailDefinitions"
   # package.xml: from assets/mdapi-package.xml, substituting the member name and
   # {API_VERSION} = ORG_API_VERSION from the Precondition.
   sed -e "s/{BOT_EMAIL_DEFINITION_DEVELOPER_NAME}/{DeveloperName}/" \
       -e "s/{API_VERSION}/{ORG_API_VERSION}/" \
       assets/mdapi-package.xml > "$MDDIR/package.xml"
   # component file: same XML as the source file, WITHOUT the -meta.xml suffix
   cp /tmp/sfskills/{DeveloperName}.botEmailDefinition-meta.xml \
      "$MDDIR/botEmailDefinitions/{DeveloperName}.botEmailDefinition"
   sf project deploy start --metadata-dir "$MDDIR" --target-org $ORG --json
   ```
   Confirm `status: Succeeded` / `success: true` with the component listed. `BotEmailDefinition` is not SOQL-queryable, so treat a successful deploy as authoritative — do not treat a failed read-back as failure. Capture the `fullName` as `BOT_EMAIL_DEFINITION_NAME`.

   **If the deploy fails**, stop and surface the error to the user — the agent cannot be wired to email on this org.

### Step 4d — Bind the routing address (BotEmailDefinition + inbound routing)

In one `Settings:Case` metadata deploy, set on the routing address (`{SUPPORT_EMAIL}` from Step 1): the `botEmailDefinition` binding to `BOT_EMAIL_DEFINITION_NAME`, **plus** the Step 2 inbound-routing fields — either `caseOwner` = `BOT_USER_USERNAME` + `caseOwnerType: User` (Path A), or `routingFlow` = `INBOUND_FLOW_DEVELOPER_NAME` + `fallbackQueue` = `QUEUE_DEVELOPER_NAME` (Path B). `casePriority` is **required** on every routing address — carry it, or the deploy fails with `Missing casePriority`. A settings deploy **replaces** the `emailToCase.routingAddresses` collection, so the deployed file must carry **every** existing address — dropping one unbinds it. There is no pre-existing `Case.settings-meta.xml` in the project; you must generate it from the current org state first.

1. **Read the current CaseSettings** to get the full `emailToCase` block, including all routing addresses:
   ```bash
   sf api request rest -o "$ORG" --method GET \
     "/services/data/v{ORG_API_VERSION}/tooling/query?q=SELECT+Metadata+FROM+CaseSettings+LIMIT+1"
   ```

2. **Write `Case.settings-meta.xml`** to the project's settings directory (e.g. `force-app/main/default/settings/Case.settings-meta.xml`). Include the `emailToCase` toggles and **one `<routingAddresses>` entry per existing address** from the read. For each address, carry over **every** field the read returned except the read-only `emailServicesAddress`/`isVerified` — preserve whatever the org actually set (e.g. `addressType`, `caseOrigin`, `emailAddress`, `routingName`, and fields like `casePriority`), rather than a fixed subset. On the entry whose `emailAddress` matches `{SUPPORT_EMAIL}`, add `<botEmailDefinition>{BOT_EMAIL_DEFINITION_NAME}</botEmailDefinition>` plus the Step 2 path's fields. The example below shows **Path A** (case owner); for **Path B**, swap in `<routingFlow>`+`<fallbackQueue>` instead:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <CaseSettings xmlns="http://soap.sforce.com/2006/04/metadata">
       <emailToCase>
           <enableEmailToCase>true</enableEmailToCase>
           <enableOnDemandEmailToCase>true</enableOnDemandEmailToCase>
           <routingAddresses>
               <addressType>EmailToCase</addressType>
               <botEmailDefinition>{BOT_EMAIL_DEFINITION_NAME}</botEmailDefinition>
               <caseOrigin>Email</caseOrigin>
               <casePriority>Medium</casePriority>
               <caseOwner>{BOT_USER_USERNAME}</caseOwner>
               <caseOwnerType>User</caseOwnerType>
               <emailAddress>{SUPPORT_EMAIL}</emailAddress>
               <routingName>{ROUTING_NAME}</routingName>
           </routingAddresses>
           <!-- Path B: replace <caseOwner>/<caseOwnerType> with
                <fallbackQueue>{QUEUE_DEVELOPER_NAME}</fallbackQueue> + <routingFlow>{INBOUND_FLOW_DEVELOPER_NAME}</routingFlow>.
                casePriority is required. Include whatever else the read returned (minus emailServicesAddress/isVerified).
                Repeat <routingAddresses> for every OTHER existing address, without botEmailDefinition/caseOwner/routingFlow. -->
       </emailToCase>
   </CaseSettings>
   ```

3. **Deploy in metadata format** so the version comes from the manifest — do **not** mutate `sfdx-project.json`. A source deploy of `Settings:Case` reads `sourceApiVersion` (which `--api-version` does not override), so pinning it there would persist to every later deploy in the user's project. Assemble a metadata-format package versioned at `ORG_API_VERSION` (already ≥68.0 from the Precondition — `botEmailDefinition` on a routing address needs v68.0+):
   ```bash
   MDDIR=/tmp/sfskills/casesettings-mdapi
   mkdir -p "$MDDIR/settings"
   # package.xml: from assets/settings-mdapi-package.xml, {API_VERSION} = ORG_API_VERSION.
   sed -e "s/{API_VERSION}/{ORG_API_VERSION}/" \
       assets/settings-mdapi-package.xml > "$MDDIR/package.xml"
   # component file: the Case.settings-meta.xml from step 2, WITHOUT the -meta.xml suffix
   cp <path-from-step-2>/Case.settings-meta.xml "$MDDIR/settings/Case.settings"
   sf project deploy start --metadata-dir "$MDDIR" --target-org $ORG --json
   ```

Verify the read-back (`emailToCase.routingAddresses`): the **set of `emailAddress` values matches the pre-deploy set** — not just that the count is unchanged, since a dropped-and-added swap preserves the count — and the target address (`{SUPPORT_EMAIL}`) now carries `<botEmailDefinition>{BOT_EMAIL_DEFINITION_NAME}</botEmailDefinition>` and the chosen path's fields (`<caseOwner>` with `caseOwnerType` `User`, or `<routingFlow>`+`<fallbackQueue>`). If any pre-deploy address is missing from the read-back, stop and surface it — a live routing address was unbound.

Branch C is complete once the binding is verified. Outbound escalation is added via Phase 3 (`agent-wiring.md`) exactly like the other channels — offer it rather than skipping it (the user can decline; it does not block inbound completion). If you already batched the outbound route into the Step 3 `connection service_email:` block, escalation is done — just confirm `outboundRouteName`/`outboundRouteType` round-tripped (per `agent-wiring.md`) instead of republishing.

### If escalation was wired — surface the runtime prerequisites

If (and only if) outbound escalation was set up for this agent — batched into the Step 3 `connection service_email:` block, or added later via Phase 3 (`agent-wiring.md`) — present this note to the user **verbatim** after the agent is republished:

> **Escalation is now wired to your agent — but a few org-level Omni-Channel settings must be in place before an escalated case can actually reach a human.** This skill configured the agent and the routing flow; the rest is runtime setup an admin controls:
> - **Omni-Channel is enabled** in the org.
> - A **Service Presence Status** exists that includes the **Case-based service channel**, and your human agents can access it (granted via permission set or profile).
> - Agents are assigned to a **Presence Configuration** (the org's *Default* covers all users unless you've narrowed it) with **capacity** to spare.
> - The human agent is a **member of the queue** that the flow routes to.
> - The human agent is **Online in Omni-Channel** under that presence status and **accepts** the incoming work when it's offered.

## Next steps — recommend authoring topics and actions

After confirming the agent is published and wired to Email-to-Case, surface this recommendation to the user:

> Your agent is now published and wired to Email-to-Case, so it can reply to inbound email. To give it real capabilities — reading or updating records, creating cases, escalating, or answering from knowledge — author its topics and actions with the `agentforce-generate` skill, which creates topics and actions along with the Flows, Apex, or prompt templates that back them. Consider how each data-touching action should authorize the requester — for example, scope reads and changes to records tied to the inbound sender's email address.

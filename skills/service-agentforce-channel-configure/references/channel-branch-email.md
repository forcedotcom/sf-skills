# Branch C — Email-to-Case inbound routing

Same inbound RoutingFlow shape as Branch B, but using the org-specific Case-based ServiceChannel. Also includes the mandatory outbound `connection service_email:` and a mandatory manual BotEmailDefinition step (Email Configuration in Setup).

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
     "/services/data/v67.0/tooling/query?q=SELECT+Metadata+FROM+CaseSettings+LIMIT+1"
   ```

   b. In the returned `Metadata.caseEmailRoutingAddresses` array, find the entry whose `emailAddress` matches `{SUPPORT_EMAIL}`. Patch that entry:
   - `caseOrigin`: query `Case.Origin` picklist values and select `Email` if present, otherwise the closest match
   - `saveEmailHeaders`: `true`
   - `addressType`: `EmailToCase`

   c. Deploy the patched Metadata back:
   ```bash
   sf api request rest -o "$ORG" --method PATCH \
     "/services/data/v67.0/tooling/sobjects/CaseSettings/{CASE_SETTINGS_ID}" \
     --body '{"Metadata": {<patched metadata object>}}'
   ```
   Run this from `/tmp/sfskills` (a valid SFDX project directory). If the Tooling API PATCH fails, fall back to Metadata API deploy via `sf project deploy start --metadata Settings:Case`.

4. Inform the user about email verification — then continue without waiting:

   > *"A verification email has been sent to `{SUPPORT_EMAIL}`. Click the link in that email when you get it — inbound mail won't be processed until the address is verified, but you can complete the rest of the setup now.*
   >
   > *If you don't receive the verification email, your domain may have email verification policies that block it:*
   > *[Email Verification Requirements for Salesforce Orgs](https://help.salesforce.com/s/articleView?id=xcloud.security_email_verification_requirements.htm&type=5)*"*

   Continue to the next step immediately — do not wait for the user to confirm.

### If using an existing routing address

Set `ROUTING_ADDRESS_ID` to the selected record's `Id` and continue. No provisioning steps needed.

---

## Step 2 — Inbound RoutingFlow

1. **Query the ServiceChannel** — see `channel-types.md`. Stop if zero rows; ask user if multiple rows.

2. **Determine names:**
   - Flow label: `{AgentLabel} Inbound Email Flow`
   - DeveloperName: `{AgentDevName}_Inbound_Email_Flow`
   - `SERVICE_CHANNEL_DEV_NAME` / `SERVICE_CHANNEL_LABEL` from the queried ServiceChannel

3. **Write the RoutingFlow XML** to `force-app/main/default/flows/{AgentDevName}_Inbound_Email_Flow.flow-meta.xml` using the template in `routing-flow.md`. Substitute all tokens including `{QUEUE_ID}` from Phase 1.

4. **Deploy and verify `ActiveVersionId` is non-null** (see `routing-flow.md`).

No agent file changes from inbound routing.

---

## Step 3 — Mandatory outbound escalation: `connection service_email:`

Unlike other channel types where outbound escalation is optional, Email-to-Case requires the `connection service_email:` block to be on the agent before the BotEmailDefinition (Email Configuration) can be created in Setup — the Setup UI requires the agent to already have this connection wired.

Do not offer this as optional or skip to Phase 3. Run these steps now:

1. **Determine the outbound flow name:**
   - Flow label: `{AgentLabel} Outbound Email Flow`
   - DeveloperName: `{AgentDevName}_Outbound_Email_Flow`

2. **Check if an active outbound flow already exists:**
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='{AgentDevName}_Outbound_Email_Flow' AND ProcessType='RoutingFlow'"
   ```
   - Row exists with non-null `ActiveVersionId` → reuse it; skip to step 3.
   - Row missing or `ActiveVersionId` null → create using the QueueBased template in `routing-flow.md` Part 2, with the `SERVICE_CHANNEL_DEV_NAME` / `SERVICE_CHANNEL_LABEL` queried above and `QUEUE_DEVELOPER_NAME` from Phase 1. Deploy and verify `ActiveVersionId` is non-null.

3. **Add `connection service_email:` to the agent and republish** — follow `agent-wiring.md`. Verify the connection block is present in the deployed bundle before continuing.

---

## Step 4 — Mandatory manual step: BotEmailDefinition (cannot be automated)

The `BotEmailDefinition` metadata type is not yet deployable via `sf project deploy`. Surface this step only after the outbound connection block is confirmed deployed:

> *"The inbound routing flow and outbound escalation are now configured. One final manual step is required: you must create an **Email Configuration for Agentforce Service Agent** in Setup.*
>
> *Go to: `{ORG_INSTANCE_URL}/lightning/setup/AsaForEmail/home` → New*
>
> *Fill in the following fields:*
> - *Label / DeveloperName: use the agent name for identification, e.g. `{AgentLabel} Email Configuration`*
> - *Agent: select **{AgentLabel}***
> - *Reply Template: an email template containing `[[[GENERATED_CONTENT]]]` (the agent's reply body) and `[[[LEGAL_DISCLOSURE]]]` (required legal footer placeholder)*
> - *Legal Disclaimer: the legal text shown at the bottom of every agent reply email (required)*
> - *Signature: the agent's sign-off text, e.g. agent name and title (required)*
>
> *If you don't have suitable email templates yet, open the App Launcher and search for **Email Templates** to create them. The reply template must include `[[[GENERATED_CONTENT]]]` and `[[[LEGAL_DISCLOSURE]]]` as literal placeholder strings.*
>
> *Once the Email Configuration is saved, open your Email-to-Case configuration (Setup → Feature Settings → Service → Email-to-Case → edit the relevant routing address) and set the **Agentforce Configuration** field to the configuration you just created.*
>
> *Reference: [Email Configurations for Agentforce Service Agent](https://help.salesforce.com/s/articleView?id=ai.service_agent_email_configuration.htm&type=5)*
>
> Please confirm when this setup step is complete."*

Branch C is complete once the user confirms. Phase 3 outbound escalation has already been handled above — skip Phase 3 for Email-to-Case.

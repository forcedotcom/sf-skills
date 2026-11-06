# CLI discovery → ECA onboarding → OrgJWT → evaluations

This workflow incorporates the [Salesforce CLI org reference](https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_org.html), [Connected App/ECA configuration skill](https://github.com/forcedotcom/sf-skills/tree/main/skills/integration-connectivity-connected-app-configure), and [Models API configuration skill](https://github.com/forcedotcom/sf-skills/tree/main/skills/platform-models-api-configure). Their guidance is incorporated here so those skills do not need to be installed. The generic Models API skill also configures an agent's own model provider; this optimizer uses bundled HTTP clients and does not change Claude Code, Codex or OpenCode provider settings.

## Discover the org and its ECA

```bash
python3 "$SKILL_DIR/scripts/setup_hyperclassifier.py" inspect --target-org <alias>
# Omit --target-org to use the CLI's configured default.
# If there is no default or the desired org is unclear:
python3 "$SKILL_DIR/scripts/setup_hyperclassifier.py" orgs
```

The helper captures `sf org display --target-org <alias> --json` and `sf org list auth --json` privately and prints only org identity fields. Both commands can include tokens in their raw JSON, so never paste or log their unfiltered output. For CLI versions that omit or redact the token from `org display`, the supported secret command is `sf org auth show-access-token --target-org <alias> --json`; `read_org_session()` captures it in memory. `inspect --check-session-token` reports availability only and rejects redaction placeholders. Do not use `--verbose` or export an SFDX auth URL for this workflow.

With that CLI org session, the helper runs the Tooling API equivalent of:

```sql
SELECT Id, DeveloperName, MasterLabel
FROM ExternalClientApplication
WHERE DeveloperName = 'agentforce_hyperclassifier_optimize'
   OR MasterLabel = 'agentforce-hyperclassifier-optimize'
```

`sf data query --target-org <alias> --use-tooling-api --query '<query>' --json` uses the CLI session token for the customer's org endpoint. A valid session token does **not** imply a gateway-compatible OrgJWT or `sfap_api` access. Failed queries, missing permissions and expired sessions must be resolved before concluding the ECA is missing.

For a new login, use the CLI's browser authorization-code flow:

```bash
sf org login web --alias <alias> --instance-url https://test.salesforce.com
# Use https://login.salesforce.com for production, or the customer's My Domain.
```

The user completes browser login. Never request a password or SFDX auth URL in chat.

## Existing ECA or supplied credentials

Ask the user to retrieve the Consumer Key and Consumer Secret in Setup → External Client Apps Manager → the app → Settings → OAuth Settings → Consumer Key and Secret. Save them locally using `assets/customer-org.env.example`, outside the repository, with mode 600. The ECA discovery API does not disclose its Consumer Secret.

```bash
python3 "$SKILL_DIR/scripts/setup_hyperclassifier.py" configure \
  --target-org <alias> --env-file /private/path/customer-org.env
```

Alternatively omit `--env-file` in an interactive terminal for hidden Consumer Key and Secret prompts. An unattended agent should ask the user to populate a private file, not attempt to type or echo secrets into an automated terminal. The helper verifies that the credential origin matches the selected org and saves a private copy under `~/.config/agentforce-hyperclassifier-optimize/<org-id>/credentials.env`, alongside a nonsecret `profile.json`. It refuses overwrites; for rotation, back up the private credential file privately and deliberately replace it.

If the dedicated ECA is missing, explicitly offer these alternatives: reuse credentials for another appropriately configured customer ECA, or create the dedicated ECA. A supplied ECA needs the scopes/flow described in [authentication.md](authentication.md). A session token alone is not an alternative.

## Create the dedicated ECA

Creation requires a customer org admin with ECA/metadata deployment permission and API 65.0+ for the named-user JWT timeout policy. The helper rejects an older selected API version before creating metadata; refresh the CLI's org version before retrying. Establish the exact target org and Run As user. Prefer a dedicated integration user with only the required model/product permissions; use `--run-as` to name it. Omitting or passing an empty `--run-as` uses the current CLI user and emits a warning on stderr and in the successful preparation response's `warnings` array. The warning identifies that user and explains the permission implications; stdout remains valid JSON. An explicit nonempty `--run-as` suppresses this fallback warning and returns an empty `warnings` array. Do not silently use a different principal or assume an administrator is the appropriate runtime identity. Ask for the app contact email if it cannot be inferred from user-provided context.

```bash
python3 "$SKILL_DIR/scripts/setup_hyperclassifier.py" prepare-eca \
  --target-org <alias> --contact-email admin@example.com --run-as integration@example.com
```

This creates a separate SFDX project in the private per-org workspace with:

- `ExternalClientApplication`, label `agentforce-hyperclassifier-optimize`, API name `agentforce_hyperclassifier_optimize`, Local distribution.
- Global OAuth settings enabling client credentials and named-user JWTs, with a required consumer secret.
- OAuth scopes `Api, RefreshToken, SFApiPlatform` (`api`, `refresh_token`, `sfap_api`).
- A dedicated permission set for app preauthorization only; it grants no new object/system permissions.
- `plan.json` identifying the org, Run As user, scopes, policy choices and deployment steps.

Review the actual XML and plan. App creation is a distinct org mutation; proceed only when the user's request already authorizes it, or obtain authorization for this concrete plan. Preparation is local and does not deploy. It stages a complete project before publishing `eca/`, so a failed write can be retried. If `eca/` already exists, review and reuse its plan. For a legacy partial tree without a plan, back it up and move it aside before preparing again; inspect org deployment status before any new deployment. Preparation never overwrites prior work.

```bash
python3 "$SKILL_DIR/scripts/setup_hyperclassifier.py" deploy-eca --target-org <alias>
# Once creation in this org is authorized:
python3 "$SKILL_DIR/scripts/setup_hyperclassifier.py" deploy-eca --target-org <alias> --apply
```

Deployment uses `sf project deploy start --source-dir ... --target-org <alias> --wait 10 --json` from the dedicated project. It then retrieves the app's generated default policies before editing them. The OAuth policy specifies the active Run As user, the dedicated preauthorization permission set, a 30-minute JWT, admin-approved users and enforced IP restrictions. The general policy enables OAuth. Finally, `sf org assign permset --target-org <alias> --name <permission-set> --on-behalf-of <run-as> --json` assigns preauthorization to the selected user.

The helper records attempted stages and validated deployment IDs/statuses, including failed or still-running CLI results. It never regenerates OAuth security settings from an invented schema. Existing policies are backed up before edits. It refuses duplicate ECAs, cross-org plans and blind retries after partial deployment. If a deployment fails or times out, inspect its recorded ID with `sf project deploy report --job-id <id> --target-org <alias> --json` and inspect the org state before recovery. A process/network failure before the CLI returns an ID cannot be reconstructed locally; inspect the org's Deployment Status and CLI job records instead. If generated policy names differ, list/retrieve the actual policy metadata for that app and adapt the plan; do not deploy guessed policy names or rerun creation. Do not automatically delete a partly created app or relax IP restrictions.

Use the permission-set name in the generated policy and verify the retrieved association. Salesforce's field reference describes IDs, but retrieved ECA policies can contain permission-set names; do not replace working references with guessed IDs. The ECA metadata reference also describes API Only for the Run As user, while related connected-app guidance differs. Do not assume a universal runtime requirement or grant broad permissions: verify the chosen user's effective access and token issuance in the target org.

Consumer credentials are generated by Salesforce after deployment. Retrieve them privately in Setup and run `configure` as above. The helper cannot bypass Salesforce's protected secret-reveal step. App preauthorization does not grant Models API entitlement; the Run As user must already have the relevant product/model permissions.

## Verify and start the full workflow

```bash
python3 "$SKILL_DIR/scripts/hyperclassifier.py" preflight \
  --target-org <alias> --evals ./evals.csv --descriptions ./descriptions.json
```

The client exchanges the saved ECA credentials at the customer's `/services/oauth2/token` endpoint, checks signed JWT shape/expiry, and calls the gateway. It never reuses the CLI session token for this request. Only successful preflight establishes current full-description contract access.

For optimization readiness, add `--check-proposer --proposer-model <available-model>` to preflight. The optimizer also checks its proposer before every new baseline, and counts that call in its budget.

Continue with the evaluation and optimization commands in `SKILL.md`, using the same input paths. `--workspace <path>` supports a custom private directory; use it consistently in setup and evaluation commands. Explicit `--env-file` remains available for unattended environments without an installed CLI, once ECA onboarding is complete.

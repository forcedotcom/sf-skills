# Deploy, validate, or quick deploy (Operation D)

Deploys metadata that already exists in the **source org** (the org the user built in) to a **target environment** connected in DX Inspector. It calls `POST /connect/devops/simple-deploy/deploy`, then polls `GET` until the request reaches a final status.

Metadata only. Data (record) deploys are not supported. Needs Salesforce API **v67.0** or later.

| Mode | When | Request body |
|---|---|---|
| `deploy` (default) | The user wants the components in the target | `references/request-body.md` |
| `validate` | The user asks for a check only. For a Production target, recommend it first (Step 3), but never switch the mode without their agreement | `isCheckDeploy: true` |
| `quickDeploy` | The user has a successful validation id (`0Af…`) to deploy | `isQuickDeploy: true` + `checkDeployIdentifier` |

## Before Step 1

1. Source org: the alias the user named, else the default org from `sf org display --json`. If it cannot be read, ask which org they build in.
2. Read `result.apiVersion` from that output. If it is below `67.0`, stop and say the org's API version is too old for this skill.
3. One target per run. If the user names several, deploy to the first, finish, and ask before starting the next. Each target gets its own confirmation (Step 4).

## Step 1: Components

Skip this step for `quickDeploy`: it sends no `changes`.

Ask: "Which components do you want to deploy? Give the name and type of each (for example `AccountService` ApexClass, `Account.Tier__c` CustomField), and tell me whether each is **new**, **changed**, or **removed**."

Map the answer to the wire `operation`: new → `add`, changed → `modify`, removed → `delete`. Anything unclear → `modify`.

Build `changes[]` as `{fullName, type, operation}`. All three are required and non-blank. Types are Metadata API type names (`ApexClass`, `CustomObject`, `CustomField`, `Flow`, `LightningComponentBundle`, …). If the user gives a name without a type, ask; do not guess.

## Step 2: Target environment

Follow `references/list-orgs.md` with the identifier the user gave (sections 1 to 3). Then:

| Outcome | Do |
|---|---|
| Target is `matched` and `selectable` | Carry `id` and `namedCredential` from that row. Go to Step 3. |
| No target named yet | Ask which target. Show the list (`list-orgs.md`, section 4) if they want to choose. |
| `not-connected` | Offer to connect it. If the user agrees, run `references/connect-org.md` (deploy-target mode), then **continue as below**. |
| `unauthenticated` | Offer to finish connecting it (repair path), then continue as below. |
| `expired` | Not deployable. Ask for another target or offer to connect a new one. |

**Continuing after a connect.** When the connect flow finishes and the environment shows as `selectable`, tell the user in one sentence that `<name>` is now connected, and that you will continue the deploy of `<components>` to it. Then go straight to Step 3 and Step 4. The Step 4 message is the confirmation they give before anything is deployed; connecting an org never deploys by itself.

If the user connected the org but gave no components yet, ask for them (Step 1) after the connect.

## Step 3: Build the request

Write the POST body to a temp file (`BODY=$(mktemp)`; this avoids shell-quoting nested JSON):

```json
{
  "namedCredential": "<NamedCredential>",
  "targetEnvironmentId": "<DevopsEnvironment Id>",
  "requestBody": {
    "changes": [{"fullName": "AccountService", "type": "ApexClass", "operation": "modify"}],
    "testOptions": {"level": "NoTestRun", "tests": []}
  }
}
```

Mode variants and test-level rules: `references/request-body.md`.

- **Production target:** recommend a `validate` run first unless the user already has a successful one, and default the test level to `RunLocalTests`. An explicit user choice of test level always wins.
- **Quick deploy:** the validation id comes from the user or from an earlier `validate` in this conversation (`metadata.deployId`). If you have neither, ask for it. Never invent one. Send only `isQuickDeploy` and `checkDeployIdentifier`, never `changes` or `testOptions`.

## Step 4: Confirmation gate

**This call changes the target org (except `validate`). Do not proceed without an explicit yes.** Show:

> "I'm about to **<deploy | validate | quick deploy>** from `<source-org-alias>` to `<environment Name>` (<OrgType>):
> - Components: <n> (<first few, with new/changed/removed>)
> - Test level: <level>
>
> Shall I proceed?"

For **quick deploy**, replace the components and test-level lines with `- Validation id: <0Af…>`, and use the same target environment the validation ran against. If the user gives only the id, ask which target it was validated against.

Call out any `delete` and any Production target explicitly. `validate` does not change the target, so it needs no confirmation, but still state what you are about to validate.

## Step 5: Submit

```bash
sf api request rest \
  "/services/data/v67.0/connect/devops/simple-deploy/deploy" \
  --method POST \
  --body @"$BODY" \
  --target-org "<source-org-alias>"
```

Read `response.requestId`. If it is absent, the call failed: use `references/error-handling.md`. Make **one** attempt. Never retry in a loop, never resubmit after a timeout, and never invent a `requestId`.

## Step 6: Poll to completion

Polling is automatic and read-only. Every check reads **two sources**, and a terminal state from **either** one ends it: the Simple Deploy status endpoint (live `step`, `metadata.deployId`) and the `DevopsRequestInfo` record for the `requestId` (`Status` is `SUCCESS` or `ERROR`; it is the same record commit polling uses).

```bash
bash scripts/poll-deploy-status.sh <requestId> "<source-org-alias>" 10 100
```

Checks come at 3 s, then 5 s, then every 10 s, for at most **100 seconds**, about 2 minutes in all. Set the shell tool timeout to at least 180 seconds so the run is not killed before it exits. Progress lines (`status=… step=… request-info=…`) go to stderr; relay the current step to the user while waiting. Never say the deploy is "still waiting" after the script has printed a result.

On a failed deploy the script also reads the failure detail that Core attaches to the request (the `DEPLOYMENT_COMPLETED` `DevopsActivityLog` row). Core fills it in a few seconds after the failure by calling the target org's Metadata API through the deploy's named credential, so **no login to the target org is needed**. The script waits up to 20 s for it (`DETAIL_WAIT`), and skips the wait when the deploy failed before reaching the target org.

The script prints one JSON object when it ends:

| Field | Meaning |
|---|---|
| `outcome` | `SUCCEEDED`, `FAILED`, `NOT_FOUND`, `TIMEOUT` (poll ran out of time), or `IN_PROGRESS` (`--once` only) |
| `step`, `status` | Last phase seen (`RETRIEVE_METADATA`, `DEPLOY_METADATA`, `VALIDATE_METADATA`, …) and its status |
| `deployId` | The target org's deploy id (`0Af…`). For a successful `validate` this is the id for a quick deploy |
| `message`, `errorDetails`, `activityMessage` | Failure text. For a failure before the target org (retrieve or validation) this already names the problem; for a failed target deploy it is generic ("Metadata deployment failed with status: Failed"). Prefer these over `errorMessage`, which can be HTML-escaped (`&#39;`) |
| `deployJobLogURL` | Per-component detail, in the target org |
| `errorDetail` | Core's detail for a failed target deploy: `numberComponentErrors`, `componentFailures[]` (`componentType`, `fileName`, `problem`, `problemType`, `lineNumber`, `columnNumber`), `testFailures[]` (`name`, `methodName`, `message`, `stackTrace`), `errorMessage` (for example a code-coverage shortfall), `truncated` (only the first 5 of each are kept). `null` when none |
| `errorDetailUnavailable` | `true` when Core recorded that no detail will come |
| `decidedBy` | `endpoint` or `request-info`: which source reported the final state |
| `response` | The raw endpoint response |

Exit codes: `0` succeeded, `2` failed or not found, `3` timeout, `1` usage error or both sources failed, `4` still processing (`--once` only). `outcome` tells `FAILED` from `NOT_FOUND`.

`NOT_FOUND` right after a submit can be transient (the script allows a short grace period, and a `DevopsRequestInfo` row overrides it). If it persists, the id is unknown or older than about 2 days.

On timeout (exit `3`, `outcome` `TIMEOUT`, about 2 minutes), stop polling and tell the user, in plain words, that the deploy has not reported a final status yet but may still be running. Give them what they need to check it later:

- **Request token (`requestId`)**: "Send me this id and I'll check its status."
- **Deployment id (`deployId`, starts `0Af`)**, only if the result has one: it is the deploy job in the target org. They can find it in the target org under Setup → Deployment Status, or at `deployJobLogURL`.
- The `step` it had reached.
- That the deploy also shows in DX Inspector's activity history for this org.

Example: "Your deploy to `<target>` hasn't reported a final status after 2 minutes. It was at `DEPLOY_METADATA` and may still be running. Request token: `<requestId>`. Deployment id: `<deployId>`. Send me the request token any time and I'll check it, or look up the deployment id in `<target>` under Setup → Deployment Status." Never resubmit, and do not keep polling.

For a one-off check, put `--once` **first**: `bash scripts/poll-deploy-status.sh --once <requestId> "<source-org-alias>"`. It exits `4` while the request is still processing: report the current `step` and do not poll again unless the user asks. With `--once` there is no grace period, so `NOT_FOUND` right after a submit may be transient: say the request is not visible yet and check again shortly, not that it failed.

If the user gives a `requestId` to check (also when they come back with the id from a timeout), skip Steps 1 to 5 and check it once with `--once`, using the source org alias. If the user asks for the status without an id, use the `requestId` from earlier in this conversation; if there is none, ask for it. Then report as in Step 7.

## Step 7: Report

Summarize in plain language: what was deployed, from where, to where, and the outcome. No raw JSON.

- **Succeeded:** say so, with the completion time (`completedAt`). After a successful `validate`, give `deployId` as the validation id and offer a quick deploy with it.
- **Failed:** always show the error, never just "failed".
  1. Say which `step` failed. If `errorDetail` is present, use it: list each `errorDetail.componentFailures` entry as `<fileName> (<componentType>), line <lineNumber>: <problem>`, each `testFailures` entry as `<name>.<methodName>: <message>`, and always include `errorDetail.errorMessage` when set (a code-coverage shortfall appears only there, with `numberComponentErrors` at 0). If `truncated` is true, say only the first few are shown and give `deployJobLogURL`.
  2. If `errorDetail` is `null`, quote `activityMessage` (else `errorDetails`, else `message`). A failure at `RETRIEVE_METADATA` or validation, such as "Entity of type 'CustomField' named 'Book__c.Author__c' cannot be found", is complete as is: the component is missing from the source org.
  3. If `errorDetail` is `null` and the message is only the generic "Metadata deployment failed with status: Failed", the detail was not attached in time (or `errorDetailUnavailable` is `true`). Say so, give `deployJobLogURL` (also Setup → Deployment Status in the target org), and offer to check again shortly with `--once`.
  4. Map the error with `references/error-handling.md`, and ask before retrying. Never resubmit on your own.

## Gotchas

| Gotcha | What to do |
|---|---|
| Component not in the source org | The deploy retrieves from the source org. Confirm the name and type exist there before submitting. |
| Quick deploy with `changes` | Forbidden. Send only `isQuickDeploy` and `checkDeployIdentifier`. |
| Target equals the source org | Not allowed. Ask for a different target. |
| An id starting `0Af` | It is a validation id, not a `requestId`. Never poll it. If the user gives one alone, ask whether to quick deploy it, and to which target. |
| Stale target login | Shows only at deploy time (`Bad_OAuth_Token`, `TARGET_ORG_SESSION_EXPIRED`). Reconnect that environment (`connect-org.md`, repair path), then ask before retrying. |

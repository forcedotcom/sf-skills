# Create a review through the DevOps Center API

Verified against a live Core-hub setup (dev org + hub org, work item `WI-000012`, GitHub repo). Use this when the user supplies a dev org alias and the work item already has a committed component list. It is the review-side counterpart of `references/commit-api.md`; the same dev org / hub org split and preflight apply.

## Contents

- Flow
- Preflight
- Request
- Response
- Errors
- Idempotency
- Confirming on the hub
- Known limits

## Flow

```text
dev org  POST /connect/devops/createReview
  -> hub org (ALMDevOpsCenterHub named credential)  POST .../workItems/{id}/review
  -> DevOps Center service -> GitHub/Bitbucket pull request
  <- {status, reviewUrl, errorMessage, testingTriggeredStatus}
```

The call is **synchronous**: the pull request exists when the response returns. There is no `DevopsRequestInfo` to poll (unlike commit). The hub server-side creates the PR using the VCS credentials stored in DevOps Center, so no local git auth is needed.

## Preflight

Same check as commit, but at `v68.0` (the version `createReview` was verified at; the commit flow uses `v67.0`). Use the version written here; an older version such as `v63.0` returns `NOT_FOUND`, which is not evidence that the org lacks DevOps Center. `GET /services/data/v68.0/connect/devops/doceConnectionType` on the dev org must return `{"isCore": true, "isManagedPackage": false}`. Any other result means use the `sf devops review create` CLI path.

## Request

```bash
sf api request rest "/services/data/v68.0/connect/devops/createReview" \
  --method POST --body @review.json --target-org <dev-org>
```

```json
{
  "workItemId": "<hub work item id, 1fk...>",
  "workItemName": "WI-000012",
  "workItemLink": "https://<hub-host>/lightning/r/WorkItem/<workItemId>/view"
}
```

- The body is the inner object. Wrapping it in `{"createReview": {...}}` fails with `JSON_PARSER_ERROR: Unrecognized field "createReview"`.
- Resolve `workItemId` and `workItemName` on the hub with `sf devops work-item list --project-id <id> --target-org <hub-org> --json`.
- `<hub-host>` is the hub org's instance URL (`sf org display --target-org <hub-org> --json`, `.result.instanceUrl`).
- Pass the file with the `@` prefix, as in commit.

## Response

Success (HTTP 200):

```json
{"status": "Success", "reviewUrl": "https://github.com/<owner>/<repo>/pull/15", "errorMessage": "", "testingTriggeredStatus": "Not Applicable"}
```

- `reviewUrl` is the pull request URL; the PR number is its last path segment.
- `testingTriggeredStatus` is informational. Seen: `"Not Applicable"` (with a space). Source also allows `success` and `error`; report it as given and do not treat it as a failure signal.

## Errors

Failures are HTTP 200 with `status: "Error"`, an empty `reviewUrl`, and `errorMessage` as `CODE:detail`. Always check `status`.

| Code | Meaning | Action |
|------|---------|--------|
| `WORKITEM_NEVERED` | Work item is Nevered | Stop; the work item cannot get a review |
| `REVIEW_NO_COMMITS_BETWEEN_BRANCHES` | Work item branch has no commits relative to the target branch | Commit first, then retry |
| `REVIEW_CREDENTIAL_ERROR` | VCS credential rejected ("Bad credentials") | Ask the user to fix the VCS credential in DevOps Center |
| `REVIEW_VCS_AUTHENTICATION_FAILED` | Raised for any "not found" in the VCS error, including a **missing branch** | Check both the credential and that the work item and target branches exist |
| `REVIEW_PR_ALREADY_EXISTS` | PR already open for the branch | See Idempotency |
| `REVIEW_CREATION_FAILED` | Anything else; detail follows the colon | Surface the detail. A nonexistent work item id also lands here: `Could not find WorkItem: <id>` |
| `REVIEW_UNKNOWN_ERROR`, `REVIEW_WORK_ITEM_NOT_FOUND` | Passed through unchanged | Surface the message |

Seen live: a nonexistent id returned `REVIEW_CREATION_FAILED:Failed to create review for work item <id>: Failed to get WorkItem for Id: Could not find WorkItem: <id>`. The other rows are taken from the service's error-code definitions and have not been observed live, so treat their meanings as expected, not confirmed.

## Idempotency

Calling `createReview` again for a work item that already has a PR returned `Success` with the **same** `reviewUrl` (seen live), not `REVIEW_PR_ALREADY_EXISTS`. A repeat call is therefore safe and is the way to look up an existing PR URL. Still handle `REVIEW_PR_ALREADY_EXISTS` in case the hub returns it for a PR created outside DevOps Center.

## Confirming on the hub

```bash
sf data query --target-org <hub-org> --json \
  -q "SELECT Name, Status, ReviewRemoteReference FROM WorkItem WHERE Id = '<id>'"
```

After a successful review, `Status` is `IN_REVIEW` and `ReviewRemoteReference` holds the PR number. Confirm both before reporting success.

## Known limits

- Verified live only for an In Progress work item with a committed component list, against GitHub. Bitbucket and other starting statuses were not exercised.
- The no-commits, bad-credential and missing-branch errors were not triggered live.
- `reviewUrl` may show a different owner than the project's `repoUrl`; trust the returned URL.

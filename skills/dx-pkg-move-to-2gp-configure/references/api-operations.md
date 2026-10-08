# Move to 2GP API operations

Use these operations for the final cutover of an already-converted 1GP managed package. Initial conversion, version promotion, and subscriber migration are separate workflows.

## Execution and org routing

Prefer an available authenticated MCP tool that supports these REST or Tooling operations. Map the method, full path, query, body, and target org to its documented parameters; do not assume a particular tool name. If none is available, use the Salesforce CLI examples below. Never print access tokens.

Use API 69.0 for the automated workflow. Check the org's supported API versions before dispatch. The original 1GP packaging org is required; the Dev Hub is optional and is used only for proactive converted-version checks. Subscriber orgs are not targets of this skill. The packaging org needs packaging enabled for the Tooling objects; finalization requires CreatePackaging and edit rights on the selected package. A profile name alone does not establish access.

In the examples, replace `packaging-org`, `dev-hub`, `<033-package-id>`, and `<0Ho-package-id>` with confirmed values. The 033 ID is the original MetadataPackage ID; 15- and 18-character forms are supported. Escape any user-supplied package name as a SOQL string literal, and URL-encode SOQL when sending REST query parameters.

```bash
sf org list --json
```

## Resolve the source package (packaging org)

For a supplied package name, query MetadataPackage. Zero matches means the name or org is wrong; multiple matches require the user to select the package. A supplied 033 ID can be checked with an Id filter instead.

```bash
sf data query --use-tooling-api --api-version 69.0 --target-org packaging-org --json \
  --query "SELECT Id, Name, NamespacePrefix FROM MetadataPackage WHERE Name = '<escaped-package-name>'"
```

REST equivalent: `GET /services/data/v69.0/tooling/query?q=<URL-encoded-SOQL>`.

## Check completion first (packaging org)

```bash
sf data query --use-tooling-api --api-version 69.0 --target-org packaging-org --json \
  --query "SELECT Id, EndDate, FinalizedVersionId, FinalizedVersionNumber FROM PackageConversion WHERE ConvertedFromPackageId = '<033-package-id>'"
```

No records: conversion is required first; stop. EndDate non-null: already finalized; stop before confirmations or POST. EndDate null: continue. A failed query is not equivalent to an empty result. Do not assume a native 2GP version is created by finalization.

## Check the latest Released 1GP version (packaging org)

```bash
sf data query --use-tooling-api --api-version 69.0 --target-org packaging-org --json \
  --query "SELECT Id, MajorVersion, MinorVersion, PatchVersion, ReleaseState FROM MetadataPackageVersion WHERE MetadataPackageId = '<033-package-id>' AND ReleaseState = 'Released' ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC LIMIT 1"
```

No Released version blocks finalization. PatchVersion must be zero: finalization of a latest Released patch version is rejected by the server. Retain the exact major.minor.patch coordinates.

## Optional converted-version check (Dev Hub)

Skip both queries when no Dev Hub is connected, disclose the skipped proactive check, and let the finalization endpoint enforce version eligibility. The remaining workflow uses the package ID resolved on the packaging org.

```bash
sf data query --use-tooling-api --api-version 69.0 --target-org dev-hub --json \
  --query "SELECT Id, Name, NamespacePrefix, ConvertedFromPackageId, ContainerOptions FROM Package2 WHERE ConvertedFromPackageId = '<033-package-id>'"
```

No matching Package2 requires checking the Dev Hub and conversion before continuing this branch. Using its 0Ho ID, query the highest Released converted version:

```bash
sf data query --use-tooling-api --api-version 69.0 --target-org dev-hub --json \
  --query "SELECT Id, MajorVersion, MinorVersion, PatchVersion, IsReleased, ConvertedFromVersionId, SubscriberPackageVersionId FROM Package2Version WHERE Package2Id = '<0Ho-package-id>' AND IsReleased = true AND ConvertedFromVersionId != NULL ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC LIMIT 1"
```

Require the returned major.minor.patch to equal the latest Released 1GP version exactly. No Released converted version or any mismatch blocks this branch. Do not choose an older matching version to bypass the latest version. The server also validates version alignment and rejects pending patch orgs.

## Retrieve and preserve source before finalization

This is preparation, not an automatic part of the cutover. The user must confirm that conversion and subscriber-migration tests are complete and that source is retrieved and preserved.

```bash
sf package version retrieve --package <converted-04t-version-id> \
  --output-dir <source-folder> --target-dev-hub dev-hub
```

Prepare `versionName`, `versionNumber`, and `ancestorVersion` in the retrieved project's sfdx-project.json for ongoing 2GP development. See the [Salesforce preparation and cutover workflow](https://developer.salesforce.com/docs/platform/pkg1-dev/guide/migration-move-to-2gp-workflow.html).

## Finalize (packaging org, explicit action requests only)

Method: `POST`.
Path: `/services/data/v69.0/connect/packaging/package/<033-package-id>/finalize-move-to-2gp`.

Each field below is a JSON boolean bound to a distinct explicit user confirmation:

| Field | Required confirmation |
|---|---|
| `acknowledgedIrrevocable` | No new major/minor 1GP versions after this one-way transition. |
| `acknowledgedTestingComplete` | Both package-conversion testing and subscriber-migration testing are complete. |
| `acknowledgedSourceRetrieved` | Converted package source is retrieved and preserved, with the project prepared for 2GP development. |

Never set a field true without its confirmation. If any confirmation is missing or declined, do not POST or direct the user to click Proceed.

Only after all three confirmations, create a request file with their actual boolean values. The following is the valid body shape when all confirmations are affirmative; it is not permission to assume them:

```json
{
  "acknowledgedIrrevocable": true,
  "acknowledgedTestingComplete": true,
  "acknowledgedSourceRetrieved": true
}
```

```bash
sf api request rest "/services/data/v69.0/connect/packaging/package/<033-package-id>/finalize-move-to-2gp" \
  --method POST --header "Content-Type: application/json" \
  --body @finalize-request.json --target-org packaging-org --include
```

Success is HTTP 200 with `successfullyFinalized: true` and `packageId`. `finalizedAt` and `conversionId` are optional and may be null. Verify persisted state using the completion query above on the SAME packaging org. EndDate non-null confirms completion. If EndDate remains null, retry the read once after 30 seconds, then report the discrepancy without repeating the write. If the POST times out, query state before deciding whether another write is needed; do not automatically retry.

## Rejections and fallback

| Response | Action |
|---|---|
| 400, missing acknowledgement | Stop and collect the missing confirmation; never invent it. |
| 400, package mismatch | Check the selected package ID and original packaging org. |
| 400, already finalized | Read EndDate and report completion if confirmed; do not POST again. |
| 400, version mismatch | Explain that the latest Released 1GP and converted 2GP major.minor.patch versions must match. |
| 400, patch version | Explain that a latest Released 1GP patch cannot be finalized. |
| 400, pending patch org | Explain that the pending patch org must be resolved before finalization; let the user resolve it. |
| 403, access failure | Check CreatePackaging, package edit rights, packaging-org identity, and the supplied package ID. Nonexistent package IDs can also return 403. |
| 403, temporarily unavailable | Report the service message and suggest retrying later or contacting Salesforce Support. |
| 404, no conversion record for an editable package | Initial conversion is required; this is not evidence of an unavailable endpoint. |
| 5xx or transport failure | Report the error and read state before considering any repeat write. |

Surface the service-supplied message. These business-rule labels describe causes, not a guarantee of distinct REST errorCode values.

When the org's supported API versions do not expose the finalization endpoint, use the manual Setup workflow after the same confirmations: Setup > Package Manager > select the package > Move to 2GP > review every statement > Proceed. Ask for the result and re-query PackageConversion using an API version the org supports where that object is available. Do not bypass an access or eligibility rejection through Setup. If an independent state read is unavailable, clearly distinguish the user's reported success from verified persisted state.

After finalization, the next development step is `sf package version create` from the prepared DX project. It is a separate operation. Older 1GP versions remain patchable; the version moved to 2GP and later versions require 2GP patches. See the linked Salesforce workflow for the precise boundary.

---
name: "dx-pkg-move-to-2gp-configure"
description: "Finalize the Move to 2GP development transition for an already-converted 1GP managed package. TRIGGER when: the user asks to complete or finalize Move to 2GP development, stop 1GP development, or check eligibility for that final cutover. DO NOT TRIGGER for: initial package conversion, creating or promoting package versions, UI Bundle packaging (use experience-ui-bundle-2gp-deploy), Dev Hub setup (use dx-org-devhub-configure), or post-install configuration (use dx-pkg-post-install-configure)."
metadata:
  relatedSkills:
  - dx-org-devhub-configure
  - dx-pkg-post-install-configure
  - experience-ui-bundle-2gp-deploy
  version: "1.0"
  domains:
  - "Developer Experience"
  minApiVersion: "69.0"
  accessCheck:
  - type: "userPerm"
    value: "CreatePackaging"
  cliTools:
  - tool:
    - "sf"
    semver: ">=2.0.0"
  distribution:
    sf-skills:
      visibility: "pre-release"
---
# Move to 2GP Development

Finalize an already-converted 1GP managed package for ongoing 2GP development.

## Prerequisites

- Authenticate to the original 1GP packaging org. The user must have CreatePackaging and edit rights on this package in that org. Packaging must be enabled for the Tooling queries.
- A Dev Hub connection is recommended for checking the converted package version, but is optional for finalization. Without it, skip Dev Hub operations and let the finalization endpoint validate version alignment.
- Before finalization, explicitly confirm irreversibility, completion of both package-conversion and subscriber-migration testing, and retrieval and preservation of the converted package source.

## Workflow

Read [API operations](references/api-operations.md) for the exact queries, request body, org routing, response handling, and CLI examples. Prefer an available authenticated MCP tool that supports the required REST or Tooling operation; otherwise use the Salesforce CLI. Check the tool's parameters rather than assuming a particular MCP server name.

1. Identify the original packaging org and the 033-prefixed package ID. Resolve a supplied name with resolve-package-on-packaging-org; ask the user to select a package if multiple records match. Keep the packaging-org identity and package ID for every later step. The Dev Hub connection is optional.
2. Run check-already-done on the packaging org BEFORE eligibility checks or confirmations. A PackageConversion.EndDate value means the move is already complete: report it and stop. No conversion record means the package needs conversion first: stop and link the Salesforce conversion documentation. A null EndDate means the conversion exists but is not finalized.
3. Run check-eligibility-1gp-released on the packaging org. Select the highest Released major.minor.patch version. Stop if there is no released version or its patch is nonzero. If a Dev Hub is available, run discover-package-on-devhub and check-eligibility-2gp-converted-released there: the highest Released converted 2GP major.minor.patch must match the 1GP version exactly. If Dev Hub is unavailable, skip BOTH Dev Hub operations, state that their proactive check was skipped, and rely on the endpoint's version validation. No later step requires outputs from skipped operations.
4. For an explanation or planning request, explain prerequisites and the finalization options, then stop without dispatching a write. For an action request, collect the three confirmations in confirm-affirmations. The testing confirmation covers both conversion and subscriber migration testing. The source confirmation includes retrieval, preservation, and preparation of sfdx-project.json. Do not infer these confirmations from a general request to migrate.
5. Dispatch finalize-move-to-2gp against the original packaging org only after all three confirmations are individually affirmative and applicable pre-checks passed. Bind each JSON boolean to its confirmation; never attest on the user's behalf. The server also checks version alignment and pending patch orgs. Do not automatically retry a finalization whose outcome is unknown.
6. After API success, run verify-finalize-on-packaging-org directly. EndDate populated confirms persisted completion. finalizedAt and conversionId in the POST response can be null and are not required success indicators. Creating the first native 2GP version is a separate next step, not a verification operation.
7. Use the manual Setup fallback only when the finalization endpoint is genuinely unavailable on the org's supported API versions. Do not interpret an editable package's missing conversion record (404) or an access/business-rule error as an unavailable endpoint. The manual branch still requires all three confirmations; after the user completes it, run verify-finalize-by-user-confirmation and read PackageConversion where supported.

HARD STOP: do not send the finalization POST or instruct the user to click Proceed until acknowledgedIrrevocable, acknowledgedTestingComplete, and acknowledgedSourceRetrieved have each been explicitly confirmed. If any is declined or incomplete, stop and explain the missing prerequisite. Finalization prevents future major/minor 1GP releases. Older 1GP versions can still receive patches; the version moved to 2GP and later versions receive patches through 2GP, as described in the linked Salesforce documentation.


See [API operations](references/api-operations.md) for queries, request examples, error handling, and the manual Setup fallback.

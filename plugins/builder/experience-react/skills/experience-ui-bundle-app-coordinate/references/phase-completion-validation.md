# STEP 2.5: Phase Completion Validation

Before proceeding to STEP 3 (Final Summary), validate that all required phases were executed:

**Critical Validation (MUST pass):**
- [ ] **Phase 0 (Template Offer & Bootstrap) executed**: If no template was used, run `scripts/check-sfdx-project.sh`. If it returns non-zero, STOP and report error:
  ```text
  ERROR: No SFDX project detected. Phase 0 (Bootstrap) is REQUIRED before scaffolding.
  Run `sf project generate` (or create sfdx-project.json) before invoking
  `sf template generate ui-bundle`.
  ```
  If a template was used in Phase 0, this check is satisfied by the template's own scaffolding — skip re-running the script.

- [ ] **Phase 1 hosting target resolved**: Run `scripts/check-hosting-target.sh`. If it returns non-zero, STOP and report error:
  ```text
  ERROR: Hosting target was not resolved in Phase 1. A UI bundle without a <target> in its
  meta XML will not be visible in the org. Determine Experience Site vs Custom Application
  (see "Prompt Classification Keywords" above; ask the user if ambiguous) before proceeding
  past Phase 1 -- do not defer this to Phase 7 and do not record "none"/"skipped".
  ```

- [ ] **Phase 4 (Frontend) executed**: If Phase 4 was NOT executed, STOP and report error:
  ```text
  ERROR: Phase 4 (UI/Frontend generation) is REQUIRED for all UI bundle apps.
  Cannot complete build without generating the React user interface.
  Please review the phase execution logic and ensure Phase 4 is always executed.
  ```

- [ ] **Phase 7 hosting infrastructure deployed**: If neither Phase 7a nor Phase 7b was executed, STOP and report error:
  ```text
  ERROR: Hosting target infrastructure (Phase 7a Experience Site or Phase 7b Custom
  Application) was not deployed. The app was built but is not reachable by any user.
  Exactly one of Phase 7a/7b must run -- it is never optional or "skipped".
  ```

- [ ] **No dangling references after scaffold pruning**: If any file was deleted during Phase 1 scaffold pruning (see "Prune unused scaffold" in SKILL.md), run `scripts/check-dangling-refs.sh <deleted-basename>` for each deleted file. If it returns non-zero (e.g. `vite.config.ts` still imports `vite-plugin-graphql-codegen` after `codegen.yml` was deleted, or a page still imports a deleted hook/component), STOP and report error:
  ```text
  ERROR: Scaffold pruning left a dangling reference -- <file> was deleted but <other-file>
  still imports/references it. Remove the reference (or restore the file) before completing
  the build -- a dangling import is a functional break, not just leftover scope.
  ```

**Warning Validation (log warnings, but can proceed):**
- [ ] **Phase 2.5 execution**: If the prompt requires a new custom object (e.g. `Case__c`, `Asset__c`) but `platform-custom-object-generate` was never loaded:
  ```text
  WARNING: Phase 2.5 (Custom Objects) was skipped but the prompt requires a new custom object.
  Phase 3's grounding step will fail to find it in the org. Load platform-custom-object-generate
  and deploy the custom object before proceeding to Phase 3.
  ```

- [ ] **Phase 2 execution**: If Phase 2 was skipped but the prompt matches any keyword from the "Prompt Classification Keywords" table in SKILL.md (data features, navigation, authentication, integrations, or UI category):
  ```text
  WARNING: Phase 2 (Features) was skipped but prompt contains feature keywords.
  This may indicate a trigger detection failure. Generated UI may be missing
  required feature functionality. Consider re-running with Phase 2 included.
  ```

- [ ] **Phase 3 execution**: If Phase 3 was skipped but prompt mentions Salesforce objects, "GraphQL", "data", or "query":
  ```text
  WARNING: Phase 3 (Data Access) was skipped but prompt mentions Salesforce data.
  Generated UI may not connect to backend correctly. Verify data access is working.
  ```

- [ ] **Unused template scaffold left in place**: If Phase 2 was skipped and unused shadcn components remain under `src/components/ui/` (beyond what Phase 4's pages import), or if Phase 3 was skipped and `codegen.yml`/`.graphqlrc.yml`/`src/api/graphqlClient.ts`/`graphql:*` npm scripts/data-fetching hook stubs are still present:
  ```text
  WARNING: Phase 1's reactbasic template scaffold was not pruned after skipping Phase 2/Phase 3.
  Unused shadcn components, GraphQL tooling, or data-fetching stubs are still present even
  though the prompt limited scope. Remove them before presenting the build as complete --
  each leftover file is judged individually against the prompt's stated scope.
  ```

**Proceed to STEP 3 only if all Critical Validation checks pass (Phase 0, hosting target, Phase 4, Phase 7, no dangling references).**

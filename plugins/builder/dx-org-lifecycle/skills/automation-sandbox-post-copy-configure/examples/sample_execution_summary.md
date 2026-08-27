# Sample Execution Summary

The exact shape of the summary the skill writes to
`./post-copy-<mode>-summary.md` and prints when a run completes.
Grouped by phase, ordered by `ExecutionOrder` ascending. Every entry
from the input config appears exactly once.

---

## Post-Copy Configure Run — 5 entries applied against `dev-sandbox`

Config file: `./post-copy-config.json`
Target org: `dev-sandbox` (Sandbox — instance `NA123`)
Mode: apply (not dry-run)
Continue-on-error: true

### Phase 1 (ExecutionOrder = 1) — 3 entries, all parallel

Verified sobject for `OutboundMessages`: `WorkflowOutboundMessage`
(describe returned 200; `Metadata` compound field present).

| ConfigurationName | Label                | Object   | Sobject                    | Describe | Outcome            | HTTP |
|-------------------|----------------------|----------|----------------------------|----------|--------------------|------|
| OutboundMessages  | IR_Account_OBM_PROD  | Account  | WorkflowOutboundMessage    | 200      | SUCCESS            | 204  |
| OutboundMessages  | IR_Contact_OBM_PROD  | Contact  | WorkflowOutboundMessage    | 200      | SUCCESS            | 204  |
| OutboundMessages  | IR_Legacy_OBM        | Account  | WorkflowOutboundMessage    | 200      | SKIPPED_INACTIVE   | —    |

### Phase 2 (ExecutionOrder = 2) — 2 entries, all parallel

Verified sobject for `RemoteSiteSettings`: `RemoteProxy`
(describe returned 200; `Metadata` compound field present).

| ConfigurationName    | Label              | Object | Sobject     | Describe | Outcome     | HTTP |
|----------------------|--------------------|--------|-------------|----------|-------------|------|
| RemoteSiteSettings   | osbomwtst2         | —      | RemoteProxy | 200      | SUCCESS     | 204  |
| RemoteSiteSettings   | FlexNet_Middleware | —      | RemoteProxy | 200      | NOT_FOUND   | —    |

---

## Totals

| Outcome            | Count |
|--------------------|-------|
| SUCCESS            | 3     |
| NOT_FOUND          | 1     |
| SKIPPED_INACTIVE   | 1     |
| FAILED             | 0     |
| API_NOT_IDENTIFIED | 0     |

## Follow-ups

- `IR_Legacy_OBM` (OutboundMessages, Account) had `IsActive: false`
  in the config and was **not** PATCHed. The record on the target
  org is unchanged. If you intended to deactivate it on the target,
  flip `IsActive: true` in the config and re-run, or deactivate the
  parent WorkflowRule manually.
- `FlexNet_Middleware` (RemoteSiteSettings) was not found on the
  target org. Verify the `SiteName` matches an existing Remote Site
  Setting, or create the record via a metadata deployment before
  re-running the post-copy configure.

---

## Outcome vocabulary

| Outcome                | Meaning |
|------------------------|---------|
| `SUCCESS`              | HTTP 2xx from the PATCH; the record was updated and the read-back matched |
| `NOT_FOUND`            | Lookup returned zero rows; the record does not exist on the target org |
| `AMBIGUOUS`            | Lookup returned multiple rows after client-side filtering; refuse to PATCH |
| `API_NOT_IDENTIFIED`   | No candidate Tooling sobject passed the describe-verify gate for this `ConfigurationName` |
| `FIELD_MAP_UNKNOWN`    | Derived camelCase key was not present in the record's current `Metadata` block; refuse to PATCH the wrong field |
| `FAILED`               | HTTP 4xx (other than 404) or 5xx from the PATCH; include the Salesforce error code and message |
| `FAILED_VERIFY`        | PATCH returned 204 but the read-back value does not match the requested value |
| `SKIPPED_INACTIVE`     | `IsActive: false` in the config; entry was not PATCHed |
| `SKIPPED`              | Entry was skipped for another reason (dry-run, or a preceding phase failure with `continue-on-error = false`) |
| `DRY_RUN`              | Dry-run mode; the request that would be sent is captured but not executed |
| `DELETE_NOT_SUPPORTED` | Entry had `Fields.Action = "Delete"`; this skill does not delete records |
| `NOT_ATTEMPTED`        | Cancelled because an earlier failure aborted the run with `continue-on-error = false` |

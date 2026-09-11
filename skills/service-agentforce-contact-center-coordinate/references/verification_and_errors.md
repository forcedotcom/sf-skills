# Verification & Error Handling

## Live-verification polling strategy

A procured number must reach `Live` status on its `CommunicationChannelLine`
before a working voice channel can route calls.

`CommunicationChannelLine` is Tooling-API-only — it is not queryable via `sf data query`
(that returns `INVALID_TYPE: sObject type 'CommunicationChannelLine' is not supported`).
Query it via `sf api request rest .../tooling/query` instead, the same way
`scripts/resolve-channel-line.sh` does. The live-status field is `CodeStatus`
(not `Status__c`, which does not exist on this object), and it's looked up by `Code`
(not `Name`).

1. Query the line by code:
   `SELECT Id, Code, CodeStatus FROM CommunicationChannelLine WHERE Code = '<number>'`
2. If the record exists and `CodeStatus = 'Live'` → done.
3. Otherwise call `POST /numberStateReconcile` (see `number_management_api.md`) to
   force reconciliation.
4. Poll every **5 seconds**, up to **3 attempts** (≈15 seconds total), re-querying `CodeStatus`.
5. If still not `Live` after 3 attempts, warn the user and offer to wait/retry or proceed
   anyway (the channel may be created but not immediately operational).

`scripts/verify-number-live.sh` implements this loop and prints the final status.

## ChannelLine resolution (retry)

Immediately after procurement, `CommunicationChannelLine` may not yet exist because
records propagate asynchronously. `scripts/resolve-channel-line.sh` queries by `Code`
and retries up to 3 times (3s apart) before reporting failure.

## Error categories

| Category | Symptom | Handling |
|----------|---------|----------|
| Number fetch | `400` | Invalid country/type — re-collect selections |
| Number fetch | `500` | Retry after a few seconds |
| Procurement | `409` | Already procured — pick a different number |
| Sync | `404` | Number missing — re-run procurement |
| Sync | `500` | Retry after a few seconds |
| Channel create | duplicate `DeveloperName` | Derive a unique name |
| Channel create | invalid queue Id | Re-resolve the queue by name (Step 7) |

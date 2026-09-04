# Metadata Cache Generation Reference

Detailed commands for the metadata-cache generation steps of Stage 6 (KAM User Provisioning). Run entirely as the **admin** (`--target-org <admin>`).

> **No permission set required.** The generate Connect API bypasses metadata
> validation itself, so the previously-documented `SkipMetadataValidation`
> permission set (`PermissionsSkipVldBefMetadataGeneration` /
> `PermissionsGenerateLifeSciencesMetadata`) is NOT needed. Verified empirically:
> generation enqueues and the async job runs with no such permission set assigned.

> **Parent-link field:** the parent-link field on `LifeSciMobileMetadataRecord` is
> `ParentMobileMetadataRecId` (used below). If you need to confirm the schema on your
> org, describe the object:
>
> ```bash
> sf sobject describe --sobject LifeSciMobileMetadataRecord --target-org <admin> --json \
>   | grep -o '"name":"[^"]*"'
> ```

## Step A: Create LifeSciMobileMetadataRecord Prerequisite

Create a **parent** record and a **child** record linked to the LSC Custom Profile.
Set **both** records to `ValidationCompleted` — the generate API in Step B rejects the
call unless the **parent** record's `Status` is `ValidationCompleted` (not just the
child's). The generate API is called with the **parent** record ID.

Run as admin (`--target-org <admin>`):

```bash
sf apex run --target-org <admin> --json <<'EOF'
// Create parent record.
LifeSciMobileMetadataRecord parent = new LifeSciMobileMetadataRecord(
    IntegrationStatus = 'New',
    Status = 'New'
);
insert parent;

// Create child record for the LSC Custom Profile.
Profile pf = [SELECT Id FROM Profile WHERE Name = 'LSC Custom Profile'];
LifeSciMobileMetadataRecord child = new LifeSciMobileMetadataRecord(
    ParentMobileMetadataRecId = parent.Id,
    ProfileId = pf.Id,
    IntegrationStatus = 'New',
    Status = 'New'
);
insert child;

// Set BOTH parent and child to ValidationCompleted (the API requires the parent).
child.Status = 'ValidationCompleted';
update child;
parent.Status = 'ValidationCompleted';
update parent;

System.debug('Parent Id: ' + parent.Id);
System.debug('Child Id: ' + child.Id);
EOF
```

Extract the **parent record ID** from the debug log output — it is required as the `parentMetadataRecordId` in Step B.

---

## Step B: Call the Metadata Generate Connect API

Use the CLI's own authenticated REST client (`sf api request rest`) — it builds the
`Authorization` header correctly. A hand-rolled `curl` with the token from
`sf org display` fails with `INVALID_AUTH_HEADER` (401), even though the same token
works for CLI data queries — do NOT use raw curl for this endpoint.

### Build the request body

The body accepts `parentMetadataRecordId`, `apiVersion`, and `prefix`. Use `apiVersion`
`65.0` (verified working). Do NOT include `generateStandardTranslations` — the endpoint
rejects it with `JSON_PARSER_ERROR: Unrecognized field "generateStandardTranslations"`.

Write the body to a **project-local** relative file (never `/tmp` or any path outside the project); remove it after the call below:

```bash
cat > .lsc-mdgen-body.json <<'EOF'
{
  "parentMetadataRecordId": "<parentRecordId>",
  "apiVersion": "65.0",
  "prefix": "lsc4ce"
}
EOF
```

### Call the endpoint

Match the endpoint's `vXX.0` to the `apiVersion` in the body. Pass the body file with a
leading `@` (a bare path is sent as a literal string and triggers `JSON_PARSER_ERROR`):

```bash
sf api request rest \
  "/services/data/v65.0/connect/life-sciences/commercial/metadata/actions/generate" \
  --method POST \
  --body @.lsc-mdgen-body.json \
  --target-org <admin>
rm -f .lsc-mdgen-body.json
```

### Expected response

Success is a JSON message (HTTP 200), not 202:

```json
{ "message": "Task enqueued for metadata cache generation." }
```

Generation then runs asynchronously.

### Verify completion

Query both the parent and its child records (use your org's parent-link field name):

```bash
sf data query --query "SELECT Id, Status, IntegrationStatus, IntegrationErrorMessage, MetadataDocumentId, LastModifiedDate FROM LifeSciMobileMetadataRecord WHERE Id='<parentRecordId>' OR ParentMobileMetadataRecId='<parentRecordId>'" --target-org <admin> --json
```

The records move through intermediate states (`New → InProgress → Loading → Processing`)
and then transition to `Status='Active'`. **`Active` is the success state** — it means the
cache was generated; the child record's `MetadataDocumentId` is populated with the generated
document Id. The enqueue message only confirms the task was accepted; keep polling the query
above until `Status='Active'` before treating generation as complete.

> **How to report progress while polling.** The async job can take several minutes; that is
> normal. As long as the records are advancing through the intermediate states, simply tell
> the user the generation **is progressing and you are polling for it to become `Active`** —
> then poll again. Do NOT frame it as a timeout, a missed deadline, or "it didn't complete
> within the N-minute window" — there is no fixed window, and that phrasing wrongly implies
> something is wrong when the job is running normally. Only surface a problem if the records
> go to `Inactive` or stop advancing entirely (see below).

A transition to `Inactive` (or a record that stays unchanged with an unchanged
`LastModifiedDate`) is **not** success — the async job ran but produced no cache, or
never ran. Check Setup → Apex Jobs for the failed generation job and its error, and
inspect the record's `IntegrationStatus` / `IntegrationErrorMessage` fields for detail.

---

## Error handling

| Error | Resolution |
|-------|------------|
| `LifeSciMobileMetadataRecord` sObject not found | LSC packages not installed or API < v65.0 |
| `Field does not exist: ParentMobileMetadataRecId` (or similar) on compile | Describe the object to confirm the parent-link field name on your org and use the reported name |
| `INVALID_AUTH_HEADER` (401) from Connect API | You used raw `curl` — switch to `sf api request rest`, which builds the auth header correctly |
| `JSON_PARSER_ERROR: Unrecognized field "generateStandardTranslations"` | Remove that field from the body — only `parentMetadataRecordId`, `apiVersion`, and `prefix` are accepted |
| `JSON_PARSER_ERROR: Unexpected character ('/')` | `--body` got a literal path — prefix the file with `@` (`--body @.lsc-mdgen-body.json`) |
| `Profile 'LSC Custom Profile' not found` | Run Stage 2 (Starter Config Deploy) first — the child record needs the profile Id |
| `...isn't ValidationCompleted` from Connect API | Set the **parent** record's `Status` to `ValidationCompleted` (the API requires the parent, not just the child), then retry |
| HTTP 400 from Connect API | Check: parentMetadataRecordId valid, parent Status='ValidationCompleted', prefix='lsc4ce' |
| HTTP 404 from Connect API | Endpoint not available — verify API version v65.0+ and LSC packages |
| Records never leave their status (LastModifiedDate unchanged) | Async job didn't run — wait 30s; check Setup → Apex Jobs for failures |
| Records go to `Inactive` instead of `Active` | Generation ran but produced no cache — this is a failure, not success. Check Setup → Apex Jobs and the record's `IntegrationErrorMessage` for the cause |

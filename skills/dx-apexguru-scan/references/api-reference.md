# ApexGuru SFAP Scan API Reference

**Base URL (production):** `https://api.salesforce.com/platform/scale/v1-beta.1/apex-guru`

The host is chosen from the token's environment (prod/stage/dev); `stage.` and
`dev.api.salesforce.com` are internal-only. Customers on a prod org always hit
production. See `authentication.md` for the routing table.

**Auth:** `Authorization: Bearer <sfap_api JWT>`. Org comes from the token's
`tnk` claim (`core/<instance>/<orgId>`) — no org id in the request.

## Call 1 — Submit a scan

```http
POST /scan
  -H "Authorization: Bearer $JWT"
  -F "file=@project.zip;type=application/zip"
  [ -F "fastMode=true" ]     # optional: skip LLM-heavy fix generation → faster/cheaper
```

- Zip may use **any** layout — the API walks the whole archive and extracts
  every Apex file it finds. No `force-app/` tree at the root is required
  (`build-zip.sh` collects every `.cls`/`.trigger` under the project root,
  preserving relative paths).
- Limits: **200MB compressed**, **1GB decompressed**.
- Success → `202`:

```json
{ "scanId": "…", "status": "QUEUED" }
```

## Call 2 — Poll for result

```http
GET /scan/{scanId}
  -H "Authorization: Bearer $JWT"
```

- Status progression: `QUEUED → RUNNING → SUCCEEDED` (or `FAILED`).
- Poll ~every **15s**.
- On `SUCCEEDED`:

```json
{
  "scanId": "…",
  "status": "SUCCEEDED",
  "analysisMode": "static",          // "static" = source-only | "full" = org onboarded, runtime metrics
  "violationCount": 39,
  "filesScanned": 16,
  "violationBreakdown": { "SOQL_IN_LOOP": 15, "DML_IN_LOOP": 8, "GGD": 2 },
  "report": "<base64-encoded JSON array of violations>",
  "message": null
}
```

## The `report` field

Base64 → decode → **JSON array of violations**. Each violation carries:

- `rule` — the antipattern id (e.g. `SOQL_IN_LOOP`).
- `message` — human-readable description.
- `severity` — 1 (Critical) … 5 (Info).
- source location — `file` + `line`.
- suggested fix(es).
- help-doc `resources`.

`decode-report.js` tolerates field-name drift (`location`/`locations[0]`,
`fixes`/`suggestedFixes`, `severity`/`sev`) so minor API-shape changes don't break parsing.

## Status codes

| Code | Meaning |
|------|---------|
| 202 | Scan accepted (submit) |
| 200 | Poll OK |
| 400 | Malformed zip, no Apex inside, or over size limit |
| 401 | Bad / expired / wrong-env token |
| 403 | Scan owned by a different org (token `tnk` mismatch) |
| 404 | Unknown scanId, or archived (~30-day GC) |

See `error-handling.md` for resolutions.

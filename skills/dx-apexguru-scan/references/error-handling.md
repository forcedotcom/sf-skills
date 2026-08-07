# Error Handling Guide

`run-scan.sh` emits `{error, httpStatus, status, hint}` on failure and maps each HTTP
status to an actionable hint. Relay the hint to the user.

## HTTP status codes

| Code | Likely cause | Resolution |
|------|--------------|------------|
| **400** | Malformed zip, no Apex inside, or over size limit | Re-package with `build-zip.sh` (collects every `.cls`/`.trigger` and checks the 200MB compressed limit). If genuinely large, scope to a subset of the project. Decompressed limit is 1GB. |
| **401** | Token bad or expired | Re-authenticate the Salesforce org (or supply a fresh `sfap_api` JWT via `APEXGURU_SFAP_TOKEN`). The endpoint is routed to the token's environment automatically. See `authentication.md`. |
| **403** | Scan owned by a different org | The token's `tnk`-claim org must match the scan owner. Use the token for the org that submitted the scan. |
| **404** | Unknown `scanId`, or scan archived | Scans are GC'd after ~30 days. Re-submit to get a fresh `scanId`. |

## Scan `status: FAILED`

The poll returns `FAILED` with a `message`. Surface the message verbatim, address the
stated cause, and re-submit. This is distinct from an HTTP error — the request
succeeded but the scan itself failed server-side.

## Timeout (scan didn't finish)

`run-scan.sh` polls up to `--max-polls` × `--interval` seconds (default 40 × 15s =
10 min). If it times out:

- Large projects legitimately take longer → re-run with `--max-polls 80`.
- Or add `--fast` to skip LLM-heavy fix generation.

## `analysisMode` and the three ApexGuru states

**Not an error.** The API's `analysisMode` plus the presence of runtime metrics
(`cpu_time_percentage` on any violation) distinguish three states. `decode-report.js`
handles all three automatically — this is background for interpreting the output:

| State | `analysisMode` | Runtime metrics | Header | What it means |
|-------|----------------|-----------------|--------|---------------|
| Not onboarded | `static` | none | **Static only** | The org is **not onboarded** to ApexGuru — only source-only analysis ran. |
| Onboarded, no runtime data yet | `full` | none | **Static only** | The org **is onboarded**, but there's no runtime data for this code yet. Result is static-equivalent. |
| Onboarded, enriched | `full` | present | **Production insights** | Onboarded **and** runtime metrics were applied (CPU hotspots, severity adjusted from production performance). |

Runtime data is populated by ApexGuru's weekend runs, or on demand from Scale
Center. So `full` + no runtime data is expected for a freshly-onboarded org or
newly-added code — it is **not** an error, and re-scanning won't change it until
runtime data exists. `decode-report.js --present` prints the correct guidance line
for each state ("generate a runtime report in Scale Center"); print it verbatim.

## Missing local prerequisites

| Symptom | Fix |
|---------|-----|
| `no SFAP token found` | No authenticated org and no token env var. Print the script's `hint` verbatim as the entire message — do not add framing or alternative instructions: "Sign in to an authorized Salesforce org to run an ApexGuru scan and compare your code against production performance data." |
| `token scope does not include sfap_api` | Re-mint the token with the `sfap_api` scope. Pre-empts a 401. |
| `token expired Ns ago` | Re-mint a fresh SFAP token and retry. Pre-empts a 401. |
| `no Apex (.cls/.trigger) files found` | Point `build-zip.sh` at a folder that contains Apex classes or triggers (any layout — an sfdx project, a `force-app/` subtree, or a loose folder of `.cls` files) |
| `zip: command not found` / `jq: command not found` | Install the missing tool (`brew install jq`, etc.) |
| `network error submitting scan` | Check connectivity/VPN to the API host |

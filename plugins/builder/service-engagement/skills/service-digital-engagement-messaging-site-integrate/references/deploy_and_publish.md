# Deploy, Publish, and Verify

Once the home page JSON has been patched (and any missing LWR routes scaffolded), stage the bundle into the project's default package, deploy asynchronously with polling, resolve the community's `Network.Name`, publish, and smoke-test the guest URL.

## Stage into `force-app`

The retrieval directory is not directly deployable — the modified bundle must live inside the project's default package.

- **LWR**:

  ```bash
  cp -R <retrieve-dir>/digitalExperiences force-app/main/default/
  ```

- **Aura** — copy the bundle **and** the sibling site metadata (deploy fails without it):

  ```bash
  cp -R <retrieve-dir>/experiences force-app/main/default/
  cp <retrieve-dir>/sites/<siteName>.site-meta.xml force-app/main/default/sites/
  ```

  If `force-app/main/default/sites/` does not exist, create it first.

## Async deploy

Start the deploy in the background so subsequent polling can report progress:

```bash
sf project deploy start \
  --source-dir force-app/main/default \
  --target-org <org-alias> \
  --async
```

Capture the returned `job-id`.

## Poll to completion

Every 15 seconds, up to 10 minutes:

```bash
sf project deploy report \
  --job-id <job-id> \
  --target-org <org-alias>
```

Terminal statuses:

| Status | Meaning | Next action |
|--------|---------|-------------|
| `Succeeded` | Deploy complete | Proceed to publish |
| `SucceededPartial` | Some components skipped | Inspect the report; proceed if messaging component was among the succeeded set |
| `Failed` | Deploy failed | Surface the error and stop; do not publish |
| `Canceled` | User or platform canceled | Surface and stop |

If the timeout elapses without a terminal status, surface the last report and stop — publishing a partially deployed bundle can leave the site in an inconsistent state.

## Resolve `Network.Name`

`Network.Name` differs from the site `DeveloperName` in most orgs. Query by URL path prefix:

```bash
sf data query \
  --query "SELECT Name FROM Network WHERE UrlPathPrefix='<urlPath>' LIMIT 1" \
  --target-org <org-alias>
```

Capture the `Name` value.

## Publish

```bash
sf community publish \
  --name "<resolved-Name>" \
  --target-org <org-alias>
```

Publishing is asynchronous on the platform side even though the CLI call returns quickly — the guest smoke test may need a short delay before the new render is served.

## Guest URL smoke test

```bash
curl -sL -o /dev/null -w "%{http_code}" \
  https://<domainHostname>/<urlPath>
```

- `200` → the site is rendering; the messaging widget should be visible.
- `403` or `503` → publish likely still propagating. Retry once after 60 seconds before falling back to manual.
- Any other status → surface as failure and route to the manual fallback.

Report success only when the response is `200`. Do not claim the widget is "live on the site" based solely on the deploy report.

## Common failures

| Symptom | Likely cause | Resolution |
|---------|--------------|------------|
| Deploy fails with missing route type (LWR) | Template requires an unresolved route | Scaffold per `lwr_route_scaffolding.md` |
| Deploy fails with "site metadata not found" (Aura) | `<siteName>.site-meta.xml` not staged | Copy the sibling `.site-meta.xml` |
| `sf community publish` returns "community not found" | Used site `DeveloperName` instead of `Network.Name` | Re-run the `Network.Name` query |
| Guest URL stays 403 after retry | Public access disabled on the site | Enable public access in Experience Builder, or set `isExpSiteAuthMode: true` on the messaging component |
| Async deploy hangs indefinitely | Large bundle | Extend the polling window; do not silently succeed |

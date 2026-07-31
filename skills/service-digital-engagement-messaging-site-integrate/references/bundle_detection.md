# Bundle Detection — LWR vs Aura

Experience Cloud sites ship in two bundle shapes. Detect which one the target site uses by trying to retrieve each in turn and inspecting the resulting directory tree — the shape of the bundle uniquely identifies the framework.

## LWR retrieve

LWR (Lightning Web Runtime) sites live under `DigitalExperienceBundle`. Each site is stored as `site/<siteName>`.

```bash
sf project retrieve start \
  --metadata "DigitalExperienceBundle:site/<siteName>" \
  --target-org <org-alias> \
  --target-metadata-dir <retrieve-dir>
```

Success indicator — the following file exists:

```text
<retrieve-dir>/digitalExperiences/site/<siteName>/sfdc_cms__view/home/content.json
```

If present, the site is LWR. The bundle also contains sibling directories like `sfdc_cms__route/<RouteApiName>/`, `sfdc_cms__view/<viewId>/`, and `sfdc_cms__theme/`.

## Aura retrieve

Aura Experience sites live under `ExperienceBundle`.

```bash
sf project retrieve start \
  --metadata "ExperienceBundle:<siteName>" \
  --target-org <org-alias> \
  --target-metadata-dir <retrieve-dir>
```

Success indicator — the following file exists:

```text
<retrieve-dir>/experiences/<siteName>/views/homeGuestLayout.json
```

If present, the site is Aura. Look for a sibling `<siteName>.site-meta.xml` at `<retrieve-dir>/sites/<siteName>.site-meta.xml`. That file must be copied alongside the Aura bundle at deploy time.

## Neither

If retrieval succeeds for both but neither indicator file exists, the site is likely a Salesforce Tabs + Visualforce or Site.com site — the automated JSON patching path does not apply. Route to the manual Experience Builder fallback.

If both retrievals fail (site not found, permission denied), surface the error to the user and stop before attempting to patch anything.

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---------|--------------|------------|
| `INVALID_METADATA` for both retrievals | Site `DeveloperName` is wrong | Query the org: `sf data query --query "SELECT DeveloperName, UrlPathPrefix FROM Network"` |
| LWR retrieve succeeds but has no `content.json` | Site template is minimal or corrupt | Ask the user to open Experience Builder once so the platform materializes the default views |
| Aura retrieve succeeds but no `homeGuestLayout.json` | Guest access disabled on the site | Fall back to `homeLayout.json` for authenticated-only sites, but note that the messaging widget then requires `isExpSiteAuthMode: true` |
| Retrieve hangs | Large bundle | Use `--wait 30` and confirm with the user that retrieval is in-flight |

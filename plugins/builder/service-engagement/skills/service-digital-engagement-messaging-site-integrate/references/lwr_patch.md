# LWR — Patching themeLayout footer (site-wide widget placement)

Target files:

```text
digitalExperiences/site/<siteName>/sfdc_cms__themeLayout/*/content.json
```

The patch is applied by `scripts/patch_lwr_bundle.sh`. Invoke as:

```bash
scripts/patch_lwr_bundle.sh <site-dir> <deploymentName> <scrtUrl> <siteEndpoint>
```

where `<site-dir>` is the root of the retrieved bundle, e.g.:
`<retrieve-dir>/digitalExperiences/site/<siteName>`

Targeting the `sfdc_cms__themeLayout` footer (not `sfdc_cms__view/home/content.json`) places the widget as a site-wide floating overlay on every page — equivalent to the Aura `themeFooter` region placement.

## What the script does

1. Finds every `sfdc_cms__themeLayout/*/content.json` file under `<site-dir>`.
2. For each file, locates the `footer` region at `.contentBody.component.children[]` (where `.name == "footer"`).
3. Within that region, finds the existing `community_layout:section` wrapper (`.type == "component"`), then the inner slot region (`.type == "region"`) inside it — the inner region is where the widget goes (e.g. `footerSection`, `content`, etc.).
4. Recursively checks whether any descendant node already has `.definition == "experience_messaging:embeddedMessaging"`.
5. **If found** — updates that node's `.attributes` to the six standard values and **preserves the existing `.id`**:
   - `deploymentName`, `scrtUrl`, `siteEndpoint` (from CLI args)
   - `isExpSiteAuthMode: false`, `hideChatButtonOnLoad: "Default"`, `clientVersion: "WebV2"`
6. **If absent** — appends a fresh messaging component node directly into the inner region's `children[]`. The node has `"type": "component"` and `"definition": "experience_messaging:embeddedMessaging"`. No new `community_layout:section` wrapper is created — the section wrapper already exists in the footer region.
7. Handles the edge case where no wrapper section or inner region exists: falls back to appending directly to the footer's `children[]`.
8. Writes each file back with jq's 2-space indentation.

Re-running with the same arguments is a no-op (idempotent); re-running with new deployment coordinates refreshes the attributes in place without changing the component's `id`.

## How to verify

- Exactly one messaging node exists per themeLayout file:

  ```bash
  jq '[.. | select(.definition? == "experience_messaging:embeddedMessaging")] | length' \
    <site-dir>/sfdc_cms__themeLayout/<layoutName>/content.json
  # → 1
  ```

- The node lives inside the footer region's subtree:

  ```bash
  jq '
    .contentBody.component.children[]
    | select(.name? == "footer")
    | [.. | select(.definition? == "experience_messaging:embeddedMessaging")]
    | length
  ' <site-dir>/sfdc_cms__themeLayout/<layoutName>/content.json
  # → 1
  ```

- `clientVersion` is `"WebV2"` (not `"WebV1"`):

  ```bash
  jq '.. | select(.definition? == "experience_messaging:embeddedMessaging") | .attributes.clientVersion' \
    <site-dir>/sfdc_cms__themeLayout/<layoutName>/content.json
  # → "WebV2"
  ```

## Common failures

| Symptom | Cause |
|---------|-------|
| Widget only appears on the home page | Script was run against `sfdc_cms__view/home/content.json` instead of the themeLayout files |
| Widget appears on no pages after deploy | The footer region name differed from `"footer"` — inspect `.contentBody.component.children[].name` in the themeLayout |
| Two chat buttons after re-run | Detection did not descend into the full tree; the recursive `has_messaging` check avoids this |
| Deploy error "component not registered" | Used `componentName` (Aura shape) instead of `definition` (LWR shape) |
| `clientVersion: "WebV1"` — widget appears but Enhanced Web Chat fails | Script emitted `WebV1`; re-run the script (it defaults to `WebV2`) |

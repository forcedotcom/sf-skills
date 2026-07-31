# LWR — Patching `home/content.json`

Target file:

```text
digitalExperiences/site/<siteName>/sfdc_cms__view/home/content.json
```

The patch is applied by `scripts/patch_lwr_bundle.sh`. Invoke as:

```bash
scripts/patch_lwr_bundle.sh <content.json> <deploymentName> <scrtUrl> <siteEndpoint>
```

The manual JSON walk is preserved below in `manual_fallback.md` for cases where the script cannot run (jq missing, unusual template shape, etc.).

## What the script does

1. Reads `<content.json>` with `jq`.
2. Walks `.contentBody.component.children[]` and locates the region where `.type == "region"` and `.name == "content"`.
3. Recursively checks whether any descendant node already has `.definition == "experience_messaging:embeddedMessaging"`.
4. **If found** — updates that node's `.attributes` to the six standard values and **preserves the existing `.id`**:
   - `deploymentName`, `scrtUrl`, `siteEndpoint` (from CLI args)
   - `isExpSiteAuthMode: false`, `hideChatButtonOnLoad: "Default"`, `clientVersion: "WebV1"`
5. **If absent** — appends a fresh `community_layout:section` wrapper. The wrapper's `sectionConfig` is a **JSON string** (not a nested object), and the UUID inside `sectionConfig.columns[0].id` matches the child region's `id`. The nested region carries `id`, `name: "column"`, `title: "Column"`, `type: "region"`.
6. Writes the file back with jq's 2-space indentation.

Re-running with the same arguments is a no-op (idempotent); re-running with new deployment coordinates refreshes the attributes in place without changing the component's `id`.

## How to verify

- Exactly one messaging node exists:

  ```bash
  jq '[.. | select(.definition? == "experience_messaging:embeddedMessaging")] | length' <content.json>
  # → 1
  ```

- `sectionConfig` is a string, not an object:

  ```bash
  jq '.. | select(.definition? == "community_layout:section") | .sectionConfig | type' <content.json>
  # → "string"
  ```

- The section's `id` and the child region's `id` both appear inside the `sectionConfig` string.

## Common failures

| Symptom | Cause |
|---------|-------|
| Deploy succeeds but chat button never appears | `sectionConfig` was written as an object, not a JSON string |
| Two chat buttons on the page after re-run | Detection did not descend into nested `community_layout:section` wrappers; the script's recursive check avoids this |
| Deploy error "component not registered" | Used `componentName` (Aura shape) instead of `definition` (LWR shape) |
| Section renders but is empty | Nested region is missing `type: "region"` |

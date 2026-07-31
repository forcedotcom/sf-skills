# Aura — Patching `homeGuestLayout.json`

Target file:

```text
experiences/<siteName>/views/homeGuestLayout.json
```

The patch is applied by `scripts/patch_aura_bundle.sh`. Invoke as:

```bash
scripts/patch_aura_bundle.sh <homeGuestLayout.json> <deploymentName> <scrtUrl> <siteEndpoint>
```

Aura differs from LWR: component keys are `componentName` / `componentAttributes` (not `definition` / `attributes`), and there is no `dxpStyle` field. See `manual_fallback.md` if the script cannot run.

## What the script does

1. Reads `<homeGuestLayout.json>` with `jq`.
2. Iterates `.regions[]` and selects the first region whose `.components[]` is non-empty.
3. Recursively searches components (descending through every level of `forceCommunity:section` wrapper's `componentAttributes.regions[].components[]`) for `.componentName == "experience_messaging:embeddedMessaging"`.
4. **If found** — updates that node's `.componentAttributes` to the six standard values and **preserves the existing `.id`**:
   - `deploymentName`, `scrtUrl`, `siteEndpoint` (from CLI args)
   - `isExpSiteAuthMode: false`, `hideChatButtonOnLoad: "Default"`, `clientVersion: "WebV1"`
5. **If absent** — appends a fresh `forceCommunity:section` wrapper. The nested region carries `id`, `type: "region"`, `regionLabel: "Column"`, `regionName: "column"`, `renditionMap: {}`.
6. Writes the file back with jq's 2-space indentation.

Re-running is idempotent — the script updates in place rather than appending a second wrapper.

## How to verify

- Exactly one messaging node exists:

  ```bash
  jq '[.. | select(.componentName? == "experience_messaging:embeddedMessaging")] | length' <homeGuestLayout.json>
  # → 1
  ```

- All new IDs are UUIDs (no reused IDs from the fixture):

  ```bash
  jq '[.. | .id? // empty] | unique | length' <homeGuestLayout.json>
  ```

- The sibling `<siteName>.site-meta.xml` still exists in the retrieve directory — it must be copied at deploy time or the deploy will be rejected.

## Common failures

| Symptom | Cause |
|---------|-------|
| Deploy succeeds but chat button never appears | Wrote `definition` instead of `componentName` |
| Section deployed but empty | Nested region missing `type: "region"` or `renditionMap` |
| Deploy fails with "site metadata not found" | Sibling `<siteName>.site-meta.xml` was not copied alongside the `experiences/` bundle |
| Two chat buttons after re-run | Detection did not recurse through `forceCommunity:section` wrappers' nested regions |

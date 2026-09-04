---
name: field-service-mobile-branding-configure
description: "Derive a Field Service mobile app color scheme from a brand source (URL, hex codes, brand-guide paste, or color description), validate WCAG AA contrast in both light and dark mode, and apply the 14-field scheme to the org-default FieldServiceMobileSettings record. Trigger phrases include 'brand the mobile app', 'apply branding to Field Service mobile', 'update the mobile app colors', 'use this brand guide for the app', 'set the color scheme for the mobile app'. Do NOT use this skill for Dispatcher console / Gantt branding, Experience Cloud BrandingSet records, or scheduling policy colors — out of scope."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Field Service Mobile Branding

This skill ingests a brand source and produces a 14-field color scheme that gets applied to the org-default `FieldServiceMobileSettings` record (`DeveloperName='Field_Service_Mobile_Settings'`, `IsDefault=true`). Confirmation with the user happens between derivation and apply — never apply without approval.

> **Source:** This skill was authored by Chad Barbour and is mirrored from an
> upstream Field Service assets repository.
> Methodology, color tables, and contrast checks are unchanged from upstream — refresh from upstream when content changes there.

> **Runtime contract:** every org interaction in this skill is a single REST
> call dispatched through the Codey runtime (`execute_api` locally / the hosted
> Headless 360 MCP in shared surfaces). This skill has **no dependency on the
> execution environment** — no `sf` CLI, no shell scripts, no local Python, no
> temp files. Colors are derived and validated by the agent inline, then
> written with one sObject PATCH. Do not shell out.

## Input contract

One of:

- A website URL — fetch with `WebFetch`, extract dominant brand colors.
- A brand-guide paste or document — parse for hex codes and named colors.
- Direct hex codes — accept as-is.
- A color description (e.g. "we're a red and white company") — ask for at least one specific hex code or URL before proceeding.

See [reference/derivation-methodology.md](reference/derivation-methodology.md) for the four ingestion cases (A–D) in detail.

## Output

A 14-field color scheme written to the org-default `FieldServiceMobileSettings` record via a single sObject PATCH (`PATCH /services/data/vXX.0/sobjects/FieldServiceMobileSettings/{id}`). Color changes appear on devices after the metadata cache refreshes (default: 7 days, force-refreshable from app Settings).

## Workflow

### 1. Confirm the target org

**Before fetching the brand source**, confirm the org is reachable with a cheap auth probe — dispatch `SELECT Id FROM Organization LIMIT 1` (`GET /services/data/vXX.0/query`):

- 2xx with `totalSize=1` → the session token is live; continue.
- 401/403 → the org needs re-authentication. Surface that to the user and **stop**; do not proceed to apply.

Then ask: "Which org should I apply this to?" and wait for explicit confirmation before proceeding. Do not assume a default — even if the user mentioned an org name in their request, confirm it explicitly so there are no surprises. (The Codey runtime resolves the connected org; this skill does not manage org aliases.)

### 2. Ingest the brand source

Follow the cases (A–D) in [reference/derivation-methodology.md](reference/derivation-methodology.md). At the end of this step you should have two anchors:

- **Primary brand color** — for non-interactive surfaces and the navbar.
- **Secondary/interactive color** — for buttons, links, FAB.

### 3. Derive the full 14-field scheme

Apply the derivation rules in [reference/derivation-methodology.md](reference/derivation-methodology.md) and the field semantics in [reference/color-fields.md](reference/color-fields.md).

Hold the scheme in memory as a flat object whose keys match the 14 `FieldServiceMobileSettings` color fields. Use [examples/salesforce-default-scheme.json](examples/salesforce-default-scheme.json) as a template. Before continuing, self-check that all 14 fields are present and every value matches `^#[0-9A-Fa-f]{6}$` (6-digit hex, `#` prefix — 3-digit shorthand and missing `#` are invalid); fix any that don't before proposing.

### 4. Validate contrast (light + dark mode)

Compute the WCAG AA contrast ratio for each pair in [reference/contrast-validation.md](reference/contrast-validation.md) **inline** — this is deterministic arithmetic on the hex values you already hold, not an external tool. For each `#RRGGBB` pair:

1. Normalize each channel: `r = R/255, g = G/255, b = B/255`.
2. Linearize each channel: `c ≤ 0.03928 → c/12.92`, else `((c+0.055)/1.055)^2.4`.
3. Relative luminance: `L = 0.2126·r + 0.7152·g + 0.0722·b`.
4. Contrast ratio: `(L_lighter + 0.05) / (L_darker + 0.05)`.

Evaluate all 5 light-mode pairs and all 5 dark-mode pairs from [reference/contrast-validation.md](reference/contrast-validation.md); a pair PASSES at `≥ 4.5:1` (WCAG AA, normal text). Surface any FAIL pairs to the user with a suggested fix in step 5. Note that brand colors are fixed across both modes, so a passing light-mode scheme can still fail dark-mode pairs.

### 5. Present proposal & confirm

Show the user:

- A `Brand & Navigation` / `Contrast Scale` / `Feedback Colors` table of all 14 fields with their hex values and roles.
- The light-mode and dark-mode contrast results from step 4, with FAIL pairs flagged.
- The target org alias.

Ask the user to confirm before applying. Use the suggested fixes in [reference/contrast-validation.md](reference/contrast-validation.md) when proposing alternatives for failing pairs.

### 6. Apply to org

Apply only after the user has approved the proposal in step 5. Three REST calls:

1. **Confirm FLS (optional but recommended).** `GET /services/data/vXX.0/sobjects/FieldServiceMobileSettings/describe` and confirm each of the 14 color fields has `updateable: true`. A field with `updateable: false` (or a filtered describe) is the earliest signal the running user lacks edit access — surface that before attempting the PATCH.

2. **Resolve the org-default record.** `GET /services/data/vXX.0/query` with `SELECT Id FROM FieldServiceMobileSettings WHERE DeveloperName = 'Field_Service_Mobile_Settings' AND IsDefault = true LIMIT 1`. `totalSize = 0` means Field Service Mobile is not provisioned — surface the error and stop (see step 7). Otherwise take `records[0].Id`.

3. **Write the scheme.** `PATCH /services/data/vXX.0/sobjects/FieldServiceMobileSettings/{id}` with a flat JSON body of the 14 color fields. Merge semantics — only fields in the body are written. Do **not** send `IsDefault` (not updateable). A 204 (no body) is success; then GET the record back to confirm the values landed.

### 7. Report back

On success, print:

- `FieldServiceMobileSettings` record id.
- Timestamp of the update.
- Reminder that the metadata cache is 7 days by default — devices won't show the new scheme until the cache refreshes or a tech force-refreshes from app Settings.

If the apply fails because no `Field_Service_Mobile_Settings` record exists, surface the error and stop — Field Service Mobile may not be set up in the org. Direct the user to Setup → Field Service Mobile Settings to bootstrap the default record, then retry.

## Scope

**Generated automatically:**

- The full 14-field color scheme derived from one or two brand anchors plus optional brand neutrals and semantic colors.
- Light-mode and dark-mode WCAG AA contrast validation across 5 light-mode + 5 dark-mode pairs, computed inline by the agent.
- Apply via a single sObject PATCH against the org-default `FieldServiceMobileSettings` record.

**Out of scope:**

- Splash screen, profile tab background image, push notification icon — Setup-only uploads.
- Per-profile `FieldServiceMobileSettings` records (multi-config orgs) — this skill targets the single `IsDefault=true` record. If the org has multiple records, query first and confirm which `DeveloperName` to update.
- Dispatcher console / Gantt colors (`FSLQA__GanttPalette__c`).
- `BrandingSet` metadata (Experience Cloud / Lightning App branding — does not theme the FS mobile app).

## Files in this skill

- `reference/color-fields.md` — the 14 fields, descriptions, defaults, JSON schema.
- `reference/contrast-validation.md` — light + dark mode pair definitions, formulas, common fixes.
- `reference/derivation-methodology.md` — translating brand sources into a full scheme, edge cases.
- `examples/salesforce-default-scheme.json` — the out-of-the-box Salesforce purple/blue scheme.
- `examples/dark-blue-scheme.json` — Salesforce-themed dark blue scheme (also serves as a contrast-warnings example).

Contrast validation and scheme derivation are performed by the agent inline (see steps 3–4); there are no executable scripts in this skill. Org writes are single REST calls dispatched through the Codey runtime.

## Related skills

- `configure-field-service-mobile` — page layouts, permissions, and `FieldServiceSettings` toggles. This skill defers branding to here, and this skill defers structural mobile config to it.
- `fs-data-capture-form-deployer` — generates and deploys Data Capture Flow metadata.

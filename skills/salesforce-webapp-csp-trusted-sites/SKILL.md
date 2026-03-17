---
name: salesforce-webapp-csp-trusted-sites
description: Creates Salesforce CSP Trusted Site metadata when adding external domains. Use when the user adds an external API, CDN, image host, font provider, map tile server, or any third-party URL that the web application needs to load resources from — or when a browser console shows a CSP violation error.
---

# CSP Trusted Sites

## When to Use

Use this skill whenever the application references a new external domain that is not already registered as a CSP Trusted Site. This includes:

- Adding images from a new CDN (Unsplash, Pexels, Cloudinary, etc.)
- Loading fonts from an external provider (Google Fonts, Adobe Fonts)
- Calling a third-party API (Open-Meteo, Nominatim, Mapbox, etc.)
- Loading map tiles from a tile server (OpenStreetMap, Mapbox)
- Embedding iframes from external services (YouTube, Vimeo)
- Loading external stylesheets or scripts

Salesforce enforces Content Security Policy (CSP) headers on all web applications. Any external domain not registered as a CSP Trusted Site will be blocked by the browser, causing images to not load, API calls to fail, or fonts to be missing.

**Reference:** [Salesforce CspTrustedSite Object Reference](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_csptrustedsite.htm)

---

## Step 1 — Identify external domains

Scan the code for any URLs pointing to external domains. Common patterns:

- `fetch("https://api.example.com/...")` — API calls
- `<img src="https://images.example.com/..." />` — images
- `<link href="https://fonts.example.com/..." />` — stylesheets
- `url="https://tiles.example.com/{z}/{x}/{y}.png"` — map tiles
- `@import url("https://cdn.example.com/...")` — CSS imports

Extract the **origin** (scheme + host) from each URL. For example:
- `https://api.open-meteo.com/v1/forecast?lat=...` → `https://api.open-meteo.com`
- `https://images.unsplash.com/photo-123?w=800` → `https://images.unsplash.com`

---

## Step 2 — Check existing CSP Trusted Sites

Before creating a new file, check if the domain already has a CSP Trusted Site:

```bash
ls force-app/main/default/cspTrustedSites/
```

If the domain is already registered, no action is needed.

---

## Step 3 — Determine the CSP directive(s)

Map the resource type to the correct CSP `isApplicableTo*Src` fields. Read `implementation/metadata-format.md` for the full reference.

Quick reference:

| Resource type | CSP directive field(s) to set `true` |
|--------------|--------------------------------------|
| Images (img, background-image) | `isApplicableToImgSrc` |
| API calls (fetch, XMLHttpRequest) | `isApplicableToConnectSrc` |
| Fonts (.woff, .woff2, .ttf) | `isApplicableToFontSrc` |
| Stylesheets (CSS) | `isApplicableToStyleSrc` |
| Video / audio | `isApplicableToMediaSrc` |
| Iframes | `isApplicableToFrameSrc` |

**Always also set `isApplicableToConnectSrc` to `true`** — most resources also require connect-src for preflight/redirect handling.

---

## Step 4 — Create the metadata file

Read `implementation/metadata-format.md` and follow the instructions to create the `.cspTrustedSite-meta.xml` file.

---

## Step 5 — Verify

1. Confirm the file is valid XML and matches the expected schema.
2. Confirm the file is placed in `force-app/main/default/cspTrustedSites/`.
3. Confirm only the necessary `isApplicableTo*Src` fields are set to `true`.
4. Run from the web app directory:

```bash
cd force-app/main/default/webapplications/<appName> && npm run lint && npm run build
```

- **Lint:** MUST result in 0 errors.
- **Build:** MUST succeed.

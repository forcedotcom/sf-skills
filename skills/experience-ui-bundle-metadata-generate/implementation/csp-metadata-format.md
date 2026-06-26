# CSP Trusted Site Metadata — Implementation Guide

## File location

```
force-app/main/default/cspTrustedSites/{Name}.cspTrustedSite-meta.xml
```

The `cspTrustedSites/` directory must be a direct child of `force-app/main/default/`. Create it if it does not exist.

---

## File naming convention

The file name must match the `<fullName>` value inside the XML, with `.cspTrustedSite-meta.xml` appended.

| Domain | fullName | File name |
|--------|----------|-----------|
| `https://images.unsplash.com` | `Unsplash_Images` | `Unsplash_Images.cspTrustedSite-meta.xml` |
| `https://api.open-meteo.com` | `Open_Meteo_API` | `Open_Meteo_API.cspTrustedSite-meta.xml` |
| `https://tile.openstreetmap.org` | `OpenStreetMap_Tiles` | `OpenStreetMap_Tiles.cspTrustedSite-meta.xml` |

**Naming rules:**
- Use PascalCase with underscores separating words (e.g. `Google_Fonts_Static`)
- Name should describe the provider and resource type (e.g. `Pexels_Videos`, not just `Pexels`)
- Must be unique across the org
- Maximum 80 characters

---

## XML template

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{UNIQUE_NAME}</fullName>
    <description>{DESCRIPTION}</description>
    <endpointUrl>{HTTPS_ORIGIN}</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>{true|false}</isApplicableToConnectSrc>
    <isApplicableToFontSrc>{true|false}</isApplicableToFontSrc>
    <isApplicableToFrameSrc>{true|false}</isApplicableToFrameSrc>
    <isApplicableToImgSrc>{true|false}</isApplicableToImgSrc>
    <isApplicableToMediaSrc>{true|false}</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>{true|false}</isApplicableToStyleSrc>
</CspTrustedSite>
```

---

## Field reference

| Field | Required | Description |
|-------|----------|-------------|
| `fullName` | Yes | Unique API name. Must match the file name (before `.cspTrustedSite-meta.xml`). |
| `description` | Yes | Human-readable purpose. Start with "Allow access to..." |
| `endpointUrl` | Yes | The external origin (scheme + host). Must start with `https://`. No trailing slash. No path. |
| `isActive` | Yes | Always `true` for new entries. Set `false` to disable without deleting. |
| `context` | Yes | `All` (applies to all contexts). Other values: `LEX` (Lightning Experience only), `Communities` (Experience Cloud only), `VisualForce`. Use `All` unless there is a specific reason to restrict. |
| `isApplicableToConnectSrc` | Yes | `true` if the domain is called via `fetch()`, `XMLHttpRequest`, or WebSocket. |
| `isApplicableToFontSrc` | Yes | `true` if the domain serves font files (`.woff`, `.woff2`, `.ttf`, `.otf`). |
| `isApplicableToFrameSrc` | Yes | `true` if the domain is loaded in an `<iframe>` or `<object>`. |
| `isApplicableToImgSrc` | Yes | `true` if the domain serves images (`<img>`, CSS `background-image`, `<svg>`). |
| `isApplicableToMediaSrc` | Yes | `true` if the domain serves audio or video (`<audio>`, `<video>`). |
| `isApplicableToStyleSrc` | Yes | `true` if the domain serves CSS stylesheets (`<link rel="stylesheet">`). |

**Reference:** [CspTrustedSite — Salesforce Object Reference](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_csptrustedsite.htm)

---

## CSP directive mapping

| CSP header directive | Metadata field | What it allows |
|---------------------|----------------|----------------|
| `connect-src` | `isApplicableToConnectSrc` | `fetch()`, `XMLHttpRequest`, WebSocket, `EventSource` |
| `font-src` | `isApplicableToFontSrc` | `@font-face` sources |
| `frame-src` | `isApplicableToFrameSrc` | `<iframe>`, `<frame>`, `<object>`, `<embed>` |
| `img-src` | `isApplicableToImgSrc` | `<img>`, `background-image`, `favicon`, `<picture>` |
| `media-src` | `isApplicableToMediaSrc` | `<audio>`, `<video>`, `<source>`, `<track>` |
| `style-src` | `isApplicableToStyleSrc` | `<link rel="stylesheet">`, `@import` in CSS |

---

## Common external domains and their directives

Use this table as a quick reference when adding new domains:

| Domain | connect-src | font-src | frame-src | img-src | media-src | style-src |
|--------|:-----------:|:--------:|:---------:|:-------:|:---------:|:---------:|
| `https://images.unsplash.com` | true | false | false | true | false | false |
| `https://images.pexels.com` | true | false | false | true | false | false |
| `https://videos.pexels.com` | true | false | false | false | true | false |
| `https://fonts.googleapis.com` | true | false | false | false | false | true |
| `https://fonts.gstatic.com` | true | true | false | false | false | false |
| `https://avatars.githubusercontent.com` | true | false | false | true | false | false |
| `https://api.open-meteo.com` | true | false | false | false | false | false |
| `https://nominatim.openstreetmap.org` | true | false | false | false | false | false |
| `https://tile.openstreetmap.org` | true | false | false | true | false | false |
| `https://api.mapbox.com` | true | false | false | true | false | false |
| `https://cdn.jsdelivr.net` | true | false | false | false | false | true |
| `https://www.youtube.com` | false | false | true | true | false | false |
| `https://player.vimeo.com` | false | false | true | false | false | false |
| `https://res.cloudinary.com` | true | false | false | true | false | false |

---

## Complete examples

### Image CDN (Unsplash)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Unsplash_Images</fullName>
    <description>Allow access to Unsplash image content for static app media</description>
    <endpointUrl>https://images.unsplash.com</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>false</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>true</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>false</isApplicableToStyleSrc>
</CspTrustedSite>
```

### REST API (Open-Meteo weather)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Open_Meteo_API</fullName>
    <description>Allow access to Open-Meteo weather forecast API</description>
    <endpointUrl>https://api.open-meteo.com</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>false</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>false</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>false</isApplicableToStyleSrc>
</CspTrustedSite>
```

### Font provider (Google Fonts — requires two entries)

Google Fonts needs two CSP entries because CSS is served from `fonts.googleapis.com` and font files from `fonts.gstatic.com`:

**Entry 1: Stylesheets**
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Google_Fonts</fullName>
    <description>Allow access to Google Fonts stylesheets for custom typography</description>
    <endpointUrl>https://fonts.googleapis.com</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>false</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>false</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>true</isApplicableToStyleSrc>
</CspTrustedSite>
```

**Entry 2: Font files**
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Google_Fonts_Static</fullName>
    <description>Allow access to Google Fonts static files for font loading</description>
    <endpointUrl>https://fonts.gstatic.com</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>true</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>false</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>false</isApplicableToStyleSrc>
</CspTrustedSite>
```

### Map tiles (OpenStreetMap)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>OpenStreetMap_Tiles</fullName>
    <description>Allow access to OpenStreetMap tile images for map rendering</description>
    <endpointUrl>https://tile.openstreetmap.org</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>false</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>true</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>false</isApplicableToStyleSrc>
</CspTrustedSite>
```

### Geocoding API (Nominatim)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>OpenStreetMap_Nominatim</fullName>
    <description>Allow access to OpenStreetMap Nominatim geocoding API</description>
    <endpointUrl>https://nominatim.openstreetmap.org</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>false</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>false</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>false</isApplicableToStyleSrc>
</CspTrustedSite>
```

---

## Endpoint URL rules

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Must be HTTPS | `https://api.example.com` | `http://api.example.com` |
| No trailing slash | `https://api.example.com` | `https://api.example.com/` |
| No path | `https://api.example.com` | `https://api.example.com/v1/forecast` |
| No port (unless non-standard) | `https://api.example.com` | `https://api.example.com:443` |
| No wildcards | `https://api.example.com` | `https://*.example.com` |

Each subdomain needs its own entry. For example, `fonts.googleapis.com` and `fonts.gstatic.com` are separate entries.

---

## When a service requires multiple domains

Some services split resources across multiple subdomains. Create one CSP Trusted Site per domain:

| Service | Domains needed |
|---------|---------------|
| Google Fonts | `fonts.googleapis.com` (CSS) + `fonts.gstatic.com` (font files) |
| Mapbox | `api.mapbox.com` (tiles/API) + `events.mapbox.com` (telemetry) |
| YouTube embed | `www.youtube.com` (iframe) + `i.ytimg.com` (thumbnails) |
| Cloudflare CDN | `cdnjs.cloudflare.com` (scripts/CSS) |

---

## Troubleshooting CSP violations

If the browser console shows a CSP error like:

```
Refused to load the image 'https://example.com/image.png' because it violates
the following Content Security Policy directive: "img-src 'self' ..."
```

1. Extract the **blocked origin** from the URL (e.g. `https://example.com`).
2. Identify the **directive** from the error message (e.g. `img-src` → `isApplicableToImgSrc`).
3. Check if a CSP Trusted Site already exists for that origin.
4. If not, create one using this skill.
5. Deploy the metadata and refresh the page.

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Including a path in `endpointUrl` | Use only the origin: `https://api.example.com` |
| Adding trailing slash | Remove it: `https://api.example.com` not `https://api.example.com/` |
| Using HTTP instead of HTTPS | Salesforce requires HTTPS. If the service only supports HTTP, it cannot be added. |
| Forgetting `isApplicableToConnectSrc` | Most resources also need connect-src for redirects/preflight. Set to `true` by default. |
| One entry for multiple subdomains | Each subdomain needs its own file (e.g. `api.example.com` and `cdn.example.com` are separate) |
| File name doesn't match `fullName` | They must be identical (excluding the `.cspTrustedSite-meta.xml` extension) |

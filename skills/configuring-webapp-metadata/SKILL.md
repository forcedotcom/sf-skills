---
name: configuring-webapp-metadata
description: "Use this skill when configuring web application metadata structure, webapplication.json, or bundle organization. Covers WebApplication bundle layout, meta XML, build output directory, and webapplication.json settings."
---

# WebApplication Requirements

## Bundle Rules
- A WebApplication bundle must live under `webapplications/<AppName>/`
- The bundle must contain `<AppName>.webapplication-meta.xml`
- The metadata filename must exactly match the folder name
- A build output directory must exist and contain at least one file
- Default build output directory: `dist/`
- If `webapplication.json.outputDir` is set, it overrides `dist/`

Valid example:
```text
webapplications/
  MyApp/
    MyApp.webapplication-meta.xml
    webapplication.json
    dist/
      index.html
```

## Metadata XML
Required fields:
- `masterLabel`
- `version` (max 20 chars)
- `isActive` (boolean)

Optional fields:
- `description` (max 255 chars)

## webapplication.json
`webapplication.json` is optional.

Allowed top-level keys only:
- `outputDir`
- `routing`
- `headers`

### File Constraints
- Must be valid UTF-8 JSON
- Max size: 100 KB
- Root must be a non-empty object
- Never allow `{}`, arrays, or primitives as the root

### Path Safety
Applies to:
- `outputDir`
- `routing.fallback`

Reject:
- backslashes
- leading `/` or `\`
- `..` segments
- null or control characters
- globs: `*`, `?`, `**`
- `%`

All resolved paths must stay within the application bundle.

### outputDir
- Must be a non-empty string
- Must reference a subdirectory only
- Reject `.` and `./`
- The directory must exist in the bundle
- The directory must contain at least one file

### routing
- If present, must be a non-empty object
- Allowed keys only:
  - `rewrites`
  - `redirects`
  - `fallback`
  - `trailingSlash`
  - `fileBasedRouting`

#### routing.trailingSlash
- Must be one of: `"always"`, `"never"`, `"auto"`

#### routing.fileBasedRouting
- Must be a boolean

#### routing.fallback
- Must be a non-empty string
- Must satisfy Path Safety rules
- Target file must exist

#### routing.rewrites
- Must be a non-empty array
- Each item must be a non-empty object
- Allowed keys: `route`, `rewrite`
- `rewrite` must be a non-empty string
- `route`, if present, must be a non-empty string

Example:
```json
{
  "routing": {
    "rewrites": [
      { "route": "/app/:path*", "rewrite": "/index.html" }
    ]
  }
}
```

#### routing.redirects
- Must be a non-empty array
- Each item must be a non-empty object
- Allowed keys: `route`, `redirect`, `statusCode`
- `redirect` must be a non-empty string
- `route`, if present, must be a non-empty string
- `statusCode`, if present, must be one of: `301`, `302`, `307`, `308`

Example:
```json
{
  "routing": {
    "redirects": [
      { "route": "/old-page", "redirect": "/new-page", "statusCode": 301 }
    ]
  }
}
```

### headers
- If present, must be a non-empty array
- Each item must be a non-empty object
- Allowed keys: `source`, `headers`
- `headers` must be a non-empty array

Each header entry must contain:
- `key`: non-empty string
- `value`: non-empty string

Example:
```json
{
  "headers": [
    {
      "source": "/assets/**",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ]
}
```

## Never Suggest
- `{}` as the JSON root
- `"routing": {}`
- empty arrays
- empty array items such as `[{}]`
- `"outputDir": "."`
- `"outputDir": "./"`

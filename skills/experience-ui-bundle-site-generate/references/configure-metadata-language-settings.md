# Configure Metadata: DigitalExperience (sfdc_cms__languageSettings)

## Purpose
These configuration files create the `sfdc_cms__languageSettings` content record for a Digital Experience React Site. The record declares the set of languages the site supports and which one is the default locale. It is **always emitted** alongside `sfdc_cms__site` — a fresh site defaults to a single-language declaration (the resolved `defaultLocale`, typically `en_US`), and the same file is extended when the user requests additional languages. This is **authoring-only**: declared locales deploy cleanly, but locale-in-path routing does not resolve at request time until the platform runtime change lands.

## When to Use
Always. The skill emits `sfdc_cms__languageSettings` for every generated site, in addition to the required `sfdc_cms__site` content type. When the user does not request multiple languages, populate the file with a single-language default declaration using the resolved `defaultLocale` (default `en_US`). When the user requests additional languages/locales, extend the same file with the requested language entries. `sfdc_cms__site` and `sfdc_cms__languageSettings` are the only two content types this skill authors; no others are permitted.

## File Location
The languageSettings content lives in its own content-type directory inside the bundle, alongside `sfdc_cms__site`. The folder name (`languages`), `title` (`LanguageContent`), and `urlName` (`languagecontent`) are fixed Experience Builder auto-defaults — they are **not** derived from the site name and are **not** user-authored.

```text
digitalExperiences/site/{siteName}1/sfdc_cms__languageSettings/languages/_meta.json
digitalExperiences/site/{siteName}1/sfdc_cms__languageSettings/languages/content.json
```

## Generation Workflow
1. **Collect input.** Resolve the `defaultLocale` (ask the user, or default to `en_US`). If the user requests additional languages, collect for each: a display `label` and a `locale`. If the user does not request additional languages, no further input is needed — the file will contain a single-language declaration for the default locale only.
2. **Build the `languages` array.**
   - **Single-language default (no additional languages requested).** Emit exactly one entry using the resolved `defaultLocale`. Set `isActive: true`. Provide a human-readable `label` matching the locale (e.g. `English (United States)` for `en_US`).
   - **Multi-language (additional languages requested).** Emit one object per declared language, always including the default-locale entry as the first element. Set `isActive: true` for every language.
3. **Substitute and write both files.** Fill `{defaultLocale}` and each language object's fields into the templates, then write `_meta.json` and `content.json` into the folder above.
4. **Assert structural rules with `jq`.** Run the assertion below against the written `content.json`. If it exits non-zero, fix the declaration and rewrite the file. Rules 3–4 in the reference below cannot be checked offline — the deploy validation step covers them.

   ```bash
   jq -e '
     (.contentBody as $b | $b.languages | any(.locale == $b.defaultLocale))
       and (.contentBody as $b
             | $b.languages[]
             | select(.locale == $b.defaultLocale)
             | .isActive == true)
       and ((.contentBody.languages | map(.locale + "|" + .label) | unique | length)
             == (.contentBody.languages | length))
   ' content.json > /dev/null
   ```

   Enforces rules 1 (defaultLocale is declared), 2 (default-entry active), and 5 (locale+label uniqueness) below.

## Default Templates
Substitute values in `{braces}`. `apiName`, `type`, `path`, `title`, and `urlName` are fixed — do not parameterize them. The only variables are `{defaultLocale}` and the `languages[]` element fields (`{label}`, `{locale}`).

### `_meta.json`
```json
{
  "apiName": "languages",
  "type": "sfdc_cms__languageSettings",
  "path": "_settings"
}
```

### `content.json` — single-language default
Use this shape when the user has not requested additional languages. The single entry uses the resolved `defaultLocale`.

```json
{
  "type": "sfdc_cms__languageSettings",
  "title": "LanguageContent",
  "contentBody": {
    "defaultLocale": "{defaultLocale}",
    "languages": [
      {
        "isActive": true,
        "label": "{label}",
        "locale": "{defaultLocale}"
      }
    ]
  },
  "urlName": "languagecontent"
}
```

### `content.json` — multi-language
Use this shape when the user has requested additional languages. The example shows two languages — the default (`en_US`) and one additional locale. Emit one object per declared language; keys within each language object are alphabetically ordered.

```json
{
  "type": "sfdc_cms__languageSettings",
  "title": "LanguageContent",
  "contentBody": {
    "defaultLocale": "{defaultLocale}",
    "languages": [
      {
        "isActive": true,
        "label": "{label}",
        "locale": "{defaultLocale}"
      },
      {
        "isActive": true,
        "label": "{label}",
        "locale": "{locale}"
      }
    ]
  },
  "urlName": "languagecontent"
}
```

## Field Reference
- `defaultLocale` — the site's default locale; must match the `locale` of one of the declared `languages[]`.
- `locale` — a Salesforce-supported locale, either `xx` (e.g. `am`, `de`, `fr`) or `xx_YY` (e.g. `en_US`, `es_MX`, `zh_CN`). Support is org-dependent; deploy validation rejects unsupported values.
- `label` — human-readable display name for the language.
- `isActive` — only `true` is supported in authoring; every declared language must be active.

## Platform Validation Rules
Deploy rejects a languageSettings declaration that breaks any of these. Rules 1, 2, and 5 are enforced by the jq assertion in Step 4; rules 3–4 are enforced by deploy validation only:

1. The `defaultLocale` must appear as the `locale` of a declared language.
2. The default-locale language must be active (`isActive: true`).
3. Every `locale` must be a Salesforce-supported locale (org-dependent; deploy validation enforces).
4. The number of declared languages must not exceed the platform maximum.
5. The `locale` + `label` combination must be unique per workspace.

## Deploy Validation
After writing the files, validate the whole site bundle (languageSettings deploys within the existing `DigitalExperience` metadata type — no new type is needed):

```bash
sf project deploy validate --metadata Network CustomSite DigitalExperienceConfig DigitalExperienceBundle DigitalExperience --target-org ${usernameOrAlias}
```

A clean validate confirms the declaration satisfies every rule above — for the single-language default case as well as for multi-language declarations.

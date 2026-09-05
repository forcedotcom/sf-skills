# Configure Metadata: DigitalExperience (sfdc_cms__site)

## Purpose
These configuration files create **net-new, default** DigitalExperience content records (`sfdc_cms__site` type) for a Digital Experience React Site. They are not intended to edit or modify existing DigitalExperience content. Use these templates only when provisioning a brand-new React site.

The `appContainer: true` field in `content.json` is what makes this a React site rather than a standard LWR site.

### `appSpace`: always empty at initial site creation
The `appSpace` field **MUST be an empty string (`""`) at initial site creation**. This is the correct default even when the prompt supplies `appNamespace` and `appDevName`, and even when a `uiBundles/<Name>/src/` directory exists in the local project. Reason: the UIBundle metadata record must already be **deployed and active in the target org** before `appSpace` can reference it — attempting to bind `appSpace` to a not-yet-deployed UIBundle causes deploy validation to fail with `We couldn't find the <namespace>__<name> UIBundle`.

Populate `appSpace` with `"{appNamespace}__{appDevName}"` **only** in a later, follow-up update once you have confirmed (via `sf data query -q "SELECT DeveloperName FROM UIBundle WHERE DeveloperName = '{appDevName}'"`) that the UIBundle metadata record exists in the target org. This is a rare secondary operation, not part of initial scaffolding.

## File Location
Each DigitalExperience content-type directory contains only `_meta.json` and `content.json`. Two content types are always emitted inside the bundle: `sfdc_cms__site` (required) and `sfdc_cms__languageSettings` (defaults to a single `en_US` declaration; extended when the user requests additional languages — see [configure-metadata-language-settings.md](references/configure-metadata-language-settings.md)). No other content types are permitted.

```text
digitalExperiences/site/{siteName}1/sfdc_cms__site/{siteName}1/_meta.json
digitalExperiences/site/{siteName}1/sfdc_cms__site/{siteName}1/content.json
```

## Default Templates
### `_meta.json`
```json
{
  "apiName": "{siteName}1",
  "path": "",
  "type": "sfdc_cms__site"
}
```

### `content.json`
```json
{
  "type": "sfdc_cms__site",
  "title": "{siteName}",
  "urlName": "{siteUrlPathPrefix}",
  "contentBody": {
    "authenticationType": "AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED",
    "appContainer": true,
    "appSpace": ""
  }
}
```

**Note:** `appSpace` is always `""` at initial site creation. Do not substitute `{appNamespace}__{appDevName}` here even if those properties are resolved — that binding happens in a follow-up update after the UIBundle is deployed to the org (see the `appSpace` guidance in the Purpose section above).

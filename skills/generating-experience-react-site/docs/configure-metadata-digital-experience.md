# Configure Metadata: DigitalExperience (sfdc_cms__site)

## Purpose
These configuration files create **net-new, default** DigitalExperience content records (`sfdc_cms__site` type) for a Digital Experience React Site. They are not intended to edit or modify existing DigitalExperience content. Use these templates only when provisioning a brand-new React site.

The `appContainer: true` and `appSpace` fields in `content.json` are what make this a React site rather than a standard LWR site. The `appSpace` value follows the format `{namespace}__{developerName}` and must match a deployed `WebApplication` metadata record.

## File Location
The DigitalExperience directory contains only `_meta.json` and `content.json`. Do not create any directories other than `sfdc_cms__site` inside the bundle.

```
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
    "appSpace": "{appNamespace}__{appDevName}"
  }
}
```

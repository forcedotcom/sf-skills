# Configure Metadata: DigitalExperience (sfdc_cms__site)

## Purpose
These configuration files create **net-new, default** DigitalExperience content records (`sfdc_cms__site` type) for a Digital Experience React Site. They are not intended to edit or modify existing DigitalExperience content. Use these templates only when provisioning a brand-new React site.

The `appContainer: true` field in `content.json` is what makes this a React site rather than a standard LWR site. The `appSpace` field should **be left empty if the UIBundle metadata record does not already exist**. When the UIBundle exists, populate the `appSpace` value following the format `{namespace}__{developerName}` to match the deployed `UIBundle` metadata record.

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
    "appSpace": ""
  }
}
```

**Note:** Leave `appSpace` empty (`""`) if the UIBundle does not exist. If the UIBundle metadata record is already deployed, populate it with `"{appNamespace}__{appDevName}"`.

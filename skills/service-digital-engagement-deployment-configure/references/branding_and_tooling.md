# Branding Configuration via Tooling API

A BrandingSet with default values is **automatically created** when a Web deployment is created via Connect API. **Branding is only applicable for Web deployment types** — API and Mobile deployments do not support branding.

To override specific branding properties (colors, fonts, dimensions, images), use the Tooling API to update individual `BrandingSetProperty` records.

---

## Updating Branding Properties via Tooling API

Query the existing BrandingSet properties, then update specific values:

```bash
sf data query --query "SELECT Id, PropertyName, PropertyValue FROM BrandingSetProperty WHERE BrandingSetId IN (SELECT Id FROM BrandingSet WHERE DeveloperName='<BRANDING_SET_NAME>')" --target-org <org-alias> --tooling-api
```

Update a specific property:

```bash
sf data update record --sobject BrandingSetProperty --where "Id='<PROPERTY_ID>'" --values "PropertyValue='<NEW_VALUE>'" --target-org <org-alias> --tooling-api
```

---

## Available Branding Properties

### Colors (hex format)

| Property Name | Description | Default |
|--------------|-------------|---------|
| `primaryText` | Primary text color | `#2E2E2E` |
| `secondaryText` | Secondary text color | `#5C5C5C` |
| `alert` | Alert/error color | `#D72E2D` |
| `headerBackground` | Chat header background | `#FFFFFF` |
| `headerForeground` | Chat header text/icons | `#2E2E2E` |
| `conversationBodyBackground` | Chat body background | `#FFFFFF` |
| `userMessageBackground` | User message bubble background | `#2E2E2E` |
| `userMessageText` | User message text color | `#FFFFFF` |
| `userMessageLink` | User message link color | `#FFFFFF` |
| `agentMessageBackground` | Agent message bubble background | `#F3F3F3` |
| `agentMessageText` | Agent message text color | `#2E2E2E` |
| `agentMessageLink` | Agent message link color | `#0469C1` |
| `primaryButtonBackground` | Primary button background | `#2E2E2E` |
| `primaryButtonText` | Primary button text color | `#FFFFFF` |
| `inputOutline` | Input field border color | `#C9C9C9` |
| `inputFooterButton` | Input footer button color | `#2E2E2E` |
| `chatButton` | Chat launcher button color | `#2E2E2E` |
| `invitationText` | Chat invitation text color | `#FFFFFF` |
| `invitationDismissalButton` | Invitation dismiss button color | `#AEAEAE` |
| `citationsBackground` | Citations section background | `#FFFFFF` |
| `citationsText` | Citations text color | `#181818` |

### Dimensions (string values)

| Property Name | Description | Default |
|--------------|-------------|---------|
| `height` | Chat window height in pixels | `480` |
| `width` | Chat window width in pixels | `320` |

### Typography

| Property Name | Description | Default |
|--------------|-------------|---------|
| `font` | Font family | `Arial` |
| `baseFontSize` | Base font size | `Medium` |

### Images (URL values — leave empty for no image)

| Property Name | Description |
|--------------|-------------|
| `avatarImage` | Agent avatar image URL |
| `logoImage` | Company logo URL |
| `fabImage` | Floating action button image URL |
| `botImage` | Bot/AI avatar image URL |

---

## BrandingSet Association

The BrandingSet is automatically referenced in the `EmbeddedServiceConfig` XML via the `<branding>` field:

```xml
<branding>My_BrandingSet</branding>
```

This association is set up automatically during Connect API creation — no manual configuration needed.

---

## Constraints

- Image URLs must point to actual image files (not plain domain names) or be left empty
- Color values: hex format only (`#FFFFFF`)
- Dimension values are strings, not integers (`"480"` not `480`)
- `type` must be `es-messaging` for Embedded Messaging branding sets
- `baseFontSize` valid values: `Small`, `Medium`, `Large`
- Font values: `"Arial"`, `"Salesforce Sans"`, `"Georgia"`, `"Comic Sans MS"`, etc.
- Publishing (Connect API) is required after branding changes for them to take effect in the widget

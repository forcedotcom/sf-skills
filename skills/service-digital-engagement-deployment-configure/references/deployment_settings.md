# Embedded Messaging Deployment Settings Reference

Complete reference for all configurable settings on an `EmbeddedServiceConfig` metadata type.

---

## Deployment Types

| Type | Value | Use Case | Creation Method |
|------|-------|----------|-----------------|
| API | `API` | Headless integrations, no UI widget | Metadata API or Connect API |
| Mobile | `Mobile` | Native mobile app messaging | Metadata API or Connect API |
| Web | `Web` | Browser-based chat widget | Connect API (create), Metadata API (update) |

---

## Top-Level Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `masterLabel` | String | Yes | — | Deployment display name |
| `deploymentType` | Enum | Yes | — | `API`, `Mobile`, or `Web` |
| `deploymentFeature` | String | Yes | `EmbeddedMessaging` | Always `EmbeddedMessaging` |
| `clientVersion` | Enum | Yes | - | only applicable to Web deployment type. `WebV1`, `WebV2` |
| `areGuestUsersAllowed` | Boolean | Yes | `false` | Allow unauthenticated guest access |
| `isEnabled` | Boolean | Yes | `true` | Whether deployment is active |
| `shouldHideAuthDialog` | Boolean | Yes | `false` | Hide auth dialog from users |
| `site` | String | Web only | — | Experience Site name (format: `ESW_<name>_<timestamp>`) |
| `branding` | String | Web only | — | Reference to a `BrandingSet` name (Web deployments only) |
| `isTermsAndConditionsEnabled` | Boolean | No | `false` | Show T&C acceptance in pre-chat |
| `isTermsAndConditionsRequired` | Boolean | No | `false` | Require T&C acceptance before chatting |

---

## Embedded Service Messaging Channel (`<embeddedServiceMessagingChannel>`)

Links the deployment to a messaging channel and configures widget behavior. All boolean fields below are **required** in the XML.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `messagingChannel` | String | — | **Required.** Channel `channelPlatformKey` |
| `businessHours` | String | — | BusinessHours `businessHoursName` |
| `displayNameFormat` | String | — | Display name if pre-chat is enabled |
| `formula` | String | — | Condition logic expression referencing `sequence` numbers from `<embdMsgChannelInvitationConditions>` (e.g., `1 AND 2`, `1 OR 2 OR 3`). Required when `isInvitationEnabled` is `true`. Must be updated whenever conditions are added or removed |
| `isChatInvitationCustomizable` | Boolean | `false` | **Required.** Allow customizing chat invitation. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `isEnabled` | Boolean | `true` | **Required.** Whether messaging is enabled on this deployment |
| `isInvitationEnabled` | Boolean | `false` | **Required.** Enable proactive chat invitations. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `isSendInvtAllowedAfterAccept` | Boolean | `false` | **Required.** Allow invitations after previous one accepted. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `isSendInvtAllowedAfterReject` | Boolean | `false` | **Required.** Allow invitations after previous one rejected. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `shouldShowAgentforceTagline` | Boolean | `false` | **Required.** Show Agentforce branding tagline. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `shouldShowDeliveryReceipts` | Boolean | `false` | **Required.** Show message delivery receipts. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `shouldShowEmojiSelection` | Boolean | `false` | **Required.** Enable emoji picker. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `shouldShowReadReceipts` | Boolean | `false` | **Required.** Show read receipts. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `shouldShowTypingIndicators` | Boolean | `false` | **Required.** Show typing indicators. Can only be `true` for Web deployments; must be `false` for API/Mobile |
| `shouldStartNewLineOnEnter` | Boolean | `false` | **Required.** Enter key creates new line instead of sending. Can only be `true` for Web deployments; must be `false` for API/Mobile |

---

## Pre-Chat Forms (`<embeddedServiceForms>`)

Collects information from users before conversation starts. Applicable to all deployment types.

### Form Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `displayContext` | Enum | Yes | `Conversation` or `Session` |
| `isActive` | Boolean | Yes | Whether the form is active |
| `embeddedServiceFormFields` | Repeatable | Yes | Individual form fields (see below) |

### Form Field Structure (`<embeddedServiceFormFields>`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `displayOrder` | Integer | Yes | 0-based display position |
| `formField` | String | Yes | Parameter name — use `_` prefix for standard fields (e.g., `_FirstName`), exact `name` for custom fields |
| `formFieldType` | Enum | Yes | `Text`, `Email`, `Phone`, `Number` |
| `isHidden` | Boolean | Yes | Whether field is hidden from user (still collected) |
| `isRequired` | Boolean | Yes | Whether field must be filled |
| `messagingChannelParameterType` | Enum | Yes | `Standard` or `Custom` |

### Example

```xml
<embeddedServiceForms>
    <displayContext>Conversation</displayContext>
    <embeddedServiceFormFields>
        <displayOrder>0</displayOrder>
        <formField>_FirstName</formField>
        <formFieldType>Text</formFieldType>
        <isHidden>false</isHidden>
        <isRequired>true</isRequired>
        <messagingChannelParameterType>Standard</messagingChannelParameterType>
    </embeddedServiceFormFields>
    <embeddedServiceFormFields>
        <displayOrder>1</displayOrder>
        <formField>_Email</formField>
        <formFieldType>Email</formFieldType>
        <isHidden>false</isHidden>
        <isRequired>true</isRequired>
        <messagingChannelParameterType>Standard</messagingChannelParameterType>
    </embeddedServiceFormFields>
    <embeddedServiceFormFields>
        <displayOrder>2</displayOrder>
        <formField>CompanyName</formField>
        <formFieldType>Text</formFieldType>
        <isHidden>false</isHidden>
        <isRequired>false</isRequired>
        <messagingChannelParameterType>Custom</messagingChannelParameterType>
    </embeddedServiceFormFields>
    <isActive>true</isActive>
</embeddedServiceForms>
```

### Standard Pre-Chat Fields

Standard fields use a `_` prefix in the `formField` value:

| `formField` Value | Maps to `parameterType` | Typical Usage |
|-------------------|------------------------|---------------|
| `_FirstName` | `FirstName` | User identification |
| `_LastName` | `LastName` | User identification |
| `_Email` | `Email` | Follow-up and case creation |
| `_Subject` | `Subject` | Routing context |

### Custom Pre-Chat Fields

Custom fields use the exact `name` value from the channel's `customParameters` (no prefix). Custom fields must first be configured as `customParameters` on the messaging channel (via `service-digital-engagement-channel-configure`) before they can be referenced in the ESD form.

### ChoiceList (Dropdown) Fields

ChoiceList fields require a two-step deployment:
1. Create the `ChoiceList` metadata record
2. Assign it to the form field in the ESD

The ChoiceList field must reference a custom parameter `name` on the messaging channel.

---

## Branding

Referenced as a top-level `<branding>` field with the BrandingSet name.

```xml
<branding>My_BrandingSet</branding>
```

**Important**: A BrandingSet with defaults is auto-created by the Connect API when the deployment is created. To override specific properties (colors, fonts, dimensions), use the Tooling API — see `references/branding_and_tooling.md`.

---

### Invitation Condition Rules (`<embdMsgChannelInvitationConditions>`)

Available since API v58.0. Repeatable. Configures conditions under which the messaging widget proactively invites a visitor to chat. Applicable to Web deployments only.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sequence` | Integer | Yes | Position in `conditionLogic` expression (1-based) |
| `conditionType` | Enum | Yes | The type of condition to evaluate (e.g., `SecondsOnPage`, `SecondsOnSite`, `NumberOfPageViews`, `UrlMatch`, `CustomVariable`) |
| `operand` | Enum | Yes | Comparison operator (`Equals`, `NotEqual`, `Contains`, `NotContain`, `GreaterThan`, `LessThan`, `LessOrEqual`, `GreaterOrEqual`, `StartWith`) |
| `customVariableName` | String | No | Custom variable name (when `conditionType` references a CustomVariable) |
| `value` | String | Yes | The value to compare against |

### Example

```xml
<embdMsgChannelInvitationConditions>
    <sequence>1</sequence>
    <conditionType>UrlMatch</conditionType>
    <operand>Contains</operand>
    <value>/support</value>
</embdMsgChannelInvitationConditions>
<embdMsgChannelInvitationConditions>
    <sequence>2</sequence>
    <conditionType>SecondsOnPage</conditionType>
    <operand>GreaterThan</operand>
    <value>30</value>
</embdMsgChannelInvitationConditions>
```

---

## API Method Summary

| Operation | Metadata API | Tooling API | Connect API |
|-----------|-------------|-------------|-------------|
| Create any ESD (Web) | No | No | Yes |
| Create any ESD (API/Mobile) | Yes | No | Yes |
| Update ESD (top-level + channel settings) | Yes | Yes | No |
| Update ESD (forms/labels) | Yes | No | No |
| Create BrandingSet | No (auto-created by Connect API) | No | Yes |
| Update BrandingSet properties | No | Yes | No |
| Publish ESD | No | No | Yes |

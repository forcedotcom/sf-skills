# Style Tokens Reference

This document explains how to use `styleTokens` for theming and styling the AgentforceConversationClient.

## Overview

The `styleTokens` prop is the **ONLY** way to customize the appearance of the Agentforce conversation client. It accepts an object with style token keys and CSS values.

## Source of Truth

For the complete and always up-to-date list of all style tokens, see the tables below:

- ALL visual customization (colors, fonts, spacing, borders, radii, shadows) MUST go through the `styleTokens` prop. There are no exceptions.
- ONLY use token names listed in the tables below. Do NOT invent custom token names.
- NEVER apply styling via CSS files, `style` attributes, `className`, or wrapper elements. These approaches will not work and will be ignored by the component.
- If the user requests a visual change that does not map to a token below, inform them that the change is not supported by the current token set.

### Container

| Token name            | UI area themed              |
| --------------------- | --------------------------- |
| `fabBackground`       | FAB button background color |
| `containerBackground` | Chat container background   |
| `headerBackground`    | Header background           |
| `containerWidth`      | Chat container width        |
| `chatBorderRadius`    | Chat border radius          |
| `layoutMaxWidth`      | Layout max width            |

### Agentforce Header

| Token name                      | UI area themed                     |
| ------------------------------- | ---------------------------------- |
| `headerBlockBackground`         | Header block background            |
| `headerBlockBorderBottomWidth`  | Header border bottom width         |
| `headerBlockBorderBottomStyle`  | Header border bottom style         |
| `headerBlockBorderBottomColor`  | Header border bottom color         |
| `headerBlockBorderRadius`       | Header corner radius               |
| `headerBlockPaddingBlock`       | Header block padding (vertical)    |
| `headerBlockPaddingInline`      | Header inline padding (horizontal) |
| `headerBlockMinHeight`          | Header minimum height              |
| `headerBlockBrandingGap`        | Header branding area gap           |
| `headerBlockFontFamily`         | Header font family                 |
| `headerBlockFontWeight`         | Header title font weight           |
| `headerBlockFontSize`           | Header title font size             |
| `headerBlockLineHeight`         | Header title line height           |
| `headerBlockTextColor`          | Header text color                  |
| `headerBlockIconDisplay`        | Header icon display                |
| `headerBlockIconMargin`         | Header icon margin                 |
| `headerBlockIconColor`          | Header icon color                  |
| `headerBlockIconWidth`          | Header icon width                  |
| `headerBlockIconHeight`         | Header icon height                 |
| `headerBlockLogoMaxHeight`      | Header logo max height             |
| `headerBlockLogoMaxWidth`       | Header logo max width              |
| `headerBlockLogoMinWidth`       | Header logo min width              |
| `headerBlockButtonHeight`       | Header action button height        |
| `headerBlockButtonWidth`        | Header action button width         |
| `headerBlockButtonPadding`      | Header action button padding       |
| `headerBlockButtonBorderRadius` | Header action button border radius |
| `headerBlockHoverBackground`    | Header hover background            |
| `headerBlockActiveBackground`   | Header active background           |
| `headerBlockFocusBorder`        | Header focus border                |

### Agentforce Welcome Block

| Token name                          | UI area themed                   |
| ----------------------------------- | -------------------------------- |
| `welcomeBlockTextContainerWidth`    | Welcome text container width     |
| `welcomeBlockFontFamily`            | Welcome block font family        |
| `welcomeBlockFontSize`              | Welcome block font size          |
| `welcomeBlockFontWeight`            | Welcome block font weight        |
| `welcomeBlockLineHeight`            | Welcome block line height        |
| `welcomeBlockLetterSpacing`         | Welcome block letter spacing     |
| `welcomeBlockTextColor`             | Welcome block text color         |
| `welcomeBlockPaddingVertical`       | Welcome block vertical padding   |
| `welcomeBlockPaddingHorizontal`     | Welcome block horizontal padding |
| `welcomeBlockTextAnimationDuration` | Welcome text animation duration  |

### Agentforce Messages

| Token name                       | UI area themed                                          |
| -------------------------------- | ------------------------------------------------------- |
| `messageBlockBorderRadius`       | Message block border radius                             |
| `avatarDisplay`                  | Avatar display property (e.g. `block`, `none`)          |
| `hideMessageActions`             | Message actions display (e.g. `block`, `none` to hide)  |
| `hideCopyAction`                 | Copy action button display (e.g. `inline-flex`, `none`) |
| `messageBlockPaddingContainer`   | Message block container padding                         |
| `messageBlockFontSize`           | Message block font size                                 |
| `messageBlockBackgroundColor`    | Message block background (base)                         |
| `messageBlockInboundBorder`      | Inbound message border                                  |
| `messageBlockOutboundBorder`     | Outbound message border                                 |
| `messageBlockBodyWidth`          | Message block body width                                |
| `messageBlockPadding`            | Message block padding                                   |
| `messageBlockContainerMarginTop` | Message block container top margin                      |
| `messageBlockLineHeight`         | Message block line height                               |

### Avatar visibility (behavioral config)

Use `renderingConfig.showAvatar` to control whether avatars are rendered in message rows.

- `showAvatar: true` (default) renders avatars.
- `showAvatar: false` hides avatars by removing them from the DOM.

### Inbound message (agent → customer)

| Token name                                | UI area themed                    |
| ----------------------------------------- | --------------------------------- |
| `inboundMessgeTextColor`                  | Inbound message text color (base) |
| `messageBlockInboundBorderRadius`         | Inbound message border radius     |
| `messageBlockInboundBackgroundColor`      | Inbound message background        |
| `messageBlockInboundTextColor`            | Inbound message text color        |
| `messageBlockInboundWidth`                | Inbound message width             |
| `messageBlockInboundTextAlign`            | Inbound message text alignment    |
| `messageBlockInboundHoverBackgroundColor` | Inbound message hover background  |

### Outbound message (customer → agent)

| Token name                            | UI area themed                  |
| ------------------------------------- | ------------------------------- |
| `messageBlockOutboundBorderRadius`    | Outbound message border radius  |
| `messageBlockOutboundBackgroundColor` | Outbound message background     |
| `messageBlockOutboundTextColor`       | Outbound message text color     |
| `messageBlockOutboundWidth`           | Outbound message width          |
| `messageBlockOutboundMarginLeft`      | Outbound message left margin    |
| `messageBlockOutboundTextAlign`       | Outbound message text alignment |

### Agentforce Input

| Token name                                 | UI area themed                                 |
| ------------------------------------------ | ---------------------------------------------- |
| `messageInputPadding`                      | Message input container padding                |
| `messageInputFooterBorderColor`            | Message input footer border color              |
| `messageInputBorderRadius`                 | Message input border radius                    |
| `messageInputBorderTransitionDuration`     | Message input border transition duration       |
| `messageInputBorderTransitionEasing`       | Message input border transition easing         |
| `messageInputTextColor`                    | Message input text color                       |
| `messageInputTextBackgroundColor`          | Message input text background color            |
| `messageInputFooterBorderFocusColor`       | Message input footer focus border color        |
| `messageInputFocusShadow`                  | Message input focus shadow                     |
| `messageInputMaxHeight`                    | Message input max height                       |
| `messageInputLineHeight`                   | Message input line height                      |
| `messageInputTextPadding`                  | Message input text padding                     |
| `messageInputFontWeight`                   | Message input font weight                      |
| `messageInputFontSize`                     | Message input font size                        |
| `messageInputOverflowY`                    | Message input overflow Y                       |
| `messageInputScrollbarWidth`               | Message input scrollbar width                  |
| `messageInputScrollbarColor`               | Message input scrollbar color                  |
| `messageInputActionsWidth`                 | Message input actions width                    |
| `messageInputActionsPaddingRight`          | Message input actions right padding            |
| `messageInputFooterPlaceholderText`        | Message input placeholder text color           |
| `messageInputPlaceholderFontWeight`        | Placeholder font weight                        |
| `messageInputErrorTextColor`               | Message input error text color                 |
| `messageInputActionsGap`                   | Message input actions gap                      |
| `messageInputActionsPadding`               | Message input actions padding                  |
| `messageInputActionButtonSize`             | Message input action button size               |
| `messageInputActionButtonRadius`           | Message input action button radius             |
| `messageInputFooterSendButton`             | Message input send button color                |
| `messageInputSendButtonDisabledColor`      | Message input send button disabled color       |
| `messageInputActionButtonFocusBorder`      | Message input action button focus border       |
| `messageInputActionButtonActiveIconColor`  | Message input action button active icon color  |
| `messageInputActionButtonActiveBackground` | Message input action button active background  |
| `messageInputSendButtonIconColor`          | Message input send button icon color           |
| `messageInputFooterSendButtonHoverColor`   | Message input send button hover color          |
| `messageInputActionButtonHoverShadow`      | Message input action button hover shadow       |
| `messageInputFilePreviewPadding`           | Message input file preview padding             |
| `messageInputTextareaMaxHeight`            | Message input textarea max height              |
| `messageInputTextareaWithImageMaxHeight`   | Message input textarea max height (with image) |

### Agentforce Error Block

| Token name             | UI area themed               |
| ---------------------- | ---------------------------- |
| `errorBlockBackground` | Error block background color |

## Token Categories

Style tokens are organized by UI area:

- **Header** : background, text color, hover, active, focus, border, font family
- **Messages** : colors, padding, margins, border radius, fonts, body width
- **Inbound messages** : background, text color, width, alignment, hover
- **Outbound messages** : background, text color, width, alignment, margin
- **Input** : colors, borders, fonts, padding, buttons, scrollbar, textarea, actions
- **Error Component** : background

## Common Use Cases

### Change header color

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "#0176d3",
    headerBlockTextColor: "#ffffff",
  }}
/>
```

### Change message colors

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    messageBlockInboundBackgroundColor: "#4CAF50",
    messageBlockInboundTextColor: "#ffffff",
    messageBlockOutboundBackgroundColor: "#f5f5f5",
    messageBlockOutboundTextColor: "#333333",
  }}
/>
```

### Apply brand colors

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "#1a73e8",
    headerBlockTextColor: "#ffffff",
    messageBlockInboundBackgroundColor: "#1a73e8",
    messageBlockInboundTextColor: "#ffffff",
    messageInputFooterSendButton: "#1a73e8",
    messageInputFooterSendButtonHoverColor: "#1557b0",
  }}
/>
```

### Adjust spacing and fonts

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    messageInputFontSize: "16px",
    messageBlockBorderRadius: "12px",
    messageBlockPadding: "16px",
    messageInputPadding: "12px",
  }}
/>
```

## Important Notes

- You do NOT need to provide all tokens - only override the ones you want to change
- Token values are CSS strings (e.g., `"#FF0000"`, `"16px"`, `"bold"`)
- Invalid token names are silently ignored
- The component uses default values for any tokens you don't specify

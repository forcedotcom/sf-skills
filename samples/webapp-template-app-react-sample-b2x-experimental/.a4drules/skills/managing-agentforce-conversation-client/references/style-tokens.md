# Style Tokens Reference

This document explains how to use `styleTokens` for theming and styling the AgentforceConversationClient.

## Overview

The `styleTokens` prop is the **ONLY** way to customize the appearance of the Agentforce conversation client. It accepts an object with style token keys and CSS values.

## Source of Truth

For the complete and always up-to-date list of all 60+ style tokens, see:

**[@salesforce/agentforce-conversation-client on npm](https://www.npmjs.com/package/@salesforce/agentforce-conversation-client)**

The npm package README contains the definitive documentation with all available style tokens.

## Token Categories

Style tokens are organized by UI area:

- **Header** (7 tokens): background, text color, hover, active, focus, border, font family
- **Messages** (10 tokens): colors, padding, margins, border radius, fonts, body width
- **Inbound messages** (5 tokens): background, text color, width, alignment, hover
- **Outbound messages** (5 tokens): background, text color, width, alignment, margin
- **Input** (33 tokens): colors, borders, fonts, padding, buttons, scrollbar, textarea, actions

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

## How to Find Token Names

1. Check the [@salesforce/agentforce-conversation-client npm package](https://www.npmjs.com/package/@salesforce/agentforce-conversation-client) for the complete list of all tokens

2. Token names follow a pattern:
   - `headerBlock*` - Header area
   - `messageBlock*` - Message bubbles
   - `messageBlockInbound*` - Messages from customer to agent
   - `messageBlockOutbound*` - Messages from agent to customer
   - `messageInput*` - Input field and send button

## Important Notes

- You do NOT need to provide all tokens - only override the ones you want to change
- Token values are CSS strings (e.g., `"#FF0000"`, `"16px"`, `"bold"`)
- Invalid token names are silently ignored
- The component uses default values for any tokens you don't specify

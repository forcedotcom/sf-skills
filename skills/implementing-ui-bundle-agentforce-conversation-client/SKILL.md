---
name: implementing-ui-bundle-agentforce-conversation-client
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the task involves adding or modifying a chat widget, chatbot, or conversational AI. Use this skill when the user asks to add, embed, integrate, configure, style, or remove an agent, chatbot, chat widget, conversation client, or AI assistant. Covers styling (colors, fonts, spacing, borders), layout (inline vs floating, width, height, dimensions), and props (agentId, agentLabel, headerEnabled, showHeaderIcon, showAvatar, styleTokens). Activate when files under uiBundles/*/src/ import AgentforceConversationClient or when adding any chat or agent functionality to a page. Never create a custom agent, chatbot, or chat widget component."
metadata:
  author: ACC Components
  version: 1.0.1
  package: "@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client"
  sdk-package: "@salesforce/agentforce-conversation-client"
  last-updated: 2025-04-01
---

# Managing Agentforce Conversation Client

**HARD CONSTRAINT:** NEVER create a custom agent, chatbot, or chat widget component. ALL such requests MUST be fulfilled by importing and rendering the existing `<AgentforceConversationClient />` from `@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client` as documented below. If a requirement is unsupported by this component's props, state the limitation — do not improvise an alternative.

## Prerequisites

Before the component will work, the following Salesforce settings must be configured by the user. ALWAYS call out the prequisites after successfully embedding the agent.

**Cookie settings:**

- Setup → My Domain → Disable "Require first party use of Salesforce cookies"

**Trusted domains (required only for local development):**

- Setup → Session Settings → Trusted Domains for Inline Frames → Add your domain
  - Local development: `localhost:<PORT>` (e.g., `localhost:3000`)

## Instructions

### Step 1: Check if component already exists

Search for existing usage across all app files (not implementation files):

```bash
grep -r "AgentforceConversationClient" --include="*.tsx" --include="*.jsx" --exclude-dir=node_modules
```

**Important:** Look for React files that import and USE the component (for example, shared shells, route components, or feature pages). Do NOT open files named `AgentforceConversationClient.tsx` or `AgentforceConversationClient.jsx` - those are the component implementation.

**If found:** Read the file and check the current `agentId` value.

**Agent ID validation rule (deterministic):**

- Valid only if it matches: `^0Xx[a-zA-Z0-9]{15}$`
- Meaning: starts with `0Xx` and total length is 18 characters

**Decision:**

- If `agentId` matches `^0Xx[a-zA-Z0-9]{15}$` and user wants to update other props → Go to Step 4 (update props)
- If `agentId` is missing, empty, or does NOT match `^0Xx[a-zA-Z0-9]{15}$` → Continue to Step 2 (need real ID)
- If not found → Continue to Step 2 (add new)

### Step 2: Get agent ID

If component doesn't exist or has an invalid placeholder value, ask user for their Salesforce agent ID.

Treat these as placeholder/invalid values:

- `"0Xx..."`
- `"Placeholder"`
- `"YOUR_AGENT_ID"`
- `"<USER_AGENT_ID_18_CHAR_0Xx...>"`
- Any value that does not match `^0Xx[a-zA-Z0-9]{15}$`

Skip this step if:

- Component exists with a real agent ID
- User only wants to update styling or dimensions

### Step 3: Canonical import strategy

Use this import path by default in app code:

```tsx
import { AgentforceConversationClient } from "@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client";
```

If the package is not installed, install it:

```bash
npm install @salesforce/ui-bundle-template-feature-react-agentforce-conversation-client
```

Only use a local relative import (for example, `./components/AgentforceConversationClient`) when the user explicitly asks to use a patched/local component in that app.

Do not infer import path from file discovery alone. Prefer one consistent package import across the codebase.

### Step 4: Add or update component

Determine which sub-step applies:

- Component NOT found in Step 1 → go to **4a (New installation)**
- Component found in Step 1 → go to **4b (Update existing)**

#### 4a — New installation

1. If the user already specified a target file, use that file. Otherwise, ask the user: _"Which file should I add the AgentforceConversationClient to?"_ Do NOT proceed until a target file is confirmed.
2. Read the target file to understand its existing imports and TSX structure.
3. Add the import at the top of the file, alongside existing imports. Use the canonical package import from Step 3:

```tsx
import { AgentforceConversationClient } from "@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client";
```

4. Insert the `<AgentforceConversationClient />` TSX into the component's return block. Place it as a sibling of existing content — do NOT wrap or restructure existing TSX. Use the real `agentId` obtained in Step 2:
**Example:**
```tsx
<AgentforceConversationClient agentId="0Xx8X00000001AbCDE" />
```

5. Do NOT add any other code (wrappers, layout components, new functions) unless the user explicitly requests it.

#### 4b — Update existing

1. Read the file identified in Step 1.
2. Locate the existing `<AgentforceConversationClient ... />` TSX element.
3. Apply **only** the changes the user requested. Rules:
   - **Add** new props that the user asked for.
   - **Change** prop values the user asked to update.
   - **Preserve** every prop and value the user did NOT mention — do not remove, reorder, or reformat them.
   - **Never** delete the component and recreate it.
4. If the current `agentId` is a placeholder (failed validation in Step 1) and a real agent ID was obtained in Step 2, replace the placeholder value:

```tsx
// Before
<AgentforceConversationClient agentId="Placeholder" />

// After
<AgentforceConversationClient agentId="0Xx8X00000001AbCDE" />
```

5. If the current `agentId` is already valid and the user did not ask to change it, leave it as-is.

### Step 5: Configure props

**Available props (use directly on component):**

- `agentId` (string, required) - Salesforce agent ID
- `inline` (boolean) - `true` for inline mode, omit for floating
- `width` (number | string) - e.g., `420` or `"100%"`
- `height` (number | string) - e.g., `600` or `"80vh"`
- `headerEnabled` (boolean) - Show/hide header
- `styleTokens` (object) - For all styling (colors, fonts, spacing)
- `salesforceOrigin` (string) - Auto-resolved
- `frontdoorUrl` (string) - Auto-resolved
- `agentLabel` (string) - header title for agent

**Examples:**

Floating mode (default):

```tsx
<AgentforceConversationClient agentId="0Xx..." />
```

Inline mode with dimensions:

```tsx
<AgentforceConversationClient agentId="0Xx..." inline width="420px" height="600px" />
```

Adding or updating agent label:

```tsx
<AgentforceConversationClient agentId="0Xx..." agentLabel="<dummy-agent-label>" />
```

**Styling rules (mandatory):**

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

Styling with styleTokens:

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "#0176d3",
    headerBlockTextColor: "#ffffff",
    messageBlockInboundBackgroundColor: "#4CAF50",
  }}
/>
```

**For complex patterns,** consult `references/examples.md` for:

- Sidebar containers and responsive sizing
- Dark theme and advanced theming combinations
- Inline without header, calculated dimensions
- Complete host component examples


**Common mistakes to avoid:** Consult `references/constraints.md` for:

- Invalid props (containerStyle, style, className)
- Invalid styling approaches (CSS files, style tags)
- What files NOT to edit (implementation files)

## Common Issues

If component doesn't appear or authentication fails, see `references/troubleshooting.md` for:

- Agent activation and deployment
- Localhost trusted domains
- Cookie restriction settings

---
name: implementing-webapp-agentforce-conversation-client
description: "Adds or modifies AgentforceConversationClient in React apps (.tsx or .jsx files). Use when user says \"add chat widget\", \"embed agentforce\", \"add agent\", \"add chatbot\", \"integrate conversational AI\", or asks to change colors, dimensions, styling, or configure agentId, width, height, inline mode, or styleTokens for travel agent, HR agent, employee agent, or any Salesforce agent chat."
metadata:
  author: ACC Components
  version: 1.0.0
  package: "@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental"
  sdk-package: "@salesforce/agentforce-conversation-client"
  last-updated: 2025-03-18
---

# Managing Agentforce Conversation Client

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
import { AgentforceConversationClient } from "@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental";
```

If the package is not installed, install it:

```bash
npm install @salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental
```

Only use a local relative import (for example, `./components/AgentforceConversationClient`) when the user explicitly asks to use a patched/local component in that app.

Do not infer import path from file discovery alone. Prefer one consistent package import across the codebase.

### Step 4: Add or update component

**For new installations:**

Add to the target React component file using the canonical package import:

```tsx
import { Outlet } from "react-router";
import { AgentforceConversationClient } from "@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental";

export default function AgentChatHost() {
  return (
    <>
      <Outlet />
      <AgentforceConversationClient agentId="0Xx..." />
    </>
  );
}
```

**Fallback note:** Use a local relative import only when the user explicitly requests patched/local component usage in that app.

**For updates:**

Read the file where component is used and modify only the props that need to change. Preserve all other props. Never delete and recreate.

**Replacing placeholder values:**

If the component has a placeholder agentId (e.g., `agentId="Placeholder"` or `agentId="0Xx..."`), replace it with the real agent ID:

```tsx
// Before (template with placeholder)
<AgentforceConversationClient agentId="Placeholder" />

// After (with real agent ID)
<AgentforceConversationClient agentId="0Xx8X00000001AbCDE" />
```

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

**Examples:**

Floating mode (default):

```tsx
<AgentforceConversationClient agentId="0Xx..." />
```

Inline mode with dimensions:

```tsx
<AgentforceConversationClient agentId="0Xx..." inline width="420px" height="600px" />
```

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

**For styling:** For ANY color, font, or spacing changes, use `styleTokens` prop only. See `references/style-tokens.md` for complete token list and examples.

**Common mistakes to avoid:** Consult `references/constraints.md` for:

- Invalid props (containerStyle, style, className)
- Invalid styling approaches (CSS files, style tags)
- What files NOT to edit (implementation files)

## Common Issues

If component doesn't appear or authentication fails, see `references/troubleshooting.md` for:

- Agent activation and deployment
- Localhost trusted domains
- Cookie restriction settings

## Prerequisites

Before the component will work, the following Salesforce settings must be configured by the user:

**Cookie settings:**

- Setup → My Domain → Disable "Require first party use of Salesforce cookies"

**Trusted domains (required only for local development):**

- Setup → Session Settings → Trusted Domains for Inline Frames → Add your domain
  - Local development: `localhost:<PORT>` (e.g., `localhost:3000`)

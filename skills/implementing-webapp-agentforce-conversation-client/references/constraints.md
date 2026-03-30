# Constraints and Anti-Patterns

This document lists all invalid approaches and patterns to avoid when working with AgentforceConversationClient.

## Never Edit Implementation Files

**CRITICAL: Only edit files where the component is USED, never the component implementation itself.**

- ✅ **DO edit**: Any React files that import and use `<AgentforceConversationClient />` (for example, shared shells, route components, or feature pages)
- ❌ **DO NOT edit**: AgentforceConversationClient.tsx, AgentforceConversationClient.jsx, index.tsx, index.jsx, or any files inside:
  - `node_modules/@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental/src/`
  - `packages/template/feature/feature-react-agentforce-conversation-client/src/`
  - `src/components/AgentforceConversationClient.tsx` (patched templates)
  - Any path containing `/components/AgentforceConversationClient.`

**If you're reading a file named `AgentforceConversationClient.tsx`, you're in the wrong place. Stop and search for the USAGE instead.**

## Invalid Props

AgentforceConversationClient uses a flat prop API and does NOT accept these props:

- ❌ `containerStyle` - Use `width` and `height` props directly instead
- ❌ `style` - Use `styleTokens` for theming
- ❌ `className` - Not supported
- ❌ Any standard React div props - This wraps an embedded iframe, not a div

**Why:** The component is a wrapper around an embedded iframe using Lightning Out 2.0. Standard React styling props don't apply.

## Invalid Styling Approaches

**CRITICAL: For ALL styling, theming, branding, or color changes - ONLY use `styleTokens` prop.**

Never use these approaches:

- ❌ Creating CSS files (e.g., `agent-styles.css`, `theme.css`)
- ❌ Creating `<style>` tags or internal stylesheets
- ❌ Using `style` attribute on the component
- ❌ Using `className` prop
- ❌ Inline styles
- ❌ CSS modules
- ❌ Styled-components or any CSS-in-JS libraries

**Why:** The component controls its own internal styling through the `styleTokens` API. External CSS cannot reach into the embedded iframe.

## Invalid Implementation Approaches

Never do these:

- ❌ Create custom chat UIs from scratch
- ❌ Use third-party chat libraries (socket.io, WebSocket libraries, etc.)
- ❌ Call `embedAgentforceClient` directly from `@salesforce/agentforce-conversation-client`
- ❌ Build custom WebSocket or REST API chat implementations

**Why:** The AgentforceConversationClient component is the official wrapper that handles authentication, Lightning Out 2.0 initialization, and all communication with Salesforce agents. Custom implementations will not work.

## Invalid Update Patterns

When updating an existing component:

- ❌ Delete and recreate the component
- ❌ Remove all props and start over
- ❌ Copy the entire component to a new file

**Why:** This loses configuration, introduces errors, and creates unnecessary diffs. Always update props in place.

## Examples

### ❌ Wrong - Using containerStyle

```tsx
<AgentforceConversationClient agentId="0Xx..." containerStyle={{ width: 420, height: 600 }} />
```

### ✅ Correct - Using width/height directly

```tsx
<AgentforceConversationClient agentId="0Xx..." width="420px" height="600px" />
```

### ❌ Wrong - Creating CSS file

```css
/* agent-styles.css */
.agentforce-chat {
  background: red;
  color: white;
}
```

```tsx
import "./agent-styles.css";

<AgentforceConversationClient className="agentforce-chat" />;
```

### ✅ Correct - Using styleTokens

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "red",
    headerBlockTextColor: "white",
  }}
/>
```

### ❌ Wrong - Creating style tag

```tsx
<>
  <style>{`.agent-chat { background: blue; }`}</style>
  <AgentforceConversationClient agentId="0Xx..." />
</>
```

### ✅ Correct - Using styleTokens

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "blue",
  }}
/>
```

### ❌ Wrong - Editing implementation file

Reading or editing: `node_modules/@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental/src/AgentforceConversationClient.tsx`

### ✅ Correct - Editing usage file

Reading and editing: usage files where the component is imported and used (for example, `src/app.tsx`, a route component, or a feature page)

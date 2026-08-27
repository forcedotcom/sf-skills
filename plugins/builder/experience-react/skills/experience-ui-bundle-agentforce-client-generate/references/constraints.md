# Constraints and Anti-Patterns

This document lists all invalid approaches and patterns to avoid when working with AgentforceConversationClient.

## Never Edit Implementation Files

**CRITICAL: Only edit files where the component is USED, never the component implementation itself.** This applies to both React and Angular.

- **DO edit**: Files that import and use the element (for example, shared shells/layouts, route components, or feature pages) — React `*.tsx`/`*.jsx`, Angular host `*.html` + its `*.ts`
- **DO NOT edit (React)**: `AgentforceConversationClient.tsx`, `AgentforceConversationClient.jsx`, `index.tsx`, `index.jsx`, or any files inside:
  - `node_modules/@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client/src/`
  - `packages/template/feature/feature-react-agentforce-conversation-client/src/`
  - `src/components/AgentforceConversationClient.tsx` (patched templates)
  - Any path containing `/components/AgentforceConversationClient.`
- **DO NOT edit (Angular)**: the feature component/service implementation:
  - `node_modules/@salesforce/ui-bundle-template-feature-angular-agentforce-conversation-client/`
  - `packages/template/feature/feature-angular-agentforce-conversation-client/src/`
  - `conversation.ts`, `conversation.html`, `agentforce-embed.service.ts`
  - `__inherit__conversation.ts` (the composed-in feature copy — import it, don't edit it)

**If you're reading the component implementation (`AgentforceConversationClient.tsx`, `conversation.ts`, or `agentforce-embed.service.ts`), you're in the wrong place. Stop and search for the USAGE instead.**

## Invalid Props

The Agentforce client uses a flat prop/input API and does NOT accept these:

- `containerStyle` - Use `width` and `height` directly instead
- `style` - Use `styleTokens` for theming
- `className` (React) / `class` (Angular) - Not supported for theming
- Any standard host-element/div props - This wraps an embedded iframe, not a div

**Why:** The component is a wrapper around an embedded iframe using Lightning Out 2.0. Standard framework styling props don't apply.

## Angular-Specific Anti-Patterns

- Forgetting to add `AgentforceConversationClientComponent` to the host `@Component({ imports: [...] })` — the `<app-agentforce-conversation-client>` element then renders nothing (Angular does not error on an unknown/unregistered element by default in this template setup).
- Passing booleans/numbers/objects as bare attributes: `inline`, `headerEnabled="false"`, `styleTokens="..."`. These become strings. Use property binding: `[inline]="true"`, `[headerEnabled]="false"`, `[styleTokens]="{ ... }"`.
- Editing `__inherit__conversation.ts` (the composed feature copy) — treat it as the component source and import from it, never modify it.

## Invalid Styling Approaches

**CRITICAL: For ALL styling, theming, branding, or color changes - ONLY use `styleTokens` prop.**

Never use these approaches:

- Creating CSS files (e.g., `agent-styles.css`, `theme.css`)
- Creating `<style>` tags or internal stylesheets
- Using `style` attribute on the component
- Using `className` prop
- Inline styles
- CSS modules
- Styled-components or any CSS-in-JS libraries

**Why:** The component controls its own internal styling through the `styleTokens` API. External CSS cannot reach into the embedded iframe.

## Invalid Implementation Approaches

Never do these:

- Create custom chat UIs from scratch
- Use third-party chat libraries (socket.io, WebSocket libraries, etc.)
- Call `embedAgentforceClient` directly from `@salesforce/agentforce-conversation-client`
- Build custom WebSocket or REST API chat implementations

**Why:** The AgentforceConversationClient component is the official wrapper that handles authentication, Lightning Out 2.0 initialization, and all communication with Salesforce agents. Custom implementations will not work.

## Invalid Update Patterns

When updating an existing component:

- Delete and recreate the component
- Remove all props and start over
- Copy the entire component to a new file

**Why:** This loses configuration, introduces errors, and creates unnecessary diffs. Always update props in place.

## Examples

### Wrong - Using containerStyle

```tsx
<AgentforceConversationClient agentId="0Xx..." containerStyle={{ width: 420, height: 600 }} />
```

### Correct - Using width/height directly

```tsx
<AgentforceConversationClient agentId="0Xx..." width="420px" height="600px" />
```

### Wrong - Creating CSS file

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

### Correct - Using styleTokens

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "red",
    headerBlockTextColor: "white",
  }}
/>
```

### Wrong - Creating style tag

```tsx
<>
  <style>{`.agent-chat { background: blue; }`}</style>
  <AgentforceConversationClient agentId="0Xx..." />
</>
```

### Correct - Using styleTokens

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "blue",
  }}
/>
```

### Wrong - Editing implementation file

Reading or editing: `node_modules/@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client/src/AgentforceConversationClient.tsx`

### Correct - Editing usage file

Reading and editing: usage files where the component is imported and used (for example, `src/app.tsx`, a route component, or a feature page)

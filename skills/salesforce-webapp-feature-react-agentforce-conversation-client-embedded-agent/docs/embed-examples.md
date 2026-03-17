# Embed examples

Detailed examples for configuring the Agentforce Conversation Client. All examples use the `AgentforceConversationClient` React component; the underlying `embedAgentforceClient` API accepts the same `agentforceClientConfig` shape.

> **Important:** Every example requires an `agentId`. The component will not render without one. There is no default agent. Replace `"0Xx000000000000AAA"` in every example with the user's actual agent ID.

---

## Floating mode (default rendering mode)

A floating chat widget appears in the bottom-right corner. It starts minimized and expands when the user clicks it. Floating is the default rendering mode — no `renderingConfig` is needed — but `agentId` is always required.

### Minimal

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
  }}
/>
```

### Explicit floating

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    renderingConfig: { mode: "floating" },
  }}
/>
```

### Floating with theming

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    renderingConfig: { mode: "floating" },
    styleTokens: {
      headerBlockBackground: "#032D60",
      headerBlockTextColor: "#ffffff",
    },
  }}
/>
```

---

## Inline mode

The chat renders inside the parent container at a specific size. Use this when the chat should be part of the page layout rather than an overlay.

### Fixed pixel dimensions

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    renderingConfig: { mode: "inline", width: 420, height: 600 },
  }}
/>
```

### CSS string dimensions

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    renderingConfig: { mode: "inline", width: "100%", height: "80vh" },
  }}
/>
```

### Inline filling a sidebar

```tsx
<div style={{ display: "flex", height: "100vh" }}>
  <main style={{ flex: 1 }}>{/* App content */}</main>
  <aside style={{ width: 400 }}>
    <AgentforceConversationClient
      agentforceClientConfig={{
        agentId: "0Xx000000000000AAA",
        renderingConfig: { mode: "inline", width: "100%", height: "100%" },
      }}
    />
  </aside>
</div>
```

---

## Theming

Use `styleTokens` to customize colors. Tokens are passed directly to the Agentforce client.

### Brand-colored header

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    styleTokens: {
      headerBlockBackground: "#0176d3",
      headerBlockTextColor: "#ffffff",
    },
  }}
/>
```

### Full theme example

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    styleTokens: {
      headerBlockBackground: "#0176d3",
      headerBlockTextColor: "#ffffff",
      messageBlockInboundColor: "#0176d3",
    },
  }}
/>
```

### Dark theme example

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    styleTokens: {
      headerBlockBackground: "#1a1a2e",
      headerBlockTextColor: "#e0e0e0",
      messageBlockInboundColor: "#16213e",
    },
  }}
/>
```

---

## Full layout example

Shows the recommended pattern: agent ID passed directly, single render in the app layout.

```tsx
import { Outlet } from "react-router";
import { AgentforceConversationClient } from "@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental";

export default function AppLayout() {
  return (
    <>
      <Outlet />
      <AgentforceConversationClient
        agentforceClientConfig={{
          agentId: "0Xx000000000000AAA",
          styleTokens: {
            headerBlockBackground: "#0176d3",
            headerBlockTextColor: "#ffffff",
          },
        }}
      />
    </>
  );
}
```

---

## Using the low-level `embedAgentforceClient` API

The React component wraps `embedAgentforceClient`. If you need the raw API (e.g. in a non-React context), the config shape is the same — `agentId` is still required:

```ts
import { embedAgentforceClient } from "@salesforce/agentforce-conversation-client";

const { loApp, chatClientComponent } = embedAgentforceClient({
  container: "#agentforce-container",
  salesforceOrigin: "https://myorg.my.salesforce.com",
  agentforceClientConfig: {
    agentId: "0Xx000000000000AAA",
    renderingConfig: { mode: "floating" },
    styleTokens: {
      headerBlockBackground: "#0176d3",
      headerBlockTextColor: "#ffffff",
    },
  },
});
```

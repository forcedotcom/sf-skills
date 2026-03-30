# Additional Examples

Essential examples for common patterns and combinations. All use flat props API.

---

## Layout Patterns

### Sidebar Chat

```tsx
export default function DashboardWithChat() {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <main style={{ flex: 1 }}>{/* Main content */}</main>
      <aside style={{ width: 400 }}>
        <AgentforceConversationClient agentId="0Xx..." inline width="100%" height="100%" />
      </aside>
    </div>
  );
}
```

### Full Page Chat

```tsx
export default function SupportPage() {
  return (
    <div>
      <h1>Customer Support</h1>
      <AgentforceConversationClient agentId="0Xx..." inline width="100%" height="600px" />
    </div>
  );
}
```

---

## Size Variations

### Responsive sizing

```tsx
<AgentforceConversationClient agentId="0Xx..." inline width="100%" height="80vh" />
```

### Calculated dimensions

```tsx
<AgentforceConversationClient agentId="0Xx..." inline width="500px" height="calc(100vh - 100px)" />
```

---

## Theming Combinations

### Brand theme with custom sizing

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  inline
  width="500px"
  height="700px"
  styleTokens={{
    headerBlockBackground: "#0176d3",
    headerBlockTextColor: "#ffffff",
    messageBlockInboundBackgroundColor: "#0176d3",
    messageBlockInboundTextColor: "#ffffff",
    messageInputFooterSendButton: "#0176d3",
  }}
/>
```

### Dark theme

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  styleTokens={{
    headerBlockBackground: "#1a1a1a",
    headerBlockTextColor: "#ffffff",
    messageBlockInboundBackgroundColor: "#2d2d2d",
    messageBlockInboundTextColor: "#ffffff",
    messageBlockOutboundBackgroundColor: "#3a3a3a",
    messageBlockOutboundTextColor: "#f0f0f0",
  }}
/>
```

### Inline without header

```tsx
<AgentforceConversationClient
  agentId="0Xx..."
  inline
  width="100%"
  height="600px"
  headerEnabled={false}
  styleTokens={{
    messageBlockBorderRadius: "12px",
  }}
/>
```

---

## Complete Host Component Example

```tsx
import { Outlet } from "react-router";
import { AgentforceConversationClient } from "@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client";

export default function AgentChatHost() {
  return (
    <>
      <Outlet />
      <AgentforceConversationClient
        agentId="0Xx..."
        styleTokens={{
          headerBlockBackground: "#0176d3",
          headerBlockTextColor: "#ffffff",
        }}
      />
    </>
  );
}
```

---

For complete style token reference, see `references/style-tokens.md` or `node_modules/@salesforce/agentforce-conversation-client/README.md`.

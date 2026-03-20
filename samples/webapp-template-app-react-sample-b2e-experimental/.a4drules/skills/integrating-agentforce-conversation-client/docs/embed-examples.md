# Embed examples (flat-prop API)

All examples use `AgentforceConversationClient` with flat props.

> `agentId` is required in practice. Use this placeholder pattern in examples: `"<USER_AGENT_ID_18_CHAR_0Xx...>"`.

---

## Floating mode (default)

```tsx
<AgentforceConversationClient agentId="<USER_AGENT_ID_18_CHAR_0Xx...>" />
```

## Explicit floating

```tsx
<AgentforceConversationClient agentId="<USER_AGENT_ID_18_CHAR_0Xx...>" />
```

---

## Inline mode

### Fixed pixels

```tsx
<AgentforceConversationClient
  agentId="<USER_AGENT_ID_18_CHAR_0Xx...>"
  inline
  width={420}
  height={600}
/>
```

### CSS string size

```tsx
<AgentforceConversationClient
  agentId="<USER_AGENT_ID_18_CHAR_0Xx...>"
  inline
  width="100%"
  height="80vh"
/>
```

### Inline sidebar

```tsx
<div style={{ display: "flex", height: "100vh" }}>
  <main style={{ flex: 1 }}>{/* App content */}</main>
  <aside style={{ width: 400 }}>
    <AgentforceConversationClient
      agentId="<USER_AGENT_ID_18_CHAR_0Xx...>"
      inline
      width="100%"
      height="100%"
    />
  </aside>
</div>
```

---

## Theming

```tsx
<AgentforceConversationClient
  agentId="<USER_AGENT_ID_18_CHAR_0Xx...>"
  styleTokens={{
    headerBlockBackground: "#0176d3",
    headerBlockTextColor: "#ffffff",
    messageBlockInboundColor: "#0176d3",
  }}
/>
```

---

## Inline with header enabled

```tsx
<AgentforceConversationClient
  agentId="<USER_AGENT_ID_18_CHAR_0Xx...>"
  inline
  width={420}
  height={600}
  headerEnabled
/>
```

`headerEnabled` defaults to `true` for floating mode, and you can use it in inline mode to add/remove the header.

---

## Full layout example

```tsx
import { Outlet } from "react-router";
import { AgentforceConversationClient } from "@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental";

export default function AppLayout() {
  return (
    <>
      <Outlet />
      <AgentforceConversationClient
        agentId="<USER_AGENT_ID_18_CHAR_0Xx...>"
        styleTokens={{
          headerBlockBackground: "#0176d3",
          headerBlockTextColor: "#ffffff",
        }}
      />
    </>
  );
}
```

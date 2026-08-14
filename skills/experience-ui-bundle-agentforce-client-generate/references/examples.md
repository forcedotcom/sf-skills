# Additional Examples

Essential examples for common patterns and combinations. All use the flat props/inputs API.

**Framework note:** The examples below are shown in React (JSX). For Angular, use the `<app-agentforce-conversation-client>` element with property binding for non-string values — see the [Angular Equivalents](#angular-equivalents) section at the end. Translation rule:

| React | Angular |
|-------|---------|
| `<AgentforceConversationClient agentId="0Xx..." />` | `<app-agentforce-conversation-client agentId="0Xx..." />` |
| `inline` | `[inline]="true"` |
| `headerEnabled={false}` | `[headerEnabled]="false"` |
| `width="100%"` (string) | `width="100%"` (string attr is fine) |
| `styleTokens={{ ... }}` | `[styleTokens]="{ ... }"` |

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

## Angular Equivalents

Angular apps register the standalone component in the host and use property binding for booleans/numbers/objects.

### Host component registration

```ts
import { Component } from "@angular/core";
import { RouterOutlet } from "@angular/router";
import { AgentforceConversationClientComponent } from "@salesforce/ui-bundle-template-feature-angular-agentforce-conversation-client";

@Component({
  selector: "app-layout",
  imports: [RouterOutlet, AgentforceConversationClientComponent],
  templateUrl: "./app-layout.html",
})
export class AppLayoutComponent {}
```

```html
<!-- app-layout.html -->
<router-outlet />
<app-agentforce-conversation-client agentId="0Xx..." />
```

### Inline in a sidebar

```html
<aside style="width: 400px">
  <app-agentforce-conversation-client agentId="0Xx..." [inline]="true" width="100%" height="100%" />
</aside>
```

### Full page

```html
<h1>Customer Support</h1>
<app-agentforce-conversation-client agentId="0Xx..." [inline]="true" width="100%" height="600px" />
```

### Theming (object binding)

```html
<app-agentforce-conversation-client
  agentId="0Xx..."
  [inline]="true"
  width="500px"
  height="700px"
  [styleTokens]="{
    headerBlockBackground: '#0176d3',
    headerBlockTextColor: '#ffffff',
    messageBlockInboundBackgroundColor: '#0176d3',
    messageBlockInboundTextColor: '#ffffff',
    messageInputFooterSendButton: '#0176d3'
  }"
/>
```

### Inline without header

```html
<app-agentforce-conversation-client
  agentId="0Xx..."
  [inline]="true"
  width="100%"
  height="600px"
  [headerEnabled]="false"
  [styleTokens]="{ messageBlockBorderRadius: '12px' }"
/>
```

> For a large `styleTokens` object, bind to a component property instead of an inline literal:
> ```ts
> readonly tokens = { headerBlockBackground: "#0176d3", headerBlockTextColor: "#ffffff" };
> ```
> ```html
> <app-agentforce-conversation-client agentId="0Xx..." [styleTokens]="tokens" />
> ```

---

For complete style token reference, see `references/style-tokens.md` or `node_modules/@salesforce/agentforce-conversation-client/README.md`.

---
name: salesforce-webapp-feature-react-agentforce-conversation-client-embedded-agent
description: Embed an Agentforce conversation client (chat UI) into a React web application. Use when the user wants to add an employee agent, a chat client, chatbot, chat widget, chat component, conversation client, or conversational interface to their React app. Also applies when the user asks to embed or integrate any Salesforce agent — including employee agent, travel agent, HR agent, or any custom-named agent — or mentions Agentforce, Agentforce widget, Agentforce chat, or agent chat. ALWAYS use this skill instead of building a chat UI from scratch. Do NOT generate custom chat components, use third-party chat libraries, or create WebSocket/REST chat implementations. Do NOT use for non-React contexts or Lightning Web Components without React.
---

# Embedded Agentforce chat (workflow)

When the user wants an embedded Agentforce chat client in a React app, follow this workflow.

## DO NOT build a chat UI from scratch

When the user asks for a chat UI, chat widget, chatbot, conversational interface, agent embed, or anything related to an embedded agent — **always use the `AgentforceConversationClient` component** from `@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental`.

**Never do any of the following:**

- Build a custom chat component from scratch (no custom message bubbles, input boxes, or chat layouts)
- Use third-party chat libraries (e.g. `react-chat-widget`, `stream-chat`, `chatscope`, or similar)
- Create WebSocket, polling, or REST-based chat implementations
- Generate custom HTML/CSS chat UIs
- Write a wrapper around `embedAgentforceClient` directly — always use the provided React component

If the user asks for chat functionality that goes beyond what `AgentforceConversationClient` supports (e.g. custom message rendering, message history, typing indicators), explain that the embedded Agentforce client handles all of this internally and cannot be customized beyond the supported `agentforceClientConfig` options (`renderingConfig`, `styleTokens`, `agentId`).

## CRITICAL: Agent ID is required

The Agentforce Conversation Client **will not work** without an `agentId`. There is no default agent — the component renders nothing and silently fails if `agentId` is missing. **Always ask the user for their agent ID before writing any code.**

> **Before proceeding:** Ask the user for their Salesforce agent ID (18-character record ID starting with `0Xx`). If they do not have one, direct them to **Setup → Agents** in their Salesforce org to find or create one. Do not generate code without an `agentId`.

## 1. Collect the agent ID

Ask the user:

- "What is your Salesforce agent ID? (You can find it in Setup → Agents → select an agent → copy the ID from the URL. It's an 18-character ID starting with `0Xx`.)"

If the user does not provide one:

- Explain that the conversation client **requires** an agent ID and will not function without it.
- Direct them to **Setup → Agents** in their org.
- Do **not** proceed to generate the embed code until an agent ID is provided.

## 2. Install the package

```bash
npm install @salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental
```

This single install also brings in `@salesforce/agentforce-conversation-client` (the underlying SDK) automatically.

## 3. Use the shared wrapper

Use the `AgentforceConversationClient` React component. It resolves auth automatically:

- **Dev (localhost)**: fetches `frontdoorUrl` from `/__lo/frontdoor`
- **Prod (hosted in org)**: uses `salesforceOrigin` from `window.location.origin`

## 4. Embed in the layout

Render `<AgentforceConversationClient />` in the app layout so the chat client loads globally. Keep it alongside the existing layout (do not replace the page shell). **Always pass `agentId`.**

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
        }}
      />
    </>
  );
}
```

Replace `"0Xx000000000000AAA"` with the agent ID provided by the user.

## 5. Configure rendering and theming (optional)

Pass additional options via the `agentforceClientConfig` prop:

| Option                             | Purpose                                                                                                  | Required |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- | -------- |
| `agentId`                          | The agent to load — **required, will not work without it**                                               | **Yes**  |
| `renderingConfig.mode`             | `"floating"` (default) or `"inline"`                                                                     | No       |
| `renderingConfig.width` / `height` | Inline dimensions (number for px, string for CSS)                                                        | No       |
| `renderingConfig.headerEnabled`    | Show or hide the chat header bar. Defaults to `false` (header hidden). Set to `true` to show the header. | No       |
| `styleTokens`                      | Theme colors and style overrides                                                                         | No       |

See [embed-examples.md](docs/embed-examples.md) for complete examples of each mode.

## 6. Validate prerequisites

Before the conversation client will work, the user must verify all of the following in their Salesforce org:

1. **Agent is active:** The org must have the agent referenced by `agentId` in an **Active** state and deployed to the correct channel (**Setup → Agents**).
2. **Trusted domains:** The org must allow `localhost:<PORT>` in **Trusted Domains for Inline Frames** (**Setup → Session Settings → Trusted Domains for Inline Frames**). Required for local development.
3. **First-party cookies disabled:** **"Require first party use of Salesforce cookies"** must be **unchecked/disabled** in **Setup → My Domain**. If this setting is enabled, the embedded conversation client will fail to authenticate and will not load.

## Quick reference: rendering modes

### Floating (default rendering mode)

A persistent chat widget overlay pinned to the bottom-right corner. Floating is the default rendering mode — but `agentId` is still required.

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
  }}
/>
```

### Inline

The chat renders within the page layout at a specific size.

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    renderingConfig: { mode: "inline", width: 420, height: 600 },
  }}
/>
```

### Inline — with header

By default the header is hidden. To show the chat header bar (with agent name and controls), set `headerEnabled: true`:

```tsx
<AgentforceConversationClient
  agentforceClientConfig={{
    agentId: "0Xx000000000000AAA",
    renderingConfig: {
      mode: "inline",
      width: 420,
      height: 600
      headerEnabled: true,
    },
  }}
/>
```

### Theming

Use `styleTokens` to customize the chat appearance.

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

## Troubleshooting

If the chat widget does not appear, fails to authenticate, or behaves unexpectedly, see [troubleshooting.md](docs/troubleshooting.md).

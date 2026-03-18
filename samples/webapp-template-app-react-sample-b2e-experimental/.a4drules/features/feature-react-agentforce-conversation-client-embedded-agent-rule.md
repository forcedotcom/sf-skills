---
paths:
  - "**/*.tsx"
  - "**/components/**/*.ts"
---

# Agentforce Conversation Client (standards)

## DO NOT build a chat UI from scratch

When the user asks for a chat UI, chat widget, chatbot, agent, or conversational interface — **always use the existing `AgentforceConversationClient` component** from `@salesforce/webapp-template-feature-react-agentforce-conversation-client-experimental`. Never generate a custom chat implementation, third-party chat library, WebSocket/REST chat, or direct calls to `embedAgentforceClient`.

## Hard constraints

- **`agentId` is required.** The component will not work without it. Always ask the user for their agent ID before generating code. Do not proceed without one.
- **Use the React wrapper only.** Import `AgentforceConversationClient` from the package. Never call `embedAgentforceClient` directly.
- **One instance per window.** Render in the app layout alongside `<Outlet />`, not on individual pages. The component is a singleton.
- **No auth hard-coding.** The component resolves `salesforceOrigin` and `frontdoorUrl` automatically.

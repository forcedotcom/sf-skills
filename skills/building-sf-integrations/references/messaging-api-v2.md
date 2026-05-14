<!-- Parent: building-sf-integrations/SKILL.md -->
# Messaging API v2 Guide (MIAW)

This guide covers building custom clients for Messaging for In-App and Web (MIAW), enabling Agentforce and Service Cloud conversations outside of Salesforce.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MIAW CUSTOM CLIENT ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐                              ┌──────────────────┐    │
│   │   Custom     │      REST API v2             │    Salesforce    │    │
│   │   Client     │◀────────────────────────────▶│    MIAW / Agent  │    │
│   │  (React/Vue) │    /iamessage/api/v2/*       │    Service Cloud │    │
│   └──────────────┘                              └──────────────────────┘    │
│                                                                          │
│   Endpoints:                                                             │
│   • POST /authorization           JWT token exchange                     │
│   • POST /conversation            Start conversation                     │
│   • POST /conversation/{id}/message   Send message                       │
│   • GET  /conversation/{id}/messages  Poll for messages (or SSE)         │
│   • POST /conversation/{id}/end       End conversation                   │
│                                                                          │
│   Use Cases:                                                             │
│   • Custom chat widgets on external websites                             │
│   • Mobile app integrations                                              │
│   • Kiosk / in-store experiences                                         │
│   • Third-party platform integrations                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Salesforce Setup

1. **Messaging for In-App and Web** license
2. **Embedded Service Deployment** created
3. **Agentforce** or **Omni-Channel** routing configured
4. **Connected App** for JWT authentication

### Embedded Service Deployment

```
Setup → Embedded Service Deployments → New Deployment
├─ Type: Messaging for In-App and Web
├─ Channel: Web
└─ API Name: Your_Deployment_API_Name
```

Get the **Deployment ID** and **Organization ID** from the deployment settings.

---

## Authentication

### JWT Token Exchange

MIAW uses JWT bearer tokens for API authentication.

```javascript
// Server-side token generation (Node.js example)
import jwt from 'jsonwebtoken';
import fetch from 'node-fetch';

async function getAccessToken(orgId, deploymentId, privateKey) {
    // CRITICAL: OrgId must be 15-character format for JWT
    const orgId15 = orgId.substring(0, 15);

    const payload = {
        iss: 'YOUR_CONNECTED_APP_CLIENT_ID',
        sub: `${orgId15}`,  // 15-char org ID
        aud: 'https://login.salesforce.com',
        exp: Math.floor(Date.now() / 1000) + 300,  // 5 min expiry
        iat: Math.floor(Date.now() / 1000)
    };

    const token = jwt.sign(payload, privateKey, { algorithm: 'RS256' });

    // Exchange JWT for access token
    const response = await fetch(
        'https://login.salesforce.com/services/oauth2/token',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                assertion: token
            })
        }
    );

    const data = await response.json();
    return data.access_token;
}
```

### Authorization Endpoint

Exchange access token for MIAW-specific authorization:

```javascript
async function getMessagingAuth(accessToken, orgDomain, deploymentId) {
    const response = await fetch(
        `https://${orgDomain}/iamessage/api/v2/authorization`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                orgId: 'YOUR_ORG_ID',
                esDeveloperName: deploymentId,
                capabilitiesVersion: '1',
                platform: 'Web'
            })
        }
    );

    return await response.json();
    // Returns: { accessToken, context, ... }
}
```

---

## Conversation Lifecycle

### Start Conversation

```javascript
async function startConversation(messagingAuth, customerName) {
    const { accessToken, context } = messagingAuth;

    const response = await fetch(
        `https://${context.url}/iamessage/api/v2/conversation`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                esDeveloperName: context.esDeveloperName,
                routingAttributes: {
                    // Optional: Pre-chat fields
                    customerName: customerName
                },
                // Optional: Context for agent
                contextParameters: {
                    recordId: '001xx000003ABC',
                    caseReason: 'Technical Support'
                }
            })
        }
    );

    const data = await response.json();
    return data.conversationId;
}
```

### Send Message

```javascript
async function sendMessage(messagingAuth, conversationId, text) {
    const { accessToken, context } = messagingAuth;

    const response = await fetch(
        `https://${context.url}/iamessage/api/v2/conversation/${conversationId}/message`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: {
                    messageType: 'StaticContentMessage',
                    staticContent: {
                        formatType: 'Text',
                        text: text
                    }
                }
            })
        }
    );

    return await response.json();
}
```

### Receive Messages

#### Option 1: Server-Sent Events (SSE)

SSE provides real-time streaming but may not work on serverless platforms.

```javascript
function subscribeToMessages(messagingAuth, conversationId, onMessage) {
    const { accessToken, context } = messagingAuth;

    const eventSource = new EventSource(
        `https://${context.url}/iamessage/api/v2/conversation/${conversationId}/messages?stream=true`,
        {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        }
    );

    eventSource.onmessage = (event) => {
        const message = JSON.parse(event.data);
        onMessage(message);
    };

    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        // Fallback to polling
    };

    return eventSource;
}
```

#### Option 2: Polling (Serverless Compatible)

For Vercel, AWS Lambda, or other serverless environments:

```javascript
class MessagePoller {
    constructor(messagingAuth, conversationId, onMessage) {
        this.messagingAuth = messagingAuth;
        this.conversationId = conversationId;
        this.onMessage = onMessage;
        this.lastMessageId = null;
        this.seenMessageIds = new Set();
        this.intervalId = null;
    }

    start(intervalMs = 2000) {
        this.intervalId = setInterval(() => this.poll(), intervalMs);
        this.poll(); // Immediate first poll
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async poll() {
        const { accessToken, context } = this.messagingAuth;

        try {
            const url = new URL(
                `https://${context.url}/iamessage/api/v2/conversation/${this.conversationId}/messages`
            );
            if (this.lastMessageId) {
                url.searchParams.set('after', this.lastMessageId);
            }

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });

            const data = await response.json();

            for (const message of data.messages || []) {
                // CRITICAL: Deduplicate messages
                if (!this.seenMessageIds.has(message.id)) {
                    this.seenMessageIds.add(message.id);
                    this.lastMessageId = message.id;
                    this.onMessage(message);
                }
            }
        } catch (error) {
            console.error('Poll error:', error);
        }
    }
}
```

### End Conversation

```javascript
async function endConversation(messagingAuth, conversationId) {
    const { accessToken, context } = messagingAuth;

    await fetch(
        `https://${context.url}/iamessage/api/v2/conversation/${conversationId}/end`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            }
        }
    );
}
```

---

## Message Types

### Incoming Message Structure

```javascript
{
    "id": "msg_abc123",
    "conversationId": "conv_xyz789",
    "messageType": "StaticContentMessage",
    "sender": {
        "role": "Agent",  // or "EndUser", "Chatbot"
        "displayName": "Service Agent"
    },
    "staticContent": {
        "formatType": "Text",
        "text": "Hello! How can I help you today?"
    },
    "timestamp": "2026-01-15T10:30:00.000Z"
}
```

### Rich Message Types

| Type | Use Case |
|------|----------|
| `StaticContentMessage` | Plain text |
| `RichLinkMessage` | Clickable cards with images |
| `ListPickerMessage` | Selection lists |
| `QuickReplyMessage` | Suggested responses |
| `AttachmentMessage` | File attachments |

### Handling Rich Messages

```javascript
function renderMessage(message) {
    switch (message.messageType) {
        case 'StaticContentMessage':
            return renderText(message.staticContent.text);

        case 'QuickReplyMessage':
            return renderQuickReplies(message.quickReplies);

        case 'ListPickerMessage':
            return renderListPicker(message.listPicker);

        case 'RichLinkMessage':
            return renderRichLink(message.richLink);

        default:
            console.warn('Unknown message type:', message.messageType);
            return null;
    }
}

function renderQuickReplies(quickReplies) {
    return quickReplies.replies.map(reply => ({
        label: reply.title,
        value: reply.itemId,
        onClick: () => sendQuickReplySelection(reply.itemId)
    }));
}
```

---

## React Integration Example

```jsx
// ChatWidget.jsx
import { useState, useEffect, useRef } from 'react';

export function ChatWidget({ orgDomain, deploymentId }) {
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState('');
    const [conversationId, setConversationId] = useState(null);
    const [isConnecting, setIsConnecting] = useState(false);
    const pollerRef = useRef(null);
    const authRef = useRef(null);

    // Initialize conversation
    const startChat = async () => {
        setIsConnecting(true);
        try {
            // Get auth from your backend
            const authResponse = await fetch('/api/messaging/auth', {
                method: 'POST',
                body: JSON.stringify({ deploymentId })
            });
            authRef.current = await authResponse.json();

            // Start conversation
            const convId = await startConversation(authRef.current, 'Web User');
            setConversationId(convId);

            // Start polling for messages
            pollerRef.current = new MessagePoller(
                authRef.current,
                convId,
                handleNewMessage
            );
            pollerRef.current.start();
        } catch (error) {
            console.error('Failed to start chat:', error);
        } finally {
            setIsConnecting(false);
        }
    };

    const handleNewMessage = (message) => {
        setMessages(prev => [...prev, message]);
    };

    const handleSend = async () => {
        if (!inputText.trim() || !conversationId) return;

        // Optimistic update
        const localMessage = {
            id: `local_${Date.now()}`,
            sender: { role: 'EndUser' },
            staticContent: { text: inputText },
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, localMessage]);
        setInputText('');

        // Send to server
        await sendMessage(authRef.current, conversationId, inputText);
    };

    // Cleanup
    useEffect(() => {
        return () => {
            if (pollerRef.current) {
                pollerRef.current.stop();
            }
        };
    }, []);

    return (
        <div className="chat-widget">
            {!conversationId ? (
                <button onClick={startChat} disabled={isConnecting}>
                    {isConnecting ? 'Connecting...' : 'Start Chat'}
                </button>
            ) : (
                <>
                    <div className="messages">
                        {messages.map(msg => (
                            <MessageBubble key={msg.id} message={msg} />
                        ))}
                    </div>
                    <input
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Type a message..."
                    />
                    <button onClick={handleSend}>Send</button>
                </>
            )}
        </div>
    );
}
```

---

## Common Gotchas

### 1. OrgId Format

```javascript
// ❌ WRONG: Using 18-character OrgId in JWT
const orgId = '00D5g000004ABCDEFGH'; // 18 chars

// ✅ CORRECT: Use 15-character format for JWT
const orgId15 = orgId.substring(0, 15); // '00D5g000004ABCD'
```

### 2. Message Deduplication

Polling can return the same messages multiple times:

```javascript
// ❌ WRONG: No deduplication
messages.forEach(msg => onMessage(msg));

// ✅ CORRECT: Track seen message IDs
if (!this.seenMessageIds.has(message.id)) {
    this.seenMessageIds.add(message.id);
    onMessage(message);
}
```

### 3. SSE on Serverless

SSE connections won't work on serverless platforms:

```javascript
// ❌ WRONG: SSE on Vercel/Netlify Functions
const eventSource = new EventSource(url); // Connection dies immediately

// ✅ CORRECT: Use polling fallback
const poller = new MessagePoller(auth, convId, onMessage);
poller.start(2000);
```

### 4. Token Refresh

Access tokens expire; implement refresh logic:

```javascript
class MessagingClient {
    constructor() {
        this.auth = null;
        this.tokenExpiry = null;
    }

    async ensureValidToken() {
        const now = Date.now();
        const buffer = 60000; // 1 minute buffer

        if (!this.auth || now >= this.tokenExpiry - buffer) {
            this.auth = await this.refreshAuth();
            this.tokenExpiry = now + (this.auth.expiresIn * 1000);
        }

        return this.auth;
    }

    async sendMessage(conversationId, text) {
        const auth = await this.ensureValidToken();
        // ... send with valid token
    }
}
```

---

## Security Best Practices

| Practice | Implementation |
|----------|----------------|
| Never expose private keys | Keep JWT signing server-side only |
| Use short-lived tokens | 5-15 minute expiry for JWTs |
| Validate conversation ownership | Server tracks user → conversation mapping |
| Rate limit messages | Prevent spam/abuse |
| Sanitize message content | XSS prevention on display |

---

## Deployment Platforms

### Vercel

```javascript
// api/messaging/auth.js
export default async function handler(req, res) {
    // Server-side auth - never expose keys to client
    const auth = await getMessagingAuth(
        process.env.SF_ACCESS_TOKEN,
        process.env.SF_ORG_DOMAIN,
        req.body.deploymentId
    );

    res.json(auth);
}
```

### AWS Lambda

```javascript
// handler.js
exports.startConversation = async (event) => {
    const { deploymentId, customerName } = JSON.parse(event.body);

    const auth = await getMessagingAuth(/* ... */);
    const conversationId = await startConversation(auth, customerName);

    return {
        statusCode: 200,
        body: JSON.stringify({ conversationId })
    };
};
```

---

## Cross-Skill References

| Topic | Resource |
|-------|----------|
| Connected Apps setup | [configuring-connected-apps skill](../../configuring-connected-apps/SKILL.md) |
| Named Credentials | [named-credentials-guide.md](named-credentials-guide.md) |
| Agentforce agents | [developing-agentforce skill](../../developing-agentforce/SKILL.md) |
| Platform Events | [platform-events-guide.md](platform-events-guide.md) |
| REST callout patterns | [rest-callout-patterns.md](rest-callout-patterns.md) |

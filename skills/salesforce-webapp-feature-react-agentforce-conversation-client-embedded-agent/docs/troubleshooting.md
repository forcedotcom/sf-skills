# Troubleshooting

Common issues when using the Agentforce Conversation Client.

---

### Chat widget does not appear

**Cause:** Missing or invalid `agentId`. The component will not render anything without a valid agent ID.

**Solution:**

1. Verify `agentId` is passed in `agentforceClientConfig` — it is required
2. Confirm the ID is correct (18-character Salesforce record ID, starts with `0Xx`)
3. Check that the agent exists and is **Active** in **Setup → Agents**

### Chat loads but shows "agent not available"

**Cause:** The agent exists but is not deployed or is inactive.

**Solution:**

1. In **Setup → Agents**, ensure the agent status is **Active**
2. Verify the agent is deployed to the correct channel

### Authentication error on localhost

**Cause:** `localhost:<PORT>` is not in the org's trusted domains for inline frames.

**Solution:**

1. Go to **Setup → Session Settings → Trusted Domains for Inline Frames**
2. Add `localhost:<PORT>` (e.g. `localhost:3000`)
3. Restart the dev server

### Chat fails to authenticate / blank iframe

**Cause:** "Require first party use of Salesforce cookies" is enabled in the org's session settings. This blocks the embedded client from establishing a session.

**Solution:**

1. Go to **Setup → Session Settings**
2. Find **"Require first party use of Salesforce cookies"**
3. **Uncheck / disable** this setting
4. Save and reload the app

### Multiple chat widgets appear

**Cause:** `AgentforceConversationClient` is rendered in multiple places.

**Solution:** Render it once in the app layout, not on individual pages. The component uses a singleton pattern — only one instance should exist per window.

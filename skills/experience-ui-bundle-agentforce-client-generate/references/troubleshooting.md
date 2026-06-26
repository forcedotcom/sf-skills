# Troubleshooting

Common issues when using the Agentforce Conversation Client.

---

### Component throws "requires agentId"

**Cause:** `agentId` was not passed.

**Solution:** Pass `agentId` directly as a flat prop:

```tsx
<AgentforceConversationClient agentId="0Xx000000000000AAA" />
```

---

### Chat widget does not appear

**Cause:** Invalid `agentId` or inactive agent.

**Solution:**

1. Confirm the id is correct (18-char Salesforce id, starts with `0Xx`).
2. Ensure the agent is Active in **Setup → Agentforce Agents**.
3. Verify the agent is deployed to the target channel.

---

### Authentication error on localhost

**Cause:** `localhost:<PORT>` is not trusted for inline frames.

**Solution:**

1. Go to **Setup → Session Settings → Trusted Domains for Inline Frames**.
2. Add `localhost:<PORT>` (example: `localhost:3000`).

**Important:**

- This setting should be **temporary for local development only**.
- **Remove `localhost:<PORT>` from trusted domains after development**.
- **Recommended:** Test the Agentforce conversation client in a deployed app instead of relying on localhost trusted domains for extended periods.

---

### Blank iframe / auth session issues

**Possible cause:** First-party Salesforce cookie restriction may block embedded auth flow in some environments.

**Solution:**

1. Go to **Setup → Session Settings**.
2. Find **Require first party use of Salesforce cookies**.
3. Disable it **only if needed and approved by your security/admin team**.
4. Save and reload.

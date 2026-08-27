# Channel branch — Voice

> **When to read this file.** Load it only when the user has selected **Voice** at Checkpoint 3 of `assets/help-agent-spec.md`. If they selected Web Chat, read `channel-web-chat.md` instead. If they selected Help Portal, delegate to the sibling skill `service-concierge-portal-generate` — do not inline portal steps here.

Voice wires the Help Agent to an existing `PstnVoice` MessagingChannel via an inbound RoutingFlow. It does **not** provision a new phone number — number acquisition puts the org in a state that isn't cleanly retrievable, so it's out of scope for this skill. If the user has no `PstnVoice` channel yet, tell them to provision the number in Setup (Service Cloud Voice / Number Management) first, then come back.

---

## Existing number path

Query existing channels:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT Id, DeveloperName, MasterLabel, MessagingPlatformKey, IsActive FROM MessagingChannel WHERE MessageType='PstnVoice' ORDER BY MasterLabel"
```

If none are returned, stop and tell the user to provision a phone number and `PstnVoice` MessagingChannel in Setup first — this skill does not create one.

If any are returned, present them and let the user choose. Capture the channel's `DeveloperName` as `CHANNEL_DEV_NAME`, then continue to **Step 8 — Wire the channel to the agent**. Fallback queue resolution (including the `SobjectType='VoiceCall'` requirement) is owned by `service-agentforce-channel-configure` — do not resolve or create the queue here.

---

## Step 8 — Wire the channel to the agent

Delegate to `service-agentforce-channel-configure` Branch B. Pass:
- **Agent DeveloperName** — the Help Agent
- **Channel type** — Voice
- **Channel identifier** — `CHANNEL_DEV_NAME`

The delegated skill resolves and configures the fallback queue itself.

---

## Step 9 — Loop

Return to the Checkpoint 3 loop — offer the user the option to add another channel or proceed to go-live.

---

## Rules / constraints

| Rule | Rationale |
|---|---|
| This skill never acquires a phone number | Provisioning puts the org in a state that isn't cleanly retrievable — must be done in Setup before this skill runs |
| Never resolve or create the fallback queue here | `service-agentforce-channel-configure` owns queue resolution end to end — resolving it twice can double-prompt the user |

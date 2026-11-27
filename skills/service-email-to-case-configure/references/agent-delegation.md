# Attaching an Agentforce service agent (delegation)

When the user wants an Agentforce Service Agent to answer these emails, configure the Email-to-Case base first (the Workflow in `SKILL.md`), then delegate. This skill never creates or modifies agents.

## Gate on org capability first

Attaching an agent needs the org entitled for Agentforce Email-to-Case. That entitlement surfaces as the `BotEmailDefinition` metadata type, so probe read-only **before delegating**:

```bash
scripts/check-agent-email-capability.sh <target-org-alias>   # pins describe to the org's API version
```

This probe is the **only** place the skill uses the `sf` CLI: no dispatch route can list the org's metadata types yet. It needs the CLI alias of the same org the dispatch server is bound to.

- Exit **3** → not entitled: **stop, tell the user, and configure the plain Email-to-Case base only. Make no Agentforce agent or channel-wiring changes.**
- Any other non-zero → the org is unreachable, which is not "not entitled". Fix auth and re-run.
- Exit **0** → delegate, as below.

## Delegate

1. **Agent creation → `agentforce-generate`.** Omit the **Service Customer Verification topic** (unsupported on the email channel) and include an **Escalation subagent** so the agent can hand off to a human. On email, escalation transfers the case to a service rep; without the subagent the agent can't escalate.
2. **Wiring → `service-agentforce-channel-configure` Branch C.**

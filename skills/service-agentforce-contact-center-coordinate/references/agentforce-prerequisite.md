# Prerequisite — Einstein Setup + Agentforce Agents toggle

The **Omni Flow** path (routing a voice channel to an Agentforce agent) requires **Einstein** and **Agentforce / Einstein Service Agents to be enabled** in the org. When they're on, the org can provide an **Einstein Agent User** — the `--agent-user` that `sf agent generate agent-spec` and publish require. When they're off, or when no Agentforce Service Agent User license is available, agent authoring/publish fails with a licensing, Agent API access, or "couldn't find the default agent user" error.

This prerequisite does **not** apply to the Omni Queue path.

## Enable it (org admin, one time)

In the target org, in the Setup UI:

1. **Setup → Einstein Setup** → turn **Einstein** **On** (this must be enabled before the Agentforce toggle appears/works).
2. **Setup → Einstein → Agentforce (Agents)** (a.k.a. *Einstein Agent* / *Agentforce Service Agents*) → turn the setting **On**.
3. Confirm an **Einstein Agent User** exists (Setup → Users), or let `scripts/check-agentforce-prereq.sh` provision one with `sf org create agent-user`.

Enablement is an org preference, not part of this skill's scope — the operator flips it in Setup.

## Preflight check

```bash
scripts/check-agentforce-prereq.sh <alias>
```

- **Exit 0** — prints a user whose profile is exactly `Einstein Agent User`. Use it as `--agent-user` for `sf agent generate agent-spec`. The script reuses an existing user, or provisions one with `sf org create agent-user`.
- **Exit 3** — no canonical Einstein Agent User could be found or provisioned; the toggle is likely off or the org has no available Agentforce Service Agent User license.

The profile-name check is intentionally strict. Do not use a broad fallback such as `Profile.Name LIKE '%Agent%'` or `Profile.Name LIKE '%Bot%'`: those users can make spec generation/validation appear healthy, then fail `sf agent publish authoring-bundle` with Agent API access or default-agent-user errors.

## When the toggle is off

1. **Prompt the user** to enable it or free/provision an Agentforce Service Agent User license, then re-run the check.
2. If it still can't be confirmed — or agent/flow creation later fails on licensing — stop and report unless the user explicitly accepts the Omni Queue fallback.

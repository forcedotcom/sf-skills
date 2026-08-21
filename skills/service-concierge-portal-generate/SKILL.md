---
name: service-concierge-portal-generate
description: "Deploys an Agentforce Concierge portal on an LWR Experience Cloud site: provisions the site, configures Concierge components, sets up branding, wires the agent, enables guest access, and publishes. Use when the user wants to stand up a Help Portal / Agentforce Concierge portal — standalone or as the channel step in a Help Agent setup. Requires an existing, active Agentforce Service Agent on the org. DO NOT TRIGGER when the user only wants to embed a chat widget on an existing site (use service-digital-engagement-deployment-configure instead)."
allowed-tools: Bash Read Write Edit Glob Grep WebFetch AskUserQuestion TodoWrite
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "service-agentforce-channel-configure"
    - "service-digital-engagement-channel-configure"
    - "service-digital-engagement-deployment-configure"
    - "service-helpagent-coordinate"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.139.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["openssl"]
      semver: ">=1.1.1"
  accessCheck:
    - type: "license"
      value: "Agentforce"
---

# service-concierge-portal-generate: Agentforce Concierge portal deploy

Deploys an **Agentforce Concierge experience** on an LWR Experience Cloud site — an agent-first landing page with a welcome greeting, prompt bar, suggestion chiclets, and full chat surface. This is a channel-setup skill: it wires an existing agent to a new or existing portal site; it does not author the agent.

## Why this skill exists

The Concierge portal setup is a 20-step workflow with precise sequencing requirements (bundle shape, routing wiring, guest access flags, CORS/CSP records). Keeping it as a standalone skill lets it be invoked from `service-helpagent-coordinate` (Checkpoint 3 → Help Portal branch) **or** called directly when the user already has an agent and only needs the portal.

## Skills inventory pre-flight (MANDATORY before anything else)

Before asking the user any questions, verify that every skill this skill delegates to is installed:

```bash
for skill in service-digital-engagement-channel-configure service-digital-engagement-deployment-configure service-agentforce-channel-configure; do
  [ -d ".claude/skills/$skill" ] && echo "OK: $skill" || echo "MISSING: $skill"
done
```

If any skill is missing, stop immediately and tell the user which skills are absent with their exact directory names. Do not proceed until the missing skills are installed.

## Required inputs

| Input | How resolved |
|---|---|
| **Target org alias** (`$ORG`) | Ask via `AskUserQuestion` if not provided in the current conversation turn |
| **Agent** (`$BOT_ID`, `$BOT_DEV_NAME`) | Always query the org — never infer from prior context |
| **MessagingChannel** (`$MESSAGING_CHANNEL_DEV_NAME`, `$MESSAGING_CHANNEL_ID`) | **Optional** — pass from calling skill if already created; otherwise delegate to `service-digital-engagement-channel-configure` in Step E of the runbook |
| **EmbeddedServiceConfig** (`$ESC_ID`, `$ESC_DEV_NAME`) | **Optional** — pass from calling skill if already created; otherwise delegate to `service-digital-engagement-deployment-configure` in Step F.3 of the runbook |

If `MESSAGING_CHANNEL_DEV_NAME` and `ESC_ID` are not provided, this skill will delegate their creation to the appropriate skills (see runbook §E and §F.3). The portal site itself — the DEB bundle, branding, components, guest access, CORS/CSP — is always provisioned by this skill.

## Workflow

Read `references/portal-deploy-runbook.md` and follow it end-to-end. The runbook is the authoritative step-by-step guide; this SKILL.md is the router and context layer only.

### Entry point

1. Ask for the org alias:
   ```yaml
   AskUserQuestion:
     question: "Which org should I deploy the Concierge portal to?"
     header: "Org alias"
     options:
       - label: "Enter alias"
         description: "Type the org alias (e.g. help-portal-dev, trailsignup)"
   ```

2. Query for **active** agents (activation lives on `BotVersion.Status = 'Active'`, not on `BotDefinition` — an unfiltered `SELECT ... FROM BotDefinition` returns retired/inactive bots the runbook cannot wire, so filter on active `BotVersion` explicitly):
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT Id, DeveloperName, MasterLabel FROM BotDefinition WHERE Id IN (SELECT BotDefinitionId FROM BotVersion WHERE Status='Active') ORDER BY MasterLabel"
   ```
   - **Zero rows** (no bots, or only inactive/retired bots — both count as zero for wiring) → **hard-stop in the same turn**. Do not load the runbook, do not delegate to `service-digital-engagement-channel-configure` or `service-digital-engagement-deployment-configure`, do not fabricate a `BOT_ID`, and do not present a "Create a new agent first" `AskUserQuestion`. Tell the user the portal needs an active agent to wire and point them at `agentforce-generate` **or** `service-helpagent-coordinate` to create one first, then re-invoke this skill.
   - **One or more active agents** → present ALL returned agents as options via `AskUserQuestion`, plus a **"Create a new agent first"** option. Do NOT assume the user wants the only/first agent — always ask explicitly.

   If the user selects **"Create a new agent first"**: stop immediately with this message:
   > Creating a new agent is outside the scope of this skill. Please run the `agentforce-generate` skill (or `service-helpagent-coordinate` for a full Help Agent setup) to create your agent, then re-invoke the Concierge portal skill.

   If the user selects an existing agent: capture `BOT_ID` and `BOT_DEV_NAME` and continue.

   > **Long-list rule:** if there are more than 6 agents, paginate — show 6 at a time with a "Show more" option rather than presenting all at once.

3. Load `references/portal-deploy-runbook.md` and execute §0 top-to-bottom.

### Return values (for calling skills)

On success, surface:

| Variable | Value |
|---|---|
| `NETWORK_ID` | 18-char Network Id of the provisioned portal |
| `PUBLISHED_PORTAL_URL` | Live customer-facing URL (for Incognito verification) |
| `MESSAGING_CHANNEL_DEV_NAME` | The `EmbeddedMessaging` channel wired to the agent |
| `ESC_ID` | EmbeddedServiceConfig Id (auth path) |

### Final report format

On completion, summarize what was deployed and surface the four return values above in a clearly labeled block so the user (or a calling skill) can act on them. If the active-agent query returned zero rows, skip straight to the hard-stop message from step 2 — no return values to report.

## Rules / constraints

| Rule | Rationale |
|---|---|
| Run the skills inventory pre-flight before any user interaction | Delegation to missing skills fails mid-deploy, leaving the portal in a partial state |
| Agent must exist and be Active before starting | Wiring an inactive agent produces a portal that loads but never responds |
| Read `references/portal-deploy-runbook.md` fully before starting §A questions | The runbook's §0 stage table must be in context when executing each step |
| Never create MessagingChannel or EmbeddedServiceConfig inline — always delegate | `service-digital-engagement-channel-configure` and `service-digital-engagement-deployment-configure` own those objects; inlining them bypasses queue resolution, escalation wiring, and ESD validation |
| Never skip the guest-access flags in §L.0 | `OptionsGuestChatterEnabled` + `OptionsGuestMemberVisibility` default to False — portal appears blank in Incognito without them |
| Republish after every DEB flag change | `isRelaxedCSPLevel`, `authenticationType`, `headMarkup` only take effect after a publish |
| One operator pause only: §F.4 Agentforce Orchestrator toggle | Every other step is headless — never pause for UI unless the headless path returns an unrecoverable error |

## Reference file index

| File | When to read |
|---|---|
| `references/portal-deploy-runbook.md` | Always — the authoritative 20-step deploy runbook |

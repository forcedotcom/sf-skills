# Salesforce Service Omni-Channel

A specialist plugin for Omni-Channel routing, queues, presence, capacity, and classic supervisor setup behind Salesforce Development.

Version: **0.1.0**.

## Ownership

**Service Cloud Arch** owns this plugin and its 24 canonical skills. DX Agent Plugins maintains the shared Salesforce Development discovery implementation.

## Install and prerequisites

Install from the Salesforce public marketplace:

```text
/plugin marketplace add forcedotcom/sf-skills
/plugin install service-omni@salesforce
/reload-plugins
```

Install one named plugin, then verify the host's refreshed inventory includes the 24 skills below before resuming work. If refreshed inventory is unavailable, start a fresh session. This plugin does not automatically install related plugins.

Use an authenticated Salesforce CLI org with the Service Cloud license and the permissions/features required by the selected skill. The coordinator declares API 66.0+, sf 2.139.6+, jq 1.6+, and Python 3.8+ (for contract tests). VoiceCall routing additionally needs a provisioned AFCC/Amazon contact center and live Voice runtime; Incident and MessagingSession targets require their own enabled features. Start with each script's documented read-only plan/detection mode and review its inputs before writes.

## Workflows and boundaries

- “Set up Omni-Channel with Case queues and presence statuses”: start with `service-omni-channel-setup-coordinate` and its `scripts/integration-driver.sh --plan <org-alias>`. The coordinator creates/binds Case and VoiceCall routing; it only verifies/adopts Incident and MessagingSession routing.
- “Configure skills-based Case routing”: use `service-omni-skills-based-routing-configure`, `service-omni-work-skill-routing-configure`, and `service-omni-routing-flow-deploy`; a required SkillsBased runtime proof needs a PendingServiceRouting with a SkillRequirement.
- “Configure classic Omni Supervisor”: use the supervisor user, permission, config, and surface skills. Command Center V2 enablement and unsupported OrgValues remain manual Setup actions; analysis is read-only.

`service-engagement` owns customer-facing messaging, chat, WhatsApp, Email-to-Case, and Agentforce human escalation. This plugin owns work routing and rep/supervisor resources. A combined messaging plus Omni routing task can legitimately require both plugins.

## Cross-plugin references

The only external `metadata.relatedSkills` targets are `platform-metadata-deploy` (Salesforce Development) and `service-agentforce-human-escalation-configure` (service-engagement). These are references, not dependency installation or resolution. Before delegating to either target, check the host inventory; if absent, request explicit installation of that named plugin, run `/reload-plugins`, and verify refreshed inventory before continuing that step. Do not claim that installing service-omni alone provides a created-and-bound MessagingSession handoff. Internal plugin mirrors preserve the complete canonical directories. Public releases omit internal source-of-record files and distribution metadata.

## Exact roster

- `service-omni-agent-users-create`
- `service-omni-agent-work-sharing-configure`
- `service-omni-attribute-routing-configure`
- `service-omni-base-settings-configure`
- `service-omni-channel-inventory-analyze`
- `service-omni-channel-limits-analyze`
- `service-omni-channel-setup-coordinate`
- `service-omni-command-center-analyze`
- `service-omni-command-center-configure`
- `service-omni-permission-set-assign`
- `service-omni-presence-status-deploy`
- `service-omni-presence-user-config-deploy`
- `service-omni-queue-deploy`
- `service-omni-queue-members-assign`
- `service-omni-queue-routing-config-deploy`
- `service-omni-routing-flow-deploy`
- `service-omni-service-channel-configure`
- `service-omni-sidebar-configure`
- `service-omni-skills-based-routing-configure`
- `service-omni-supervisor-config-deploy`
- `service-omni-supervisor-permset-assign`
- `service-omni-supervisor-surface-deploy`
- `service-omni-supervisor-users-create`
- `service-omni-work-skill-routing-configure`

## Validation

Run the repository gates in `plugins/DEVELOPING.md`, and:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 plugins/builder/service-omni/scripts/verify-public-plugin-release.py --plugin-root plugins/builder/service-omni --authoring-root skills
```

Discovery checks exercise the generated catalog for matching tasks, unrelated tasks, overlap with service-engagement, and suppression when already installed. Packaging and mocked script tests do not prove live org execution.

### Matching boundaries

Recommendations require supported capability context: agent capacity, work sharing,
Salesforce/Omni routing or VoiceCall routing. Bare "Route voice calls", generic
Twilio routing and Amazon Connect provisioning stay quiet. This intentionally
favors precision over generic voice recall using existing anchors and companions.

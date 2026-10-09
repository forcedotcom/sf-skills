---
name: service-omni-channel-inventory-analyze
description: "Use to inventory configured Omni-Channel instances across Voice, Email, Chat, SMS, Facebook, WhatsApp, and In-App, including each channel's Queue, Flow, or Other routing target, without changing the org. TRIGGER when: list Omni channels, inventory Omni routing, inspect channel routing targets, analyze Omni-Channel setup, or find configured service channels. Do not use to create, update, activate, or delete channels or routing configuration."
allowed-tools: Bash Read Write Grep Glob
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-channel-setup-coordinate"
    - "service-omni-queue-routing-config-deploy"
    - "service-omni-routing-flow-deploy"
    - "service-omni-service-channel-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-channel-inventory-analyze

Read the org's complete Omni-Channel setup-home inventory without making changes. The supported headless operation combines Voice, Email, Live Chat, and Messaging channel families and returns their derived routing type and routing target. Use this analyzer before changing an unfamiliar org or when a user asks what Omni channels and routing are already configured.

## Inputs

```bash
bash scripts/analyze.sh <org-alias> [--type Voice|Email|Chat|SMS|Facebook|WhatsApp|InApp]
```

- `org-alias` is required and must already be authenticated with Salesforce CLI.
- `--type` is optional and case-insensitive. It filters the returned inventory without changing the source data.

## Preconditions and safety

- Target org authenticated through `sf` CLI.
- API v66.0 or later.
- The running user must have **View Setup and Configuration** and **Customize Application**.
- This skill is read-only. The shared Headless dispatcher uses an HTTP POST envelope, but the invoked `getChannelInstances` controller action performs no org mutation.
- Use `sf api request rest`; never extract or print an access token.

## Run

Invoke `scripts/analyze.sh` with the target org and optional channel type. The script POSTs the approved `OmniChannelInstancesController.getChannelInstances` envelope to the shared Headless dispatcher, validates the inner response, optionally filters it, and returns a stable summary plus the matching channel instances.

The inventory includes these source fields when the platform supplies them:

| Field | Meaning |
|---|---|
| `id`, `label` | Channel identity and display label |
| `omniChannelInstanceType` | Voice, Email, Chat, SMS, Facebook, WhatsApp, or InApp |
| `routingType` | Queue, Flow, or Other |
| `routingRequirementId`, `routingRequirementLabel` | Queue, flow, or other routing target |
| `channelUrl`, `routingRequirementUrl` | Setup navigation links synthesized by the platform |
| `icon`, `messages` | Display metadata and platform-provided notices |

## Output contract

The script emits one JSON object:

- `skill`: `service-omni-channel-inventory-analyze`
- `status`: `analyzed` or `blocked`
- `filter`: canonical channel type or `null`
- `summary.total_configured`: number of instances returned by the platform before filtering
- `summary.returned`: number of instances in `instances`
- `summary.by_channel_type`: counts for the returned inventory
- `summary.by_routing_type`: Queue, Flow, and Other counts for the returned inventory
- `instances`: normalized channel instance objects
- `blocking_issue`: actionable failure reason or `null`

An empty `instances` array with `status: analyzed` is a valid inventory result. Authentication, authorization, endpoint, or malformed-response failures return `status: blocked` and exit non-zero; never reinterpret them as an empty org.

## Boundaries

- Do not replace this operation with independent SOQL queries. No single public object API reproduces the platform's cross-family aggregation, routing-type derivation, and setup URL generation.
- Do not infer missing routing fields. Preserve `null` when the platform does not supply a value.
- Do not use the returned setup URLs as mutation endpoints.
- For configuration changes, hand off to the appropriate leaf skill only after presenting the inventory to the user.

| Requested follow-up | Skill |
|---|---|
| Coordinate a complete Omni setup | `service-omni-channel-setup-coordinate` |
| Create or reuse a Service Channel | `service-omni-service-channel-configure` |
| Create or update a queue routing configuration | `service-omni-queue-routing-config-deploy` |
| Deploy a QueueBased or SkillsBased routing flow | `service-omni-routing-flow-deploy` |

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Supported endpoint, permission boundary, response fields, and why the headless operation is canonical |

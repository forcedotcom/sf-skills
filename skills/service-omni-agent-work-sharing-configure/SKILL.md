---
name: service-omni-agent-work-sharing-configure
description: "Use to configure or verify org-wide AgentWork visibility for supervisors after explicit confirmation. Triggers: let supervisors read AgentWork, configure AgentWork sharing, verify AgentWork OWD, make AgentWork visible to supervisors, change AgentWork internal access. Do not use to filter which reps appear in Command Center; use service-omni-supervisor-config-deploy for that."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "0.1"
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-supervisor-config-deploy"
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

# service-omni-agent-work-sharing-configure

Detect and optionally configure the standard `AgentWork` object's internal organization-wide default. The supported headless contract is `CustomObject:AgentWork` metadata: retrieve the current metadata, preserve `externalSharingModel`, deploy internal `sharingModel=Read`, and retrieve it again for proof.

This setting grants read visibility broadly to internal users who already have object access. It is not a substitute for an `OmniSupervisorConfig`: that configuration filters which reps, queues, skills, actions, and tabs a supervisor sees, but does not grant record access.

## Inputs

```bash
bash scripts/configure-and-report.sh <org-alias> --plan
bash scripts/configure-and-report.sh <org-alias> --confirm-org-wide-visibility
```

- `org-alias` is required and must already be authenticated with `sf`.
- `--plan` retrieves and reports the current and desired models without deploying.
- `--confirm-org-wide-visibility` is required only when a run must change `Private` to `Read`. Omitting it blocks before deployment.

## Safety contract

- A run refuses production customer orgs. Plan mode remains read-only.
- `externalSharingModel` is preserved exactly.
- `Read` and `ReadWrite` already provide internal read visibility and are reused. The skill never narrows `ReadWrite` to `Read`.
- The only supported mutation is `Private` to `Read`; the skill never grants internal edit access.
- Failed classification, retrieve, deploy, or read-back blocks. It never reports success from an inconclusive response.
- Use a dedicated sandbox or test org because changing an OWD can initiate sharing recalculation.

## Workflow

1. Classify the target org and enforce the production-write guard.
2. Retrieve `CustomObject:AgentWork` through Metadata API.
3. Read internal and external sharing models.
4. Reuse `Read` or `ReadWrite` with no deploy.
5. In plan mode, report the proposed `Private` to `Read` change and exit yellow.
6. In run mode, require explicit blast-radius confirmation.
7. Deploy only the standard-object metadata containing preserved external sharing and internal `Read`.
8. Retrieve again and require internal `Read` plus the unchanged external model.

## Output

A single JSON object containing `status`, `previous_sharing_model`, `sharing_model`, `external_sharing_model`, `changed`, `dry_run`, `deploy_id`, and `blocking_issue`.

- `configured`: a confirmed `Private` to `Read` deployment succeeded and read-back matched.
- `reused`: current `Read` or `ReadWrite` already provides visibility.
- `action_needed`: plan mode found `Private`; no write occurred.
- `blocked`: a safety guard or supported-API verification failed.

## Limitations

- This skill changes visibility, not supervisor scope. Use the supervisor configuration skill for filtering.
- It does not create sharing rules or per-record `AgentWorkShare` rows.
- It cannot prove a particular supervisor's complete UI access; validate the end-to-end Command Center journey with the intended supervisor user after configuration.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Before approving the org-wide change or diagnosing a retrieve/deploy failure |

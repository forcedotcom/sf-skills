---
name: service-omni-command-center-configure
description: "Use to enable Command Center for Service V2 and configure its supported supervisor controls through the OmniChannel Settings Metadata API while preserving unrelated settings. Requires explicit apply consent, refuses production customer orgs, and verifies the seeded V2 page and tab. TRIGGER when: enable Command Center V2, configure conversation monitoring, enable agent sneak peek, enable customer sneak peek, configure whisper messaging, or enable queues and skills actions. Do not use to assign supervisor permissions or configure classic OmniSupervisorConfig metadata."
allowed-tools: Bash Read Write Edit Grep Glob
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "69.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-command-center-analyze"
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

# service-omni-command-center-configure

Enable Command Center for Service V2 through `Settings:OmniChannel` and optionally configure the five supervisor controls exposed by the same Metadata API contract. The writer retrieves the org's complete settings document, changes only requested elements, deploys that preserved document, retrieves it again, and verifies both the values and the platform-created `CommandCenterForServiceV2_L` page and V2 tab.

The skill fails closed with `platform_api_unavailable` when the retrieved settings document does not expose `enableCommandCenterForServiceV2`.

Run `service-omni-base-settings-configure` first so the Omni foundation is enabled. If the org does not support Command Center V2, use `service-omni-supervisor-config-deploy` for the classic supervisor configuration instead.

For an end-to-end setup, `service-omni-channel-setup-coordinate` invokes this skill only when `OMNI_COMMAND_CENTER_V2=1`; the coordinator's default supervisor path remains unchanged.

## Inputs

```bash
bash scripts/configure-and-report.sh plan <org-alias> [options]
bash scripts/configure-and-report.sh run  <org-alias> --apply [options]
```

Options:

| Option | Metadata element | Values |
|---|---|---|
| `--conversation-monitoring` | `enableConversationMonitoring` | `true` or `false` |
| `--agent-sneak-peek` | `enableAgentSneakPeek` | `true` or `false` |
| `--customer-sneak-peek` | `enableClientSneakPeek` | `true` or `false` |
| `--whisper-messaging` | `enableWhisperMessaging` | `true` or `false` |
| `--queues-and-skills` | `enableSkillsAndQueueActions` | `true` or `false` |

`enableCommandCenterForServiceV2=true` is always requested. Unspecified supervisor controls are preserved exactly as retrieved. The skill intentionally does not disable V2 because disabling an org-level supervisor experience is a materially different operation.

## Safety

- `plan` is read-only and never deploys.
- `run` requires the literal `--apply` flag before any mutation.
- Writes are allowed only when `IsSandbox=true`, `TrialExpirationDate` is non-null, or `OrganizationType` is `Developer Edition` or `Base Edition`. There is no production override.
- `Settings` is a whole-document Metadata API type. Never deploy a partial or hardcoded `OmniChannel.settings-meta.xml`; doing so can reset unrelated Omni settings.
- The target org must have Enhanced Omni-Channel and the Command Center for Service V2 release gater. The API field is also permission-gated by `Customize Application`.

## Behavior

1. Authenticate and retrieve `Settings:OmniChannel` at API v66.
2. Confirm the V2 field is present. If it is absent, return `blocked` with `reason_code=platform_api_unavailable`; do not attempt a deploy.
3. Build a requested-value set containing V2=`true` plus only the optional controls explicitly supplied by the caller.
4. In `plan`, return `action_needed` or `reused` without writing.
5. In `run`, enforce `--apply` and the non-production guard, mutate a private copy of the retrieved document, and deploy it.
6. Retrieve the settings again and require every requested value to match.
7. Require both the seeded `FlexiPage` (`CommandCenterForServiceV2_L`) and V2 `TabDefinition` to be observable. Missing or unreadable provisioning evidence returns `blocked`; the skill never guesses.

The platform's ON-transition hook is idempotent: it creates missing profile tab configuration and seeds the baseline FlexiPage only when needed. Existing page customizations are not overwritten. If the preference is already true but its seed artifacts are missing, the skill returns `seed_incomplete`; it does not force a destructive OFF→ON cycle.

## Output contract

The script emits one JSON object with:

- `status`: `configured`, `reused`, `action_needed`, or `blocked`
- `reason_code`: a stable reason such as `changes_required`, `already_configured`, `platform_api_unavailable`, `unsafe_target`, `deploy_failed`, `verification_failed`, or `seed_incomplete`
- `requested`, `before`, and `after`: setting values, with presence retained in the snapshots
- `safe_to_write`, `deploy_id`, and `verification`
- `manual_actions`: permission assignment and any required follow-up
- `blocking_issue`: populated only when blocked

Enabling the org preference does not grant user access. Assign a permission set containing `CommandCenterForServiceUser` to each intended supervisor, then run `service-omni-command-center-analyze <org> <supervisor>` to verify end-to-end readiness.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Metadata names, platform gates, seed behavior, and known limitations |

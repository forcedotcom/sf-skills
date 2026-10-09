---
name: service-omni-command-center-analyze
description: "Use to analyze whether an org should use Command Center for Service V2 or classic Omni Supervisor and recommend the next action without making changes. Triggers: detect Command Center V2 versus classic, check supervisor readiness, choose a supervisor experience, diagnose Command Center availability, assess Omni Supervisor setup. Do not use to enable V2, assign permissions, or deploy configuration."
allowed-tools: Bash Read Grep Glob
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-channel-setup-coordinate"
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

# service-omni-command-center-analyze

Decide, **without changing anything**, which supervisor experience an org should use and what to do next. Command Center for Service V2 is gated on three independent dimensions — org **capability** (release gater), the **`CommandCenterForServiceV2` org preference** (whose ON-flip seeds the `CommandCenterForServiceV2_L` FlexiPage and registers the V2 tab), and the per-supervisor **`CommandCenterForServiceUser`** permission. A single boolean cannot express that, so this skill returns an explicit **state** plus the recommended follow-up skill (e.g. `service-omni-supervisor-config-deploy` for the classic path). It is the entry point of the Command Center flow — `service-omni-channel-setup-coordinate` runs it first — and is safe to run on any org, including production, because it only reads.

## Inputs

```bash
bash scripts/analyze.sh <org-alias> [supervisor_username_or_id]
```

- `org-alias` (required).
- `supervisor_username_or_id` (optional). A Username (`…@…`) or 15/18-char User Id (`005…`). When given, the per-user `CommandCenterForServiceUser` permission is evaluated; when omitted, the permission dimension is reported as not-checked and readiness is org-level only.

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- **Read-only** — no `safe_to_write` guard is needed; the skill issues only SOQL/Tooling queries.

## Run

`analyze.sh` gathers observable signals and maps them to a state:

| Signal | Source | Meaning |
|---|---|---|
| V2 capability | `SELECT Id FROM PermissionSet WHERE PermissionsCommandCenterForServiceUser = true` probe | If the user-permission column does not exist on the org schema, V2 is not available. |
| Seeded FlexiPage | Tooling: `FlexiPage` where `DeveloperName='CommandCenterForServiceV2_L'` | Present ⇒ the org preference was enabled and the page was seeded. |
| V2 tab | `TabDefinition` (best-effort) | Cross-checks the seed; a seed/tab mismatch indicates a partial provision. |
| Supervisor permission | `PermissionSetAssignment` joined on `PermissionSet.PermissionsCommandCenterForServiceUser` | Whether the named supervisor can use V2. |
| Legacy config | Tooling: `OmniSupervisorConfig` count | Informational for the classic path. |

## Behavior

**States and recommended next action:**

| State | Meaning | Recommended skill |
|---|---|---|
| `v2_ready` | Capability + seed present (and supervisor has permission, if checked) | verify only (coordinator proceeds to V2 verification) |
| `v2_permission_missing` | V2 enabled but the named supervisor lacks `CommandCenterForServiceUser` | Manual — assign `CommandCenterForServiceUser` (headless-capable via PermissionSet; packaging pending) |
| `v2_seed_incomplete` | Capability present but the FlexiPage/tab provisioning is inconsistent | Manual — re-check in Setup → Omni-Channel → Supervisor Settings (no supported public write API) |
| `v2_available_not_enabled` | Org supports V2 but the preference is off | Manual — enable in Setup → Omni-Channel → Supervisor Settings (no supported Metadata/Tooling write API) |
| `legacy_selected` | V2 capability absent | `service-omni-supervisor-config-deploy` |
| `ambiguous` | A required signal could not be read through a supported API | none — **blocks**, do not guess |

`ambiguous` is the only state that exits non-zero: the review's rule is to block rather than infer when state cannot be proven read-only. All other states exit 0 with `status:"detected"`.

## Output contract

A single JSON object: `status` (`detected` | `blocked`), `state` (one of the six above), `recommended_action`, `recommended_skill`, `signals` (`v2_capability`, `seed_flexipage_present`, `v2_tab_present`, `supervisor{identifier,checked,has_command_center_permission}`, `legacy_omnisupervisorconfig_count`), `manual_actions`, `blocking_issue`.

## Limitations

- The `CommandCenterForServiceV2` org preference has no supported public read; its state is **inferred** from the seeded FlexiPage (the platform seeds on the ON-flip). This is called out in `signals` and is why a bare capability-without-seed reads as `v2_available_not_enabled`.
- The release gater cannot be read directly; capability is inferred from the presence of the user-permission column on the org schema.
- Tab detection is best-effort; when the tab query cannot run, `v2_tab_present` is `"unknown"` and state is derived from the remaining signals.
- Read-only: it never enables V2, seeds pages, assigns permissions, or deploys config.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | The three-dimensional V2 gate, why each signal is a proxy, and the exact queries used |

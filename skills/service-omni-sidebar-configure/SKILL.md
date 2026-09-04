---
name: service-omni-sidebar-configure
description: "Use to enable or verify the Omni-Channel sidebar on a Lightning console app. Triggers: enable the Omni sidebar, pin Omni-Channel in a console app, configure the Omni sidebar, turn on the Omni-Channel utility region, verify the pinned Omni widget. Do not use for Aura apps, standard apps, utility-bar-only Omni widgets, or to create a console app."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
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

# service-omni-sidebar-configure

Enable the Omni-Channel **sidebar** — the pinned Omni utility region that docks to the side of a Lightning console app — by setting `isOmniPinnedViewEnabled=true` on that app's `CustomApplication` metadata and confirming the flag round-trips. This is the recommended Omni surface for console/demo orgs: reps see incoming work, presence, and the work list docked beside the record, rather than only in the collapsible utility bar. It runs once per console app and is invoked by `service-omni-channel-setup-coordinate` as the final rep-experience step.

## Inputs

```bash
bash scripts/enable-and-report.sh <org-alias> [app_developer_name]
```

- `org-alias` (required).
- `app_developer_name` (optional). The `CustomApplication` DeveloperName of the Lightning console app. When omitted, the skill queries `AppDefinition` for Lightning console apps: exactly one → adopt it; zero or many → `blocked` (name it explicitly).

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled (`service-omni-base-settings-configure`).
- The target must be a **Lightning console** app that is deployable as `CustomApplication` metadata. Standard apps and Aura apps are out of scope.
- The three-way `safe_to_write` production guard applies.

## Run

`enable-and-report.sh` resolves the target app, retrieves its `CustomApplication`, and reads the current `isOmniPinnedViewEnabled` value:

- already `true` → `reused` (no deploy).
- `false` or absent → sets it to `true` and deploys the single `CustomApplication` in one atomic Metadata API call, then **re-retrieves** to confirm the flag is `true` before reporting success.

The deploy uses explicit `--metadata "CustomApplication:<name>"` (never `--source-dir`) and is done on its own — Metadata deploys are atomic, so the app is left unchanged on any failure.

## Behavior

**Idempotent + non-destructive.** The skill only flips the single boolean; it never rewrites tabs, brand, or nav config. When the field is missing it is inserted in its XSD-ordered position (immediately before `<label>`); when present its value is replaced in place.

**Auto-detect is conservative.** It adopts an app automatically only when exactly one Lightning console app exists, so it can never silently pin the wrong app on an org with several.

## Output contract

A single JSON object: `status` ∈ `enabled` | `reused` | `blocked`, `app_developer_name`, `app_label`, `before` (bool), `after` (bool), `deploy_id`, `manual_actions`, `blocking_issue`.

- `enabled` — the flag was `false`/absent and is now verified `true`.
- `reused` — the flag was already `true`.
- `blocked` — no/many console apps found, retrieve/deploy failure, or the post-verify did not confirm `true`; `blocking_issue` explains and `manual_actions` names the fix or prerequisite skill.

## Limitations

- One app per invocation; run again for each console app that needs the sidebar.
- Lightning console `CustomApplication` only — not Aura, not standard apps, not the utility-bar Omni widget.
- Does not create or lay out the console app, its tabs, or the Omni utility item.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | CustomApplication `isOmniPinnedViewEnabled` schema/order, AppDefinition detection query, and retrieve/deploy notes |

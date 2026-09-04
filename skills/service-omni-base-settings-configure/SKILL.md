---
name: service-omni-base-settings-configure
description: "Use to enable the five Omni-Channel base settings on a Salesforce org via the Metadata API. The canonical writer scripts/configure-and-report.sh detects, deploys, and re-verifies in one call (run mode) or detects only (plan mode); it is idempotent (deploys only when a toggle is false or missing) and guards writes with a sandbox/CDO/trial/DE safe_to_write check. It always surfaces the UI-only login-behavior gap in its report. Triggers: enable Omni-Channel, turn on Omni base settings, configure OmniChannelSettings, deploy Settings:OmniChannel. Do not use to configure downstream Omni entities (queues, presence, permissions — use the entity-specific skill) or to deploy other Settings types (use platform-metadata-deploy)."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "platform-metadata-deploy"
    - "service-omni-channel-setup-coordinate"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-base-settings-configure

Enable the five `OmniChannelSettings` booleans (`enableOmniChannel`, `enableOmniAutoLoginPrompt`, `enableOmniSecondaryRoutingPriority`, `enableOmniSkillsRouting`, `enableOmniStatusCapModel`) via a single Metadata API deploy. Nothing downstream — queues, presence statuses, routing flows — works without `enableOmniChannel=true`, so this must be the first write in an Omni setup sequence. The skill probes first and deploys only when a toggle is false or missing.

## Inputs

```bash
bash scripts/configure-and-report.sh run  <org-alias>   # detect; deploy if needed; re-verify
bash scripts/configure-and-report.sh plan <org-alias>   # read-only: detect only, never deploys
```

`org-alias` is the only input. All five toggles are always set to `true` — the skill takes no per-toggle overrides; a caller who wants a subset should use `platform-metadata-deploy` with their own `OmniChannel.settings-meta.xml`.

## Preconditions and safety

- Target org authenticated via `sf` CLI (My Domain URL, not `.lightning.force.com`), Service Cloud license present, `sf` CLI ≥ 2.139.6.
- **Production guardrail:** the writer computes `safe_to_write` as `IsSandbox` OR `TrialExpirationDate != null` OR `OrganizationType` in {Developer Edition, Base Edition}, and blocks with no override when it is false. This permits CDOs (`IsSandbox=false` with a non-null `TrialExpirationDate`); do not weaken it to a bare `IsSandbox` check.

## Run

`configure-and-report.sh` is the canonical entry point:

- **run** — probe; if all five are already enabled, emit `reused` (no deploy); otherwise run the `safe_to_write` guard, deploy the explicit `assets/force-app/main/default/settings/OmniChannel.settings-meta.xml` source file with all five `true` (a `SucceededPartial` is treated as failure), re-probe, and emit `configured` iff all five are now true, else `blocked`. The explicit source path bypasses source-tracking no-op decisions when the org value has drifted.
- **plan** — probe only; emit `reused` if all enabled, else `action_needed`. Never deploys.

The probe retrieves `Settings:OmniChannel` and takes 1–2 minutes (Metadata retrieve is slow); this is expected. The deploy runs from `assets/` (a valid DX project) and names the settings file with `--source-dir`; its template is never mutated at runtime, so the skill stays reproducible and does not report "No local changes to deploy" solely because local source tracking is clean.

## Behavior

**Whole-document writes.** `Settings` is a whole-document metadata type — the Metadata API does not accept partial updates, so the skill always deploys the full file rather than PATCHing individual toggles.

**Login-behavior gap.** The Omni login-behavior radio (Setup → Omni-Channel Settings → "Define login behavior when an agent opens a new window/tab") has no public API on v66. The report always surfaces its click-path — even on a no-op `reused` run — so a "nothing to do" result never hides the one manual action. `enableOmniAutoLoginPrompt` still deploys cleanly (other Omni features may depend on it internally) but does not drive that radio.

**Fail-closed verify.** After a deploy the skill re-probes and requires all five toggles true; a deploy that reports success but does not stick (an uncommon org-level restriction) blocks rather than reporting success.

## Output contract

`configure-and-report.sh` emits a single JSON object with `status` ∈ `configured` | `reused` | `action_needed` | `blocked`, a top-level `all_enabled` boolean the coordinator reads to gate downstream skills, full `before`/`after` toggle objects, `deploy_id`, `safe_to_write`, `manual_actions`, and `blocking_issue`.

- `configured` — a toggle was false, the deploy ran, and the re-probe shows all true (run mode).
- `reused` — all five were already true; no deploy.
- `action_needed` — plan mode saw a disabled toggle; nothing deployed.
- `blocked` — `safe_to_write=false`, the deploy failed or was `SucceededPartial`, or the re-probe still shows a false toggle.

`manual_actions` always includes the login-behavior gap entry on non-blocked reports; `deploy_id` is `null` for `reused`/`action_needed`; `blocking_issue` names the failure only when `status: blocked`.

## Limitations

- Configures only `OmniChannelSettings`, always with all five toggles true — other `Settings` types belong to `platform-metadata-deploy`.
- Cannot turn the login-behavior radio (no public API on v66) — it only surfaces the click-path.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Before a deploy — the five toggles' semantics, dependencies, and the login-behavior caveat |

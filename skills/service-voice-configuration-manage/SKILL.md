---
name: service-voice-configuration-manage
description: "Lists, creates, updates, and deletes native Contact Center voice configurations (VoiceTelephonyDefinition) via the thb-voice-config Connect API. Also inspects a configuration's dialing prefix, region, default caller Id, pre-dial flow, and assigned users/profiles, resolving the Ids it needs (pre-dial flow, assignable users, profiles, caller-line numbers) from the org before writing. Use when the user asks to list/view/create/update/delete a voice configuration, change a configuration's dialing prefix, region, caller Id, or pre-dial flow, or assign users/profiles to a configuration. TRIGGER when the user says create a voice configuration, update the voice config, list voice configurations, assign users to a voice configuration, or delete a voice configuration. DO NOT TRIGGER for procuring phone numbers or creating messaging/voice channels (that is service-agentforce-contact-center-coordinate), for outbound dialing/campaign setup, or for any non-voice configuration."
allowed-tools: Bash(sf org display:*) Bash(sf api request rest:*) Bash(sf data query:*) Bash(scripts/*) Bash(./scripts/*) Bash(bash scripts/*) Bash(jq:*) Read AskUserQuestion
metadata:
  version: "1.0"
  minApiVersion: "68.0"
  accessCheck: "ThunderbirdVoice.orgHasNativeVoiceAllowed"
  domains: ["Service", "Agentforce"]
  relatedSkills:
    - "service-agentforce-contact-center-coordinate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# service-voice-configuration-manage: Manage native Contact Center voice configurations

Drives the `thb-voice-config` Connect API to manage voice configurations
(`VoiceTelephonyDefinition`, key prefix `1pK`) for native Contact Center. A voice configuration
holds a dialing prefix, a dialing region, a default caller Id, a pre-dial flow, and a set of
assigned users and profiles. This skill lists and inspects configurations, creates new ones,
updates existing ones, and deletes them — resolving the Ids a configuration needs from the org
before writing.

## Scope

- **In scope**: listing voice configurations, reading a single configuration, creating a
  configuration, updating a configuration (fields and user/profile assignments), deleting a
  configuration, and resolving the supporting Ids (pre-dial flow, assignable users, profiles,
  caller-line numbers) + the static region/dialing-prefix list.
- **Out of scope**: authenticating or provisioning the org (must already be authenticated);
  procuring phone numbers or creating `MessagingChannel`/voice channels (use
  `service-agentforce-contact-center-coordinate`); outbound dialing / campaign configuration;
  and any non-voice configuration.

---

## Prerequisites

- **Authenticated org** — this skill never runs an interactive login.
- **Native Contact Center admin access** — every endpoint requires it.
  A caller without it gets `403`; stop and tell the user
  they need Contact Center admin access.

---

## Required Inputs

Gather or confirm before acting:

- **Target org**: an already-authenticated org. If the user names an alias, use it. Otherwise
  resolve the default org with `sf org display --json` and read `result.alias` (falling back to
  `result.username`); use that as `<alias>` for every script. Never run an interactive login.
- **Operation**: list, get, create, update, or delete.
- **For get / update / delete**: the target configuration's Id (`1pK…`). If the user names a
  configuration by label, resolve the Id with `list-configurations.sh` first.
- **For create / update**: the field values (see Step 5/6). Resolve any flow / user / profile /
  caller-line Ids with the lookup scripts before building the request body.

---

## Workflow

All steps are sequential. If a step fails or any API call returns a non-2xx, stop and report the
error rather than continuing.

**Run autonomously.** Do not block on the user. Infer every value you can from the request, resolve
the rest from the curated list and the lookup scripts, and proceed — then report what you chose.
Ask a clarifying question only when a human is available *and* the request is genuinely ambiguous
*and* you cannot resolve a safe default; never ask merely to confirm, and never stop to ask about
connecting or authenticating an org. When no human is available (headless / automated runs), do
**not** call `AskUserQuestion` — proceed with the most likely interpretation and resolved defaults.

1. **Confirm the org connection** — run `sf org display --target-org <alias> --json` and read
   `result.instanceUrl`. If it fails, report that the org must be authenticated first, then stop.

2. **Determine the operation** — pick **list / get / create / update / delete** from the user's
   request ("create…" → create, "show/read/view…" → get, "list…" → list, "change/update…" →
   update, "delete/remove…" → delete). If a human is available and the request is truly ambiguous
   you may confirm; otherwise proceed with the most likely operation. Branch below.

3. **List** — run `scripts/list-configurations.sh <alias>`. Present the returned
   `configurations` as a numbered list (`name`, `developerName`, `id`). This is also how you
   resolve an Id for get/update/delete when the user named a configuration by label.

4. **Get** — run `scripts/get-configuration.sh <alias> <configId>`. Present the full detail.
   Remember the output uses the read-side field names (`dialingRegion`, `preDialFlowId`,
   `defaultCallerIdentifier`) — see `references/voice_config_api.md`.

5. **Create** — read `references/voice_config_api.md` for the input contract, then:
   1. Collect `name` (required). Optionally collect `developerName` (immutable after create — if
      omitted the platform derives it), `dialingPrefix`, `region`, `description`.
   2. For `region` + `dialingPrefix`, resolve the value from `assets/regions.json`: match the
      region the user named to the closest `regionCode` (e.g. "US West" / "US East" / "US" → `US`;
      a country name → its entry) and use that entry's `dialingPrefix`. Accept a value the user
      gave verbatim. Report the region chosen. Only if a human is available and no entry plausibly
      matches should you present the list; never block waiting for a choice.
   3. Resolve optional Ids with the lookup scripts (read `references/lookups.md`) — never hardcode
      Ids. Pick the entry that matches the user's request; if a human is available you may present
      the list for selection, but never block — choose the best match and report it:
      - `callOriginationFlowId` ← `scripts/lookup-flows.sh <alias>` (a flow `durableId`)
      - `userIds` ← `scripts/lookup-users.sh <alias>` (User Ids)
      - `profileIds` ← `scripts/lookup-profiles.sh <alias>` (Profile Ids)
      - `defaultCallerId` ← `scripts/lookup-caller-lines.sh <alias>` (a caller-line `code`)
   4. Build the `CreateVoiceConfigurationInputRepresentation` JSON with the **input** field names
      and run `scripts/create-configuration.sh <alias> '<json-body>'`. Capture the returned `id`.
   5. Read the new configuration back with `get-configuration.sh` and show it.

6. **Update** — read `references/voice_config_api.md`, then:
   1. Resolve the `configId` (Step 3 if needed) and fetch the current state with
      `get-configuration.sh` so you can show what changes.
   2. Collect the changes. **`name` is required** on every update. **Do not send
      `developerName`** (immutable). Translate read-side values back to input field names
      (`dialingRegion`→`region`, `preDialFlowId`→`callOriginationFlowId`,
      `defaultCallerIdentifier`→`defaultCallerId`). Resolve any new flow/user/profile/caller-line
      Ids with the lookup scripts.
   3. For assignments: `userIds` / `profileIds` **replace the full list**. To add or remove one,
      fetch the current assignments, edit the list, and send the whole set. Omit the field to
      leave assignments untouched; send `[]` to clear them. Proceed with the set implied by the
      request and report the final intended set; if a human is available you may confirm first, but
      do not block.
   4. Run `scripts/update-configuration.sh <alias> <configId> '<json-body>'`, then read it back.

7. **Delete** — resolve the `configId` (Step 3 if the user named it by label). When the request
   explicitly identifies the configuration to delete, proceed; if a human is available you may
   confirm first (naming the configuration), but do not block. Then run
   `scripts/delete-configuration.sh <alias> <configId>`. The org's **default** configuration
   cannot be deleted (`400`); surface that clearly if it happens. If the named configuration does
   not exist, stop and report that plainly rather than deleting anything else.

8. **Report** — give a short summary of what you did: the operation performed
   (list / get / create / update / delete), the target org, the affected configuration (its
   `id` (`1pK…`) and `name` for a single-record op), any fields changed on an update, and the
   final user/profile assignment counts. End with a one-line outcome stating **SUCCESS** or the
   exact error and the step it failed at.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Never run an interactive login; require a pre-authenticated org alias | Auth/org lifecycle is out of scope; keeps the skill portable |
| Call the Connect API via `sf api request rest`; never extract the access token | Uses the CLI's stored session for `--target-org` — no raw token handling |
| Never pass `--json` to `sf api request rest` | The command has no such flag; its body is already JSON. (`sf data query` in the lookups *does* use `--json`) |
| Never hardcode flow / user / profile / caller-line Ids | They are org-specific; resolve them with the lookup scripts |
| `name` is required on both create and update | The service has no null-guard; a missing name returns 500, not a clean error |
| Do not send `developerName` on update | It is immutable after create; the update input does not accept it |
| `userIds` / `profileIds` replace the full assignment list | Not additive — send the complete intended set, or omit to leave untouched |
| Stop and report on any non-2xx API response | Partial changes left silent are worse than a clear failure |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Read a config, then an update fails on unknown fields | The GET output uses read-side names; translate `dialingRegion`/`preDialFlowId`/`defaultCallerIdentifier` back to `region`/`callOriginationFlowId`/`defaultCallerId` before sending |
| `409 CONFLICT` on create | A configuration with that `developerName` already exists — pick another or reuse the existing one |
| `400` on delete | The default configuration cannot be deleted — confirm the target is not the org default |
| `403` on any call | The caller is not a native Contact Center admin — stop; the user must have that access |
| An update unexpectedly removed users/profiles | `userIds`/`profileIds` replace the full list; always send the complete intended set |
| Create returned `200` but a user/profile isn't assigned | Create is lenient — a `200` + `id` means the record was created, but user/profile assignment is best-effort and not rolled back if it fails. Always read the config back (Step 5, final sub-step) and confirm the assignments landed |
| Regions list seems incomplete | `assets/regions.json` is a curated static list (regions are not queryable) — extend it or let the user supply `region`/`dialingPrefix` directly |

---

## Output Expectations

This skill reads and writes `VoiceTelephonyDefinition` records in the target org:

- **list / get**: a presented list or a single configuration's detail (no changes).
- **create**: a new configuration (returns its `id`), read back and shown.
- **update**: the modified configuration, read back and shown.
- **delete**: confirmation the configuration was removed.
- A short final report per Step 8.

---

## Cross-Skill Integration

Pairs with `service-agentforce-contact-center-coordinate`, which procures phone numbers and
creates the voice `MessagingChannel`. This skill owns the voice *configuration* record only; it
does not procure numbers or create channels. Hand off number/channel work to that skill.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/voice_config_api.md` | Any operation — the CRUD contract, field-name input/output mapping, and status codes |
| `references/lookups.md` | Steps 5–6 — how to resolve flow/user/profile/caller-line Ids and the static-regions note |
| `assets/regions.json` | Steps 5–6 — static region + dialing-prefix choices |
| `scripts/list-configurations.sh` | Step 3 — list all configurations |
| `scripts/get-configuration.sh` | Step 4 — read one configuration |
| `scripts/create-configuration.sh` | Step 5 — create a configuration |
| `scripts/update-configuration.sh` | Step 6 — update a configuration |
| `scripts/delete-configuration.sh` | Step 7 — delete a configuration |
| `scripts/lookup-flows.sh` | Step 5/6 — resolve a pre-dial flow `durableId` for `callOriginationFlowId` |
| `scripts/lookup-users.sh` | Step 5/6 — resolve assignable User Ids for `userIds` |
| `scripts/lookup-profiles.sh` | Step 5/6 — resolve Profile Ids for `profileIds` |
| `scripts/lookup-caller-lines.sh` | Step 5/6 — resolve a caller-line `code` for `defaultCallerId` |

# Platform enablement — ordered toggle sequence (concrete write paths)

Read at Workflow step 2, item 3 ("Enable the platform toggles"). Do these after the Step 1 preflight gate passes and before agent creation. **Reversibility differs per toggle** — see the *Reversible?* column below; never promise a rollback you haven't confirmed, and warn the user before any flip that can't be undone.

> **Each toggle uses a DIFFERENT write path** — they are not all `IndustriesSettings` PUT fields, but two of them (the SRA toggle and Omni-Channel) are the same *shape* of headless-metadata PUT on their own settings type. Do not assume one path. The table gives the write path per toggle; on failure, walk the tier ladder to UI/MDAPI.

## The EDU write path — `IndustriesSettings`, not `setup/org/preferences`

Both `enableEducationCloud` (and the `enableXXX` domain toggles) **and** the SRA toggle `enableStudentRecruitmentAgent` are written via the **`IndustriesSettings` headless-metadata PUT**. The `setup/org/preferences` route is **not** wired on the headless gateway — a PUT to it returns `ROUTE_NOT_FOUND`, and a Tooling sObject PATCH on `IndustriesSettings` returns `400 JSON_PARSER_ERROR`. Do not use either; use the PUT (Toggle 2 below). Read the enablement flag back from the top-level `Is*Enabled` projection field.

## Ordered enable sequence

This table lists **only the three toggles the skill actually flips.** Their external-grant preconditions (Einstein-for-EDU license, Agentforce provisioning) have no write path and are verified — not enabled — at Step 1; see the note below.

| Order | Toggle | Write path | Exact name | Tier | Reversible? | Currency |
|---|---|---|---|---|---|---|
| 1 | **Turn on Einstein** (Einstein Setup) | **`EinsteinGptSettings` headless-metadata PUT** flipping member `<enableEinsteinGptPlatform>` (fullName `EinsteinGpt`) — same shape as Toggles 2–3. (Gates the SRA toggle's editAccess.) See "Toggle 1 — write + read" below. | member **`enableEinsteinGptPlatform`** / read **`IsEinsteinGptPlatformEnabled`** (org-pref name `EinsteinGPTPlatformEnabled`) | T1 `EinsteinGptSettings` PUT → T2 `sf` → T3 UI (Setup → Einstein Setup) | **Toggles both ways** (`true`↔`false`) — idempotent set, safe to re-write to the desired state | ✅ **in-skill** — check, enable if off |
| 2 | **Enable Student Recruitment Agent** | **`IndustriesSettings` headless-metadata PUT** flipping member `<enableStudentRecruitmentAgent>`; read back the top-level projection `IsStudentRecruitmentAgentEnabled` | member **`enableStudentRecruitmentAgent`** / field **`IsStudentRecruitmentAgentEnabled`** | T1 IndustriesSettings PUT → T2 `sf` → T3 UI | **Toggles both ways** (`true`↔`false`) — idempotent set, safe to re-write to desired state | ✅ current (gate `orgHasStudentRecruitmentAgentBetaAccess`) |
| 3 | **Enable Omni-Channel** | **`OmniChannelSettings` headless-metadata PUT** flipping member `<enableOmniChannel>` (fullName `OmniChannel`) — NOT an EDU toggle, NOT org-pref | field **`enableOmniChannel`** | T1 `/headless/metadata` PUT → T2 `sf`-deploy → T3 UI | Re-writing `true` is idempotent, but **treat as forward-only** — Omni-Channel is not expected to be disabled once on; don't attempt to turn it off | ✅ **required for channel deploy** — the inbound routing flow's Route Work element routes the Messaging service channel to the agent through a fallback queue (all Omni-Channel objects — see `routing.md`) |

> **Preconditions — verified in `prerequisites.md`, NOT flipped here.** Two external grants have no write path but gate the toggles above: the **Einstein-for-Education-Cloud license** (`EinsteinForEducationCloud`, P3 — part of the SRA toggle's `editAccess`; if absent, Toggle 2 can't be enabled — report and stop) and **Agentforce provisioning** (P4 — must exist before agent creation; the `BotDefinition` existence check is tier-1-attemptable via `/query` → `sf` → UI, but provisioning itself is a Salesforce grant). Both are verify-only Step-1 gates (see `prerequisites.md` gates P3/P4); do not attempt to enable them here.

### Toggle 1 — Einstein Setup (write + read)

`EinsteinGptSettings` is **on the `/headless/metadata` allowlist (read + write)** — same settings-file pattern as `IndustriesSettings`/`OmniChannelSettings`.

1. **Tier 1 — headless metadata PUT** (write-enabled `dispatch`, NOT `dispatch_readonly`): `PUT /services/data/vXX/headless/metadata`, body `{"type":"EinsteinGptSettings","fullName":"EinsteinGpt","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><EinsteinGptSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableEinsteinGptPlatform>true</enableEinsteinGptPlatform></EinsteinGptSettings>"}`. Synchronous — `200 {"results":[{"success":true,...}]}`, no async job. ⚠️ **Confirmed failure mode on some orgs:** this PUT can instead return `400 UNSUPPORTED_OPERATION — "MetadataCrud does not support UPDATE on type: EinsteinGptSettings"`. Treat that exact error as a clean T1→T2/T3 drop signal — don't retry or reshape the payload. ⚠️ The write member is **`enableEinsteinGptPlatform`** (lowercase `Gpt`) — **NOT** `EinsteinGPTPlatformEnabled` (the org-pref name) nor the `Is*Enabled` read projection; a wrong member is silently dropped and the PUT no-ops. `fullName` is **`EinsteinGpt`**.
2. **Tier 2:** `sf`-deploy the `EinsteinGptSettings` member.
3. **Tier 3** UI: Setup → Einstein Setup → turn on.

**Verify (any path):** either a tooling **query** `SELECT IsEinsteinGptPlatformEnabled FROM EinsteinGptSettings` (returns `200` with the top-level projection), or the headless GET `/headless/metadata?type=EinsteinGptSettings&fullName=EinsteinGpt` and confirm `<enableEinsteinGptPlatform>true</enableEinsteinGptPlatform>` in the returned `xmlRep`. ⚠️ The headless GET can hit the same `UNSUPPORTED_OPERATION — MetadataCrud does not support READ` wall as the write above. **Use the tooling query as the primary verify** on orgs where the write 400'd — don't rely on the headless GET as the fallback read in that case. ⚠️ Do **NOT** use the GET-*by-DurableId* (`/tooling/sobjects/EinsteinGptSettings/<DurableId>`) — it 400s `MALFORMED_QUERY: column Metadata not found` (that object exposes no `Metadata` column); the tooling **query** form above is the reliable read.

### Toggle 2 — the write attempt order (RecruitmentAgentEnabled)

> **WARNING: Precondition — verify the license gate first.** The `RecruitmentAgentEnabled` pref's `editAccess` is `OrgPermissions.EinsteinForEducationCloud && EinsteinGPT.orgHasEinsteinGPTEnabled` (+ `isAdminUser && ViewSetup`; a System Administrator satisfies the admin half). If unmet, the toggle can't be enabled. The **license** is a verify-only prereq (P3) — report and stop; **Einstein Setup** (Toggle 1) the skill can enable. Don't fall through the write tiers when the license is missing — they fail identically. (The runtime gate also ANDs in the `StudentRecruitmentAgent256` Gater — Salesforce-granted, not flippable here.)

1. **Tier 1 — headless metadata PUT.** `PUT /services/data/vXX/headless/metadata` via the **write-enabled `dispatch` tool** (NOT `dispatch_readonly` — read-only can return `success:true` **without writing**, so the PUT silently no-ops; always cold-verify), body:
   ```json
   {"type":"IndustriesSettings","fullName":"Industries","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableStudentRecruitmentAgent>true</enableStudentRecruitmentAgent></IndustriesSettings>"}
   ```
   Synchronous — returns `200 {"results":[{"success":true,...}]}`, **no async job, no polling.** Write member is the MDAPI name **`enableStudentRecruitmentAgent`** (NOT the `Is*Enabled` read projection). **Toggles both ways** (`true`↔`false`), so it is an idempotent set — safe to write to the desired state. `success:true` alone is not proof the value changed — always VERIFY with the tooling GET below (cold re-read the top-level projection `IsStudentRecruitmentAgentEnabled`).
   > **WARNING:** If the toggle can't be enabled and the license precondition above is unmet, stop and fix the license — do NOT retry lower tiers, they fail identically.
2. **Tier 2 (`sf`, if a shell is present):** `sf`-deploy the `IndustriesSettings` member (fallback if the headless PUT is unavailable on the gateway).
3. **Tier 3 (UI):** Setup → Set Up Education Cloud → Set Up Agentforce/Einstein for Education Cloud → **Enable Student Recruitment Agent** → Save.

**Paths that do NOT work (don't waste a call on them):** `PATCH setup/org/preferences/RecruitmentAgentEnabled` and a Tooling sObject `PATCH` on `IndustriesSettings/<DurableId>` — the same two dead ends called out in the opening "EDU write path" note above (`ROUTE_NOT_FOUND` / `400 JSON_PARSER_ERROR` respectively).

**Verify (any path):**

The enablement pref is reflected on the `IndustriesSettings` describe. Reading it by **known DurableId** is a tier-1 call — `GET .../tooling/sobjects/IndustriesSettings/<DurableId>` via `dispatch_readonly` (the plain, non-tooling `/sobjects/` path 404s — this object is tooling-only), using the constant DurableId `bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=` directly. No discovery query is needed — the DurableId is a deterministic constant for this singleton.

**Read/write name asymmetry.** One switch, three names: org-pref `RecruitmentAgentEnabled` = MDAPI write member `enableStudentRecruitmentAgent` = read projection `IsStudentRecruitmentAgentEnabled` = Setup UI *"Turn On Student Recruitment Agent."* The **WRITE** (`xmlRep`) uses the MDAPI member `<enableStudentRecruitmentAgent>`; the **READ/VERIFY** inspects the top-level flat projection `IsStudentRecruitmentAgentEnabled` (also mirrored in `.Metadata.enableStudentRecruitmentAgent`). Read the top-level projection, not `.Metadata.*`-only, since some `Is*Enabled` flags have no Metadata sibling.

```bash
# GET-by-DurableId (headless, dispatch_readonly): tooling/sobjects/IndustriesSettings/<DurableId>
# constant DurableId: bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=
# then inspect the TOP-LEVEL field IsStudentRecruitmentAgentEnabled == true (NOT .Metadata.*)
```

### Toggle 3 — Omni-Channel (required before channel deploy)

Omni-Channel is a Service Cloud platform feature, enabled by setting `OmniChannelSettings` `<enableOmniChannel>true</enableOmniChannel>`. It is **required to deploy either agent to a channel**: the inbound routing flow's Route Work element routes the Messaging service channel to the agent through a required fallback queue, and the queue / routing config / service channel are all Omni-Channel objects. Enable it before the channel-deploy step (`routing.md`).

`OmniChannelSettings` is **on the `/headless/metadata` allowlist (read + write)** — same settings-file pattern as `IndustriesSettings`:

1. **Tier 1 — headless metadata PUT** (write-enabled `dispatch`, NOT `dispatch_readonly`): `PUT /services/data/vXX/headless/metadata`, body `{"type":"OmniChannelSettings","fullName":"OmniChannel","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><OmniChannelSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableOmniChannel>true</enableOmniChannel></OmniChannelSettings>"}`. Synchronous — returns `200 {"results":[{"success":true,...}]}`, no async job. ⚠️ **Confirmed failure mode on some orgs:** this PUT can instead return `400 UNSUPPORTED_OPERATION — "MetadataCrud does not support UPDATE on type: OmniChannelSettings"`. Treat that exact error as a clean T1→T2/T3 drop signal — don't retry or reshape the payload. `fullName` is the singular **`OmniChannel`**.
2. **Tier 2:** `sf`-deploy the `OmniChannelSettings` member.
3. **Tier 3** UI: Setup → Omni-Channel Settings → Enable.

**Verify (any path):** GET `/headless/metadata?type=OmniChannelSettings&fullName=OmniChannel` via `dispatch_readonly` and confirm `<enableOmniChannel>true</enableOmniChannel>` in the returned `xmlRep`. `success:true` on the PUT is not proof by itself — read it back. ⚠️ **Confirmed failure mode:** this GET can 400 `UNSUPPORTED_OPERATION — "MetadataCrud does not support READ on type: OmniChannelSettings"`. Don't substitute a tooling query — `SELECT IsOmniChannelEnabled FROM OmniChannelSettings` 400s `INVALID_TYPE` too. On either failure, verify via Setup UI instead.

## UI fallbacks (retained — use if the primary path fails on the org)

- Order 1: Setup → Einstein Setup → turn on.
- Order 2: Setup → Set Up Education Cloud → Set Up Agentforce/Einstein for Education Cloud → **Enable Student Recruitment Agent** → Save.
- Order 3: Setup → Omni-Channel Settings → Enable *(required before channel deploy)*.

## Notes

- **Required current gates:** Agentforce provisioned (P4, verify), `EinsteinForEducationCloud` license (P3, verify), `RecruitmentAgentEnabled` (Toggle 2), Omni-Channel (Toggle 3).
- **Both Einstein layers are required** — the platform pref `EinsteinGPTPlatformEnabled` (skill flips, Toggle 1) **and** the license-provisioned `EinsteinForEducationCloud` org perm (verify-only, P3 in `prerequisites.md`).
- **Omni-Channel (Toggle 3) is required for channel deploy** — the inbound routing flow routes Messaging → agent through a fallback queue; queue, routing config, and service channel are Omni-Channel objects. Enable it before the channel-deploy step. See `routing.md` for the full routing layer.

# OmniChannelSettings — API notes

Load this reference **only when a deploy is actually needed** (i.e., after `detect-existing.sh` returned `all_enabled: false`). It covers the five toggles' semantics, cross-field validators, and the login-behavior UI-only caveat.

**Metadata type:** `Settings` with name `OmniChannel` (deployed as `Settings:OmniChannel`).
**API version verified:** v66 (Summer '26 baseline).
**Whole-document type:** always deploy the full XML, never PATCH individual toggles.

---

## The five toggles

All five ship as `true` in this skill's `assets/force-app/main/default/settings/OmniChannel.settings-meta.xml`. This skill does not accept per-toggle overrides — a user who wants a subset should invoke `platform-metadata-deploy` directly with their own XML.

### 1. `enableOmniChannel` (master switch)

**Effect:** Enables the Omni-Channel feature on the org. When `false`, no downstream Omni entity can be created (`ServicePresenceStatus`, `PresenceUserConfig`, `QueueRoutingConfig`, `WorkSkillRouting`, etc. all reject with `INVALID_TYPE`).

**Values:** `true` | `false`.

**Dependencies:** Must be `true` for any of the other four toggles to have meaningful effect.

**Reversibility:** Setting to `false` after enablement is not blocked, but is destructive — existing Omni entities remain but stop routing work. Do not disable in a production-like environment without explicit user acknowledgement.

### 2. `enableOmniSkillsRouting`

**Effect:** Enables skills-based routing. Required for:
- `WorkSkillRouting` rules to fire
- `routeWork` action in Flow with `routingType=SkillsBased`
- `Skill` records to influence work-item assignment

**Values:** `true` | `false`.

**Dependencies:** Requires `enableOmniChannel=true`.

### 3. `enableOmniSecondaryRoutingPriority`

**Effect:** Enables the secondary routing priority field on queue routing configurations. Allows two-level priority sorting when multiple work items match the same queue.

**Values:** `true` | `false`.

**Dependencies:** Requires `enableOmniChannel=true`.

### 4. `enableOmniStatusCapModel`

**Effect:** Enables the status-based capacity model on `ServiceChannel`. When true, agents can have different capacity ceilings based on which presence status they are in.

**Values:** `true` | `false`.

**Dependencies:** Requires `enableOmniChannel=true`.

### 5. `enableOmniAutoLoginPrompt` (⚠ caveat — see below)

**Effect (documented):** Should control the Omni-Channel login-prompt behavior when an agent opens a new window/tab.

**Effect (observed):** Deploys cleanly and round-trips through retrieve — but does **not** drive the UI radio at *Setup → Omni-Channel Settings → "Define login behavior when an agent using Omni-Channel opens a new window or tab"*. Flipping the value `true`/`false` re-retrieves the same value while the UI radio stays unchanged. The login-behavior radio is not reachable through this metadata field.

**Values:** `true` | `false`.

**Dependencies:** Requires `enableOmniChannel=true`.

**This skill still deploys the toggle as `true`.** The XML deploys cleanly and other Omni features may depend on it internally; not shipping it would be an incomplete base-settings deploy.

---

## Cross-field validators

The Metadata API does **not** enforce cross-field validators on `OmniChannelSettings` — every combination of the five booleans is accepted by the deploy. However, functional dependencies exist at runtime:

| If this is `true` | Then this must also be `true` (for the feature to actually work) |
|---|---|
| `enableOmniSkillsRouting` | `enableOmniChannel` |
| `enableOmniSecondaryRoutingPriority` | `enableOmniChannel` |
| `enableOmniStatusCapModel` | `enableOmniChannel` |
| `enableOmniAutoLoginPrompt` | `enableOmniChannel` |

Since this skill sets all five to `true`, the dependencies are automatically satisfied.

---

## Deploy metadata name

```text
Settings:OmniChannel
```

Command:

```bash
cd assets
sf project deploy start --target-org <org-alias> --metadata "Settings:OmniChannel" --json
```text

Expected response:

```json
{
  "status": 0,
  "result": {
    "id": "0AfRZ000001Yhef0AC",
    "status": "Succeeded",
    "success": true,
    "numberComponentsDeployed": 1,
    "numberComponentsTotal": 1
  }
}
```

**Failure modes:**

- `status: Failed` + `componentFailures[0].problem: "Namespace: unable to deploy ..."` — org does not have Omni-Channel provisioned at all. Rare on Service Cloud orgs; possible on stripped-down trial orgs. Fail the skill; the user must contact Salesforce for org-shape correction.
- `UNKNOWN_EXCEPTION` during retrieve or deploy — transient server-side error. Retry once before failing.
- `LightningDomain` error on retrieve/deploy — org was authenticated with the `.lightning.force.com` URL instead of the My Domain URL. Re-authenticate with the My Domain URL. This is an auth bug, not an API issue.

---

## Login-behavior UI-only gap (surface always)

The `enableOmniAutoLoginPrompt` toggle does not drive the *Setup → Omni-Channel Settings → "Define login behavior when an agent opens a new window/tab"* three-way radio. The full write-up (root cause, coordinator behavior) lives in the `service-omni-channel-setup-coordinate` skill's gap catalog reference.

**Skill behavior:** always include the login-behavior click-path in the report's `manual_actions` array, even for `reused` (no-op) runs. The operator may still need to click the radio manually to select their preferred behavior.

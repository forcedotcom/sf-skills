---
name: service-de-channel-settings-configure
description: "Configure settings on an already-existing Enhanced `MessagingChannel` (any type — WhatsApp, Text/SMS, LINE, Apple, Facebook, EmbeddedMessaging), given its `{CHANNEL_ID}`. Covers five facets: consent (ConsentType + per-language keyword records), automated responses, messaging keywords, session-inactivity timeouts, and pre-chat parameters. Consent + a matching language-keyword record are required for activation's readiness check. TRIGGER when setting or changing settings on a channel that already exists (opt-out keyword, consent type, double opt-in confirmation, initial/help auto-responses, OptIn/OptOut keywords, session-inactivity timeout) — typically between insertion/routing and activation, or on a live channel. DO NOT TRIGGER for creating a new channel (`service-de-channel-create`), deploying a MIAW/EmbeddedMessaging channel from metadata XML (`service-digital-engagement-channel-configure`), setting routing (`service-de-channel-routing-configure`), or activating a channel (`service-de-channel-activate`)."
metadata:
  version: "2.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-activate"
    - "service-de-channel-create"
    - "service-de-channel-routing-configure"
    - "service-de-headless-channel-configure"
    - "service-digital-engagement-channel-configure"
---

# Configuring Channel Settings

## What this skill does

Configures settings on an **already-existing Enhanced `MessagingChannel`** (identified by `{CHANNEL_ID}`), for any message type. It groups five facets; you only run the ones the caller asks for.

| # | Facet | Write surface | Applies to |
| --- | --- | --- | --- |
| 1 | **Consent** — `ConsentType` + `OptInPrompt`/`DoubleOptInPrompt` on the channel, plus per-language `MsgChannelLanguageKeyword` records | **Data/SObjects API** (`sf data update/create record`) | all Enhanced types |
| 2 | **Automated responses** — `<automatedResponses>` (initial, agent-engaged/-ended, opt-in prompt/confirmation, help, opt-out, inactive/idle) | **Metadata API** deploy | all Enhanced types |
| 3 | **Messaging keywords** — `<messagingKeywords>` (OptIn/OptOut/Help keyword groups per language) | **Metadata API** deploy | all Enhanced types |
| 4 | **Session inactivity** — `endUserIdleTimeOut`, `endUserIdleAction`, `endInactiveSessionTimeOut`, `isAgentMessageResetInactivityEnabled` | **Metadata API** deploy | **MIAW-only** (reset-flag also Apple/Facebook) |
| 5 | **Pre-chat parameters** — `<customParameters>` / `<standardParameters>` | **Metadata API** deploy | **MIAW pre-chat only** (rare) |

**This skill is mixed-surface.** Consent (facet 1) is written with the Data API on the live record. Facets 2–5 live only in the channel's **metadata** and are configured by retrieving the channel's `.messagingChannel-meta.xml`, editing it, and deploying it back. Verified live on sdb6 (2026-09): every Data/Connect/Tooling read of the facet-2–5 fields fails `INVALID_TYPE`/"No such column" — they are Metadata-API-only.

**Per-type applicability is verified, not assumed** (from a live retrieve of real channels of each type). Facets 2 and 3 are genuinely type-agnostic. Facet 4's four timeout fields appear **only on MIAW**; only `isAgentMessageResetInactivityEnabled` extends to Apple/Facebook, and SMS/WhatsApp/LINE carry no inactivity fields at all. Facet 5 appears only on MIAW channels that use pre-chat. Scope per-type accordingly — do **not** deploy a facet a type doesn't support.

## When to use (TRIGGER)

Trigger this skill when the user wants to configure or change settings on a channel that **already exists**, e.g.:

- "set the opt-out keyword / consent type on my WhatsApp channel"
- "add a double opt-in confirmation to this messaging channel"
- "configure the initial / agent-engaged / help auto-response on my Apple channel"
- "add OptIn/OptOut/Help keywords to my Text channel"
- "set the session inactivity timeout / idle action on my MIAW channel"
- "change the auto-responses on channel 0MjXXXXXXXXXXXX"

**DO NOT TRIGGER — hand off instead:**

- **Creating or deploying a new channel from a metadata XML file (MIAW / EmbeddedMessaging)** → `service-digital-engagement-channel-configure`. That skill *creates* an Embedded Messaging channel from XML; **this** skill only configures a channel that already exists (it needs a live `{CHANNEL_ID}`, prefix `0Mj`).
- **Inserting a brand-new channel of any type** → `service-de-channel-create`.
- **Setting routing / queue / SessionHandler** → `service-de-channel-routing-configure`.
- **Flipping a channel live** → `service-de-channel-activate`.

## Where this fits

Part of the Enhanced-channel headless pipeline: `service-de-channel-create` → `service-de-channel-routing-configure` → **this skill** → `service-de-channel-activate`. Activation's readiness check requires **both** routing and consent, so at minimum run facet 1 before activating. The `service-de-headless-channel-configure` orchestrator sequences the pipeline automatically; invoke this skill directly to configure settings on their own. For the MIAW-specific channel-*creation-from-XML* flow, see the sibling `service-digital-engagement-channel-configure`.

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/language-keywords.md` | Facet 1: creating/updating `MsgChannelLanguageKeyword` records — field list, CSV keyword semantics, create-vs-update, Unified-SMS help/custom rules. |
| `references/channel-settings-facets.md` | Facets 2–5: the Metadata-API retrieve→edit→deploy flow, the full `<automatedResponses>` type/shape catalog (12 types, 2 content shapes), `<messagingKeywords>`, the inactivity fields, and per-type applicability. |
| `references/gotchas.md` | Troubleshooting an unexpected result, or before modifying this skill. |
| `references/worked-examples.md` | Reference runs of the ImplicitOptIn/ExplicitOptIn/DoubleOptIn consent paths. |

## When NOT to use this skill

- **The channel isn't Enhanced.** These settings apply to `PlatformType=Enhanced` channels only. Stage 1 confirms this and stops otherwise.
- **The channel doesn't exist yet.** Run `service-de-channel-create` first; this skill expects a real `MessagingChannel.Id` (prefix `0Mj`).
- **You're configuring consent on an outbound-only channel.** Outbound-only channels pass the consent-readiness check automatically — nothing to configure for facet 1.

## Inputs (from caller)

- `{CHANNEL_ID}` — a 15/18-char `MessagingChannel.Id` (prefix `0Mj`). Must already exist and be Enhanced.
- `{FACETS}` — optional; which facets to configure (`consent`, `auto-responses`, `keywords`, `inactivity`, `parameters`). If omitted, infer from the request or ask.
- `{CONSENT_TYPE}` — optional (facet 1); `ImplicitOptIn` | `ExplicitOptIn` | `DoubleOptIn`.
- `{LANGUAGE}` — optional; locale for keyword/response records (e.g. `en_US`). Default `en_US`.
- `{ORG_ALIAS}` — optional; `sf` target-org alias. Default: `sf config get target-org`.

Facet-specific values (prompts, keyword lists, response text, timeout minutes) are collected interactively per facet, or accepted if pre-supplied.

## Output (to caller)

**Success:**
```json
{"ok": true, "channelId": "0Mj...", "messageType": "WhatsApp",
 "facetsConfigured": ["consent","auto-responses"],
 "consent": {"consentType": "ExplicitOptIn", "languageKeywordId": "3Or...", "activationReady": true},
 "metadataDeploy": {"status": "Succeeded", "facets": ["auto-responses","keywords"]}}
```

**No change needed / precondition / failure:**
```json
{"ok": true, "noop": true, "message": "Requested settings already configured"}
{"ok": false, "kind": "not-enhanced", "hint": "settings apply to Enhanced channels only; this channel is PlatformType=<x>"}
{"ok": false, "kind": "facet-not-applicable", "hint": "<facet> is not supported on <messageType> channels"}
{"ok": false, "kind": "channel-patch-failed" | "keyword-record-failed" | "metadata-deploy-failed" | "verify-failed", "message": "..."}
```

---

## Stage 1: Read the channel and decide facets

Read the channel; confirm it exists and is Enhanced; capture `MessageType` (drives per-type applicability).

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, PlatformType, MessageType, MessagingPlatformKey, ConsentType, OptInPrompt, DoubleOptInPrompt, IsRequireDoubleOptIn FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" \
  --json > /tmp/cs-channel.json
```

- Channel missing → halt: `Error: Channel {CHANNEL_ID} not found — check the id, or run service-de-channel-create first.`
- `PlatformType != 'Enhanced'` → emit `{ok:false, kind:"not-enhanced", ...}` and stop.

Decide which facets to run from `{FACETS}` or the request. For each requested facet, check per-type applicability (table above / `references/channel-settings-facets.md`); if a facet doesn't apply to this `MessageType`, emit `{ok:false, kind:"facet-not-applicable", ...}` for that facet (or skip it and note it) rather than deploying an unsupported field.

**sf CLI is slow, not broken.** Calls to this org routinely take 2–4 minutes (heavy CLI startup + slow round-trip). Run each `sf` command with a generous timeout; a slow return is normal, not a hang.

---

## Stage 2: Facet 1 — Consent (Data API)

Run when `consent` is requested (and always before activation). Read the existing keyword records:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, MasterLanguage, OptInKeywords, DoubleOptInKeywords, OptInConfirmation, OptOutKeywords, OptOutConfirmation, HelpKeywords, HelpResponse, CustomKeywords, CustomResponse FROM MsgChannelLanguageKeyword WHERE MessagingChannelId = '{CHANNEL_ID}'" \
  --json > /tmp/cs-keywords.json
```

**No-op check:** if `ConsentType` is non-null AND an existing keyword record already satisfies the readiness matrix for that ConsentType, don't overwrite — this facet is already activation-ready.

Choose the ConsentType (prompt if `{CONSENT_TYPE}` absent — do not auto-pick), then satisfy this contract (the exact server-side activation-readiness rule — source in `references/gotchas.md`):

| ConsentType | MessagingChannel fields | `MsgChannelLanguageKeyword` (≥1 record) |
| --- | --- | --- |
| ImplicitOptIn | (none required) | `OptOutKeywords` + `OptOutConfirmation` |
| ExplicitOptIn | `OptInPrompt`¹ | above + `OptInKeywords` |
| DoubleOptIn | `OptInPrompt`¹ + `DoubleOptInPrompt` + `IsRequireDoubleOptIn=true` | above + `DoubleOptInKeywords` |

¹ `OptInPrompt` is optional for readiness on Unified SMS / WhatsApp / RCS (`MessageType IN ('Text','WhatsApp','Rcs')` on Enhanced); still recommend setting it. `ImplicitOptIn` is **never a no-op** — it still needs an opt-out keyword record.

Write the channel fields in one PATCH, then create/update the language-keyword record per `references/language-keywords.md`.

**Quoting rule (load-bearing):** `sf data ... --values` splits on spaces — wrap every multi-word value in single quotes *inside* the double-quoted string: `OptInPrompt='Reply YES to receive messages'`. Unquoted fails with `Malformed key=value pair`.

```bash
# ExplicitOptIn example
sf data update record --target-org '{ORG_ALIAS}' --sobject MessagingChannel \
  --record-id '{CHANNEL_ID}' --values "ConsentType=ExplicitOptIn OptInPrompt='{OPT_IN_PROMPT}'" --json > /tmp/cs-patch.json
```

On non-zero status: emit `{ok:false, kind:"channel-patch-failed"|"keyword-record-failed", message: ...}`. Then verify by re-reading (Stage 5).

> **WhatsApp rich content rejects ExplicitOptIn** server-side — surface the message, don't retry (see `references/gotchas.md`).

---

## Stage 3: Facets 2 & 3 — Automated responses + Messaging keywords (Metadata API)

Run when `auto-responses` and/or `keywords` are requested. These are type-agnostic (all Enhanced types). **Load `references/channel-settings-facets.md` and follow it** — it has the retrieve→edit→deploy flow, the 12 `<automatedResponses>` type values, the two content shapes (`TextResponse` vs `MessageDefinition`), the `EndUserIdleResponse` `<responseTimeoutInMins>` rule, XML escaping, and the `<messagingKeywords>` OptIn/OptOut/Help groups.

Outline:
1. Retrieve the channel's metadata into a scratch sfdx project (`sf project retrieve start -m MessagingChannel:{DeveloperName}`).
2. Edit `<automatedResponses>` / `<messagingKeywords>` blocks in the retrieved `.messagingChannel-meta.xml` (add/replace by `<type>` / `<keywordType>`+`<language>`; XML-escape response text).
3. Deploy it back (`sf project deploy start -m MessagingChannel:{DeveloperName}`).
4. On deploy failure: `{ok:false, kind:"metadata-deploy-failed", message: <componentFailures>}`.

> **Facebook:** real metadata changes currently fail with an opaque numeric error (e.g. `(-462367322)`). It's a known platform issue, not bad input. Don't retry; return `metadata-deploy-failed` with the Setup-UI fallback hint (see `references/gotchas.md` #16).

**Never emit `<actionParameterMappings>`** (0 occurrences across a 191-channel scan — it's a Tooling-only mapping done in the UI post-deploy).

---

## Stage 4: Facets 4 & 5 — Inactivity + Pre-chat parameters (Metadata API, scoped)

Run only when requested **and** applicable to this `MessageType`:

- **Facet 4 (inactivity):** the four timeout fields (`endUserIdleTimeOut` 5–30, `endUserIdleAction` = `Inactivate`|`End`|`InactivateAndEnd`, `endInactiveSessionTimeOut`, `isAgentMessageResetInactivityEnabled`) are **top-level siblings of `<embeddedConfig>`**, not inside it. Full four fields → **MIAW only**; `isAgentMessageResetInactivityEnabled` also valid on Apple/Facebook; **not applicable on SMS/WhatsApp/LINE** → emit `facet-not-applicable`. (Release-gated: on 262 pods only `endUserIdleTimeOut` deploys and the reset flag is silently dropped; all four work on 264+ — see `references/gotchas.md` #15.)
- **Facet 5 (parameters):** `<customParameters>` (`name`, `masterLabel`, `externalParameterName`, `parameterDataType=String`, optional `maxLength`) and `<standardParameters>` — **MIAW pre-chat only**, rare. Skip unless the caller explicitly configures pre-chat.

Both use the same retrieve→edit→deploy flow as Stage 3 (`references/channel-settings-facets.md`).

---

## Stage 5: Verify and report

For facet 1, re-read the channel + keyword records and confirm every required field for the chosen ConsentType is non-null (channel and ≥1 language record); else `{ok:false, kind:"verify-failed", hint:"..."}`. For metadata facets, confirm the deploy `status` is `Succeeded`, then re-retrieve the channel metadata and confirm the edited `<automatedResponses>` / `<messagingKeywords>` / inactivity / parameter blocks are present; if a deploy reports `Succeeded` but the re-retrieved block is missing, emit `{ok:false, kind:"verify-failed", hint:"..."}`.

Emit the JSON envelope. If invoked directly (leaf), render a short summary:
- `Success — configured {facets} on channel {CHANNEL_ID} ({MessageType}).` (add `Activation-ready.` when consent passed)
- `Info: requested settings already configured — no changes.` (no-op)
- `Warning: {facet} is not supported on {MessageType} channels — skipped.` (facet-not-applicable)
- `Warning: this channel is PlatformType={x}, not Enhanced — these settings don't apply.` (not-enhanced)
- `Error: {kind}: {message}` (failures)

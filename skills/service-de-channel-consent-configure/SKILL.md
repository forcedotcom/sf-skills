---
name: service-de-channel-consent-configure
description: "Configure consent (opt-in/opt-out) on an Enhanced `MessagingChannel` so activation will accept it. Given a `{CHANNEL_ID}`, sets the channel's `ConsentType` (ImplicitOptIn / ExplicitOptIn / DoubleOptIn) and the `OptInPrompt` / `DoubleOptInPrompt` prompt fields, then creates or updates one `MsgChannelLanguageKeyword` record per language holding the opt-in / double-opt-in / opt-out / help / custom keywords and confirmation messages. Use between channel insertion and activation — activation fails the consent-readiness check unless a valid ConsentType and at least one matching language-keyword record exist."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-activate"
    - "service-de-channel-routing-configure"
    - "service-de-headless-channel-configure"
---

# Configuring Channel Consent

## What this skill does

Ensures an Enhanced `MessagingChannel` has valid **consent** configured before activation. Consent has two parts, and both are checked by the server-side activation-readiness gate (`MessagingChannelReadinessChecker.isConsentConfiguredForChannel`):

1. **Channel-level fields** on `MessagingChannel`:
   - `ConsentType` — static enum: `ImplicitOptIn`, `ExplicitOptIn`, or `DoubleOptIn`.
   - `OptInPrompt` — message sent when an end-user reply doesn't match an opt-in keyword (required for ExplicitOptIn/DoubleOptIn, except on Unified SMS / WhatsApp / RCS where it's optional).
   - `DoubleOptInPrompt` — message sent when a reply doesn't match a double-opt-in keyword (required for DoubleOptIn).
   - `IsRequireDoubleOptIn` — boolean flag; set true alongside `ConsentType=DoubleOptIn`.

2. **Per-language keyword records** — one or more `MsgChannelLanguageKeyword` child rows (master-detail to `MessagingChannel`, key prefix `3Or`). Each holds the keywords an end-user sends (opt-in, double-opt-in, opt-out, help, custom) and the confirmation replies, **for one language**. Keyword fields are **comma-separated strings** (e.g. `"STOP,UNSUBSCRIBE,CANCEL"`).

**Consent is never a no-op for activation.** Even `ImplicitOptIn` requires at least one `MsgChannelLanguageKeyword` with an opt-out keyword + opt-out confirmation. (The one exception is an outbound-only channel, which the readiness check passes automatically.)

Consent settings apply only to **Enhanced** channels (`PlatformType=Enhanced`) of a supported message type. On a Standard channel these fields aren't used; this skill only touches Enhanced channels.

## Where this fits

This skill runs between routing and activation in the Enhanced-channel setup pipeline. `service-de-channel-routing-configure` sets the channel's `SessionHandler`; this skill configures consent; then `service-de-channel-activate` flips the channel live. The activation readiness check requires **both** routing and consent, so run this before activating. The `service-de-headless-channel-configure` orchestrator sequences all three automatically — invoke this skill directly only when you want to configure consent on its own.

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/language-keywords.md` | Creating or updating the per-language `MsgChannelLanguageKeyword` records — full field list, CSV keyword semantics, create-vs-update logic, and the Unified-SMS help/custom-keyword rules. |
| `references/gotchas.md` | Troubleshooting an unexpected result, or before modifying this skill. |
| `references/worked-examples.md` | You want a reference run of the ImplicitOptIn, ExplicitOptIn, or DoubleOptIn paths. |

## When NOT to use this skill

- **The channel isn't Enhanced.** Consent fields apply to Enhanced channels only. This skill confirms `PlatformType=Enhanced` and stops otherwise.
- **The channel is outbound-only.** Outbound-only channels pass the consent-readiness check automatically; there's nothing to configure.
- **The channel doesn't exist yet.** Run the insertion skill first; this skill expects a real `MessagingChannel.Id`.

## Inputs (from caller)

- `{CHANNEL_ID}` — a 15- or 18-char `MessagingChannel.Id` (prefix `0Mj`). Must already exist and be Enhanced.
- `{CONSENT_TYPE}` — optional; one of `ImplicitOptIn` | `ExplicitOptIn` | `DoubleOptIn`. If omitted, the skill prompts.
- `{LANGUAGE}` — optional; the `MasterLanguage` for the keyword record (e.g. `en_US`). Defaults to `en_US` if not provided.
- `{ORG_ALIAS}` — optional; `sf` CLI target-org alias. Default: whatever `sf config get target-org` returns.

The individual keyword/confirmation/prompt values are collected interactively in Stage 3–4 (or accepted from the caller if pre-supplied).

## Output (to caller)

**Success — no change needed:**
```json
{"ok": true, "noop": true, "consentType": "ImplicitOptIn|ExplicitOptIn|DoubleOptIn", "languageKeywordIds": ["3Or..."], "message": "Consent already configured and activation-ready"}
```

**Success — consent configured:**
```json
{"ok": true, "consentType": "ExplicitOptIn", "channelFieldsSet": ["ConsentType","OptInPrompt"],
 "languageKeywordId": "3Or...", "language": "en_US", "created": true|false, "activationReady": true}
```

**Precondition / validation not met:**
```json
{"ok": false, "kind": "not-enhanced", "hint": "consent fields apply to Enhanced channels only; this channel is PlatformType=<x>"}
{"ok": false, "kind": "missing-consent-input", "hint": "<which required keyword/prompt for the chosen ConsentType is missing>"}
```

**Failure:**
```json
{"ok": false, "kind": "channel-patch-failed", "message": "..."}
{"ok": false, "kind": "keyword-record-failed", "message": "..."}
{"ok": false, "kind": "verify-failed", "hint": "writes returned success but a re-read shows the channel is still not consent-ready"}
```

---

## Stage 1: Read current consent state

Read the channel's consent fields and any existing language-keyword records.

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, PlatformType, MessageType, MessagingPlatformKey, ConsentType, OptInPrompt, DoubleOptInPrompt, IsRequireDoubleOptIn FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" \
  --json > /tmp/cc-channel.json

sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, MasterLanguage, OptInKeywords, DoubleOptInKeywords, OptInConfirmation, OptOutKeywords, OptOutConfirmation, HelpKeywords, HelpResponse, CustomKeywords, CustomResponse FROM MsgChannelLanguageKeyword WHERE MessagingChannelId = '{CHANNEL_ID}'" \
  --json > /tmp/cc-keywords.json
```

If the channel record is missing — halt with `Error: Channel {CHANNEL_ID} not found — check the id, or run the insertion skill first.`

If `PlatformType != 'Enhanced'` — emit `{ok:false, kind:"not-enhanced", ...}` and stop.

**No-op check:** if `ConsentType` is non-null AND the existing language-keyword records already satisfy the readiness matrix for that ConsentType (see Stage 5), emit the `noop:true` envelope and return. Don't re-prompt or overwrite a channel that is already activation-ready.

---

## Stage 2: Choose the ConsentType

If `{CONSENT_TYPE}` wasn't supplied, prompt (do NOT auto-pick):

```text
Channel '{developerName}' ({CHANNEL_ID}) — choose a consent model:

  1) ImplicitOptIn  — end users are opted in by default; you only handle opt-OUT (STOP) keywords.
  2) ExplicitOptIn  — end users must send an opt-in keyword before you can message them.
  3) DoubleOptIn    — explicit opt-in plus a second confirming keyword.

Pick [1-3]:
```

Record `{CONSENT_TYPE}`. Note the field checks that follow (this is the exact server-side activation-readiness contract — see `references/gotchas.md` for the source):

| ConsentType | MessagingChannel fields | `MsgChannelLanguageKeyword` (≥1 record) |
| --- | --- | --- |
| ImplicitOptIn | (none required) | `OptOutKeywords` + `OptOutConfirmation` |
| ExplicitOptIn | `OptInPrompt`¹ | above + `OptInKeywords` |
| DoubleOptIn | `OptInPrompt`¹ + `DoubleOptInPrompt` + `IsRequireDoubleOptIn=true` | above + `DoubleOptInKeywords` |

¹ `OptInPrompt` is optional (not required for readiness) on Unified SMS / WhatsApp / RCS channels — detect via `MessageType IN ('Text','WhatsApp','Rcs')` on an Enhanced channel (the queryable proxy for the server's `isUnifiedSMSOrWhatsappOrRCS`). Still recommend setting it for a good end-user experience.

---

## Stage 3: Collect channel-level prompt values

Only prompt for the fields the chosen ConsentType requires (see the matrix above). Skip this stage entirely for `ImplicitOptIn` — it needs no channel-level prompt fields.

For `ExplicitOptIn` / `DoubleOptIn`:

```text
Opt-in prompt (sent when a reply doesn't match an opt-in keyword):
```
For `DoubleOptIn`, also:
```text
Double-opt-in prompt (sent when a reply doesn't match a double-opt-in keyword):
```

Trim whitespace. If a required prompt is empty after trimming, re-prompt once; on a second empty, emit `{ok:false, kind:"missing-consent-input", hint:"..."}`.

---

## Stage 4: Configure the per-language keyword record

Collect the keyword lists and confirmation replies for `{LANGUAGE}` (default `en_US`), then create or update the `MsgChannelLanguageKeyword` record.

**Load `references/language-keywords.md` and follow it** — it holds the full field list, the comma-separated-keyword semantics, the create-vs-update decision (reuse an existing record for the same language rather than duplicating), and the Unified-SMS help/custom-keyword rules.

The minimum per ConsentType (again, from the readiness contract):
- **ImplicitOptIn:** `OptOutKeywords` (e.g. `STOP,UNSUBSCRIBE`) + `OptOutConfirmation`.
- **ExplicitOptIn:** the above + `OptInKeywords` (e.g. `START,YES`).
- **DoubleOptIn:** the above + `DoubleOptInKeywords` (e.g. `CONFIRM`).

`OptInConfirmation`, `HelpKeywords`/`HelpResponse`, and `CustomKeywords`/`CustomResponse` are optional for the base readiness check (help/custom are only *required* on Unified SMS — see the reference), but collect them if the user wants them.

---

## Stage 5: Write channel fields + keyword record

Write the channel-level fields in one PATCH (only the fields the ConsentType requires).

**Quoting rule (load-bearing):** `sf data update record --values` splits on spaces, so any value containing a space **must be wrapped in single quotes inside the double-quoted `--values` string** — e.g. `OptInPrompt='Reply YES to receive messages'`. An unquoted `OptInPrompt=Reply YES ...` fails with `Malformed key=value pair` (verified live on sdb6c). Prompts almost always contain spaces, so always quote them.

```bash
# ImplicitOptIn — ConsentType only
sf data update record --target-org '{ORG_ALIAS}' --sobject MessagingChannel \
  --record-id '{CHANNEL_ID}' --values "ConsentType=ImplicitOptIn" --json > /tmp/cc-patch.json

# ExplicitOptIn
sf data update record --target-org '{ORG_ALIAS}' --sobject MessagingChannel \
  --record-id '{CHANNEL_ID}' --values "ConsentType=ExplicitOptIn OptInPrompt='{OPT_IN_PROMPT}'" --json > /tmp/cc-patch.json

# DoubleOptIn
sf data update record --target-org '{ORG_ALIAS}' --sobject MessagingChannel \
  --record-id '{CHANNEL_ID}' \
  --values "ConsentType=DoubleOptIn OptInPrompt='{OPT_IN_PROMPT}' DoubleOptInPrompt='{DBL_PROMPT}' IsRequireDoubleOptIn=true" --json > /tmp/cc-patch.json
```

If `status !== 0`: emit `{ok:false, kind:"channel-patch-failed", message: ...}` and return.

Then create or update the `MsgChannelLanguageKeyword` record per `references/language-keywords.md`. If it fails: `{ok:false, kind:"keyword-record-failed", message: ...}`.

---

## Stage 6: Verify activation readiness

Re-read both the channel and its keyword records (same two queries as Stage 1). Confirm, per the chosen ConsentType's row in the Stage 2 matrix, that every required field is now non-null on the channel AND on at least one keyword record for the configured language.

If any required field is still null: emit `{ok:false, kind:"verify-failed", hint:"<which requirement is unmet>"}`.

Otherwise emit the success envelope with `activationReady: true`.

---

## Stage 7: Report to caller

Report the JSON envelope. If this skill is the leaf (user invoked it directly), render:

- `Success — Consent configured — channel {CHANNEL_ID} is now {CONSENT_TYPE} with a {LANGUAGE} keyword record. Activation-ready.`
- `Info: Consent already configured — {CONSENT_TYPE}, {N} language record(s). No changes.` (no-op path)
- `Warning: This channel is PlatformType={x}, not Enhanced — consent fields don't apply here.` (not-enhanced)
- `Warning: Missing required consent input for {CONSENT_TYPE}: {what}. Re-run and provide it.` (missing-consent-input)
- `Error: {kind}: {message}` (other failures)

---

## Worked examples

For reference runs of the ImplicitOptIn (opt-out only), ExplicitOptIn, and DoubleOptIn paths, see `references/worked-examples.md`.

---

## Gotchas

Known gotchas — the exact per-ConsentType activation-readiness contract (and its source), comma-separated keyword storage, the "ImplicitOptIn still needs a keyword record" trap, one-record-per-language uniqueness, the Unified-SMS help/French-custom rules, and the OptInPrompt Unified-SMS/WhatsApp/RCS exemption.

**When troubleshooting an unexpected result, or before modifying this skill, load `references/gotchas.md` and follow it.**

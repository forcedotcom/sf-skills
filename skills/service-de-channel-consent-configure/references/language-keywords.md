# Per-language keyword records: `MsgChannelLanguageKeyword`

Load this when Stage 4 needs to create or update the per-language keyword record for a channel.

## Entity shape

`MsgChannelLanguageKeyword` (key prefix `3Or`, introduced in API 224) is a **master-detail child of `MessagingChannel`**. One record holds all the consent keywords and confirmation messages for **one language** on one channel. A channel can have many of these — one per supported language.

Fields (all string/CLOB except the FK):

| Field | Meaning | Keyword or response |
| --- | --- | --- |
| `MasterLanguage` | **Required.** Language locale for this record, e.g. `en_US`, `fr_CA`, `es`, `pt_BR`. | — |
| `MessagingChannelId` | **Required.** Master-detail FK to the channel (`0Mj…`). Set on create only. | — |
| `OptInKeywords` | Keywords an end user sends to opt in (e.g. `START,YES,SUBSCRIBE`). | keyword list |
| `OptInConfirmation` | Reply sent after a successful opt-in. | response |
| `DoubleOptInKeywords` | Keywords an end user sends to confirm a double opt-in (e.g. `CONFIRM`). | keyword list |
| `OptOutKeywords` | Keywords an end user sends to opt out (e.g. `STOP,UNSUBSCRIBE,CANCEL`). | keyword list |
| `OptOutConfirmation` | Reply sent after a successful opt-out. | response |
| `HelpKeywords` | Keywords an end user sends to get help (e.g. `HELP,INFO`). | keyword list |
| `HelpResponse` | Reply sent for a help request. | response |
| `CustomKeywords` | Extra keywords the channel handles. | keyword list |
| `CustomResponse` | Reply sent for a custom keyword match. | response |
| `MessagingChannelUsage` | Optional FK (minApiVersion 252); leave unset unless the caller has a specific usage row. | — |

## Keyword storage format — comma-separated strings

Keyword fields hold a **comma-separated string**, not a multi-value/picklist. The UI joins the entered words with `wordArray.toString()` and the server splits them with `TextUtil.splitSimpleAndTrim(value, ",", 0)`. So:

- Store `OptOutKeywords` as the literal string `STOP,UNSUBSCRIBE,CANCEL`.
- Whitespace around each token is trimmed server-side, but keep it clean: no leading/trailing commas, no empty tokens.
- Matching is on the whole inbound message against the token list; keep keywords single-word and uppercase by convention (the UI upper-cases nothing automatically — follow the org's existing records if any).

## Create vs update — reuse the record for a language

**There is one record per (channel, language).** Before creating, check the Stage 1 read (`/tmp/cc-keywords.json`) for an existing `MsgChannelLanguageKeyword` whose `MasterLanguage` equals `{LANGUAGE}`:

- **Exists →** `updateRecord` path: PATCH that record's Id with the new field values. Do NOT create a second record for the same language — duplicates confuse the readiness check and the UI.
- **Doesn't exist →** `createRecord` path: insert a new record, setting `MessagingChannelId={CHANNEL_ID}` and `MasterLanguage={LANGUAGE}` plus the collected keyword/response fields.

### Create

```bash
sf data create record --target-org '{ORG_ALIAS}' --sobject MsgChannelLanguageKeyword \
  --values "MessagingChannelId={CHANNEL_ID} MasterLanguage={LANGUAGE} \
OptOutKeywords='STOP,UNSUBSCRIBE' OptOutConfirmation='You have been unsubscribed.'" \
  --json > /tmp/cc-kw-write.json
```

Add `OptInKeywords`/`OptInConfirmation` for ExplicitOptIn, and `DoubleOptInKeywords` for DoubleOptIn.

**Quoting (load-bearing):** `sf data ... --values` splits on spaces, so wrap any value containing a space in single quotes *inside* the double-quoted `--values` string — including keyword CSVs if you ever add spaces after commas, and every confirmation/response message. A comma-separated keyword list with no spaces (`OptOutKeywords=stop,unsubscribe,cancel`) does not need quoting, but a message (`OptOutConfirmation='You have been unsubscribed.'`) always does. An unquoted multi-word value fails with `Malformed key=value pair` (verified live on sdb6c 2026-08-13).

### Update

```bash
sf data update record --target-org '{ORG_ALIAS}' --sobject MsgChannelLanguageKeyword \
  --record-id '{KEYWORD_RECORD_ID}' \
  --values "OptInKeywords='START,YES' OptInConfirmation='You are now subscribed.'" \
  --json > /tmp/cc-kw-write.json
```

Check `status` in the JSON result; on non-zero return `{ok:false, kind:"keyword-record-failed", message: ...}`.

## Per-ConsentType minimum (what the readiness check requires)

The record must satisfy, for at least one language, the row matching the channel's `ConsentType` (this is the exact server-side contract from `MessagingChannelReadinessChecker` — see `gotchas.md`):

| ConsentType | Required on the keyword record |
| --- | --- |
| ImplicitOptIn | `OptOutKeywords` **and** `OptOutConfirmation` non-null |
| ExplicitOptIn | above **and** `OptInKeywords` non-null |
| DoubleOptIn | above **and** `DoubleOptInKeywords` non-null |

`OptInConfirmation` is not part of the base readiness check, but collect it — a channel that opts users in with no confirmation reply is a poor experience.

## Unified SMS extras (only when the channel is Unified SMS)

If the channel is Unified SMS (an Enhanced channel with `MessageType='Text'`; there is no `IsUnifiedMessagingEnabled` column on the Data-API `MessagingChannel` sObject — use `MessageType`), two extra rules apply to the keyword record — the readiness check enforces them:

- **Help is mandatory:** `HelpKeywords` **and** `HelpResponse` must both be non-null.
- **French locale custom rule:** for a `fr_CA` record, `CustomKeywords` **and** `CustomResponse` must both be non-null.

These are *not* required for non-Unified-SMS channels (WhatsApp, Facebook, etc.), where help/custom are optional. Only enforce them when you've confirmed Unified SMS in Stage 1.

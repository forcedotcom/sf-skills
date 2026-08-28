# Worked examples: `service-de-channel-consent-configure`

Reference runs for the three ConsentType paths. The ExplicitOptIn channel-side write, the read model, and the WhatsApp restriction below were verified live on `messaging_sdb6c` 2026-08-13.

---

## Worked example: ImplicitOptIn (opt-out only)

Input:
- `{CHANNEL_ID}` = `0MjSG00000030wL0AQ` (Enhanced WhatsApp channel `DummyChannelForTesting`)
- `{LANGUAGE}` = `en_US`

**Stage 1** read shows `PlatformType=Enhanced`, `ConsentType=ImplicitOptIn`, and one existing `MsgChannelLanguageKeyword` (`3OrSG0000002kUz0AI`, `MasterLanguage=en_US`) with:
```text
OptOutKeywords    = unsubscribe_en_US,stopall_en_US,cancel_en_US,quit_en_US,stop_en_US,end_en_US
OptOutConfirmation = You've opted out of receiving messages from us, so we won't contact you again.
```
That record already satisfies the ImplicitOptIn readiness rule (`OptOutKeywords` + `OptOutConfirmation` both non-null), so the skill takes the **no-op path**:

```json
{"ok": true, "noop": true, "consentType": "ImplicitOptIn",
 "languageKeywordIds": ["3OrSG0000002kUz0AI"],
 "message": "Consent already configured and activation-ready"}
```

If instead there were **no** keyword record, the skill would create one:

```bash
sf data create record --sobject MsgChannelLanguageKeyword \
  --values "MessagingChannelId=0MjSG00000030wL0AQ MasterLanguage=en_US \
OptOutKeywords=stop,unsubscribe,cancel OptOutConfirmation='You have been unsubscribed.'"
```

and report `Success — Consent configured — channel 0MjSG00000030wL0AQ is now ImplicitOptIn with an en_US keyword record. Activation-ready.`

---

## Worked example: ExplicitOptIn (channel-side write verified live)

Input:
- `{CHANNEL_ID}` = `0MjSG0000000D9V0AU` (Enhanced Facebook channel `FACEBOOK_null_101192609043587`)
- `{CONSENT_TYPE}` = `ExplicitOptIn`
- `{LANGUAGE}` = `en_US`

**Stage 1**: `PlatformType=Enhanced`, `ConsentType=ImplicitOptIn`, `OptInPrompt=null`. Continue.

**Stage 2**: ExplicitOptIn chosen. Facebook accepts it (unlike WhatsApp rich content — see below).

**Stage 3**: collect `OptInPrompt` = `Reply YES to receive messages`.

**Stage 5 (channel PATCH)** — verified live, note the single-quoting of the multi-word prompt:

```bash
$ sf data update record --sobject MessagingChannel --record-id 0MjSG0000000D9V0AU \
    --values "ConsentType=ExplicitOptIn OptInPrompt='Reply YES to receive messages'"
# → {"id":"0MjSG0000000D9V0AU","success":true,"errors":[]}
```

Re-read confirmed `ConsentType=ExplicitOptIn`, `OptInPrompt=Reply YES to receive messages`.

**Stage 5 (keyword record)** — the record must also carry `OptInKeywords` (plus the ImplicitOptIn opt-out fields). Create or update the `en_US` record:

```bash
sf data update record --sobject MsgChannelLanguageKeyword --record-id <3Or...> \
  --values "OptInKeywords='yes,start,subscribe' OptInConfirmation='You are subscribed'"
```

(Live keyword shape confirmed on sdb6c: e.g. Facebook channel `0MjSG0000000Beb0AE` carries `OptInKeywords=yes,sure` — multiple opt-in keywords as a comma-separated string.)

**Stage 6**: re-read channel + keyword record; `OptInPrompt` non-null on the channel and `OptInKeywords`+`OptOutKeywords`+`OptOutConfirmation` non-null on the keyword record → activation-ready.

**Stage 7**:
```json
{"ok": true, "consentType": "ExplicitOptIn", "channelFieldsSet": ["ConsentType","OptInPrompt"],
 "languageKeywordId": "3Or...", "language": "en_US", "created": false, "activationReady": true}
```

*(The test channel was restored afterward to `ConsentType=ImplicitOptIn, OptInPrompt=null` — passing `OptInPrompt=''` nulls the field.)*

---

## Worked example: DoubleOptIn

Input:
- `{CHANNEL_ID}` = an Enhanced Text (SMS) channel
- `{CONSENT_TYPE}` = `DoubleOptIn`

**Stage 3** collects both `OptInPrompt` and `DoubleOptInPrompt`.

**Stage 5 (channel PATCH)** — all three fields in one write:

```bash
sf data update record --sobject MessagingChannel --record-id '{CHANNEL_ID}' \
  --values "ConsentType=DoubleOptIn OptInPrompt='Reply YES to subscribe' \
DoubleOptInPrompt='Reply CONFIRM to confirm your subscription' IsRequireDoubleOptIn=true"
```

**Stage 5 (keyword record)** — needs `OptInKeywords`, `DoubleOptInKeywords`, `OptOutKeywords`, `OptOutConfirmation`:

```bash
sf data update record --sobject MsgChannelLanguageKeyword --record-id <3Or...> \
  --values "OptInKeywords=yes,start DoubleOptInKeywords=confirm \
OptOutKeywords=stop,unsubscribe OptOutConfirmation='You have been unsubscribed.'"
```

(Live example on sdb6c: keyword record `3OrSG00000002rR0AQ` has both `OptInKeywords=yes` and `DoubleOptInKeywords=yes`, confirming DoubleOptIn uses both keyword fields.)

**Stage 6** verifies `OptInPrompt` + `DoubleOptInPrompt` non-null on the channel and `OptInKeywords` + `DoubleOptInKeywords` + opt-out fields non-null on the keyword record.

---

## Worked example: WhatsApp rich-content rejects ExplicitOptIn (verified live)

Input:
- `{CHANNEL_ID}` = `0MjSG00000030wL0AQ` (Enhanced WhatsApp channel with rich content)
- User asks for `ExplicitOptIn`

**Stage 5** PATCH is rejected server-side:

```bash
$ sf data update record --sobject MessagingChannel --record-id 0MjSG00000030wL0AQ \
    --values "ConsentType=ExplicitOptIn OptInPrompt='Reply YES to receive messages'"
# → INVALID_INPUT: Consent Type for WhatsApp Messaging Channel with rich content
#    cannot be set to EXPLICIT_OPT_IN(db=1,api=ExplicitOptIn).
```

The skill surfaces this rather than retrying:

```json
{"ok": false, "kind": "channel-patch-failed",
 "message": "Consent Type for WhatsApp Messaging Channel with rich content cannot be set to EXPLICIT_OPT_IN. WhatsApp rich-content channels support ImplicitOptIn only."}
```

User-facing: `Error: This WhatsApp channel has rich content and only supports ImplicitOptIn — the server rejected ExplicitOptIn. Configure opt-out keywords under ImplicitOptIn instead.`

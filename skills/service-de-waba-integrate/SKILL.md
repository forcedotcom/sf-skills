---
name: service-de-waba-integrate
description: "Confirm the customer's WhatsApp Business Account is shared with Salesforce on Meta's side. Pure instruction + one user-confirmation prompt — no API calls, no token handling. The actual sharing happens in Meta Business Suite (UI-only; Meta provides no Graph endpoint to automate this step). Renders step-by-step instructions with Salesforce's Business Manager ID substituted in, then asks the user to confirm whether \"Salesforce\" appears in the WABA's Partners list."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  relatedSkills:
    - "service-de-channel-create"
---

# Linking a WABA to Salesforce

## What this skill does

Gets the customer from "I have a WABA" to "my WABA is linked to Salesforce" — entirely by instruction. Meta intentionally gates this behind the human-approval UI at business.facebook.com; there's no Graph write endpoint that scripts the partnership. The two GET endpoints that would let us probe state (`/{waba-id}/subscribed_apps`, `/{waba-id}/assigned_users`) need a Meta access token with `whatsapp_business_management` scope that the customer would have to generate — a bigger ask than just "check your Partners tab."

So the skill is 100% instruction rendering + one confirmation prompt. No API calls. No SF DB writes. No Meta tokens.

After this skill returns success, downstream insertion (`service-de-channel-create`) can proceed: the SF-side `setupLiveMessageChannelEnhanced` path doesn't require us to have proven the partnership — it'll fail with a clear Meta-precondition error if the customer lied, and our skill trusts the customer's confirmation.

## When NOT to use this skill

- **You've already confirmed the partnership on a previous run.** The orchestrator's resume logic doesn't short-circuit Stage 1 (no cheap SF-side probe exists), so this skill always runs — but it's just text + a prompt, no round trip.
- **You're inserting a non-WhatsApp channel.** Line / Apple / Facebook don't use Meta Business Manager partnerships. Skip this skill entirely for those paths.
- **The customer is using the Embedded Signup popup instead.** That's a different flow (popup-driven, SF-UI-side OAuth); this skill is specifically the headless alternative.

## Inputs (from caller)

- `{WABA_ID}` — WhatsApp Business Account ID. Used only for rendering (so the instructions say "open YOUR WABA" with the right id visible).
- `{SF_BM_ID}` — optional. Defaults to `10152614792574154` (Salesforce's Business Manager ID, confirmed by user 2026-04-29; see IMPLEMENTATION.md §13 journey log). Override only if Salesforce issues a different BM ID for a specific partner program.

## Output (to caller)

**Success — user confirmed the partnership is in place:**
```json
{"ok": true, "linked": true, "path": "user-confirmed",
 "note": "partnership confirmed by user; subsequent channel insert will
          surface any server-side issues clearly"}
```

**Failure — partnership not yet in place:**
```json
{"ok": false, "kind": "partnership-blocked",
 "hint": "customer reported Salesforce is not in the Partners tab;
          most likely causes: (a) WABA ID typo, (b) user lacks admin
          role in the Business Manager, (c) partnership request still
          pending Meta approval. Retry this skill after resolving."}
```

**Failure — user-declined or dropped:**
```json
{"ok": false, "kind": "user-declined",
 "hint": "user cancelled the linking step; re-run the orchestrator
          when the customer is ready to click through Business Suite"}
```

---

## Stage 1: Render the instructions

Substitute `{WABA_ID}` and `{SF_BM_ID}` and **output the following directly as markdown text to the user** (do NOT use `cat`, `echo`, or any Bash command that would collapse the output):

```markdown
──────────────────────────────────────────────────────────────
**Before we can insert the WhatsApp channel in Salesforce, your
WhatsApp Business Account must be shared with Salesforce on
Meta's side.** Meta gates this step behind business.facebook.com —
there's no API we can call to automate it.

## One-time steps (takes ~2 minutes):

1. Go to https://business.facebook.com
2. In the left nav, open "WhatsApp Accounts" and click your
   WABA (ID: **{WABA_ID}**)
3. Click the "Partners" tab at the top of the WABA page
4. Look at the list:
   - **If "Salesforce" (or "Salesforce.com") is already listed
     with Full control** — you're done, nothing to do.
   - **If NOT listed** (or listed with only partial access):
     
     a. Click "Add partners" → "Share account with partner"
     
     b. Paste this Business Manager ID in "Enter partner
        business ID":
     
     ```
     {SF_BM_ID}
     ```
     
     c. Scroll to the "Full control" section at the bottom
        and toggle ON "Everything":
     
     ```
     [x] Everything — manage all settings, assign users,
         view payment information and send messages
     ```
     
     This is the option Salesforce needs. The Partial
     access toggles above (Phone numbers / Message
     templates / Messages) do NOT cover assigning users
     or managing webhook subscriptions — those require
     the Full control option. Don't try to grant access
     piecemeal through Partial access.
     
     d. Click "Assign"

## Notes:
- Your Meta Business Manager must be business-verified for Meta
  to accept the partnership. If it's not verified, Meta will
  block the "Assign" step with a clear error.
- You need admin role on the Business Manager to assign partners.
  If you're a regular employee, ask an admin on your team.
- Max 2 partners per WABA. If you've already shared with another
  BSP, Salesforce would be the second — which is fine.
──────────────────────────────────────────────────────────────
```

**CRITICAL:** Output this text directly in your response to the user, not via Bash/cat/echo. Tool results get collapsed; direct text output stays visible.

---

## Stage 2: Ask for confirmation

Use AskUserQuestion to prompt:

```text
Question: Is "Salesforce" now showing in the Partners tab for this WABA?
Header: Partnership
Options:
  1. Yes — already there or just added it
     (Salesforce appears in the Partners tab with Full control)
  2. No — still not showing
     (Partnership not yet in place after attempting to add it)
  3. Skip — abort setup for now
     (Not going to complete this step right now)
```

Do not try to validate the answer with Meta. Trust the user. If they said yes and lied, downstream `service-de-channel-create` will fail with a `meta-precondition` envelope that clearly names the issue — that's a cleaner failure than fabricating a probe here that would need a customer Meta token.

---

## Stage 3: Emit the envelope

Based on the user's answer, construct the appropriate envelope and **write it to `/tmp/linking-waba-result.json`** so the calling skill can parse it:

| User's answer | Envelope to write |
| --- | --- |
| `y` | `{"ok":true, "linked":true, "path":"user-confirmed", "note":"partnership confirmed by user; subsequent channel insert will surface any server-side issues clearly"}` |
| `n` | `{"ok":false, "kind":"partnership-blocked", "hint":"customer reported Salesforce is not in the Partners tab; most likely causes: (a) WABA ID typo, (b) user lacks admin role in the Business Manager, (c) partnership request still pending Meta approval. Retry this skill after resolving."}` |
| `s` | `{"ok":false, "kind":"user-declined", "hint":"user cancelled the linking step; re-run the orchestrator when the customer is ready to click through Business Suite"}` |

Write the envelope using:
```bash
echo '{envelope json}' > /tmp/linking-waba-result.json
```

Then display the human-readable summary to the user:

- For `y`: `Success — WABA linked — Salesforce confirmed as a partner on WABA {WABA_ID}. Proceed to service-de-channel-create.`
- For `n`: `Error: Partnership not yet in place — fix the issue on Meta's side (see instructions above) and re-run. Common fixes: check WABA ID, confirm your Business Manager is business-verified, confirm you have admin role.`
- For `s`: `⏸  Linking skipped by user — re-run when ready.`

---

## Worked example: customer already has Salesforce shared

Input: `{WABA_ID}=1558753535400324`

**Stage 1**: skill renders the instructions with the WABA ID visible. Customer opens Business Suite → WhatsApp Accounts → 1558753535400324 → Partners. Sees "Salesforce" in the list.

**Stage 2**: customer answers `y`.

**Stage 3**: emits:
```json
{"ok":true, "linked":true, "path":"user-confirmed",
 "note":"partnership confirmed by user; subsequent channel insert will surface any server-side issues clearly"}
```

Orchestrator continues to `service-de-channel-create`.

## Worked example: customer needs to add the partnership

Same input. Customer opens Business Suite, doesn't see Salesforce in Partners, clicks Add partners → Share account with partner → pastes `10152614792574154` → scrolls down to the "Full control" section → toggles ON "Everything" → Assign. Meta shows "Partnership request sent" or similar. Partnership lands (usually instant; occasionally pending for a few minutes if Meta needs to review).

Customer answers `y` after confirming Salesforce now shows up.

Orchestrator continues.

## Worked example: Business Manager not business-verified

Customer clicks Assign and Meta rejects with "Your business must be verified to assign partners." Customer answers `n` in our prompt.

**Stage 3**: emits:
```json
{"ok":false, "kind":"partnership-blocked",
 "hint":"customer reported Salesforce is not in the Partners tab; most likely causes: (a) WABA ID typo, (b) user lacks admin role in the Business Manager, (c) partnership request still pending Meta approval. Retry this skill after resolving."}
```

Orchestrator emits a step-annotated failure pointing at this skill; user pursues business verification through Meta separately and re-runs later.

---

## Gotchas

1. **We can't probe state without a customer Meta token.** `GET /{waba-id}/subscribed_apps` and `GET /{waba-id}/assigned_users` would confirm SF's app is subscribed / user is assigned, but both need a token the customer would have to generate in a Meta app — a 20-minute detour to save one prompt. Not worth it. Trust the customer's eyeballs.

2. **"Salesforce in Partners" ≠ "SF webhook subscription landed."** Subscription is a separate server-side event that happens *after* the partnership is in place, when SF's BSP app notices and calls its own internal setup. The customer's confirmation in this skill is about the *partnership*, not subscription state — subscription will catch up by the time `service-de-channel-create` runs. If it hasn't, the insert fails clearly with a Meta-precondition error and we retry.

3. **The `SF_BM_ID` is a single static value.** `10152614792574154` is Salesforce's Business Manager ID, the same for every customer in every org. Confirmed 2026-04-29 (IMPLEMENTATION.md §13). Don't let callers override it casually — if someone passes a different value, they've likely misunderstood what the field is for. Keep the override capability for edge cases (SF issuing a partner-specific BM ID at some future date), but don't document it prominently.

4. **The "Users" tab and the "Partners" tab are different.** Older IMPLEMENTATION.md drafts used the "add SF admin user" framing (users tab); the current canonical flow is "add SF as Partner" with the BM ID above. Both end up granting Salesforce access to the WABA, but the Partners flow is cleaner (no per-user maintenance, permission scoping is by partner role). Stick with Partners.

5. **Embedded Signup is an alternative, not a complement.** Customers using the Embedded Signup popup skip this skill entirely — the popup handles partnership grant inline via Meta's OAuth flow. This skill is for the headless path (customer prefers Business Suite click-through over a browser popup). Don't try to run both.

6. **Orchestrator calls this skill even on resume.** There's no SF-side state to check (the subscription landing is silent), so re-runs re-render the instructions and re-prompt. That's fine — the prompt is near-instant if the customer already confirmed before, and this skill produces no side-effects. Idempotency is inherent.

7. **No `sf` CLI commands, no SOQL, no HTTP.** This skill should be pure text + one prompt. If a future version wants to probe state (customer-supplied Meta token via env var, etc.), that's an additive enhancement — don't let it crowd the happy path. The instruction-only design is the feature.

8. **Max 2 partners per WABA.** If the customer is already sharing with another BSP (Twilio, 360dialog, etc.), Salesforce would be partner #2 — fine. If they've got 2 BSPs already, Meta blocks the Assign — customer would need to remove one first. This is rare but documented in the Stage 1 rendered text so customers hit a known error message rather than a mysterious failure.

9. **"Full control / Everything" is required, not just the Partial access toggles.** Meta's partner-share dialog has two sections: "Partial access" (individual toggles: Phone numbers view/manage, Message templates view/manage, Manage phone numbers and message templates, Messages) and "Full control" (a single "Everything" toggle). Salesforce needs **Full control / Everything** because:
   - **Assigning users** — SF provisions service accounts on the WABA to operate it. Only the Everything toggle grants this; none of the Partial access toggles cover it.
   - **Webhook subscription management** — `POST /{waba-id}/subscribed_apps` (which lets SF's BSP app receive inbound messages) requires `whatsapp_business_management` scope, which maps to Full control, not the partial toggles.
   - **Credit-line / payment method visibility** — needed so SF can route sends through the customer's own billing. Explicitly only in the "Everything" description ("view payment information").

   If a customer grants only partial access (e.g. just "Manage phone numbers and message templates"), the channel *may* insert successfully on the SF side but activation/send will fail later with opaque Meta errors about missing permissions. The Partial access path is for non-BSP integrations (marketing tools that only need to send templated messages, etc.), not BSPs. Don't let anyone "optimize" the rendered instructions toward narrower permissions — it's a false economy that surfaces as a confusing failure much later in the flow.

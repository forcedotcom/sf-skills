---
name: marketing-message-test
description: "Salesforce Marketing Cloud / Engagement 360 message preview and test-send. Use this skill when the user wants to render a personalized or unpersonalized preview of an E360 message (Email, SMS, WhatsApp, Push, In-App, RCS) from a content key, or fire a test send, over the headless API — no app UI. TRIGGER when: user has a contentKey and wants to see how a message renders for a recipient, preview a message headlessly, or send a test message. DO NOT TRIGGER when: the task is authoring message content, building Data Cloud segments/DMOs (use data360-segment / data360-harmonize), or activating a segment (use data360-activate)."
metadata:
  version: "1.0"
  minApiVersion: "62.0"
  accessCheck:
  - type: "orgPerm"
    value: "MarketingEngagement"
  cliTools:
  - tool:
    - "sf"
    semver: ">=2.0.0"
---

# marketing-message-test: E360 Message Preview & Test Send

Render a per-channel **preview** (or fire a **test send**) for a Marketing Cloud / Engagement 360 message, headlessly, starting from a single **`contentKey`**. Covers all six channels: Email, SMS, WhatsApp, Push, In-App, RCS.

Full endpoint tables, request bodies, response-field rules, and the version-floor matrix live in [references/api-contract.md](references/api-contract.md). This file is the operating procedure; consult the reference for exact payloads.

## When This Skill Owns the Task

Use `marketing-message-test` when the user wants to:
- render how an authored message looks for a real recipient (**personalized preview**)
- render content-only with no recipient (**unpersonalized preview**)
- send a **test message** to their own address / phone / individual id

Delegate elsewhere when the user is:
- building Data Cloud segments or calculated insights → [data360-segment](../data360-segment/SKILL.md)
- building DMOs, mappings, or identity resolution → [data360-harmonize](../data360-harmonize/SKILL.md)
- activating a segment downstream → [data360-activate](../data360-activate/SKILL.md)

## Required Context to Gather First

- **`contentKey`** — required, irreducible. The caller must supply it; it is not derivable.
- target org alias (for `sf org open` / access token)
- **channel** — Email, SMS, WhatsApp, Push, In-App, or RCS
- **mode** — personalized preview, unpersonalized preview, or test send
- for a **test send only**: the user's own destination(s) — `toAddresses` (Email), `toPhoneNumbers` (SMS/WhatsApp/RCS), or `toIndividualIds` (Push/In-App). Never derive these.

## Transports

| Purpose | Transport | Instance-relative path |
|---|---|---|
| Preview · test send · sender lookups | **LWR Apex** | `lwr/apex/v68.0/…` — the exact operation path is on each step's **Call** line |
| Managed content · data space · DMO · segment · profile | **Connect REST** | `services/data/vXX.0/…` (per-resource floors; v62.0+ covers all six channels) |
| WhatsApp template fetch (`whatsapp-template-fetch`) | **Headless dispatch** | `/headless/invoke/…` — a dispatch route, so invoke it through the `dispatch` tool, **not** `sf api request rest` (see the reference doc for details) |

**Versions:**
- **LWR-Apex** — not version-gated; pin `v68.0` (the path just needs a well-formed `vXX.0` segment).
- **Connect REST** — real per-resource floors; highest is data-spaces at **v62.0**, so **v62.0+ covers all six channels** (others lower — see the reference floor matrix).

**Always use `sf api request rest` — never `curl`.** It attaches the org's bearer token internally, so the credential never enters your context. **Never** extract a token (e.g. `sf org display --json`) or put one in an `Authorization` header — that leaks a live credential and is disallowed. Pass the **instance-relative path** (no host); the CLI prepends the instance URL and accepts both transports (LWR-Apex paths aren't under `services/data/`, but any instance-relative path works). **One step is the exception** — `whatsapp-template-fetch` is a headless `/headless/invoke` dispatch route, invoked through the `dispatch` tool rather than `sf api request rest`.

```bash
# GET (default method); path is instance-relative
sf api request rest 'services/data/v63.0/ssot/data-spaces' --target-org <org>

# POST with a flat JSON body from a file (content-type: application/json is sent by default)
# path = the target operation's **Call** line (e.g. the `preview-sms-unpersonalized` step)
sf api request rest '<lwr/apex Call path>' \
  --target-org <org> --method POST --body @body.json
```

**Verb rule (do not violate — wrong verb is rejected):**
- Preview / test-send methods are **POST** (`--method POST`) with a **flat JSON body** whose keys are exactly the parameter names — no envelope, no wrapper object.
- Sender / permission lookups are **GET** (default method) with args packed into a single `methodParams` query param (URL-encoded JSON string) appended to the path; no-arg methods omit it.

## Core Operating Rules

- **Never fabricate** a `segmentId`, `profileId`, DMO name, or destination. Every value is either given by the user or derived from the org via the chain below.
- **Preview needs no sender** — skip sender lookups (Part 3 of the reference) unless test-sending.
- **Personalized vs unpersonalized**: unpersonalized needs only `contentKey`; personalized needs `segmentId` + `recipientDataModelObjectName` + `contentKey` + `profileId`, **and the `profileId` must be a member of that `segmentId`** (it comes from that segment's member list — see the chain).
- **Personalization is supported ONLY with a valid segment and a member of it.** The recipient (`profileId`) comes solely from the chosen segment's member list, and must be a member of the `segmentId` passed to the render. If the segment has no members — or no segment exists in the content's data space — the personalization render **cannot be performed**: report `cannot personalize — no valid segment member` and stop. The unpersonalized preview (`contentKey` only) is still available; offer it. Never source the recipient from anywhere else (e.g. by listing individuals from the DMO) — a non-member `profileId` is rejected by the render with an opaque error.
- A **test send is a real send** to the supplied destinations — confirm the user asked for it and has provided their own destinations before firing any test send (the `send-test-…` steps). If the user asked only to preview, never fire a test send.
- **Check send permission before every test send.** Before firing any `send-test-<channel>`, call that channel's permission check (step `perm-can-send-test-<channel>` — a no-arg GET returning a Boolean). If it returns **false**, surface a permission error and **stop** — do not attempt the send. Preview never needs this check.
- **`profileId` is a Data Cloud profile key** (e.g. `a1b2c3d4…`), NOT a CRM id (`003…`) or a segment id (`1sg…`).
- Run the derivation yourself end to end via `sf api request rest`; don't hand the user raw commands to run.

## Derivation Chain (personalized preview / test send, from `contentKey`)

Detailed payloads for every step: [references/api-contract.md](references/api-contract.md).

1. **Fetch content** — `GET /services/data/vXX.0/connect/cms/contents/{contentKey}` (v57+) → `managedContentId`, `contentBody`. Use the CMS **Authoring** API (keyed by `contentKey`), not the delivery API — it returns the draft the preview renders.
2. **Recipient DMO (from content)** → `recipientDataModelObjectName`. Parse `contentBody['lightning:dataProviders']` for `objectApiName` (that is the DMO) or `dataGraphApiName` — for the latter, `GET /ssot/data-graphs/{dataGraphApiName}` (v58+) and read `primaryObjectName` (its response also returns `dataspaceName`, usable directly in step 3). If the content declares no data provider, leave the DMO unresolved for now — it comes from the org fallback in step 3, which needs the data space first.
3. **Data space** → `dataSpaceName` (scopes every `/ssot/…` call below). `GET /ssot/data-spaces` (v62+).
   - **DMO declared in step 2** — derive the data space from the DMO name: `ssot__…` prefix or an unrecognized name → `default`; a `<prefix>_` token → match against the `prefix` field and take that entry's `name`. `default` on single-space orgs.
   - **No DMO declared** — there's no name to match, so choose the data space first: `default` on a single-space org, otherwise ask the user which space. Then resolve the DMO from the org via the org-fallback lookup (step `messaging-selected-uma-dmo`, body `{ dataSpaceName }`). A `null` result means "no personalized preview available for this org" — report that, do NOT retry.
4. **Segment** → `GET /ssot/segments?dataspace=<name>` (v55+). Keep the `apiName` (fetches members) and the `1sg…` `marketSegmentId` (the `segmentId`).
5. **profileId** — from the chosen segment's members, the only valid source:
   - `GET /ssot/segments/{segmentApiName}/members?limit=10&dataspace=<name>` (v58+) → member `id`. That `id` **is** the `profileId`; because it's a member of the segment, the render accepts it.
   - **If the member list is empty (or no segment exists in the data space), stop — personalization cannot be performed.** There is no valid recipient: report `cannot personalize — no valid segment member` and offer the unpersonalized preview instead. Do **not** source the recipient elsewhere (e.g. by listing individuals from the DMO) — a `profileId` that isn't a member of the passed `segmentId` is rejected by the render with an opaque error.
6. **Render** — call the channel's personalized-preview operation (step `preview-<channel>-personalized`, or the `…-by-locale` variant) with the flat body `{ segmentId, recipientDataModelObjectName, contentKey, profileId, … }`.

**Unpersonalized** short-circuits after step 1: call the channel's unpersonalized-preview operation (step `preview-<channel>-unpersonalized`) with `{ contentKey }` (add `locale` for Email's `…-by-locale` variant).

**Test send** = the channel's permission check (step `perm-can-send-test-<channel>`; stop if false), then steps 1–6, then a sender lookup (Part 3 of the reference) for `fromAddress`/`senderId`, then the channel's test-send operation (step `send-test-<channel>`) with the user's supplied destination array.

## Reading the Rendered Output

- **Email** — flat object of string fields. Rendered HTML is in `body` for personalized calls, `nonAggregateHtmlBody` for unpersonalized — **read `body` first, fall back to `nonAggregateHtmlBody`**. Also surface `subject` and `preheader`.
- **SMS** — rendered text is the `content` string; MMS also carries `mediaUrl`.
- **WhatsApp** — returns `{ content, metadata }` as JSON strings; reassemble `{{k}}` slots from the fetched template (see the reference — this is the fiddly one).
- **Push / In-App / RCS** — read the returned rendered fields per channel.

> **Fetch media from the rendered `<img src>`, not the content definition.** Rendered srcs are public-CDN URLs (`…salesforce-experience.com/_scs/cms/…`) that fetch unauthenticated. `contentBody` `/cms/media/…` refs are session-gated — unauthenticated they return an HTML login page (HTTP 200, no error), not image bytes.

## Content Variables

If the content declares content variables under `sfdc_cms:schema.properties`, they render empty unless supplied. **Ask the user for a value for each — never invent one** — and pass them via `recipientAttributesJson` (a JSON string), on Email/SMS/WhatsApp/RCS only.

> **Push and In-App personalized previews do not support content variables.** If any are declared in the content definition (`sfdc_cms:schema.properties` non-empty) for one of those channels, stop and inform the user it's not supported — do not troubleshoot.

## High-Signal Gotchas

- **Wrong verb is rejected** — preview/send = POST + flat body; sender lookups = GET + `methodParams`.
- **`contentKey` is irreducible** — every path bottoms out at it; the user must supply it.
- **Data space must match the content**, or segments/profiles won't personalize correctly.
- **DMO may need the org fallback**; the org-fallback DMO lookup (`messaging-selected-uma-dmo`) returning `null` = "no personalized preview available," not a retryable error.
- **Recipient must be a segment member**: the `profileId` comes only from the chosen segment's member list and must be a member of the `segmentId` passed to the render. No members (or no segment) → personalization cannot be performed; stop and offer unpersonalized. Never source the recipient from a DMO listing — a non-member `profileId` is rejected with an opaque error.
- **Profile-key field**: segment members return the profile key as `id` (a Data Cloud key, e.g. `a1b2c3d4…` — not a `1sg…` segment id or a `003…` CRM id); that `id` is the `profileId`.
- **Version floors are per-resource** — LWR-Apex is not version-gated (pin `v68.0`; the path segment just needs to be well-formed); the REST derivation resources have per-resource minimums. Highest REST floor is data-spaces at **v62.0**, so target **v62.0+** for full six-channel coverage (lower channels work below that).

## Output Format

```text
Message: <contentKey>  (channel: <Email/SMS/WhatsApp/Push/In-App/RCS>)
Mode: <personalized preview / unpersonalized preview / test send>
Target org: <alias>
Derived inputs: dataSpace=<name> DMO=<…__dlm> segmentId=<1sg…> profileId=<profile key>
API calls: <method — verb — endpoint>  (one line each)
Rendered output:
  <subject / rendered text / HTML body, per channel>
Next step: <act / adjust inputs / follow-up>
```

## References

- [references/api-contract.md](references/api-contract.md) — full endpoint tables, request bodies, response-field rules, per-resource version floors, and the end-to-end recipe for all six channels.

<!-- skill-validate: ignore-start -->
<!-- codey:operations start -->
## Operations Reference

Operations this skill uses — routing and dependency reference.

| Operation | Purpose | Status | Call | Depends on |
|-----------|---------|--------|------|------------|
| `cms-content-fetch` | read | — | `GET /services/data/v63.0/connect/cms/contents/{contentKeyOrId}` | — |
| `messaging-selected-uma-dmo` | read | — | `POST lwr/apex/v68.0/interaction__MessagingController/getSelectedUnifiedIndividualDmoForUma` | `data-spaces-list` |
| `data-graph-primary-object` | read | — | `GET /services/data/v63.0/ssot/data-graphs/{dataGraphApiName}` | — |
| `data-spaces-list` | read | — | `GET /services/data/v63.0/ssot/data-spaces` | — |
| `dmo-describe` | read | — | `GET /services/data/v63.0/ssot/data-model-objects/{dmoName}` | — |
| `segments-list` | read | — | `GET /services/data/v63.0/ssot/segments` | `data-spaces-list` |
| `segment-members-list` | read | — | `GET /services/data/v63.0/ssot/segments/{segmentApiName}/members` | `segments-list` |
| `profile-fetch-by-id` | verify | — | `GET /services/data/v63.0/ssot/profile/{dmoName}/{profileId}` | — |
| `cms-spaces-list` | read | — | `GET /services/data/v63.0/connect/cms/spaces` | — |
| `preview-email-unpersonalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getEmailUnpersonalizedPreviewContent` | `cms-content-fetch` |
| `preview-email-unpersonalized-by-locale` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getEmailUnpersonalizedPreviewContentByLocale` | `cms-content-fetch` |
| `preview-email-personalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getEmailPersonalizedPreviewContent` | `cms-content-fetch`, `segments-list` |
| `preview-email-personalized-by-locale` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getEmailPersonalizedPreviewContentByLocale` | `cms-content-fetch`, `segments-list` |
| `preview-sms-unpersonalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getSmsUnpersonalizedPreviewContent` | `cms-content-fetch` |
| `preview-sms-personalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getSmsPersonalizedPreviewContent` | `cms-content-fetch`, `segments-list` |
| `preview-whatsapp-unpersonalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getWhatsappUnpersonalizedPreviewContent` | `cms-content-fetch` |
| `preview-whatsapp-personalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getWhatsappPersonalizedPreviewContent` | `cms-content-fetch`, `segments-list` |
| `preview-push-unpersonalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getPushUnpersonalizedPreviewContent` | `cms-content-fetch` |
| `preview-push-personalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getPushPersonalizedPreviewContent` | `cms-content-fetch`, `segments-list` |
| `preview-inapp-unpersonalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getInAppUnpersonalizedPreviewContent` | `cms-content-fetch` |
| `preview-inapp-personalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getInAppPersonalizedPreviewContent` | `cms-content-fetch`, `segments-list` |
| `preview-rcs-unpersonalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getRcsUnpersonalizedPreviewContent` | `cms-content-fetch` |
| `preview-rcs-personalized` | read | — | `POST lwr/apex/v68.0/interaction__JourneyController/getRcsPersonalizedPreviewContent` | `cms-content-fetch`, `segments-list` |
| `whatsapp-template-fetch` | read | — | `GET /headless/invoke/platform/conversation-setup/whats-app-templates/get-by-id` | — |
| `send-test-email` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestEmail` | `cms-content-fetch`, `segments-list`, `sender-email-from-addresses`, `perm-can-send-test-email` |
| `send-test-email-by-locale` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestEmailByLocale` | `cms-content-fetch`, `segments-list`, `sender-email-from-addresses`, `perm-can-send-test-email` |
| `send-test-sms` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestSms` | `cms-content-fetch`, `segments-list`, `sender-sms-codes`, `perm-can-send-test-sms` |
| `send-test-whatsapp` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestWhatsapp` | `cms-content-fetch`, `segments-list`, `sender-whatsapp-numbers`, `perm-can-send-test-whatsapp` |
| `send-test-push` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestPush` | `cms-content-fetch`, `segments-list`, `perm-can-send-test-push` |
| `send-test-inapp` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestInApp` | `cms-content-fetch`, `segments-list`, `perm-can-send-test-inapp` |
| `send-test-rcs` | write | — | `POST lwr/apex/v68.0/interaction__JourneyController/sendTestRcs` | `cms-content-fetch`, `segments-list`, `sender-rcs-agents`, `perm-can-send-test-rcs` |
| `sender-email-from-addresses` | read | — | `GET lwr/apex/v68.0/interaction__JourneyController/getFromAddresses` | — |
| `sender-email-dkim-valid` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/fromAddressHasValidDKIM` | `sender-email-from-addresses` |
| `sender-sms-codes` | read | — | `GET lwr/apex/v68.0/interaction__JourneyController/getSenderSmsCodes` | — |
| `sender-whatsapp-numbers` | read | — | `GET lwr/apex/v68.0/interaction__JourneyController/getSenderWhatsappNumbers` | — |
| `sender-whatsapp-waba-ids` | read | — | `GET lwr/apex/v68.0/interaction__JourneyController/getSenderWabaIdsAndNames` | — |
| `sender-rcs-agents` | read | — | `GET lwr/apex/v68.0/interaction__JourneyController/getSenderRcsAgents` | — |
| `perm-can-send-test-email` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/canUserSendTestEmail` | — |
| `perm-can-send-test-sms` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/canUserSendTestSms` | — |
| `perm-can-send-test-whatsapp` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/canUserSendTestWhatsapp` | — |
| `perm-can-send-test-push` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/canUserSendTestPush` | — |
| `perm-can-send-test-inapp` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/canUserSendTestInApp` | — |
| `perm-can-send-test-rcs` | verify | — | `GET lwr/apex/v68.0/interaction__JourneyController/canUserSendTestRcs` | — |
<!-- codey:operations end -->
<!-- skill-validate: ignore-end -->

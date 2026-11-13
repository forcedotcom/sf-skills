---
name: service-de-headless-channel-configure-gotchas
description: "Load when debugging unexpected orchestrator behavior — duplicate-key errors, resume/idempotency questions, preflight SOQL shape, or unattended/CI usage of the headless channel setup orchestrator. Covers the nine known gotchas: prereq ownership, MessagingPlatformKey uniqueness, resume-by-reinvocation, CSOT-only support, error-classification boundaries, prompt placement, platform-key mapping, wall-clock duration, and the two-query preflight. DO NOT load during a normal end-to-end run with no errors."
metadata:
  version: "1.0"
  related-skills: service-de-headless-channel-configure
---

# Gotchas

1. **Type-specific prereqs are owned by the insertion skill, not this orchestrator.** For WhatsApp, `service-de-channel-create` handles the WABA-linking prompt internally. For Line/Apple, `service-de-channel-create` is likewise responsible for its own credential-collection prereq, per the `MESSAGE_TYPE` it's given. This orchestrator stays type-agnostic — it doesn't know (or want to know) what a WABA is.

2. **Idempotency relies on `(MessagingPlatformKey, MessageType)` uniqueness.** The preflight query keys off the pair. If there are stale/deleted channels with the same key, SF should prevent duplicates on insert (DB uniqueness constraint on `(MessagePlatform, MessageType, MessagingPlatformKey)` for active rows). If insert fails with `DUPLICATE_VALUE` but preflight found no record, the backing MCU index is inconsistent — escalate to user.

3. **Resume is opt-in-by-reinvocation, not background.** The orchestrator doesn't store state files — it re-queries on each run. Keeps it simple.

4. **Step ordering assumes CSOT channels (Enhanced).** Legacy pre-CSOT channels used different activation paths (`activateWhatsAppNumber`, etc.). Not supported here.

5. **Don't catch transport/internal errors at this layer.** The leaf skills handle that — by the time a failure reaches this orchestrator, it's already classified into `ok:false, kind:"..."`. Just annotate which step failed.

6. **The orchestrator's prompts are limited to Stage 0 (type if omitted) and Stage 3 (routing choices).** Stages 2 and 4 are non-interactive. For fully-unattended mode (CI, cron), you need `{MESSAGE_TYPE}` supplied, and either (a) use an already-configured queue so Stage 3 no-ops, or (b) add a `--queue-id` override. Not built yet.

7. **Channel-agnostic preflight keys off `{PLATFORM_KEY}`, not the type-specific id name.** The SOQL filter is always `MessagingPlatformKey = '{PLATFORM_KEY}'`. Map the per-type input to `{PLATFORM_KEY}` once at Stage 0 rather than branching the SOQL — keeps Stage 1 one query, not three.

8. **Total duration is wall-clock, not sum-of-steps.** If the user pauses mid-prompt in Stage 0 or Stage 3, `totalDurationMs` includes think time. For perf analysis, care about the per-leaf `durationMs` values.

9. **Preflight uses two queries, not a subquery.** The `MessagingChannel` → `MessagingChannelUsage` child relationship is `MessagingChannelUsages` on some orgs (`test1`) but unnameable on others (`wadtesting` has `relationshipName: None` in `sf sobject describe`). Subqueries fail with `INVALID_TYPE` on the latter. FK-keyed second query (`MessagingChannelUsage WHERE MessagingChannelId = '{CHANNEL_ID}'`) works everywhere. Cost is one extra SOQL per preflight — negligible.

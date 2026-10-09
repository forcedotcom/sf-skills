# API notes — service-omni-presence-user-config-deploy

## Why one whole-record Metadata write

`PresenceUserConfig` has **cross-field validators** that make field-by-field editing fragile — the
correct combination only validates when the whole record is written together:

- `enableAutoAccept` is allowed only when `enableDecline=false`, and vice versa. They are mutually
  exclusive; this skill sets Auto-Accept **off** and Decline **on**.
- `enableDeclineReason=true` is permitted only when decline reasons are enabled (Decline on) and at
  least one `declineReasons` entry is present.
- `presenceStatusOnDecline` is available only when `enableDecline=true`.
- The ACW timer is paired: `hasAfterConvoWorkTimer=true` **requires** `afterConvoWorkMaxTime`
  (10–3600 s). Optional extension uses `hasAcwExtensionEnabled` + `acwExtensionDuration` +
  `maxExtensions` (not set by this skill).

Deploying the record as a single Metadata component applies all of these atomically.

## Required fields + XSD element order

`capacity` and `label` are required. Metadata API enforces element order; the emitted document
follows the schema sequence:

```text
acwExtensionDuration, afterConvoWorkMaxTime, assignments, capacity, declineReasons,
enableAutoAccept, enableDecline, enableDeclineReason, enableDisconnectSound, enableRequestSound,
hasAcwExtensionEnabled, hasAfterConvoWorkTimer, interruptibleCapacity, label, maxExtensions,
presenceStatusOnDecline, presenceStatusOnPushTimeout, userDisplayName
```

This skill emits: `afterConvoWorkMaxTime → assignments → capacity → declineReasons →
enableAutoAccept → enableDecline → enableDeclineReason → hasAfterConvoWorkTimer → label →
[presenceStatusOnDecline]` — all ascending in the sequence above.

## Decline reason packaging

`declineReasons` references a `PresenceDeclineReason` by its DeveloperName (fullName). The two
components are deployed in the **same package** so the reference resolves in one deploy; a
standalone config referencing a not-yet-deployed reason would fail. `PresenceDeclineReason` itself
carries only a `label`.

## Assignments

`assignments/users/user` takes **usernames**, not User Ids — the skill resolves any `005…` Ids to
usernames first. A redeploy declares the full assignment set for this config; the skill does not
remove users it did not add. The `<assignments>` block is omitted entirely when no agents are given
(a valid, unassigned config).

## Idempotency signal

Per-component `files[].state` from the Metadata API is authoritative: `Unchanged` → reused,
`Changed` → updated, `Created` → created. The deploy runs `--async` and polls
`sf project deploy report` to a terminal state; a job that never reaches one is reported as blocked
rather than assumed successful.

## Out of scope: channel-level ACW

The steel thread also mentions an After-Conversation-Work timer on the **Voice `ServiceChannel`**.
That is a different field on a different object (the channel, not the presence config) and is not set
here — this skill governs the agent-level presence/wrap-up behavior only.

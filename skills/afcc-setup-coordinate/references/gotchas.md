# afcc-setup-coordinate gotchas

Symptoms and resolutions seen while running the steps in `SKILL.md`.

| Issue | Resolution |
|---|---|
| `QueueRoutingConfig` create fails with "capacity field must be defined" | Always POST `CapacityWeight=1` and `RoutingPriority=1` together with `RoutingModel` |
| `404 NOT_FOUND` on `number-management/v1/numbers` | Almost always an API version pin bug — resolve org max version and retry at that version |
| `CommunicationChannelLine` not found right after procurement | Records propagate async — retry with backoff (sub-skill handles this) |
| `MessagingChannel` create fails with `INVALID_FIELD: ChannelLine` | Field is release-gated — drop it and rely on `MessagingPlatformKey` for the binding |
| `MessagingChannel` create fails with `FIELD_INTEGRITY_EXCEPTION: Communication Channel Line ID` | Salesforce validates `MessagingPlatformKey` against a Live `CommunicationChannelLine`. Do not proceed to Step 6 until `CodeStatus=Live`. |
| Number stays `Provisioning` or `Failed` after the 3-minute wait | On test/sandbox orgs carrier provisioning may not complete. Stop and tell the user (Step 5); the channel is not created on a non-live line. Re-running later reuses the procured number |
| `ChannelLine` vs `ChannelLineId` confusion | `ChannelLine` is the relationship name; `ChannelLineId` is the writable field on create |
| `MessageType=Phone` conflict | Only one `Phone`-type channel allowed per org — use `PstnVoice`, not `Phone` |
| `QueueRoutingConfig` has no `QueueId` field | Link the routing config to the queue AFTER queue creation via PATCH on `Group.QueueRoutingConfigId` |
| `QueueSobject` missing for VoiceCall | Create a `QueueSobject` record (`SobjectType=VoiceCall`, `QueueId=<id>`) BEFORE attaching routing config to the queue |
| `phoneNumberType` URL encoding | Toll Free must be URL-encoded as `Toll%20Free` in GET params — `TollFree` (no space) returns `BAD_REQUEST` |
| Step 1 fails with `LICENSE_LIMIT_EXCEEDED, content feature license limit exceeded` | The Service Cloud User feature-license seat is exhausted, not the user licenses. Reuse existing users (Step 1) |
| Number/channel calls fail for the executing admin | Assign `ContactCenterAdminNativeCCaaS` first (Step 4) |
| Presence-status access cannot be added to `ContactCenterAdminNativeCCaaS` | It is a license-bound standard set (not retrievable; `SetupEntityAccess` returns `INVALID_CROSS_REFERENCE_KEY`). Grant presence access through `Omni_Agent` |
| Profile deploy for the console app | Standard profile API names are `Admin` (System Administrator) and `Standard` (Standard User); a file with only `applicationVisibilities` is a partial update |
| Shell `USERNAME` env var conflict | `USERNAME` is a macOS env variable set to the system username. Never use `USERNAME=...` in scripts — use `NEW_USER` or `SF_NEW_USER` instead |

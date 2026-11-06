# AFCC Setup Report

## Run Details
- **Org Alias:** <alias>
- **Instance URL:** <instanceUrl>
- **Country:** <US|CA>
- **Number Type:** <Toll Free|10DLC>
- **Run Date:** <date>

## Steps

| Step | Artifact | Status | Id / Value |
|---|---|---|---|
| 1 | Agent users | ✔ / ⏭ SKIP | <user names> |
| 2 | Omni base settings | ✔ / ⏭ SKIP | — |
| 3 | Queue | ✔ / ⏭ SKIP | <name> (<Id>) |
|   | Routing config | ✔ / ⏭ SKIP | <DeveloperName> (<Id>) |
|   | Queue members | ✔ / ⏭ SKIP | <N> members assigned |
| 4 | Presence statuses | ✔ / ⏭ SKIP | <names> |
|   | Permission sets | ✔ / ⏭ SKIP | assigned to <N> users |
| 5 | Voice number | ✔ / ⏭ SKIP | <E.164 phone> |
|   | CommunicationChannelLine | ✔ | <Id> — CodeStatus: <Live|Provisioning> |
| 6 | MessagingChannel | ✔ / ⏭ SKIP | <Id> |
|   | DeveloperName | | <DeveloperName> |
|   | MessagingPlatformKey | | <E.164 phone> |
|   | SessionHandlerId | | <Queue Id> |
|   | IsActive | | true |

## Gaps / Deferred Verifications

<list any UI-only gaps or deferred steps — or "None">

## Outcome

`SUCCESS` or `FAILED at Step <N> — <exact error message>`

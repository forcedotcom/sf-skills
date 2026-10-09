# API notes — service-omni-command-center-analyze

## The three-dimensional V2 gate

Command Center for Service V2 renders only when **all** of the following hold, per the runtime
access check on the seeded page (`OmniChannel.userCanUseCommandCenterForServiceV2`):

```text
orgHasCommandCenterForServiceV2Enabled
    = release Gater
      AND CommandCenterForServiceV2 org preference
      AND NOT StandardOmniEOLExtension
AND UserPermissions.CommandCenterForServiceUser   (per user)
```

A single boolean cannot capture this, so the detector reports an explicit **state** across the
capability, preference/seed, and per-user permission dimensions.

## Why the preference is read via a proxy

The `CommandCenterForServiceV2` org preference is flipped only by an **internal** Setup
`SettingMutator` (`OmniChannelSettings.OrgPreferences.commandCenterForServiceV2`) and is **not**
exposed by the v66 Metadata API `OmniChannelSettings` (nor any other proven public write/read
surface). Its ON-flip, however, has an observable side effect: the platform seeds the
`CommandCenterForServiceV2_L` FlexiPage into a DB row and registers the V2 tab (idempotently). The
detector therefore treats the **seeded FlexiPage** as the proxy for "preference is ON":

- capability present + seed present ⇒ preference was enabled.
- capability present + seed absent ⇒ preference is off (`v2_available_not_enabled`).

This proxy is called out in the output; the detector does not claim to read the preference directly.

## Signals and queries

| Signal | Query | Notes |
|---|---|---|
| V2 capability | `SELECT Id FROM PermissionSet WHERE PermissionsCommandCenterForServiceUser = true LIMIT 1` | A `No such column`/`INVALID_FIELD` error ⇒ capability **absent** (org schema has no such user permission). Success ⇒ capability present. Any other error ⇒ `unknown` ⇒ `ambiguous`. |
| Seeded FlexiPage | Tooling: `SELECT Id FROM FlexiPage WHERE DeveloperName='CommandCenterForServiceV2_L'` | Presence ⇒ preference enabled + page seeded. Query error ⇒ `unknown` ⇒ `ambiguous`. |
| V2 tab | `SELECT Name FROM TabDefinition WHERE Name='standard-commandcenterforservicev2'` | Best-effort cross-check. Error ⇒ `"unknown"`; state falls back to capability + seed. |
| Supervisor permission | `SELECT Id FROM PermissionSetAssignment WHERE AssigneeId='…' AND PermissionSet.PermissionsCommandCenterForServiceUser = true` | Catches both permission-set and profile-granted permission (profiles surface as owned permission sets). Only run when a supervisor is supplied. |
| Legacy config | Tooling: `SELECT Id FROM OmniSupervisorConfig` | Informational count for the classic path. |

## Seed/tab consistency

The enable hook performs **two** side effects — tab registration and FlexiPage seed. A partial
failure can leave exactly one present. When both signals are known and disagree, the detector
returns `v2_seed_incomplete` (re-provision or apply the manual Setup step) rather than a misleading
`v2_ready`.

## Why `ambiguous` blocks

The review's rule is explicit: when a required signal cannot be read through a supported API, **block
and do not guess**. `ambiguous` is the only state that exits non-zero, so a coordinator will not
proceed to enable or configure on unproven state.

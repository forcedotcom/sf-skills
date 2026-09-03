# Known Non-Triggerable Standard Objects

Fast-path heuristic used by the Trigger section of `SKILL.md` to decide whether to stop
before authoring. It is not exhaustive: custom objects, managed-package objects, and
new/changed standard objects per release may not be listed here.

Common standard objects where Apex triggers are **not** supported:

- `LoginHistory`
- `SetupAuditTrail`
- `LoginGeo`
- `LoginIp`
- `AsyncApexJob`
- `ApexLog`
- `EventLogFile`
- `FieldHistoryArchive` / `__hd` big objects
- `AggregateResult`
- `UserRole` (limited/no trigger support historically — verify per org)
- `PermissionSetAssignment`-adjacent setup/audit objects generally
- all *Share objects
- all *History objects
- Most objects under Setup that are system-managed and read-only (audit, history, log objects)

If the target object isn't in one of these categories, proceed with authoring the trigger.

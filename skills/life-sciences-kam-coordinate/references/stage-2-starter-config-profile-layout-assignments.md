# Profile Layout Assignments Reference (KAM)

## Overview

After the KAM page layouts are deployed (Step 10), the skeleton profile files must be updated with `<layoutAssignments>` entries that map each deployed layout to its object and record types.

Both profile files under `.lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile/` must be updated:
- `LSC Custom Profile.profile-meta.xml`
- `Admin.profile-meta.xml`

## The Four KAM Layouts

For the KAM workflow, only these four layouts are offered and confirmed with the user (see `stage-2-starter-config-overview.md`, Step 10). Their object/record-type mappings:

| Layout File | Object | Record Type(s) |
|-------------|--------|----------------|
| Account-HCO Account Layout | Account | Health_Care_Organization |
| PersonAccount-Person Account HCP Layout | PersonAccount | Health_Care_Provider, PersonAccount |
| HealthcareProvider-Healthcare Provider Layout | HealthcareProvider | Health_Care_Organization, Health_Care_Provider |
| ActionPlan-Action Plan Layout | ActionPlan | — (no record types; profile default) |

## XML Format for layoutAssignments

Insert these entries directly, right before the closing `</Profile>` tag in each file. This is a mechanical edit driven by the Step 10 layout selection — do not show the block for review or ask the user to confirm the profile edit (see the Step 11 note in `overview.md`). Placement inside `<Profile>` is not order-sensitive; before `</Profile>` is always valid.

## Full layoutAssignments Block (all four KAM layouts)

If all four KAM layouts are deployed, add these entries to BOTH profiles:

```xml
<layoutAssignments>
    <layout>Account-HCO Account Layout</layout>
    <recordType>Account.Health_Care_Organization</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>PersonAccount-Person Account HCP Layout</layout>
    <recordType>PersonAccount.Health_Care_Provider</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>PersonAccount-Person Account HCP Layout</layout>
    <recordType>PersonAccount.PersonAccount</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>HealthcareProvider-Healthcare Provider Layout</layout>
    <recordType>HealthcareProvider.Health_Care_Organization</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>HealthcareProvider-Healthcare Provider Layout</layout>
    <recordType>HealthcareProvider.Health_Care_Provider</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>ActionPlan-Action Plan Layout</layout>
</layoutAssignments>
```

> The `ActionPlan-Action Plan Layout` entry has **no `<recordType>`** — ActionPlan is a standard object with no record types in the starter config, so the assignment sets the profile's default ActionPlan layout. A `<recordType>` child here would fail the profile deploy with an invalid-record-type error.

## Selective Assignment

If the user confirmed only a subset of the four layouts, include only the `<layoutAssignments>` entries for the confirmed layouts (all record-type entries for each). Before deploying, count the `<layoutAssignments>` blocks in each profile file against this reference for the deployed set — a missing assignment does not fail the deploy but silently leaves that object rendering the wrong layout for the profile.

## Deploy Updated Profiles

After adding layout assignments, deploy both profiles:
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile --target-org <org>
```

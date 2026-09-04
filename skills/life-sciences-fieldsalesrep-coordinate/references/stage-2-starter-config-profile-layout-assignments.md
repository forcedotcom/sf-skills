# Profile Layout Assignments Reference

## Overview

After page layouts are deployed (Step 10), the skeleton profile files must be updated with `<layoutAssignments>` entries that map each layout to its object and optionally a record type.

Both profile files under `.lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile/` must be updated:
- `LSC Custom Profile.profile-meta.xml`
- `Admin.profile-meta.xml`

## Layout-to-Object/RecordType Mapping

| Layout File | Object | Record Type (if applicable) |
|-------------|--------|---------------------------|
| Account-HCO Account Layout | Account | Health_Care_Organization |
| ActivityPlanTerritory-Activity Plan Territory Layout | ActivityPlanTerritory | — |
| Case-LSC Case Layout | Case | Medical_Info_Request, Medical_Inquiry, Question |
| CommSubscription-Communication Subscription Layout | CommSubscription | — |
| CommSubscriptionChannelType-Communication Subscription Channel Type Layout | CommSubscriptionChannelType | — |
| CommSubscriptionConsent-Communication Subscription Consent Layout | CommSubscriptionConsent | — |
| HealthcareProvider-Healthcare Provider Layout | HealthcareProvider | Health_Care_Organization, Health_Care_Provider |
| Inquiry-LSC Inquiry Layout | Inquiry | Adverse_Event, LSC_General, Medical_Inquiry |
| InquiryQuestion-LSC Inquiry Question Layout | InquiryQuestion | — |
| InquiryQuestionAnswer-LSC Inquiry Question Answer Layout | InquiryQuestionAnswer | — |
| PersonAccount-Person Account HCP Layout | PersonAccount | Health_Care_Provider, PersonAccount |
| ProviderVisit-LSC Provider Visit Layout | ProviderVisit | — |
| ProviderVisitProdDiscussion-Product Feedback | ProviderVisitProdDiscussion | Patient_Tracking, Product_Feedback |
| Visit-LSC Visit Layout | Visit | — |

## XML Format for layoutAssignments

Insert these entries directly, right before the closing `</Profile>` tag in each file. This is a mechanical edit driven by the Step 10 layout selection — do not show the block for review or ask the user to confirm the profile edit (see the Step 11 note in `overview.md`). Placement inside `<Profile>` is not order-sensitive; before `</Profile>` is always valid.

### Without Record Type

```xml
<layoutAssignments>
    <layout>Account-HCO Account Layout</layout>
</layoutAssignments>
```

### With Record Type

When a layout is assigned to specific record types, add one entry per record type:

```xml
<layoutAssignments>
    <layout>Case-LSC Case Layout</layout>
    <recordType>Case.Medical_Info_Request</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-LSC Case Layout</layout>
    <recordType>Case.Medical_Inquiry</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-LSC Case Layout</layout>
    <recordType>Case.Question</recordType>
</layoutAssignments>
```

## Full layoutAssignments Block (All Layouts)

If all layouts are selected, add these entries to both profiles:

```xml
<layoutAssignments>
    <layout>Account-HCO Account Layout</layout>
    <recordType>Account.Health_Care_Organization</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>ActivityPlanTerritory-Activity Plan Territory Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-LSC Case Layout</layout>
    <recordType>Case.Medical_Info_Request</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-LSC Case Layout</layout>
    <recordType>Case.Medical_Inquiry</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-LSC Case Layout</layout>
    <recordType>Case.Question</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>CommSubscription-Communication Subscription Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>CommSubscriptionChannelType-Communication Subscription Channel Type Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>CommSubscriptionConsent-Communication Subscription Consent Layout</layout>
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
    <layout>Inquiry-LSC Inquiry Layout</layout>
    <recordType>Inquiry.Adverse_Event</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Inquiry-LSC Inquiry Layout</layout>
    <recordType>Inquiry.LSC_General</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Inquiry-LSC Inquiry Layout</layout>
    <recordType>Inquiry.Medical_Inquiry</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>InquiryQuestion-LSC Inquiry Question Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>InquiryQuestionAnswer-LSC Inquiry Question Answer Layout</layout>
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
    <layout>ProviderVisit-LSC Provider Visit Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>ProviderVisitProdDiscussion-Product Feedback</layout>
    <recordType>ProviderVisitProdDiscussion.Patient_Tracking</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>ProviderVisitProdDiscussion-Product Feedback</layout>
    <recordType>ProviderVisitProdDiscussion.Product_Feedback</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Visit-LSC Visit Layout</layout>
</layoutAssignments>
```

## Selective Assignment

If the user selected only specific layouts, include only the `<layoutAssignments>` entries for those layouts. For example, if only "Inquiry-LSC Inquiry Layout" and "Visit-LSC Visit Layout" were selected:

```xml
<layoutAssignments>
    <layout>Inquiry-LSC Inquiry Layout</layout>
    <recordType>Inquiry.Adverse_Event</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Inquiry-LSC Inquiry Layout</layout>
    <recordType>Inquiry.LSC_General</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Inquiry-LSC Inquiry Layout</layout>
    <recordType>Inquiry.Medical_Inquiry</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Visit-LSC Visit Layout</layout>
</layoutAssignments>
```

## Deploy Updated Profiles

After adding layout assignments, deploy both profiles:
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile --target-org <org>
```

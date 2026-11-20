---
name: industries-patient-card-generate
description: "Build specification for the Health Cloud Patient Card Lightning Web Component: a single-card patient summary with a Provider (clinical) and a Payer (coverage) persona, header, member plan selector, allergy and communication pills, info row, and six expandable summary tiles, all driven by the UI API GraphQL wire adapter (lightning/graphql) with custom labels and Jest tests. Use when the user asks to \"build the Patient Card\", \"create a Health Cloud patient card component\", \"build a patient summary LWC\", or needs the Patient Card spec, deliverables, platform rules, styling values, or acceptance tests."
metadata:
  version: "1.0"
---

# Patient Card: Build Specification

> **Notice: Intended Use**
>
> This tool is intended to provide capabilities for Customers to configure and optimize use of their implemented Salesforce Services. Customers should ensure that their use of this tool meets their own use case needs and compliance requirements (including any applicable healthcare and privacy laws, rules, and regulation).

This document fully specifies a **Patient Card** Lightning Web Component for a Health Cloud org. It is written so that an AI coding assistant (or a developer) can build, test and deploy the component from scratch in a Salesforce DX project, using only public platform features.

> **For the AI assistant:** build everything in the **Deliverables** section and follow every rule in this document. Where this document doesn't decide something, choose the simplest option that fits the existing rules. When you finish, check your work against the **Acceptance tests** section.

---

## 1. What the card does

The Patient Card summarizes one patient on a single card. It has two **personas**, which an admin picks when placing the card:

- **Provider**: clinical view (appointments, encounters, allergies, care team).
- **Payer**: coverage view (plans, benefits, prior authorizations).

From top to bottom, the card shows:

1. **Header**: initials avatar, role, name, date of birth and age, phone, email, and address.
2. **Member plan selector**: the patient's member plans. The first plan is selected by default, and the user can switch plans.
3. **Patient pills**: allergies, then communication preferences (best time to contact, consents).
4. **Info row**: MRN, primary language, and the number of members on the selected plan.
5. **Show More / Show Less** toggle. When expanded, a **two-column grid of six summary tiles** appears. Which six depends on the persona:

| # | Provider persona | Payer persona |
| --- | --- | --- |
| 1 | Care Gaps | Coordination of Benefits |
| 2 | Primary Care | Pending Prior Auths |
| 3 | Next Appointment | Deductible |
| 4 | Recent Encounter | Out of Pocket Max |
| 5 | Allergies | Care Gaps |
| 6 | Preferred Pharmacy | Primary Care |

---

## 2. Deliverables

Build these in a Salesforce DX project, under `force-app/main/default/`:

- **Lightning Web Components** in the default `c` namespace:
  - One **exposed** root component, the Patient Card.
  - Private child components for the header, the member plan section, the pills, the plan details (info row, toggle and tiles), a reusable tile, a reusable pill list, and a shared utilities module (labels, constants, formatters).

  Pick clear camelCase names, for example `patientCard`, `patientCardHeader` and so on. Only the root component is exposed.
- **Custom labels** for every user-facing string (section 9), in `labels/CustomLabels.labels-meta.xml`.
- **Jest tests** for every component and the utilities, using `@salesforce/sfdx-lwc-jest` (section 12, `references/acceptance-tests.md`).
- No Apex. All data comes from the **UI API GraphQL wire adapter** (`lightning/graphql`).
- **API version 65.0** or later: set `sourceApiVersion` in `sfdx-project.json` and `apiVersion` in every component's `.js-meta.xml`. Earlier versions don't support `lightning/graphql` or some of the query syntax used here.
- **`.forceignore`** at the project root, listing `**/__tests__/**`, `**/jsconfig.json` and `**/.eslintrc.json`. Without it, the deploy uploads the Jest tests and fails with `LWC1702: Invalid LWC imported identifier "createElement"`.
- **Project tooling**: `package.json` with dev dependencies `@salesforce/sfdx-lwc-jest`, `@salesforce/wire-service-jest-util` and `@sa11y/jest`, and a `test` script that runs `sfdx-lwc-jest`.

---

## 3. Platform rules

- **Data access**: read all data with `@wire(graphql, { query: gql\`...\`, variables: '$someGetter' })`.
  - Give each data area its own query, so that a missing permission or a failed query only empties that one area. Never fail the whole card.
  - The GraphQL API enforces the running user's object and field access; don't add any other access checks.
- **Inactive wires**: when a getter used as `variables` returns `undefined`, its wire doesn't run. Use this to skip queries that the current persona doesn't need, or that are missing an input such as a selected plan.
- **Stale data**: when variables become `undefined`, the wire does **not** emit again, so the old data stays in component state. Whenever the input that drives a wire changes (the patient or the selected plan), reset the related state in the `@api` setter. The previous patient's or plan's data must never show while the new data loads.
- **Response handling**: wire handlers receive `{ data, errors }`. Treat a response with no data as "no records" and show the empty state. Read records through one helper that returns `data?.uiapi?.query?.<Object>?.edges?.map(e => e.node) || []`.
- **Field values**: for display, use `displayValue`, falling back to `value`.
- **Styling**:
  - Use fixed values, not SLDS global styling hooks (`--slds-g-*`). The org's theme sets those hooks, and SLDS 1 and SLDS 2 (Cosmos) orgs give them different values, so the same CSS can look completely different (for example, a light tint can become solid brand blue). Section 10 lists every value.
  - Use logical CSS properties (`padding-inline`, `border-inline-start`, `text-align: start`) so the card also works right-to-left.
  - Don't override base component internals.
- **Localization**:
  - Format dates, times and currency with `Intl` using `@salesforce/i18n/locale` and `@salesforce/i18n/currency`.
  - All text comes from custom labels. Labels with placeholders use `{0}`, `{1}`, … and are filled by a small `formatLabel(label, ...args)` helper.

---

## 4. Configuration (root component meta)

- **Targets**:
  - `lightning__RecordPage`, restricted to the `Account` object, with form factors Large and Small.
  - `lightningCommunity__Page` and `lightningCommunity__Default` (Experience Cloud).
- **`persona`** property: String, datasource `Provider,Payer`, default `Provider`. Available on the record page and on Experience Cloud.
- **`patientId`** property: String, Experience Cloud only. The site sets it, for example to `{!recordId}`.
- **Target configs**:
  - The `lightning__RecordPage` targetConfig holds `objects` (Account), `supportedFormFactors` and `persona`.
  - The `lightningCommunity__Default` targetConfig holds `persona` and `patientId`.
- **Public property names**: don't name child component properties after native HTML attributes. Use `roleText`, not `role`, for the header role, and `heading`, not `title`, for the tile title. Otherwise the browser applies them to the host element (an ARIA role, or a tooltip).
- Give the root component a `masterLabel` ("Patient Card") and a `description`.
- **Patient resolution**: the patient ID is the explicit `patientId` when one is set, otherwise the record page's `recordId`. Implement both as `@api` setter/getter pairs, so a change to either one re-resolves the patient.
- **Persona fallback**: any persona value other than `Payer` is treated as `Provider`.
- When there's no patient ID, the card renders an empty card with no content and runs no queries.

---

## 5. Data model

The patient is a **person account**. The table lists the objects, fields and relationships the card reads; all of them are standard Health Cloud or platform objects.

| Area | Object | Filter | Fields |
| --- | --- | --- | --- |
| Header | Account | `Id = patient` | Name, PersonBirthdate, Phone, PersonMobilePhone, PersonEmail, PersonMailingStreet/City/State/PostalCode, BillingStreet/City/State/PostalCode |
| Pills: Individual | Account | `Id = patient` | PersonIndividualId, Phone, PersonMobilePhone |
| Pills: allergies | AllergyIntolerance | `PatientId = patient`, `Status = "Active"` and `VerificationStatus` not in (`"Refuted"`, `"Entered in error"`), first 20 | Code.Name, Severity |
| Pills: best time | ContactPointPhone | `ParentId = patient` and `BestTimeToContactStartTime != null`, ordered by IsPrimary DESC, first 20 | TelephoneNumber, BestTimeToContactStartTime, BestTimeToContactEndTime, BestTimeToContactTimezone |
| Pills: consents | ContactPointTypeConsent | `PartyId = patient's PersonIndividualId`, first 20 | EngagementChannelType.Name, PrivacyConsentStatus |
| Member plans | MemberPlan | `MemberId = patient`, ordered by PriorityOrder ASC (nulls last) then EffectiveFrom DESC, first 50 | Name, Status, GroupNumber, SubscriberId, PlanId, PrimarySecondaryTertiary, PriorityOrder, RelationshipToSubscriber, PrimaryCarePhysician, EffectiveFrom, EffectiveTo, Payer.Name |
| MRN | Identifier | `ParentRecordId = patient`, ordered by EffectiveDate DESC (nulls last), first 50 | IdValue, EndDate, IdType (a CodeSet; read its `Code` with an inline fragment `... on CodeSet { Code { value } }`) |
| Language | PersonLanguage | `IndividualId = patient`, ordered by Rank ASC (nulls last), first 1 | Language |
| Members | MemberPlan | `SubscriberId = selected plan's subscriber`, first 200 | Name, MemberId, PlanId |
| Care Gaps | CareGap | `AccountId = patient` and `Status = "Open"`, first 200 | Name |
| Care relations (Provider) | AccountContactRelation | `Contact.AccountId = patient`, first 200 | Roles, Account.Name |
| Next Appointment (Provider) | ServiceAppointment | `AccountId = patient`, `SchedStartTime >= now` and `StatusCategory` not in (`"Canceled"`, `"CannotComplete"`), ordered by SchedStartTime ASC, first 1 | SchedStartTime, AppointmentType, Status |
| Recent Encounter (Provider) | ClinicalEncounter | `PatientId = patient`, ordered by StartDate DESC, first 1 | StartDate, Status, DischargeDisposition.Name |
| Allergies tile (Provider) | AllergyIntolerance | `PatientId = patient`, `Status = "Active"` and `VerificationStatus` not in (`"Refuted"`, `"Entered in error"`), first 20 | Code.Name |
| Prior auths (Payer) | CareRequest, CareRequestItem | see section 7.4 in `references/values-and-rules.md` | |
| Benefits (Payer) | CoverageBenefit | `MemberPlanId = selected plan` and `IsActive = true`, first 1 | IndividualInNetworkDeductibleApplied/Limit, FamilyInNetworkDeductibleApplied/Limit, IndividualInNetworkOutofPocketApplied/Limit, PrimaryCareCopay |

**GraphQL notes:**
- Pass "now" as a `DateTime` variable, computed in JavaScript as `new Date().toISOString()`, and filter with `{SchedStartTime: {gte: {value: $now}}}`. Don't use a `TODAY` literal: it would match appointments that already happened earlier today.
- **Strings in queries use double quotes only.** GraphQL has no single-quoted strings. Every string inside a `gql` query (filter values, `ApiName`, `nin` lists, variable defaults) must be written as `"..."`, for example `{Code: {eq: "MR"}}`, `{Status: {nin: ["Canceled", "Approved"]}}` and `$patientId: ID = ""`. A single `'` anywhere in a query makes Lightning App Builder fail to load every component on the page, with `Syntax Error: Unexpected single quote character (')` from `loadComponentDefinitions`. The same applies to customer-supplied values pasted into a query.
  - If a query uses a JavaScript constant through `${...}`, interpolate only numbers (such as `first:` limits) or strings built with `JSON.stringify(value)`, which always produces double quotes. For a list: `STATUSES.map((s) => JSON.stringify(s)).join(", ")`. Never interpolate a raw string or wrap one in `'...'`.
- Declare ID variables as `$patientId: ID = ""`.
- `PersonLanguage.IndividualId` is a polymorphic lookup (Account, Contact or Individual), so filter it directly with the patient's account ID. Don't look up the Individual first.
- Select `Id` on every node; use it as the record key (for example the plan object's `id`).
- Combine several conditions with `where: {and: [{...}, {...}]}`. A "not null" filter is `{Field: {ne: null}}`.
- **Field shape**: each field is an object, for example `Name { value }` or `PersonBirthdate { value displayValue }`; ask for `displayValue` wherever you display it. Parent lookups nest: `Payer { Name { value } }`.
- **Relationship filters** nest the same way: `where: {Contact: {AccountId: {eq: $patientId}}}`.
- **Ordering with nulls**: `orderBy: {PriorityOrder: {order: ASC, nulls: LAST}, EffectiveFrom: {order: DESC}}`.
- **Value formats** in responses:
  - Date fields: `YYYY-MM-DD`. Parse the parts yourself; don't pass the string to `new Date()`, which can shift the day.
  - Time fields (`BestTimeToContactStartTime/EndTime`): a wall-clock time like `14:00:00.000Z`. Read the hours and minutes from the string, and build `new Date(Date.UTC(1970, 0, 1, h, m))` to format it.
  - DateTime fields: ISO 8601 in UTC; use `displayValue` for display.
  - Time zone (`BestTimeToContactTimezone`): an IANA zone ID such as `America/Los_Angeles`.
- **Child relationships** (for prior auths): `CareRequestItems(where: ..., orderBy: ..., first: 1) { edges { node { StatusReason { value } } } }` inside the `CareRequest` node.
- **Semi-join and anti-join** filters use `inq` and `ninq` with `ApiName` naming the child's lookup field to the parent, exactly as written in section 7.4.

---

## 6. Component behavior

Read `references/component-behavior.md` for how every part of the card behaves: root card, header, member plan section, patient pills, plan details and tiles. Build all of it.

## 7. Values and rules

Read `references/values-and-rules.md` for the exact values and rules: the info row (including MRN), shared tiles (Care Gaps, Primary Care), Provider tiles, and Payer tiles (including the pending prior authorization count and subtitle).

## 8. Formatting helpers

Put these in the shared utilities module and unit-test each one:

- **`formatLabel(label, ...args)`**: replaces `{n}` placeholders; null or undefined arguments leave the placeholder.
- **`joinParts(...parts)`**: joins the non-empty parts with ` · `.
- **`formatCurrency(amount)`**: user currency with no decimals, e.g. "$1,500". Returns undefined for null, undefined or NaN.
- **`formatDate(isoDate)`**: medium date in UTC, as described in 6.2 of `references/component-behavior.md`.
- **`ageFromBirthdate(isoDate, today)`**: whole years, as described in 6.2 of `references/component-behavior.md`.
- **`formatTimeRange(start, end)`** and **`timeZoneAbbreviation(zone)`**: as described in 6.4 of `references/component-behavior.md`.
- **`isSamePhoneNumber(a, b)`**: the number match described in 6.4.
- **`patientPhone(account)`**: mobile, otherwise phone.
- **`memberRoleLabel(relationship)`**: "Subscriber" for `Self`, "Dependent" for any other non-empty value, otherwise undefined.

---

## 9. Custom labels

Read `references/custom-labels.md` for the full list of custom labels (names and default text). Create every label in it in the project's `CustomLabels.labels-meta.xml`, and use only these labels for user-visible text.

## 10. Visual design

Read `references/visual-design.md` for all styling: card, header, member plan section, pills, info row, toggle and tile grid, tiles, and general rules, with exact SLDS token names and values. Use only the token values listed there.

## 11. Accessibility

- Use semantic structure: `<article>` for the card and tiles, `<h2>` for the name, `<h3>` for tile titles, and `<dl>` for the info row and contact details.
- Every interactive element is a native `<button type="button">` with an accessible name, and every button has a visible `:focus-visible` outline.
- The plan picker follows the disclosure pattern (6.3 in `references/component-behavior.md`): `aria-expanded`, `aria-controls`, `aria-current` on the selected option, Escape support, and focus returned to the toggle.
- Decorative icons and the avatar are hidden from assistive technology.
- Every component should pass an automated accessibility check (`@sa11y/jest` `toBeAccessible()`) in its Jest tests.

---

## 12. Acceptance tests

Read `references/acceptance-tests.md` for the acceptance tests to check your work against, and write Jest tests that cover every case in it.

## 13. Deploy and place

1. Deploy the `force-app` source directory to the target org using your normal Salesforce DX deployment workflow.
2. **Record page**: open a person account, choose **Edit Page**, and drag **Patient Card** from Custom components onto the page. Set **persona**, then save and activate.
3. **Experience Cloud**: in Experience Builder, add **Patient Card**. Set **patientId** (for example `{!recordId}`) and **persona**, then publish.
4. Give viewers read access (through a permission set) to the objects and fields in section 5. A missing permission only empties the related area.
5. Turn on **Contacts to Multiple Accounts** (Setup > Account Settings > "Allow users to relate a contact to multiple accounts"). Without it, `AccountContactRelation` doesn't exist. The provider Primary Care and Preferred Pharmacy tiles then stay empty, because their query fails with `Field 'AccountContactRelation' in type 'RecordQuery' is undefined`; the rest of the card still works.
6. If the org doesn't have them, add the `Primary Care Physician` and `Preferred Pharmacy` values to the `AccountContactRelation.Roles` picklist, or change the two role constants to roles you already use.
7. **Troubleshooting: App Builder shows `Syntax Error: Unexpected single quote character (')` ... `loadComponentDefinitions`** when you open Edit Page. A `gql` query contains a single-quoted string. Search the component's `.js` files for `'` between `` gql` `` and the closing backtick, change those strings to double quotes (see the GraphQL notes in section 5), run test 27, and deploy again.

---

## 14. Customization guidance

- **Add a tile**: add a query and a wire that skips itself when it isn't needed, add a label, and add a tile entry to the persona's tile list. Keep an even number of tiles per persona so the two-column grid has no gaps.
- **Change the business rules**: the final prior-auth statuses, the MRN identifier type code, the relationship roles, the plan ordering, and the record limits (`first:`) should each be defined once as a named constant or query argument, so they're easy to change. To exclude prior-auth items with a blank status, add `{Status: {ne: null}}` next to each status filter.
- **Add a persona**: add it to the persona constant and the meta datasource, extend the persona fallback, and add a tile list for it.
- **Restyle**: change the values in each component's CSS. To follow the org's theme instead of the fixed design, swap the fixed values for SLDS global styling hooks, and check the result on both SLDS 1 and SLDS 2 orgs.
- **Translate**: use Translation Workbench for the `PatientCard_*` labels.

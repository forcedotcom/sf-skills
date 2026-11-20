## 7. Values and rules

### 7.1 Info row

- **MRN**: the first identifier that is active and has `IdType.Code = "MR"`. Active means the `EndDate` is empty or later than now (a DateTime field), and the `EffectiveDate` is empty or not later than now.
- **Language**: the display value of the top-ranked PersonLanguage.
- **Members**: the number of people on the selected plan.
  - No plan: "—".
  - Subscriber: the plan's `SubscriberId`, or the patient when `RelationshipToSubscriber` is `Self`. With no subscriber, the count is 1.
  - Otherwise, take the subscriber's MemberPlans that are on the **same plan**: the same `PlanId`, or the same plan name when the selected plan has no `PlanId`. Count the distinct `MemberId`s plus the patient. Ignore blank `MemberId`s.

### 7.2 Shared tiles

- **Care Gaps** (`utility:warning`): value "{0} open" with the count, and subtitle the names joined with " · ". Warning variant when the count is above 0. Empty when there are none.
- **Primary Care** (`utility:user`):
  - Provider: the name of the account related to the patient with the role `Primary Care Physician`. `Roles` is a `;`-separated multi-select.
  - Payer: the selected plan's `PrimaryCarePhysician`.

  For role matching, split the raw `Roles` value (not `displayValue`) on `;`, trim each entry, and compare exactly. For example, "Primary Care Physician Assistant" does not match.

  Provider never falls back to the plan's PCP.

### 7.3 Provider tiles

- **Next Appointment** (`utility:event`): the appointment's start date and time (display value). Subtitle: appointment type · status.
- **Recent Encounter** (`utility:clock`): the encounter's start (display value). Subtitle: status · discharge disposition name.
- **Allergies** (`utility:alert`): the first allergy's code name. Subtitle "+{0} more" when there are others.
- **Preferred Pharmacy** (`utility:store`): the name of the account related to the patient with the role `Preferred Pharmacy`.

### 7.4 Payer tiles

- **Coordination of Benefits** (`utility:shield`): the plan's priority (PrimarySecondaryTertiary). Subtitle "Priority order {0}" when `PriorityOrder` is set.
- **Pending Prior Auths** (`utility:approval`):
  - **Pending** means a `CareRequest` for the member (`MemberId = patient`) that either:
    - has at least one `CareRequestItem` whose `Status` is **not** a final status, or
    - has no `CareRequestItem` at all.
  - **Final statuses** (picklist API values, not labels): `Certified in Total`, `Certified - Partial`, `Not Certified`, `Canceled`, `Complete`, `No Action Required`, `Term Expired`. Note the single L in `Canceled`. Check the values in your org (Object Manager > Care Request Item > Status); a misspelled value silently counts those items as pending.
  - Items with a blank status count as **not final**. GraphQL `nin` includes nulls, so a plain `nin` filter does this automatically.
  - Do the filtering **in the query**, so the count is exact. Use one GraphQL request with two aliased `CareRequest` queries, each with `totalCount`, ordered by CreatedDate DESC, first 1:
    - `pendingRequests`: semi-join `{Id: {inq: {CareRequestItem: {Status: {nin: [...final]}}, ApiName: "CareRequestId"}}}`. It includes a child `CareRequestItems` subquery with the same status filter, ordered by StatusReason ASC (nulls last), first 1, returning `StatusReason`.
    - `requestsWithoutItems`: anti-join `{Id: {ninq: {CareRequestItem: {}, ApiName: "CareRequestId"}}}`.
  - **Value**: "{0} pending", where the count is the sum of both `totalCount`s. Warning variant when the count is above 0.
  - **Subtitle**: the `StatusReason` of the newest pending request's undecided item, shown only when the newest pending request overall has items. Select `CreatedDate` on both aliases. Show the reason when `requestsWithoutItems` has no records, or when the newest `pendingRequests` record's `CreatedDate` is later than the newest `requestsWithoutItems` record's. (The two aliases never return the same record, so do not test for equal dates.) No subtitle when the count is 0.
- **Deductible** (`utility:money`):
  - Value "{0} / {1}": individual in-network deductible applied / limit. Show it only when both amounts are present.
  - Subtitle joins, with " · ":
    - "Family {0}", where `{0}` is the family applied / limit
    - "PCP copay {0}"
- **Out of Pocket Max** (`utility:money`): value "{0} / {1}" for the individual in-network out-of-pocket applied / limit. Subtitle "{0}% met", the rounded percentage, shown only when the limit is above 0.

---

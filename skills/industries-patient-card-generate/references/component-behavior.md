## 6. Component behavior

### 6.1 Root card

- Renders an `<article>` with an `aria-label` from the card title label. The article contains the header and, below a divider, the member plan section.
- Owns the **expanded** state, which is collapsed by default. It flips when the plan details fire a `detailstoggle` event; the card stops that event's propagation.
- **Persists the expanded state per patient** in `sessionStorage` under the key `patientCard.expanded.<patientId>`, so it survives a page refresh. Wrap storage access in `try/catch`; if storage is unavailable, the state just isn't persisted.
- When the resolved patient changes:
  - Clear the selected plan.
  - Re-read the expanded state for the new patient.
- Listens for `planselect` (`detail: { plan }`) from the member plan section and keeps the selected plan. It uses that plan only to compute the header's role.
- **Header role**:
  - Provider persona: "Patient".
  - Payer persona: "Subscriber" when the selected plan's `RelationshipToSubscriber` is `Self`, and "Dependent" for any other non-empty relationship. "Member" when there is no plan or no relationship.

### 6.2 Header

- When the `patientId` input changes:
  - Clear the shown account.
  - Show a small spinner until the Account query responds.
  - If the response has no record, or only errors, render nothing.
- **Avatar**: a circle showing the initials of the first and last words of the name, uppercase. One word gives one initial. Mark the avatar `aria-hidden`.
- **Role** line (small, brand color), then the **name** as an `<h2>`.
- **Demographics**: the birthdate as a medium date in the user's locale, e.g. "May 12, 1991", then "Age {0}", joined with " · ".
  - Format the date with `timeZone: 'UTC'`, so the date never shifts by a day.
  - Age is whole years, one less if this year's birthday hasn't happened yet. Omit negative ages.
- **Contact details**: a `<dl>` with visually hidden `<dt>` labels (Phone, Email, Address) and visible values, in this order:
  - Phone: the mobile phone, otherwise the account phone.
  - Email.
  - Street.
  - City line, built as `City, ST 12345`.

  Omit empty rows. Use the mailing address; when both the mailing street and the mailing city line are empty, use the billing address.

### 6.3 Member plan section

- When the `patientId` input changes, clear the plans, the selection and the loaded flag, close the plan list, and show a spinner until plans load.
- When the query responds (data or errors), map the plans and set `loaded`.
  - If the selected plan isn't among the results, select the first plan (or none) and fire `planselect` with the plan object, or `undefined`.
  - Also fire `planselect` whenever the user picks a plan.
- **Plan header**:
  - a shield icon in a rounded chip
  - the "Member Plan" label
  - the selected plan's name, or "No member plans"
  - a subtitle: role on the plan ("Subscriber" for `Self`, otherwise "Dependent"), the payer name, and the years (`2026–2026` from EffectiveFrom and EffectiveTo, or just the start year), joined with " · "
- **Plan picker** (only when there are plans): a round icon button (down chevron) with `aria-label` and `title` "Select member plan", `aria-expanded`, and `aria-controls` pointing to the list.
  - It opens an absolutely positioned list of plan buttons, each showing the name and the subtitle. The selected plan has `aria-current="true"` and a highlighted background.
  - Choosing a plan selects it, closes the list and returns focus to the toggle.
  - **Escape** closes the list and returns focus to the toggle; stop the Escape event's propagation.
  - Moving focus outside the plan header also closes the list. Only close it when `relatedTarget` is set and outside the header. A null `relatedTarget` happens in Safari when a button is clicked, and closing then would swallow the click.
- Below the header, render the **pills** and then the **plan details**. Pass the patient ID, persona, selected plan and expanded flag down to them. Plan details still render with no plan.
- **Plan object** passed down: `{ id, name, status, groupNumber, subscriberId, planId, priority (PrimarySecondaryTertiary display value), priorityOrder, primaryCarePhysician, relationshipToSubscriber, effectiveFrom, effectiveTo, payerName }`.

### 6.4 Patient pills

There are two rows of pills, and each row renders only when it has pills. Each row is a `<ul>` with an `aria-label` ("Allergies" or "Communication preferences").

- **Allergies** (danger variant): one pill per allergy that has a code name, labeled "Name (Severity)", or just the name when there's no severity.
- **Best time to contact** (neutral variant): at most one pill, and only for the `ContactPointPhone` whose number matches the phone shown in the header. Read that phone from the Individual query: mobile, otherwise phone.
  - **Number match**: compare digits only. The shorter digit string must be at least 7 digits, the longer one must end with it, and the lengths can differ by at most 3. This allows a country code.
  - **Label**: "Best {0} {1}", where `{0}` is the start–end time range and `{1}` is the time zone's short generic name.
    - Format the range with `Intl.DateTimeFormat(...).formatRange`, using UTC wall-clock dates, e.g. "2 – 6 PM". Show minutes only when either time has non-zero minutes.
    - Get the time zone name with `timeZoneName: 'shortGeneric'`, e.g. "PT". Fall back to the zone ID if formatting fails.
    - Trim the result.
- **Consents**: one pill per consent whose `PrivacyConsentStatus` is `OptIn` or `OptOut` and that has an engagement channel type name.
  - `OptIn`: "{0} Opt-In", success variant.
  - `OptOut`: "{0} Opt-Out", neutral variant.

  Load consents only after the Individual ID is known.
- **Pill appearance**: a rounded pill with a small dot in the current text color and the text in a semibold small font.
  - Danger: error colors.
  - Success: success colors.
  - Neutral: neutral grays.
  - An unknown variant is shown as neutral.

### 6.5 Plan details

- When the `plan` input changes to a plan with a different `id`, clear the benefit (deductible and out-of-pocket) data right away.
- **Info row**: a `<dl>` with three items: MRN, Language and Members. Each item shows its value above its label, with a vertical divider between items (no divider before the first). Missing values show "—".
- **Toggle**: a centered base-variant `lightning-button` ("Show More" or "Show Less") with `aria-expanded`. It sits above a top border and fires `detailstoggle` (`bubbles: true, composed: true`).
- **Tiles**: rendered only when expanded, in a two-column grid. Each tile receives `iconName`, `heading`, `value`, `subtitle` and `variant`, plus the empty text "No data available".
- **Wires that skip themselves**:
  - Payer-only queries (prior auths, benefits) don't run for Provider.
  - Provider-only queries (appointment, encounter, allergies, care relations) don't run for Payer.
  - The benefits query also needs a selected plan, and the members query needs a subscriber.

### 6.6 Tile

A tile is an `<article>` with:
- a header: an icon in a small rounded chip, and an `<h3>` title
- the value (large and bold) with an optional subtitle; or, when the value is empty, the empty text in the subtitle style

The `warning` variant colors the value and the icon chip with warning colors; any other variant uses the default style. Tiles only display text: the parent formats every value.

---

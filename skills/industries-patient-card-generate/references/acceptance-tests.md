## 12. Acceptance tests

Write Jest tests that cover at least the following.

**Test setup:**
- Mock `lightning/graphql` with `createTestWireAdapter` from `@salesforce/wire-service-jest-util`, and export a `gql` tag that rebuilds the template string.
- Map the mock in `jest.config.js` (`moduleNameMapper: { '^lightning/graphql$': '<path to mock>' }`).
- `graphql.emit(response)` sends the same response to every graphql wire in a component, so a single fixture can include several objects.
- **Jest config**: build `jest.config.js` from `jestConfig` in `@salesforce/sfdx-lwc-jest/config`, and merge in `moduleNameMapper` and `setupFilesAfterEnv`. Put shared fixtures outside `__tests__` folders (for example `test-utils/fixtures.js`), so Jest doesn't run them as tests.
- **Accessibility matcher**: add a `jest.setup.js` that calls `registerSa11yMatcher()` from `@sa11y/jest`, and list it in `setupFilesAfterEnv` in `jest.config.js`.
  - `toBeAccessible()` refuses to run while fake timers are on. Call `jest.useRealTimers()` before checking accessibility.
- **Labels in tests**: sfdx-lwc-jest resolves every `@salesforce/label/c.X` import to the string `"c.X"`, not the label's value. So, by default, `LABELS.ageFormat` is `"c.PatientCard_ageFormat"`, which has no `{0}` for `formatLabel` to fill.
  - To test real text (e.g. "Age 34" or "2 pending"), give every label its real value once, in `jest.setup.js`: for each label in section 9, `jest.doMock('@salesforce/label/c.PatientCard_<name>', () => ({ default: '<value>' }), { virtual: true })`. Generate these calls from a name/value map.
- **`Intl` whitespace**: `Intl` output can contain narrow or thin no-break spaces (e.g. in "2 – 6 PM"). Normalize with `.replace(/\s/g, ' ')` before comparing strings.
- **Skipped wires in tests**: the mock's `emit()` also reaches wires whose variables are `undefined`. So test that a wire is skipped by checking its configuration (`graphql.getLastConfig()`), or by recording the queries the `gql` mock builds, not by checking that no data arrives.
- **Locale and currency**: in Jest, `@salesforce/i18n/locale` is `en-US` and `@salesforce/i18n/currency` is `USD`. Expected strings such as "May 12, 1991" and "$1,500" assume those values.
- **Async rendering**: after `emit()` or after changing a property, await a flush (`await Promise.resolve()`, or a `setTimeout(0)` promise) before asserting.
- **Dates in tests**: for anything that depends on "today" (age, next appointment), use `jest.useFakeTimers().setSystemTime(...)`, or pass `today` explicitly to the helper.

### Root card
1. It renders the header and the plan section, collapsed by default.
2. Clicking Show More expands the card and writes `true` to sessionStorage for that patient; clicking again collapses it and writes `false`.
3. An expanded state already stored for the patient is restored on load.
4. Payer persona: the header role follows the selected plan (Subscriber or Dependent), and is "Member" with no plan.
5. An explicit `patientId` wins over `recordId`. An unknown persona falls back to Provider.
6. A `recordId` change is followed while no explicit `patientId` is set.
7. Changing the patient clears the selected plan and reads the new patient's expanded state.

### Header
8. It shows the name, initials, the "May 12, 1991 · Age N" line, the mobile phone, the email and the mailing address.
9. It falls back to the account phone and the billing address.
10. It shows a spinner while loading. On a new patient it hides the previous patient right away. It renders nothing on an empty or error response.

### Member plan section
11. It selects the first plan and fires `planselect`. The picker opens, the selected option has `aria-current`, choosing another plan updates the details and fires `planselect`, and the list closes.
12. Escape closes the list.
13. A patient change shows the spinner, removes the old plan details and pills, then renders the new plans.
14. When member plans fail to load, it shows "No member plans" with no picker, and the plan details still render without a plan.

### Pills
15. It shows allergy pills with severity, the best-time pill only for the matching phone, and opt-in and opt-out pills with the right variants.
16. It skips consents that aren't OptIn or OptOut, or have no channel. Each row is hidden when empty.

### Plan details
17. Collapsed: the info row shows the active MRN (skipping ended MRNs and other ID types), the language and the members count, with Show More and no tiles.
18. Members counts only the selected plan's members, and is 1 when there is no known subscriber.
19. Provider expanded: all six provider tiles have the expected values and subtitles. The PCP and the pharmacy come only from relation roles.
20. Payer expanded: the Coordination of Benefits values and subtitle (no subtitle without a priority order), "2 pending" with the reason and the warning variant, the deductible and family and copay subtitle, the out-of-pocket value and percentage met, and the plan's PCP.
21. Switching plans clears the deductible and out-of-pocket values until the new benefit arrives.
22. Prior auths:
    - The count is the sum of both `totalCount`s, not the returned rows.
    - There's no reason when the newest pending request has no items, or when its item has no reason.
    - With zero pending, the tile is empty and the variant is default.
23. Error or empty responses show empty tiles and "—" in the info row.

### Tile, pill list and utilities
24. Tile: shows the value and subtitle, or the empty text when there's no value; the warning variant classes apply.
25. Pill list: renders the pills with variant classes, falls back to neutral for unknown variants, and renders nothing for an empty list.
26. Utilities: each helper in section 8, including edge cases (null input, before or after the birthday, phone numbers with a country code, times with and without minutes).

### Queries
27. Every query is valid GraphQL text: have the `gql` mock record each query string it builds, import every component, and assert that no recorded query contains a `'` character. (The Jest mock doesn't parse queries, so without this test a single-quoted string passes every other test and only fails in the org.)

---

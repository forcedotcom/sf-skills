# Aura to LWC Conversion Completeness Checklist

You are a Salesforce principal architect. Your task is to help a developer verify whether their conversion of a Salesforce Aura component to a Lightning Web Component (LWC) is truly complete. This is a developer-focused self-checklist, not a platform evaluation or LLM-as-judge scenario. The goal is to provide confidence and clarity for the developer, not to benchmark platform performance.

## Instructions

1. **Review the Completeness Metrics:**
   For each of the following metrics, use the provided rating to assess the LWC conversion. For each metric, select one of the following qualitative ratings:

   - **Excellent**: Perfect or near-perfect match in understanding and detail
   - **Good**: Strong understanding with minor differences
   - **Satisfactory**: Adequate understanding with some notable differences
   - **Limited**: Basic understanding with significant gaps
   - **Poor**: Major misunderstandings or omissions
   - **Missing**: Issue completely overlooked or fatally misunderstood

2. **For Each Metric:**

   - State the metric and its description
   - Assign a rating (from the list above)
   - Provide a brief justification for the rating
   - Optionally, add one or two sentences explaining any gaps, strengths, or issues

3. **Checklist Output:**

   - Present your results as a list, not a table
   - For each metric, include:
     - Metric name
     - Description
     - Rating
     - Justification/comments

4. **Summary and Recommendations:**

   - At the end, summarize your overall confidence in the conversion's completeness
   - List specific, actionable recommendations to address any gaps or issues

5. **Context:**

   - The component name is: `{{componentName}}`
   - The Aura component file is: `{{componentName}}.cmp`
   - The LWC template file is: `{{componentName}}.html`
   - You have access to supporting files such as controllers, helpers, CSS, blueprints, Jest tests (in `__tests__`), and UTAM page objects (in `__utam__`).

6. **Important Notes:**
   - This checklist is a comprehensive aid for developers to verify their work, not a judge of platform performance.
   - The resulting ratings are confidence measures for the developer, not benchmarks.
   - Each metric could, in the future, have a more detailed, dedicated tool for finer-grained verification, but avoid duplicating existing tools unless a true gap is identified.
   - If you find that guidance is unclear or tools are not being applied consistently, note this as a potential process/tooling gap.

## Completeness Metrics and Scoring

- **Functional Parity**: Are all user-facing features, states, and flows from the Aura component present in the LWC?

  - _Excellent_: All features and flows are present and work as intended.
  - _Good_: Minor features or flows are missing or slightly altered.
  - _Satisfactory_: Most features are present, but some notable differences exist.
  - _Limited_: Several important features are missing or incomplete.
  - _Poor_: Major features are missing or broken.
  - _Missing_: No attempt at parity.

- **Event Handling**: Are all events (custom, platform, UI) handled equivalently in the LWC?

  - _Excellent_: All events are handled as in Aura.
  - _Good_: Minor event handling differences.
  - _Satisfactory_: Most events handled, some notable gaps.
  - _Limited_: Several events missing or mishandled.
  - _Poor_: Major event handling missing.
  - _Missing_: No event handling present.

- **Data Binding & State**: Are all data flows, attributes, and state transitions preserved and correctly mapped?

  - _Excellent_: All data/state flows are preserved and correct.
  - _Good_: Minor data/state differences.
  - _Satisfactory_: Most data/state flows present, some gaps.
  - _Limited_: Several data/state flows missing.
  - _Poor_: Major data/state issues.
  - _Missing_: No data/state mapping.

- **UI/UX Parity**: Is the user interface (including accessibility, responsiveness, and SLDS usage) equivalent?

  - _Excellent_: UI/UX matches or improves on Aura.
  - _Good_: Minor UI/UX differences.
  - _Satisfactory_: Most UI/UX present, some gaps.
  - _Limited_: Several UI/UX issues.
  - _Poor_: Major UI/UX issues.
  - _Missing_: No UI/UX parity.

- **Extensibility & Modularity**: Is the LWC designed for maintainability and future extension?

  - _Excellent_: Highly modular and extensible.
  - _Good_: Minor modularity/extensibility issues.
  - _Satisfactory_: Adequate, but some concerns.
  - _Limited_: Several modularity/extensibility issues.
  - _Poor_: Major issues.
  - _Missing_: Not modular/extensible.

- **Error Handling**: Are all error states and recovery actions present and clear in the LWC?

  - _Excellent_: All error handling present and clear.
  - _Good_: Minor error handling gaps.
  - _Satisfactory_: Most error handling present, some gaps.
  - _Limited_: Several error handling issues.
  - _Poor_: Major error handling missing.
  - _Missing_: No error handling.

- **Localization**: Are all labels/messages localized as in Aura?

  - _Excellent_: All localization present.
  - _Good_: Minor localization gaps.
  - _Satisfactory_: Most localization present, some gaps.
  - _Limited_: Several localization issues.
  - _Poor_: Major localization missing.
  - _Missing_: No localization.

- **Security & Access Control**: Are there any regressions in data access or exposure?

  - _Excellent_: No regressions, all controls present.
  - _Good_: Minor security/access gaps.
  - _Satisfactory_: Most controls present, some gaps.
  - _Limited_: Several security/access issues.
  - _Poor_: Major security/access issues.
  - _Missing_: No security/access controls.

- **Performance**: Is the LWC at least as performant, or improved, compared to Aura?

  - _Excellent_: Performance matches or improves on Aura.
  - _Good_: Minor performance differences.
  - _Satisfactory_: Most performance present, some gaps.
  - _Limited_: Several performance issues.
  - _Poor_: Major performance issues.
  - _Missing_: No performance consideration.

- **Salesforce Best Practices**: Does the LWC follow modern Salesforce LWC and SLDS guidelines?

  - _Excellent_: All best practices followed.
  - _Good_: Minor best practice gaps.
  - _Satisfactory_: Most best practices followed, some gaps.
  - _Limited_: Several best practice issues.
  - _Poor_: Major best practice issues.
  - _Missing_: No best practices followed.

- **Jest Test Coverage**: Are Jest unit tests present (usually in a `__tests__` folder) and do they cover key logic?

  - _Excellent_: Comprehensive test coverage.
  - _Good_: Minor test coverage gaps.
  - _Satisfactory_: Most key logic covered, some gaps.
  - _Limited_: Several test coverage issues.
  - _Poor_: Major test coverage missing.
  - _Missing_: No tests present.

- **UTAM Page Objects**: Are UTAM page objects generated (usually in a `__utam__` folder) for UI automation?
  - _Excellent_: Comprehensive UTAM coverage.
  - _Good_: Minor UTAM coverage gaps.
  - _Satisfactory_: Most key UI flows covered, some gaps.
  - _Limited_: Several UTAM coverage issues.
  - _Poor_: Major UTAM coverage missing.
  - _Missing_: No UTAM page objects present.

---

## Example Output Structure

```markdown
# Aura to LWC Conversion Completeness Checklist

- **Functional Parity**
  - Description: Are all user-facing features, states, and flows from the Aura component present in the LWC?
  - Rating: Good
  - Justification: All major features are present, but one minor flow is missing.
  - Comments: The save flow is slightly different, but overall parity is strong.

- **Event Handling**
  - Description: Are all events (custom, platform, UI) handled equivalently in the LWC?
  - Rating: Excellent
  - Justification: All events are handled as in Aura.

... (repeat for each metric)

# Summary

Overall, the conversion is strong, with only minor gaps in functional parity and localization. Confidence in completeness is high.

# Recommendations

- Address the missing flow in functional parity.
- Improve localization for error messages.
```

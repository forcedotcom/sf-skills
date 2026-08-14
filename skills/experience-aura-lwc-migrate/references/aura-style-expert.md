## 🎨 Style Expert Analysis Framework

### Analysis Focus

Analyze styling patterns, CSS architecture, and design token usage in the Aura component.

### Key Areas to Review

#### 1. CSS File Analysis

- Document all CSS classes and their purposes
- Identify SLDS (Salesforce Lightning Design System) usage patterns
- Note any custom CSS that may conflict with LWC styling
- Check for responsive design patterns and media queries

#### 2. Styling Token Usage

- Look for design token references and their usage
- Document theme customization patterns
- Identify brand-specific styling requirements
- Note any dynamic styling based on component state

#### 3. CSS Encapsulation Patterns

- Analyze CSS scoping and inheritance patterns
- Document any global CSS dependencies
- Identify component-specific styling isolation
- Note potential CSS conflicts or specificity issues

#### 4. Dynamic Styling

- Find any JavaScript-based style manipulation
- Document conditional styling based on component state
- Identify user preference or theme switching patterns
- Note any performance-critical styling operations

### Migration Considerations

- Aura CSS files become LWC CSS modules with different scoping
- SLDS usage patterns may need updates for LWC compatibility
- CSS custom properties and design tokens have different APIs
- Shadow DOM styling requires different approaches
- Global CSS access is more restricted in LWC

### Additional knowledge

#### Style Intent analysis

Your task is to look at the Aura Component definition, and make sure that the blueprint only describes the experiences a user may have with a component.
Developers often accidentially expose APIs that allow customization of styles or CSS classes.

Review Aura component above and fix its blueprint using following rules:

1. Look for the following patterns: an attribute name that suggests it may be used for passing styles or CSS class names.
2. For each match found, reason about the intent around the reference. Why is the style being provided and what is it used for in the component?
3. Review existing sections in the blueprint, and propose updates if necessary.

- If something appears in the 'styling' section already, verify it doesn't appear the data section.
- If something appears in both sections, the dataRequirements section should be updated to remove it.

* For each issue found, provide a separate, detailed report.
* Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

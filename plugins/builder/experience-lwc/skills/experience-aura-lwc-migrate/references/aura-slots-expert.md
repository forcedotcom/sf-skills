## 🎰 Slots Expert Analysis Framework

### Analysis Focus

Analyze component composition patterns, content projection, and child component integration in the Aura component.

### Key Areas to Review

#### 1. Aura Facet Analysis

- Look for `<aura:facet>` declarations and usage
- Document how facets are used for content projection
- Identify dynamic facet content and conditional rendering
- Note any nested facet patterns or complex compositions

#### 2. Body Content Patterns

- Analyze `{!v.body}` usage for content projection
- Document how child components are composed
- Identify conditional rendering of body content
- Note any iteration patterns over child elements

#### 3. Component Composition

- Find all child components and their content patterns
- Document how content is passed to child components
- Identify any wrapper or container component patterns
- Note any dynamic component creation or destruction

#### 4. Content Distribution

- Analyze how different content types are distributed
- Document named slots vs default content patterns
- Identify any content transformation or filtering
- Note accessibility considerations for content structure

### Migration Considerations

#### Default Slot Analysis

Your task is to identify a placeholder for an anonymous block of markup that translates into a default slot in LWC.
Named slots or other elements and attributes are not part of this analysis and will be covered separately.
In Aura an anonymous block of markup is injected using the expression "{!v.body}" or "{#v.body}".

Review Aura component above and fix its blueprint using following rules:

1. Every occurance of the expression "{!v.body}" or "{#v.body}" should be present as an element in the "contentRequirements" section.
2. If such element has already been added, do not add another one but update one that has been added by adding "default slot" in "what" section.
3. LWC components can have only one default slot, so it's crucial to include conditions under which this fragment is present in "what".

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Named Slot Analysis

In Aura, placeholders for blocks of markup are added by declaring attributes with type "Aura.Component" or "Aura.Component[]" for one or more component instances.
Such placeholders are similar to slots in LWC web components.

Review Aura component above and fix its blueprint using following rules:

1. Every `<aura:attribute>` with type "Aura.Component" or "Aura.Component[]" should be added as an element in the "contentRequirements" section.
2. Only elements for `<aura:attribute>` with type "Aura.Component" or "Aura.Component[]" can be added as part of this review. Ignore all other elements.
3. The "name" of the included element should be set to the name of the attribute.
4. The "what" of the included element should be set to "named slot inside <name of other existing item inside contentRequirements or root>".

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

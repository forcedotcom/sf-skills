## 🔍 Reference Expert Analysis

### Analysis Focus

Analyze the component for all external dependencies, static references, and component references that need to be addressed in the LWC migration.

### Key Areas to Review

#### Static Resources Analysis

Review Aura component above and fix its blueprint.
Your task is to make sure that the blueprint includes all references to static resources needed for the component to function, specifically labels, assets and resources.
The developer working on the LWC experience will need to know the value of those references when implementing the component based on the blueprint.
Follow these steps to identify and describe the references to global resources:

1. Look for the following patterns:
   - `$ContentAsset` for references to images, stylesheets, and JavaScript used as asset files.
   - `$Label` for labels from salesforce platform stored outside your code.
   - `$Resource` for references to static resources.
2. For each match found, reason about the intent around the reference. What resource is being referenced, why is it being referenced, and what is it used for in the component?
3. Review the blueprint and ensure each reference exists in the blueprint and is described thoroughly under the "staticReferences" section. Propose updates if necessary.
   - The blueprint should NEVER directly include the strings: `$ContentAsset`, `$Label`, or `$Resource`. Those are Aura-specific constructs and the blueprint should have no references to them. If you see these in the blueprint, replace it with the actual value and a description of the intent.

- Static resources identified must always be listed in the "staticReferences" section.
- The correct value of the static resource as described above must be specified in the suggestedAction.
- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Global Value Providers Analysis

Review Aura component above and fix its blueprint.
Your task is to make sure that the blueprint clearly describes where the component access global resources provided by the framework.
The developer working on the LWC experience will need to review these references and determine how to access them when implementing their component based on the blueprint.

Follow these steps to identify and describe the references to global resources:

1. Look for the following patterns:
   - `$Browser` for information about the browser form factor; additional information like the current user, the user id, whether the user is a guest or not, etc. This is often used for personalization and contextual data fetching.
   - `$Locale` for internationalization information about the current user's preferred lang, locale, etc. This is used to localize the component.
2. For each match found, reason about the intent around the reference. What is being referenced, why is it being referenced, and what is it used for in the component?
3. Review the blueprint and ensure each the intent of each reference exists in the blueprint and is described thoroughly. Propose updates if necessary.
   - The blueprint should NEVER directly include the strings: `$Browser`, or `$Locale`. If you see these in the blueprint, replace it with a description of the intent. Those are Aura-specific constructs and the blueprint should have no references to them.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Standard HTML Tags Reference Analysis

Review Aura component above and fix its blueprint.
Your task is to look at the Aura Component definition, and make sure that the blueprint clearly leverages generic terms or wording instead of standard HTML tags.

Follow these steps to identify and describe the references to standard HTML tags:

1. Find specific references to HTML element or tag name.
2. For each match found, reason about the intent around the reference. What resource is being referenced, why is it being referenced, and what is it used for in the component?
3. If anything in the blueprint directly references HTML tags then replace it with a description of the intent. Those are Aura-specific pattern and the blueprint should have no references to them.

Rules to follow:

1. div should be referenced as containers
2. <p> to be referenced paragraphs
3. <li> to be referenced as lists
4. <ol> to be referenced as ordered list
5. <ul> to be referenced as unordered list
6. <a> to be referenced as links
7. <img> to be referenced as images
8. <table> to be referenced as tables
9. <form> to be referenced as forms
10. <input> to be referenced as input fields

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### URL References Analysis

Review Aura component above and fix its blueprint.
Your task is to capture URLs based on their purpose and location (HTML or CSS) in the component, categorizing each in relevant blueprint sections (e.g., staticReferences, interactions) to aid in an accurate LWC implementation.

Follow these steps to document URL-based assets:

1. Locate URLs in Aura Component and CSS files:

- Component URLs: Expect to find static URLs throughout the component. Identify URLs in attributes like href (for navigation links) or src (for images and other assets).
- CSS URLs: Capture URLs within CSS properties (e.g., background-image) that link to static assets like images or custom fonts. These contribute significantly to the component's look, feel, and brand consistency.

2. Classify and Describe Each URL:

- Purpose: For each URL, determine its role within the component (e.g., providing navigation links, displaying assets, supporting branding, or contributing to the visual style).
- Categorize: Place each URL reference under the appropriate type (e.g., url, asset) in the staticReferences section of the blueprint.
- CSS-Specific URLs: Document any static URLs in the CSS as url types within staticReferences, with details on how they contribute to the component's visual presentation.

3. Rules for URL References:

- <a> should be described as "url", with preserved href URLs.
- CSS background images or font URLs should be referenced as "url" and include details about their visual contribution.

* Organize each URL reference based on its function under contentRequirements or interactions, grouping similar URLs to avoid redundancy.
* Be precise in documenting CSS-based URLs, as these contribute to design continuity and user experience.
* For each issue found, provide a separate, detailed report.
* Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Component References Analysis

Review Aura component above, and make sure that the blueprint is clearly stating the "unknowns", which is a list of references to other components that this experience depends on.
The developer writing the LWC experience will need to review those other components to fully understand what this experience is about it before implement it in LWC.

Follow these steps to identify and add potential unknowns:

1. Review the Aura component definition line by line looking for the following patterns:

   - `<aura:component extends="namespace:componentName" ...>` for the super component is defined
   - `<aura:component implements="namespace:interfaceName" ...>` for interfaces definitions
   - `<aura:handler event="namespace:eventName" ...>` for aura event dependencies
   - `<namespace:componentName ...>` for an aura component used by the aura component as a dependency.

2. For each match found, reasoning about a potential new "unknown" entry:

   - ref: The matched pattern in `namespace:exampleName` format from the patterns defined above
   - what: Brief description of the item's purpose or role
   - why: Explanation of why understanding this item is important for the component

3. Review the existing "unknowns" section in the blueprint, and propose updates if necessary based on the above patterns listed in step 1.

- Highlight areas that require further investigation to fully understand the component's behavior and dependencies. When in doubt, include it as an unknown.
- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems

#### Action Handler Analysis

Review Aura component above and fix its blueprint.
Follow these steps to identify usage of Aura.Action attribute types:

1. Review the Aura component definition line by line and identify the Aura.Action Attribute Type. An Aura.Action is a reference to an action in the framework.
   If a child component has an Aura.Action attribute, a parent component can pass in an action handler when it instantiates the child component in its markup.
   This pattern is a shortcut to pass a controller action from a parent component to a child component that it contains, and is used for on\* handlers, such as onclick.
2. For each match found, reason about the usage of the on\*handler within Aura.Action attribute.
3. Review each on\*handler with in Aura.Action attribute and propose a solution to leverage standard DOM events to fulfill the intended purpose and propose update to the blueprint.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

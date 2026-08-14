## 🔌 API Expert Analysis Framework

### Analysis Focus

Analyze all API integrations, server communication patterns, and external service interactions in the Aura component.

### Key Areas to Review

#### 1. Component API Surface

- Document all public properties (`@api` in LWC terms)
- Identify component methods exposed to parent components
- Note any component events that form the public API
- Check for API versioning or compatibility considerations

#### 2. Server Communication

- Document all server-side controller methods called
- Identify parameter patterns and return value structures
- Note error handling mechanisms for server calls
- Check for batch processing or bulk operations

#### 3. Lightning Data Service Integration

- Look for `force:recordData` or similar components
- Document CRUD operations and their patterns
- Identify record loading, saving, and deletion logic
- Note any optimistic UI patterns or caching

#### 4. Event-Driven Communication

- Find component events and their usage patterns
- Document event payloads and their structures
- Note parent-child communication mechanisms
- Check for event bubbling or propagation patterns

#### 5. External Service Integration

- Identify any external API calls or web service usage
- Document authentication mechanisms and security
- Note any third-party service dependencies
- Check for rate limiting or throttling requirements

### Migration Considerations

- Aura public attributes become LWC `@api` properties
- Component events need LWC CustomEvent equivalents
- Server communication moves to `@wire` services
- API surface design may need restructuring for LWC

### Additional knowledge

#### Component Events Analysis

Review Aura component above and fix its blueprint.
Follow these steps to identify and analyze the component events:

1. Review the Aura component code line by line looking for the following pattern:

   - `component.getEvent("eventName")` or any similar code where `.getEvent()` is called on the component. This creates an instance of the custom event.
   - `event.setParams()` or any similar code where `.setParams()` is called on the event. This sets the details payload of the event.
   - `event.fire()` or any similar code where `.fire()` is called on the event. This fires the event.
   - Any code using the event or modifying it.

2. For each match found:

   - Identify the name of the event and the content of its payload.
   - Identify the intent behind this event, when and why the component fires this event.
   - Summarize and describe when this event is fired, why it is fired, and what properties belong in its payload. What functionality is this event intended to provide?

3. Review the existing sections in the blueprint and analyze whether it comprehensively describes the intent of all identified events.
   - The blueprint should clearly and explicitly state that this is an event that the component fires.
   - The blueprint should describe what information is included with the event and summarize the intent behind each variable.
   - Propose updates if necessary.

It is possible that the Aura component fires no public events, in which case, the blueprint should not include anything about firing events.

Remember: the goal is to identify the public events in the component and make sure the blueprint identifies and describes the intent of those events.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Component Layout Analysis

Review Aura component above and fix its blueprint using following rules:

Things to pay attention to:

1. Does the aura component have a visual UI?
2. Which elements contribute to the visual UI of the component?
3. What user interactions are allowed by the component UI?
4. Does the blueprint fully describe what needs to be rendered for the component?
5. Does the blueprint fully describe the interactions that can be done on the component?

- For each issue found, provide a separate, detailed report.
- It is possible that the Aura component has no visual UI, in which case, return an empty list.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Methods Analysis

Review Aura component above and fix its blueprint.
Identify the public methods in the component and make sure the blueprint describes the intent of those methods.

1. Look for the following pattern:

   - `<aura:method ... >` for public methods

2. For each match found:

   - Find the corresponding controller function referenced by the `action="{!...}"` attribute.
   - Identify the intent of the function and what's supposed to happen when that function is called on the component.
   - If the function in the controller references any additional helper functions:
     - Find those functions and summarize their intents.
     - Include their intent as part of the description of the original function.

3. Review the existing sections in the blueprint and analyze whether it comprehensively describes the intent of all identified public methods.
   - If a method triggers a specific interaction, make sure that the interaction describes the method as the `trigger` that initiates the interaction.
   - Propose updates if necessary.

- For each issue found, provide a separate, detailed report.
- It is possible that the Aura component exposes no public methods, in which case, the blueprint should not include anything about public methods.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Public Properties Analysis

Review Aura component above and fix its blueprint using following rules:

1. Look for the following pattern:

   - `<aura:attribute ...>` for public attributes. Ignore all the matches where `access="private"`.

2. For each match found:

   - Identify the name, type, default value and validation rules for the attribute.
   - Summarize the intent behind the attribute and what the attribute is used for in the component.
     - Attributes can be used in multiple places. Make sure you identify and summarize the full intent, considering all uses of the attribute.
     - If an attribute has multiple intents, please identify each intent separately and succinctly.
     - Consider the default value of the attribute, the values that this attribute can accept given its type and validation rules if any.
     - Focus on the what and why the attribute is exposed publicly to describe the intent.

3. Review the sections in the blueprint and analyze whether the blueprint comprehensively describes the intent of all identified public attributes.
   - Does the blueprint include the type of the attribute?
   - Does the blueprint include the default value of the attribute?
   - Does the blueprint describe the type of the attribute and potential validation? Use JS primitive types in single quotes, e.g.: 'string', to denote the type.
   - If the attribute is an enum, does the blueprint describe all possible values assign to the attribute, use single quotes to list all possible values?
   - Does the blueprint summarize all instances where the attribute is used?
   - Does the blueprint correctly summarize the intents behind where the attribute is used?

- For each issue found, provide a separate, detailed report.
- It is possible that the Aura component exposes no public attributes, in which case, return an empty list.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### DOM Event Analysis

Identify attributes in Aura markup that:

1. declare action(s) or callback function(s)
2. have type "Object" or "Object[]". If the attribute does not have these types, do not include it in the list of issues.
3. referenced from controller, helper or renderer as an event, function or action.
   For every such attribute LWC component needs to fire custom DOM event(s) that will be handled by other components.

Review Aura component above and fix its blueprint using following rules:

1. Create a proper event and add it to the "componentCommunication" section.
2. In "name" property identify the name of the event.
3. In "what" property identify the intent behind this event and list all properties that belong in its payload.
4. In "why" property identify when this event is fired, why it is fired and how it should be processed.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
